from agents.orchestrator.errors import InvalidOrchestrationTransitionError
from agents.orchestrator.models import (
    OrchestrationState,
    OrchestrationStatus,
    OrchestrationStepType,
)

_ALLOWED_TRANSITIONS: dict[
    OrchestrationStatus,
    frozenset[OrchestrationStatus],
] = {
    OrchestrationStatus.PENDING: frozenset(
        {
            OrchestrationStatus.UNDERSTANDING,
            OrchestrationStatus.CANCELLED,
            OrchestrationStatus.FAILED,
        }
    ),
    OrchestrationStatus.UNDERSTANDING: frozenset(
        {
            OrchestrationStatus.PLANNING,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.PLANNING: frozenset(
        {
            OrchestrationStatus.IMPLEMENTING,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.IMPLEMENTING: frozenset(
        {
            OrchestrationStatus.TESTING,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.TESTING: frozenset(
        {
            OrchestrationStatus.REVIEWING,
            OrchestrationStatus.DEBUGGING,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.DEBUGGING: frozenset(
        {
            OrchestrationStatus.TESTING,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.REVIEWING: frozenset(
        {
            OrchestrationStatus.WAITING_APPROVAL,
            OrchestrationStatus.IMPLEMENTING,
            OrchestrationStatus.CREATING_PR,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.CREATING_PR: frozenset(
        {
            OrchestrationStatus.WAITING_APPROVAL,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.WAITING_APPROVAL: frozenset(
        {
            OrchestrationStatus.COMPLETED,
            OrchestrationStatus.FAILED,
            OrchestrationStatus.CANCELLED,
        }
    ),
    OrchestrationStatus.COMPLETED: frozenset(),
    OrchestrationStatus.FAILED: frozenset(),
    OrchestrationStatus.CANCELLED: frozenset(),
}


_STEP_STATUSES: dict[OrchestrationStepType, OrchestrationStatus] = {
    OrchestrationStepType.UNDERSTAND: OrchestrationStatus.UNDERSTANDING,
    OrchestrationStepType.PLAN: OrchestrationStatus.PLANNING,
    OrchestrationStepType.IMPLEMENT: OrchestrationStatus.IMPLEMENTING,
    OrchestrationStepType.EXECUTE: OrchestrationStatus.TESTING,
    OrchestrationStepType.DEBUG: OrchestrationStatus.DEBUGGING,
    OrchestrationStepType.REVIEW: OrchestrationStatus.REVIEWING,
    OrchestrationStepType.APPROVAL: OrchestrationStatus.WAITING_APPROVAL,
    OrchestrationStepType.CREATE_PR: OrchestrationStatus.CREATING_PR,
}


def can_transition(
    current: OrchestrationStatus,
    target: OrchestrationStatus,
) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


def transition(
    state: OrchestrationState,
    target: OrchestrationStatus,
    *,
    current_step: OrchestrationStepType | None = None,
    attempt: int | None = None,
    error: str | None = None,
) -> OrchestrationState:
    if not can_transition(state.status, target):
        raise InvalidOrchestrationTransitionError(
            f"Cannot transition orchestration from "
            f"{state.status.value!r} to {target.value!r}."
        )

    return OrchestrationState(
        task_id=state.task_id,
        repository_id=state.repository_id,
        status=target,
        current_step=current_step,
        attempt=state.attempt if attempt is None else attempt,
        max_debug_attempts=state.max_debug_attempts,
        error=error,
    )


def status_for_step(step: OrchestrationStepType) -> OrchestrationStatus:
    return _STEP_STATUSES[step]


def validate_transition(
    current: OrchestrationStatus,
    target: OrchestrationStatus,
) -> None:
    """Validate a state transition and raise if it is not allowed."""
    if not can_transition(current, target):
        raise InvalidOrchestrationTransitionError(
            f"Invalid orchestration transition: "
            f"{current.value!r} -> {target.value!r}."
        )
