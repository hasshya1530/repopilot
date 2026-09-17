from pathlib import Path

import pytest

from agents.implementer.applier.errors import (
    ChangeApplicationConflictError,
    ChangeApplicationValidationError,
)
from agents.implementer.applier.models import AppliedChangeStatus
from agents.implementer.applier.service import ChangeApplier
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)


def make_result(*changes: CodeChange) -> ImplementationResult:
    return ImplementationResult(
        summary="Test implementation.",
        changes=changes,
    )


def test_create_file(tmp_path: Path) -> None:
    applier = ChangeApplier(tmp_path)

    result = applier.apply(
        make_result(
            CodeChange(
                file_path="src/auth.py",
                operation=ChangeOperation.CREATE,
                content="def validate_token(token):\n    return bool(token)\n",
                reason="Add token validation.",
            )
        )
    )

    target = tmp_path / "src" / "auth.py"

    assert target.exists()
    assert target.read_text() == (
        "def validate_token(token):\n"
        "    return bool(token)\n"
    )
    assert result.files_changed == 1
    assert result.changes[0].status == AppliedChangeStatus.APPLIED


def test_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "auth.py"
    target.write_text("return False\n")

    applier = ChangeApplier(tmp_path)

    result = applier.apply(
        make_result(
            CodeChange(
                file_path="auth.py",
                operation=ChangeOperation.MODIFY,
                content="return True\n",
                reason="Fix validation.",
            )
        )
    )

    assert target.read_text() == "return True\n"
    assert "-return False" in result.changes[0].diff
    assert "+return True" in result.changes[0].diff


def test_delete_file(tmp_path: Path) -> None:
    target = tmp_path / "old.py"
    target.write_text("obsolete = True\n")

    applier = ChangeApplier(tmp_path)

    result = applier.apply(
        make_result(
            CodeChange(
                file_path="old.py",
                operation=ChangeOperation.DELETE,
                content="",
                reason="Remove obsolete code.",
            )
        )
    )

    assert not target.exists()
    assert result.files_changed == 1


def test_dry_run_does_not_modify_workspace(tmp_path: Path) -> None:
    target = tmp_path / "auth.py"
    target.write_text("return False\n")

    applier = ChangeApplier(tmp_path)

    result = applier.apply(
        make_result(
            CodeChange(
                file_path="auth.py",
                operation=ChangeOperation.MODIFY,
                content="return True\n",
                reason="Fix validation.",
            )
        ),
        dry_run=True,
    )

    assert target.read_text() == "return False\n"
    assert result.dry_run is True
    assert result.files_changed == 1
    assert "+return True" in result.changes[0].diff


def test_rejects_path_traversal(tmp_path: Path) -> None:
    applier = ChangeApplier(tmp_path)

    with pytest.raises(ChangeApplicationValidationError):
        applier.apply(
            make_result(
                CodeChange(
                    file_path="../outside.py",
                    operation=ChangeOperation.CREATE,
                    content="malicious = True\n",
                    reason="Invalid path.",
                )
            )
        )


def test_rejects_absolute_path(tmp_path: Path) -> None:
    applier = ChangeApplier(tmp_path)

    with pytest.raises(ChangeApplicationValidationError):
        applier.apply(
            make_result(
                CodeChange(
                    file_path="/tmp/outside.py",
                    operation=ChangeOperation.CREATE,
                    content="bad = True\n",
                    reason="Invalid path.",
                )
            )
        )


def test_rejects_create_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "auth.py"
    target.write_text("existing = True\n")

    applier = ChangeApplier(tmp_path)

    with pytest.raises(ChangeApplicationConflictError):
        applier.apply(
            make_result(
                CodeChange(
                    file_path="auth.py",
                    operation=ChangeOperation.CREATE,
                    content="new = True\n",
                    reason="Conflict test.",
                )
            )
        )


def test_rejects_modify_missing_file(tmp_path: Path) -> None:
    applier = ChangeApplier(tmp_path)

    with pytest.raises(ChangeApplicationConflictError):
        applier.apply(
            make_result(
                CodeChange(
                    file_path="missing.py",
                    operation=ChangeOperation.MODIFY,
                    content="value = True\n",
                    reason="Conflict test.",
                )
            )
        )


def test_rejects_delete_missing_file(tmp_path: Path) -> None:
    applier = ChangeApplier(tmp_path)

    with pytest.raises(ChangeApplicationConflictError):
        applier.apply(
            make_result(
                CodeChange(
                    file_path="missing.py",
                    operation=ChangeOperation.DELETE,
                    content="",
                    reason="Conflict test.",
                )
            )
        )
