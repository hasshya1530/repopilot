from datetime import UTC, datetime
from uuid import uuid4

from apps.api.app.models.background_job import BackgroundJob
from apps.api.app.schemas.background_job import BackgroundJobResponse


def test_background_job_response_from_model() -> None:
    job_id = uuid4()
    task_id = uuid4()
    now = datetime.now(UTC)

    job = BackgroundJob(
        id=job_id,
        task_id=task_id,
        job_type="orchestration",
        status="running",
        attempt=1,
        max_attempts=3,
        started_at=now,
        completed_at=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )

    response = BackgroundJobResponse.model_validate(job)

    assert response.id == job_id
    assert response.task_id == task_id
    assert response.job_type == "orchestration"
    assert response.status == "running"
    assert response.attempt == 1
    assert response.max_attempts == 3
    assert response.started_at == now
    assert response.completed_at is None
    assert response.error_message is None
    assert response.created_at == now
    assert response.updated_at == now
