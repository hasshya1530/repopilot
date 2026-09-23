from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlanStepType,
)


def build_locked_plan() -> ImplementationPlan:
    """Return the planner-approved plan used by the real E2E execution path."""

    return ImplementationPlan(
        summary=(
            "Improve background job retry handling by adding jitter to retry "
            "delays to avoid thundering herd and improve fairness."
        ),
        assumptions=(),
        files_to_modify=(
            PlannedFile(
                file_path="agents/jobs/retry.py",
                reason=(
                    "Add jitter support to RetryPolicy.delay_for_attempt "
                    "method, including new parameters and logic."
                ),
            ),
        ),
        files_to_create=(),
        test_files=(
            PlannedFile(
                file_path="tests/unit/jobs/test_retry.py",
                reason=(
                    "Add tests for jitter behavior, including verification "
                    "that delays are within expected range and that jitter "
                    "is applied."
                ),
            ),
        ),
        symbols_to_modify=(),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description=(
                    "Examine the current RetryPolicy implementation in "
                    "agents/jobs/retry.py to understand its structure and "
                    "add jitter parameters."
                ),
                step_type=PlanStepType.MODIFY,
                file_path="agents/jobs/retry.py",
            ),
            ImplementationStep(
                order=2,
                description=(
                    "Modify RetryPolicy.__init__ to accept optional "
                    "jitter_range_seconds parameter and store it."
                ),
                step_type=PlanStepType.MODIFY,
                file_path="agents/jobs/retry.py",
                symbol_name="__init__",
            ),
            ImplementationStep(
                order=3,
                description=(
                    "Update RetryPolicy.delay_for_attempt to incorporate "
                    "random jitter within the specified range, ensuring "
                    "delays stay within base and max caps."
                ),
                step_type=PlanStepType.MODIFY,
                file_path="agents/jobs/retry.py",
                symbol_name="delay_for_attempt",
            ),
            ImplementationStep(
                order=4,
                description=(
                    "Add new test cases to test_retry.py to verify jitter "
                    "behavior, including checking that delays are within "
                    "expected range and that jitter is applied."
                ),
                step_type=PlanStepType.MODIFY,
                file_path="tests/unit/jobs/test_retry.py",
            ),
            ImplementationStep(
                order=5,
                description=(
                    "Run existing tests to ensure backward compatibility "
                    "and that new jitter tests pass."
                ),
                step_type=PlanStepType.VALIDATE,
            ),
        ),
        dependencies=(),
        tests_to_add=(
            "test_retry_policy_applies_jitter",
            "test_retry_policy_jitter_within_range",
            "test_retry_policy_jitter_does_not_exceed_max",
        ),
        validation_commands=(
            "python -m pytest tests/unit/jobs/test_retry.py -xvs",
        ),
        risks=(),
    )
