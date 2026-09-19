from uuid import uuid4

from agents.events.models import JobEvent, JobEventType


def test_job_event_create() -> None:
    job_id = uuid4()
    task_id = uuid4()
    event_id = uuid4()

    event = JobEvent.create(
        event_id=event_id,
        job_id=job_id,
        task_id=task_id,
        event_type=JobEventType.STARTED,
        message="Worker started",
        attempt=0,
    )

    assert event.event_id == event_id
    assert event.job_id == job_id
    assert event.task_id == task_id
    assert event.event_type is JobEventType.STARTED
    assert event.message == "Worker started"
    assert event.attempt == 0
    assert event.created_at.tzinfo is not None


def test_job_event_to_dict() -> None:
    job_id = uuid4()
    task_id = uuid4()
    event_id = uuid4()

    event = JobEvent.create(
        event_id=event_id,
        job_id=job_id,
        task_id=task_id,
        event_type=JobEventType.PROGRESS,
        message="Repository analyzed",
        attempt=1,
        metadata={"files": 42},
    )

    payload = event.to_dict()

    assert payload["event_id"] == str(event_id)
    assert payload["job_id"] == str(job_id)
    assert payload["task_id"] == str(task_id)
    assert payload["event_type"] == "job.progress"
    assert payload["metadata"] == {"files": 42}
