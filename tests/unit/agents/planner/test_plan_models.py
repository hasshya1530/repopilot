from uuid import uuid4

from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlannedSymbol,
    PlanStepType,
)


def test_implementation_step_defaults() -> None:
    step = ImplementationStep(
        order=1,
        description="Update authentication logic",
        step_type=PlanStepType.MODIFY,
    )

    assert step.order == 1
    assert step.description == "Update authentication logic"
    assert step.step_type == PlanStepType.MODIFY
    assert step.file_path is None
    assert step.symbol_name is None


def test_planned_file() -> None:
    planned_file = PlannedFile(
        file_path="src/auth.py",
        reason="Authentication logic must be updated.",
    )

    assert planned_file.file_path == "src/auth.py"
    assert planned_file.reason == "Authentication logic must be updated."


def test_planned_symbol() -> None:
    symbol_id = uuid4()

    symbol = PlannedSymbol(
        symbol_id=symbol_id,
        file_path="src/auth.py",
        name="validate_token",
        reason="Token validation behavior must change.",
    )

    assert symbol.symbol_id == symbol_id
    assert symbol.file_path == "src/auth.py"
    assert symbol.name == "validate_token"


def test_implementation_plan() -> None:
    symbol_id = uuid4()

    plan = ImplementationPlan(
        summary="Update token validation.",
        assumptions=("Existing authentication middleware remains unchanged.",),
        files_to_modify=(
            PlannedFile(
                file_path="src/auth.py",
                reason="Contains token validation.",
            ),
        ),
        files_to_create=(),
        symbols_to_modify=(
            PlannedSymbol(
                symbol_id=symbol_id,
                file_path="src/auth.py",
                name="validate_token",
                reason="Update validation behavior.",
            ),
        ),
        implementation_steps=(
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
        ),
        dependencies=("Authentication middleware",),
        tests_to_add=("Test expired tokens are rejected.",),
        validation_commands=("pytest tests/test_auth.py",),
        risks=("Existing authentication flows may depend on current validation behavior.",),
    )

    assert plan.summary == "Update token validation."
    assert len(plan.files_to_modify) == 1
    assert len(plan.files_to_create) == 0
    assert len(plan.symbols_to_modify) == 1
    assert len(plan.implementation_steps) == 2
    assert len(plan.tests_to_add) == 1
    assert len(plan.validation_commands) == 1
    assert len(plan.risks) == 1


def test_plan_step_types() -> None:
    assert PlanStepType.MODIFY.value == "modify"
    assert PlanStepType.CREATE.value == "create"
    assert PlanStepType.DELETE.value == "delete"
    assert PlanStepType.TEST.value == "test"
    assert PlanStepType.VALIDATE.value == "validate"
