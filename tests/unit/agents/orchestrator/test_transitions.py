from uuid import uuid4

import pytest

from agents.orchestrator.models import (
    OrchestrationState,
    OrchestrationStatus,
    OrchestrationStepType,
)
from agents.orchestrator.transitions import (
    can_transition,
    status_for_step,
    validate_transition,
)


def test_pending_can_start_understanding() -> None:
    assert can_transition(
        OrchestrationStatus.PENDING,
        OrchestrationStatus.UNDERSTANDING,
    )


def test_testing_can_enter_debugging() -> None:
    assert can_transition(
        OrchestrationStatus.TESTING,
        OrchestrationStatus.DEBUGGING,
    )


def test_testing_can_enter_reviewing() -> None:
    assert can_transition(
        OrchestrationStatus.TESTING,
        OrchestrationStatus.REVIEWING,
    )


def test_debugging_returns_to_testing() -> None:
    assert can_transition(
        OrchestrationStatus.DEBUGGING,
        OrchestrationStatus.TESTING,
    )


def test_completed_has_no_outgoing_transitions() -> None:
    assert not can_transition(
        OrchestrationStatus.COMPLETED,
        OrchestrationStatus.PENDING,
    )


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid orchestration transition"):
        validate_transition(
            OrchestrationStatus.PENDING,
            OrchestrationStatus.COMPLETED,
        )


@pytest.mark.parametrize(
    ("step", "status"),
    [
        (
            OrchestrationStepType.UNDERSTAND,
            OrchestrationStatus.UNDERSTANDING,
        ),
        (
            OrchestrationStepType.PLAN,
            OrchestrationStatus.PLANNING,
        ),
        (
            OrchestrationStepType.IMPLEMENT,
            OrchestrationStatus.IMPLEMENTING,
        ),
        (
            OrchestrationStepType.EXECUTE,
            OrchestrationStatus.TESTING,
        ),
        (
            OrchestrationStepType.DEBUG,
            OrchestrationStatus.DEBUGGING,
        ),
        (
            OrchestrationStepType.REVIEW,
            OrchestrationStatus.REVIEWING,
        ),
        (
            OrchestrationStepType.APPROVAL,
            OrchestrationStatus.WAITING_APPROVAL,
        ),
        (
            OrchestrationStepType.CREATE_PR,
            OrchestrationStatus.CREATING_PR,
        ),
    ],
)
def test_status_for_step(
    step: OrchestrationStepType,
    status: OrchestrationStatus,
) -> None:
    assert status_for_step(step) == status


def test_orchestration_state_defaults() -> None:
    task_id = uuid4()
    repository_id = uuid4()

    state = OrchestrationState(
        task_id=task_id,
        repository_id=repository_id,
        status=OrchestrationStatus.PENDING,
    )

    assert state.task_id == task_id
    assert state.repository_id == repository_id
    assert state.status == OrchestrationStatus.PENDING
    assert state.current_step is None
    assert state.attempt == 0
    assert state.max_debug_attempts == 3
    assert state.error is None
