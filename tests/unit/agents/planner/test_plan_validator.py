from uuid import uuid4

import pytest

from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlannedSymbol,
    PlanStepType,
)
from agents.planner.plan_validator import PlanValidationError, validate_plan


def make_plan(**overrides: object) -> ImplementationPlan:
    values: dict[str, object] = {
        "summary": "Update authentication.",
        "assumptions": (),
        "files_to_modify": (
            PlannedFile(
                file_path="src/auth.py",
                reason="Contains authentication logic.",
            ),
        ),
        "files_to_create": (),
        "symbols_to_modify": (
            PlannedSymbol(
                symbol_id=uuid4(),
                file_path="src/auth.py",
                name="validate_token",
                reason="Update token validation.",
            ),
        ),
        "implementation_steps": (
            ImplementationStep(
                order=1,
                description="Update token validation.",
                step_type=PlanStepType.MODIFY,
                file_path="src/auth.py",
                symbol_name="validate_token",
            ),
            ImplementationStep(
                order=2,
                description="Add regression tests.",
                step_type=PlanStepType.TEST,
                file_path="tests/test_auth.py",
            ),
            ImplementationStep(
                order=3,
                description="Run the test suite.",
                step_type=PlanStepType.VALIDATE,
            ),
        ),
        "dependencies": (),
        "tests_to_add": ("Test expired tokens are rejected.",),
        "validation_commands": ("pytest tests/test_auth.py",),
        "risks": (),
    }
    values.update(overrides)
    return ImplementationPlan(**values)


def test_valid_plan_passes() -> None:
    validate_plan(make_plan())


def test_empty_summary_is_rejected() -> None:
    with pytest.raises(PlanValidationError, match="summary"):
        validate_plan(make_plan(summary="   "))


def test_empty_steps_are_rejected() -> None:
    with pytest.raises(PlanValidationError, match="at least one"):
        validate_plan(make_plan(implementation_steps=()))


def test_non_sequential_step_orders_are_rejected() -> None:
    steps = (
        ImplementationStep(
            order=1,
            description="First step.",
            step_type=PlanStepType.MODIFY,
            file_path="src/auth.py",
        ),
        ImplementationStep(
            order=3,
            description="Third step.",
            step_type=PlanStepType.TEST,
            file_path="tests/test_auth.py",
        ),
    )

    with pytest.raises(PlanValidationError, match="sequential"):
        validate_plan(
            make_plan(
                implementation_steps=steps,
                tests_to_add=("Add regression test.",),
            )
        )


@pytest.mark.parametrize(
    "file_path",
    [
        "/tmp/auth.py",
        "../auth.py",
        "src/../auth.py",
    ],
)
def test_unsafe_file_paths_are_rejected(file_path: str) -> None:
    with pytest.raises(PlanValidationError):
        validate_plan(
            make_plan(
                files_to_modify=(
                    PlannedFile(
                        file_path=file_path,
                        reason="Unsafe path.",
                    ),
                )
            )
        )


def test_modify_step_requires_file_path() -> None:
    steps = (
        ImplementationStep(
            order=1,
            description="Modify authentication.",
            step_type=PlanStepType.MODIFY,
        ),
    )

    with pytest.raises(PlanValidationError, match="requires a file path"):
        validate_plan(make_plan(implementation_steps=steps))


def test_create_step_requires_file_path() -> None:
    steps = (
        ImplementationStep(
            order=1,
            description="Create authentication tests.",
            step_type=PlanStepType.CREATE,
        ),
    )

    with pytest.raises(PlanValidationError, match="requires a file path"):
        validate_plan(make_plan(implementation_steps=steps))


def test_delete_step_requires_file_path() -> None:
    steps = (
        ImplementationStep(
            order=1,
            description="Delete obsolete authentication code.",
            step_type=PlanStepType.DELETE,
        ),
    )

    with pytest.raises(PlanValidationError, match="requires a file path"):
        validate_plan(make_plan(implementation_steps=steps))


def test_test_step_requires_tests() -> None:
    steps = (
        ImplementationStep(
            order=1,
            description="Add authentication regression tests.",
            step_type=PlanStepType.TEST,
            file_path="tests/test_auth.py",
        ),
    )

    with pytest.raises(PlanValidationError, match="TEST"):
        validate_plan(
            make_plan(
                implementation_steps=steps,
                tests_to_add=(),
            )
        )


def test_validate_step_requires_validation_commands() -> None:
    steps = (
        ImplementationStep(
            order=1,
            description="Validate the implementation.",
            step_type=PlanStepType.VALIDATE,
        ),
    )

    with pytest.raises(PlanValidationError, match="VALIDATE"):
        validate_plan(
            make_plan(
                implementation_steps=steps,
                validation_commands=(),
            )
        )


def test_empty_planned_file_reason_is_rejected() -> None:
    with pytest.raises(PlanValidationError, match="reason"):
        validate_plan(
            make_plan(
                files_to_modify=(
                    PlannedFile(
                        file_path="src/auth.py",
                        reason=" ",
                    ),
                )
            )
        )


def test_empty_planned_symbol_name_is_rejected() -> None:
    with pytest.raises(PlanValidationError, match="must have a name"):
        validate_plan(
            make_plan(
                symbols_to_modify=(
                    PlannedSymbol(
                        symbol_id=uuid4(),
                        file_path="src/auth.py",
                        name=" ",
                        reason="Update authentication.",
                    ),
                )
            )
        )


def test_empty_step_description_is_rejected() -> None:
    steps = (
        ImplementationStep(
            order=1,
            description=" ",
            step_type=PlanStepType.MODIFY,
            file_path="src/auth.py",
        ),
    )

    with pytest.raises(PlanValidationError, match="description"):
        validate_plan(make_plan(implementation_steps=steps))
