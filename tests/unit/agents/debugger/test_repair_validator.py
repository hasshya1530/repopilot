from agents.debugger.repair_models import RepairProposal
from agents.debugger.validator import (
    RepairValidationCode,
    RepairValidator,
)
from agents.implementer.models import ChangeOperation, CodeChange


def make_change(
    *,
    file_path: str = "src/service.py",
    operation: ChangeOperation = ChangeOperation.MODIFY,
    content: str = "updated\n",
) -> CodeChange:
    return CodeChange(
        file_path=file_path,
        operation=operation,
        content=content,
        reason="Repair failing behavior.",
    )


def make_proposal(
    *changes: CodeChange,
    diagnosis: str = "Fix the failing behavior.",
) -> RepairProposal:
    return RepairProposal(
        diagnosis=diagnosis,
        changes=changes,
    )


def test_accepts_valid_modify_repair() -> None:
    result = RepairValidator().validate(
        make_proposal(make_change()),
    )

    assert result.valid is True
    assert result.issues == ()


def test_accepts_valid_create_repair() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(
                file_path="tests/test_service.py",
                operation=ChangeOperation.CREATE,
                content="def test_service():\n    assert True\n",
            ),
        ),
    )

    assert result.valid is True


def test_accepts_valid_delete_repair() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(
                file_path="obsolete.py",
                operation=ChangeOperation.DELETE,
                content="",
            ),
        ),
    )

    assert result.valid is True


def test_rejects_empty_diagnosis() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(),
            diagnosis="   ",
        ),
    )

    assert result.valid is False
    assert any(
        issue.code == RepairValidationCode.EMPTY_DIAGNOSIS
        for issue in result.issues
    )


def test_rejects_empty_repair() -> None:
    result = RepairValidator().validate(
        make_proposal(),
    )

    assert result.valid is False
    assert any(
        issue.code == RepairValidationCode.EMPTY_REPAIR
        for issue in result.issues
    )


def test_rejects_absolute_path() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(file_path="/tmp/evil.py"),
        ),
    )

    assert result.valid is False
    assert any(
        issue.code == RepairValidationCode.INVALID_PATH
        for issue in result.issues
    )


def test_rejects_path_traversal() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(file_path="../outside.py"),
        ),
    )

    assert result.valid is False
    assert any(
        issue.code == RepairValidationCode.PATH_TRAVERSAL
        for issue in result.issues
    )


def test_rejects_duplicate_paths() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(),
            make_change(),
        ),
    )

    assert result.valid is False
    assert any(
        issue.code == RepairValidationCode.DUPLICATE_FILE
        for issue in result.issues
    )


def test_rejects_empty_modify_content() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(content="   "),
        ),
    )

    assert result.valid is False
    assert any(
        issue.code == RepairValidationCode.INVALID_CONTENT
        for issue in result.issues
    )


def test_rejects_delete_content() -> None:
    result = RepairValidator().validate(
        make_proposal(
            make_change(
                operation=ChangeOperation.DELETE,
                content="should not exist",
            ),
        ),
    )

    assert result.valid is False
    assert any(
        issue.code == RepairValidationCode.INVALID_CONTENT
        for issue in result.issues
    )
