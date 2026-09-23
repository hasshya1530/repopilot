from pathlib import Path

from agents.implementer.applier.models import (
    AppliedChange,
    AppliedChangeStatus,
    ChangeApplicationResult,
)
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from apps.api.app.services.implementation_artifacts import (
    _hash_content,
    _line_counts,
    capture_implementation_snapshots,
)


def test_hash_content_is_deterministic() -> None:
    first = _hash_content("hello\n")
    second = _hash_content("hello\n")

    assert first == second
    assert first is not None
    assert len(first) == 64


def test_hash_content_handles_none() -> None:
    assert _hash_content(None) is None


def test_line_counts() -> None:
    diff = (
        "--- before\n"
        "+++ after\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        "+another\n"
    )

    additions, deletions = _line_counts(diff)

    assert additions == 2
    assert deletions == 1


def test_capture_snapshots_for_existing_and_new_files(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing.py"
    existing.write_text(
        "def old():\n    return 1\n",
        encoding="utf-8",
    )

    implementation = ImplementationResult(
        summary="Update implementation.",
        changes=(
            CodeChange(
                file_path="existing.py",
                operation=ChangeOperation.MODIFY,
                content="def new():\n    return 2\n",
                reason="Update implementation.",
            ),
            CodeChange(
                file_path="new.py",
                operation=ChangeOperation.CREATE,
                content="print('hello')\n",
                reason="Add new module.",
            ),
        ),
    )

    snapshots = capture_implementation_snapshots(
        tmp_path,
        implementation,
    )

    assert snapshots["existing.py"].exists is True
    assert snapshots["existing.py"].content == (
        "def old():\n"
        "    return 1\n"
    )
    assert snapshots["existing.py"].content_hash is not None

    assert snapshots["new.py"].exists is False
    assert snapshots["new.py"].content is None
    assert snapshots["new.py"].content_hash is None


def test_change_application_result_contains_actual_changes() -> None:
    result = ChangeApplicationResult(
        changes=(
            AppliedChange(
                file_path="src/example.py",
                status=AppliedChangeStatus.APPLIED,
                operation="modify",
                diff="-old\n+new\n",
            ),
        ),
        files_changed=1,
        dry_run=False,
    )

    assert result.files_changed == 1
    assert result.dry_run is False
    assert result.changes[0].status == AppliedChangeStatus.APPLIED
    assert result.changes[0].file_path == "src/example.py"
