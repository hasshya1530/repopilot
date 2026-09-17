from pathlib import Path
from uuid import uuid4

from agents.implementer.context.service import (
    ImplementationContextService,
)
from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlannedSymbol,
    PlanStepType,
)
from ingestion.change_context.models import (
    ChangeContextFile,
    ChangeContextSymbol,
    RepositoryChangeContext,
)


def test_build_reads_repository_source(tmp_path: Path) -> None:
    repository_id = uuid4()

    (tmp_path / "auth.py").write_text(
        """
def validate_token(token: str) -> bool:
    return token == "valid"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    symbol_id = uuid4()

    change_context = RepositoryChangeContext(
        repository_id=repository_id,
        task_description="Improve authentication.",
        files=(
            ChangeContextFile(
                file_path="auth.py",
                reason="Authentication logic is relevant.",
                relevance_score=1.0,
            ),
        ),
        symbols=(
            ChangeContextSymbol(
                symbol_id=symbol_id,
                file_path="auth.py",
                name="validate_token",
                symbol_type="function",
                start_line=1,
                end_line=2,
                reason="Target validation function.",
            ),
        ),
        dependencies=(),
    )

    plan = ImplementationPlan(
        summary="Improve authentication validation.",
        assumptions=(),
        files_to_modify=(
            PlannedFile(
                file_path="auth.py",
                reason="Modify token validation.",
            ),
        ),
        files_to_create=(),
        symbols_to_modify=(
            PlannedSymbol(
                symbol_id=symbol_id,
                file_path="auth.py",
                name="validate_token",
                reason="Modify validation.",
            ),
        ),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Modify validation.",
                step_type=PlanStepType.MODIFY,
                file_path="auth.py",
                symbol_name="validate_token",
            ),
        ),
        dependencies=(),
        tests_to_add=("Add invalid token tests.",),
        validation_commands=("pytest",),
        risks=(),
    )

    service = ImplementationContextService()

    result = service.build(
        repository_id=repository_id,
        repository_path=tmp_path,
        task_description="Improve authentication.",
        change_context=change_context,
        plan=plan,
    )

    assert result.repository_id == repository_id
    assert result.task_description == "Improve authentication."

    assert len(result.files) == 1
    assert result.files[0].file_path == "auth.py"
    assert "validate_token" in result.files[0].content

    assert len(result.symbols) == 1
    assert result.symbols[0].name == "validate_token"
    assert result.symbols[0].content == (
        'def validate_token(token: str) -> bool:\n    return token == "valid"'
    )


def test_build_rejects_missing_repository_file(tmp_path: Path) -> None:
    repository_id = uuid4()

    change_context = RepositoryChangeContext(
        repository_id=repository_id,
        task_description="Modify authentication.",
        files=(
            ChangeContextFile(
                file_path="missing.py",
                reason="Relevant file.",
                relevance_score=1.0,
            ),
        ),
        symbols=(),
        dependencies=(),
    )

    plan = ImplementationPlan(
        summary="Modify authentication.",
        assumptions=(),
        files_to_modify=(
            PlannedFile(
                file_path="missing.py",
                reason="Modify authentication.",
            ),
        ),
        files_to_create=(),
        symbols_to_modify=(),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Modify authentication.",
                step_type=PlanStepType.MODIFY,
                file_path="missing.py",
            ),
        ),
        dependencies=(),
        tests_to_add=("Add tests.",),
        validation_commands=("pytest",),
        risks=(),
    )

    service = ImplementationContextService()

    import pytest

    from agents.implementer.context.errors import (
        ImplementationContextRetrievalError,
    )

    with pytest.raises(ImplementationContextRetrievalError):
        service.build(
            repository_id=repository_id,
            repository_path=tmp_path,
            task_description="Modify authentication.",
            change_context=change_context,
            plan=plan,
        )
