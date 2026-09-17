from pathlib import PurePosixPath

from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlanStepType,
)


class PlanValidationError(ValueError):
    """Raised when an implementation plan is invalid."""


def validate_plan(plan: ImplementationPlan) -> None:
    """Validate an implementation plan before execution."""
    _validate_summary(plan.summary)
    _validate_collection_entries(plan)
    _validate_steps(plan.implementation_steps)
    _validate_file_paths(plan)
    _validate_step_requirements(plan)


def _validate_summary(summary: str) -> None:
    if not summary.strip():
        raise PlanValidationError("Implementation plan summary cannot be empty.")


def _validate_collection_entries(plan: ImplementationPlan) -> None:
    for planned_file in (*plan.files_to_modify, *plan.files_to_create):
        if not planned_file.file_path.strip():
            raise PlanValidationError("Planned file path cannot be empty.")
        if not planned_file.reason.strip():
            raise PlanValidationError(
                f"Planned file '{planned_file.file_path}' must have a reason."
            )

    for symbol in plan.symbols_to_modify:
        if not symbol.file_path.strip():
            raise PlanValidationError("Planned symbol file path cannot be empty.")
        if not symbol.name.strip():
            raise PlanValidationError(
                f"Planned symbol in '{symbol.file_path}' must have a name."
            )
        if not symbol.reason.strip():
            raise PlanValidationError(
                f"Planned symbol '{symbol.name}' must have a reason."
            )


def _validate_steps(steps: tuple[ImplementationStep, ...]) -> None:
    if not steps:
        raise PlanValidationError(
            "Implementation plan must contain at least one implementation step."
        )

    expected_orders = tuple(range(1, len(steps) + 1))
    actual_orders = tuple(step.order for step in steps)

    if actual_orders != expected_orders:
        raise PlanValidationError(
            "Implementation step orders must be sequential starting at 1."
        )

    for step in steps:
        if not step.description.strip():
            raise PlanValidationError(
                f"Implementation step {step.order} must have a description."
            )


def _validate_file_paths(plan: ImplementationPlan) -> None:
    paths = [
        planned_file.file_path
        for planned_file in (*plan.files_to_modify, *plan.files_to_create)
    ]

    paths.extend(
        symbol.file_path
        for symbol in plan.symbols_to_modify
    )

    paths.extend(
        step.file_path
        for step in plan.implementation_steps
        if step.file_path is not None
    )

    for file_path in paths:
        _validate_file_path(file_path)


def _validate_file_path(file_path: str) -> None:
    path = PurePosixPath(file_path)

    if not file_path.strip():
        raise PlanValidationError("File path cannot be empty.")

    if path.is_absolute():
        raise PlanValidationError(
            f"Absolute file paths are not allowed: '{file_path}'."
        )

    if ".." in path.parts:
        raise PlanValidationError(
            f"Path traversal is not allowed: '{file_path}'."
        )


def _validate_step_requirements(plan: ImplementationPlan) -> None:
    for step in plan.implementation_steps:
        if step.step_type in {
            PlanStepType.MODIFY,
            PlanStepType.CREATE,
            PlanStepType.DELETE,
        } and not step.file_path:
            raise PlanValidationError(
                f"{step.step_type.value.upper()} step {step.order} requires a file path."
            )

    step_types = {step.step_type for step in plan.implementation_steps}

    if PlanStepType.TEST in step_types and not plan.tests_to_add:
        raise PlanValidationError(
            "A TEST implementation step requires at least one test to add."
        )

    if PlanStepType.VALIDATE in step_types and not plan.validation_commands:
        raise PlanValidationError(
            "A VALIDATE implementation step requires at least one validation command."
        )
