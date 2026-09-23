from agents.planner.plan_models import ImplementationPlan, PlanStepType


class PlanValidationError(ValueError):
    """Raised when an implementation plan violates a planner contract."""


def validate_plan(plan: ImplementationPlan) -> None:
    """Validate structural and semantic invariants of an implementation plan."""

    _validate_summary(plan)
    _validate_files(plan)
    _validate_symbols(plan)
    _validate_steps(plan)
    _validate_new_file_operations(plan)
    _validate_test_files(plan)


def _validate_summary(plan: ImplementationPlan) -> None:
    if not plan.summary.strip():
        raise PlanValidationError(
            "Plan summary must not be empty."
        )


def _validate_files(plan: ImplementationPlan) -> None:
    for planned_file in (
        *plan.files_to_modify,
        *plan.files_to_create,
    ):
        if not planned_file.file_path.strip():
            raise PlanValidationError(
                "Planned file path must not be empty."
            )

        if not planned_file.reason.strip():
            raise PlanValidationError(
                f"Planned file {planned_file.file_path} must have a reason."
            )

        if planned_file.file_path.startswith("/"):
            raise PlanValidationError(
                f"Planned file path must be relative: "
                f"{planned_file.file_path}"
            )

        if ".." in planned_file.file_path.split("/"):
            raise PlanValidationError(
                "Planned file path must not contain '..': "
                f"{planned_file.file_path}"
            )


def _validate_symbols(plan: ImplementationPlan) -> None:
    modify_paths = {
        item.file_path
        for item in plan.files_to_modify
    }

    for symbol in plan.symbols_to_modify:
        if symbol.file_path not in modify_paths:
            raise PlanValidationError(
                "Every planned symbol must belong to a modified file: "
                f"{symbol.file_path}"
            )

        if not symbol.name.strip():
            raise PlanValidationError(
                f"Planned symbol {symbol.symbol_id} must have a name."
            )

        if not symbol.reason.strip():
            raise PlanValidationError(
                f"Planned symbol {symbol.name} must have a reason."
            )


def _validate_steps(plan: ImplementationPlan) -> None:
    if not plan.implementation_steps:
        raise PlanValidationError(
            "Implementation plan must contain at least one implementation step."
        )

    orders = [
        step.order
        for step in plan.implementation_steps
    ]

    if orders != list(range(1, len(orders) + 1)):
        raise PlanValidationError(
            "Implementation step orders must be sequential starting at 1."
        )

    step_types = {
        step.step_type
        for step in plan.implementation_steps
    }

    if PlanStepType.TEST in step_types and not plan.tests_to_add:
        raise PlanValidationError(
            "A TEST implementation step requires tests_to_add."
        )

    for step in plan.implementation_steps:
        if not step.description.strip():
            raise PlanValidationError(
                f"Implementation step {step.order} description must not be empty."
            )

        if step.step_type in {
            PlanStepType.MODIFY,
            PlanStepType.CREATE,
            PlanStepType.DELETE,
        } and step.file_path is None:
            raise PlanValidationError(
                f"{step.step_type.value.upper()} step requires a file path."
            )

        if step.step_type == PlanStepType.VALIDATE:
            if not plan.validation_commands:
                raise PlanValidationError(
                    "VALIDATE step requires validation commands."
                )


def _validate_new_file_operations(plan: ImplementationPlan) -> None:
    """Reject the same file appearing in both modify and create operations."""

    modify_paths = {
        item.file_path
        for item in plan.files_to_modify
    }

    create_paths = {
        item.file_path
        for item in plan.files_to_create
    }

    overlap = sorted(modify_paths & create_paths)

    if overlap:
        raise PlanValidationError(
            "A file cannot be both modified and created: "
            + ", ".join(overlap)
        )


def _validate_test_files(plan: ImplementationPlan) -> None:
    """Validate optional concrete test-file declarations."""

    if not plan.test_files:
        return

    test_paths = {
        item.file_path
        for item in plan.test_files
    }

    if len(test_paths) != len(plan.test_files):
        raise PlanValidationError(
            "Test files must not contain duplicates."
        )

    operation_paths = {
        item.file_path
        for item in plan.files_to_modify
    } | {
        item.file_path
        for item in plan.files_to_create
    }

    missing_operations = sorted(
        test_paths - operation_paths
    )

    if missing_operations:
        raise PlanValidationError(
            "Every test file must have a corresponding file operation: "
            + ", ".join(missing_operations)
        )
