from pathlib import Path
from uuid import uuid4

from agents.implementer.context.service import ImplementationContextService
from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlanStepType,
)
from ingestion.change_context.models import RepositoryChangeContext


def test_build_allows_missing_planned_file_creation(
    tmp_path: Path,
) -> None:
    repository_id = uuid4()

    change_context = RepositoryChangeContext(
        repository_id=repository_id,
        task_description="Add project documentation.",
        files=(),
        symbols=(),
        dependencies=(),
    )

    plan = ImplementationPlan(
        summary="Create project documentation.",
        assumptions=(),
        files_to_modify=(),
        files_to_create=(
            PlannedFile(
                file_path="docs/README.md",
                reason="Add project documentation.",
            ),
        ),
        symbols_to_modify=(),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Create the project documentation.",
                step_type=PlanStepType.CREATE,
                file_path="docs/README.md",
            ),
        ),
        dependencies=(),
        tests_to_add=(),
        validation_commands=(),
        risks=(),
    )

    service = ImplementationContextService()

    result = service.build(
        repository_id=repository_id,
        repository_path=tmp_path,
        task_description="Add project documentation.",
        change_context=change_context,
        plan=plan,
    )

    assert result.repository_id == repository_id
    assert result.task_description == "Add project documentation."
    assert result.files == ()
    assert result.symbols == ()
    assert result.dependencies == ()
