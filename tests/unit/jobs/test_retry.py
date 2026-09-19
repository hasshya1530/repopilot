import pytest

from agents.jobs.retry import RetryPolicy


def test_retry_policy_uses_exponential_backoff() -> None:
    policy = RetryPolicy(
        max_attempts=5,
        base_delay_seconds=1.0,
        max_delay_seconds=30.0,
    )

    assert policy.delay_for_attempt(0) == 1.0
    assert policy.delay_for_attempt(1) == 2.0
    assert policy.delay_for_attempt(2) == 4.0
    assert policy.delay_for_attempt(3) == 8.0


def test_retry_policy_caps_delay() -> None:
    policy = RetryPolicy(
        max_attempts=10,
        base_delay_seconds=1.0,
        max_delay_seconds=5.0,
    )

    assert policy.delay_for_attempt(10) == 5.0


def test_retry_policy_rejects_invalid_attempt_count() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)


def test_retry_policy_rejects_invalid_delay() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(
            base_delay_seconds=10.0,
            max_delay_seconds=5.0,
        )


def test_retry_policy_rejects_negative_attempt() -> None:
    policy = RetryPolicy()

    with pytest.raises(ValueError):
        policy.delay_for_attempt(-1)


def test_job_attempt_helpers() -> None:
    from uuid import uuid4

    from agents.jobs.models import Job, JobType

    job = Job(
        id=uuid4(),
        job_type=JobType.ORCHESTRATION,
        task_id=uuid4(),
        attempt=1,
        max_attempts=3,
    )

    assert job.has_attempts_remaining is True
    assert job.next_attempt == 2
