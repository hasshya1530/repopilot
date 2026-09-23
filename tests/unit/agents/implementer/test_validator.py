
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.implementer.validator import (
    ImplementationValidationCode,
    ImplementationValidator,
)
from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlanStepType,
)


def make_plan(
    *,
    files_to_modify: tuple[PlannedFile, ...] = (),
    files_to_create: tuple[PlannedFile, ...] = (),
    implementation_steps: tuple[ImplementationStep, ...] = (),
    tests_to_add: tuple[str, ...] = (),
) -> ImplementationPlan:
    return ImplementationPlan(
        summary="Implement requested change.",
        assumptions=(),
        files_to_modify=files_to_modify,
        files_to_create=files_to_create,
        symbols_to_modify=(),
        implementation_steps=implementation_steps,
        dependencies=(),
        tests_to_add=tests_to_add,
        validation_commands=(),
        risks=(),
    )


def make_result(
    *changes: CodeChange,
) -> ImplementationResult:
    return ImplementationResult(
        summary="Implementation result.",
        changes=changes,
    )


def test_accepts_matching_modify_and_create_changes() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
        files_to_create=(
            PlannedFile(
                file_path="src/helper.py",
                reason="Add helper.",
            ),
        ),
    )

    result = make_result(
        CodeChange(
            file_path="src/service.py",
            operation=ChangeOperation.MODIFY,
            content="updated",
            reason="Update service.",
        ),
        CodeChange(
            file_path="src/helper.py",
            operation=ChangeOperation.CREATE,
            content="helper",
            reason="Add helper.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is True
    assert validation.issues == ()


def test_rejects_unplanned_file() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
    )

    result = make_result(
        CodeChange(
            file_path="src/unplanned.py",
            operation=ChangeOperation.MODIFY,
            content="unexpected",
            reason="Unexpected change.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is False
    assert any(
        issue.code == ImplementationValidationCode.UNPLANNED_FILE
        for issue in validation.issues
    )


def test_rejects_missing_planned_file() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
    )

    result = make_result()

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is False
    assert any(
        issue.code == ImplementationValidationCode.MISSING_PLANNED_FILE
        for issue in validation.issues
    )


def test_rejects_invalid_operation() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
    )

    result = make_result(
        CodeChange(
            file_path="src/service.py",
            operation=ChangeOperation.CREATE,
            content="unexpected",
            reason="Wrong operation.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is False
    assert any(
        issue.code == ImplementationValidationCode.INVALID_OPERATION
        for issue in validation.issues
    )


def test_rejects_duplicate_file() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
    )

    result = make_result(
        CodeChange(
            file_path="src/service.py",
            operation=ChangeOperation.MODIFY,
            content="first",
            reason="First change.",
        ),
        CodeChange(
            file_path="src/service.py",
            operation=ChangeOperation.MODIFY,
            content="second",
            reason="Second change.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is False
    assert any(
        issue.code == ImplementationValidationCode.DUPLICATE_FILE
        for issue in validation.issues
    )


def test_accepts_planned_test_change() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
        files_to_create=(
            PlannedFile(
                file_path="tests/test_service.py",
                reason="Add regression coverage.",
            ),
        ),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Update service behavior.",
                step_type=PlanStepType.MODIFY,
                file_path="src/service.py",
            ),
            ImplementationStep(
                order=2,
                description="Add regression test.",
                step_type=PlanStepType.TEST,
                file_path="tests/test_service.py",
            ),
        ),
        tests_to_add=("Add regression coverage.",),
    )

    result = make_result(
        CodeChange(
            file_path="src/service.py",
            operation=ChangeOperation.MODIFY,
            content="updated",
            reason="Update service.",
        ),
        CodeChange(
            file_path="tests/test_service.py",
            operation=ChangeOperation.CREATE,
            content="def test_service():\n    assert True\n",
            reason="Add regression coverage.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is True


def test_rejects_missing_test_change_when_plan_requires_tests() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Update service.",
                step_type=PlanStepType.MODIFY,
                file_path="src/service.py",
            ),
            ImplementationStep(
                order=2,
                description="Add regression coverage.",
                step_type=PlanStepType.TEST,
                file_path="tests/test_service.py",
            ),
        ),
        tests_to_add=("Add regression coverage.",),
    )

    result = make_result(
        CodeChange(
            file_path="src/service.py",
            operation=ChangeOperation.MODIFY,
            content="updated",
            reason="Update service.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is False
    assert any(
        issue.code == ImplementationValidationCode.MISSING_TEST_CHANGE
        for issue in validation.issues
    )


def test_detects_common_test_file_conventions() -> None:
    paths = (
        "tests/test_service.py",
        "src/tests/test_service.py",
        "service_test.py",
        "service.test.ts",
        "service.test.tsx",
        "service.spec.ts",
        "service.spec.tsx",
        "service.spec.js",
        "service.spec.jsx",
    )

    validator = ImplementationValidator()

    for path in paths:
        assert validator._looks_like_test_path(path) is True


def test_non_test_plan_does_not_require_test_change() -> None:
    plan = make_plan(
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update service.",
            ),
        ),
    )

    result = make_result(
        CodeChange(
            file_path="src/service.py",
            operation=ChangeOperation.MODIFY,
            content="updated",
            reason="Update service.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is True


def test_accepts_test_file_declared_in_test_files() -> None:
    plan = ImplementationPlan(
        summary="Add retry jitter.",
        assumptions=(),
        files_to_modify=(
            PlannedFile(
                file_path="agents/jobs/retry.py",
                reason="Add retry jitter.",
            ),
        ),
        files_to_create=(),
        test_files=(
            PlannedFile(
                file_path="tests/unit/jobs/test_retry.py",
                reason="Add retry jitter regression tests.",
            ),
        ),
        symbols_to_modify=(),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Update retry policy.",
                step_type=PlanStepType.MODIFY,
                file_path="agents/jobs/retry.py",
            ),
            ImplementationStep(
                order=2,
                description="Add retry jitter tests.",
                step_type=PlanStepType.TEST,
                file_path="tests/unit/jobs/test_retry.py",
            ),
        ),
        dependencies=(),
        tests_to_add=("test_retry_policy_applies_jitter",),
        validation_commands=(),
        risks=(),
    )

    result = make_result(
        CodeChange(
            file_path="agents/jobs/retry.py",
            operation=ChangeOperation.MODIFY,
            content="updated retry policy",
            reason="Add retry jitter.",
        ),
        CodeChange(
            file_path="tests/unit/jobs/test_retry.py",
            operation=ChangeOperation.MODIFY,
            content="updated tests",
            reason="Add retry jitter regression tests.",
        ),
    )

    validation = ImplementationValidator().validate(
        plan=plan,
        implementation=result,
    )

    assert validation.valid is True
    assert validation.issues == ()
