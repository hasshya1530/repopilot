from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.core.redis import get_redis
from apps.api.app.main import app
from apps.api.app.models.background_job import (
    BackgroundJob,
    BackgroundJobStatus,
)
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus


class FakeRedis:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, str]] = []

    async def rpush(
        self,
        queue_name: str,
        payload: str,
    ) -> int:
        self.enqueued.append(
            (queue_name, payload),
        )
        return len(self.enqueued)


@pytest_asyncio.fixture
async def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture
async def api_client(
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_redis, None)


async def create_task(
    session: AsyncSession,
) -> Task:
    repository = Repository(
        owner="hasshya1530",
        name=f"repopilot-job-{uuid4().hex[:8]}",
        full_name=f"hasshya1530/repopilot-job-{uuid4().hex[:8]}",
        github_repo_id=abs(hash(uuid4().hex)) % 900_000_000,
        default_branch="main",
        description="Job API test repository",
        is_private=False,
        clone_url="https://github.com/hasshya1530/repopilot-test.git",
    )

    session.add(repository)
    await session.flush()

    task = Task(
        repository_id=repository.id,
        external_issue_id=1001,
        issue_number=42,
        title="Run background job",
        description="Test durable orchestration queue.",
        status=TaskStatus.PENDING,
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return task


@pytest.mark.asyncio
async def test_start_orchestration_creates_persistent_job(
    api_client: AsyncClient,
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> None:
    task = await create_task(db_session)

    response = await api_client.post(
        f"/api/v1/tasks/{task.id}/run",
    )

    assert response.status_code == 202

    data = response.json()

    assert data["task_id"] == str(task.id)
    assert data["status"] == "pending"
    assert "Orchestration queued." in data["message"]

    result = await db_session.execute(
        select(BackgroundJob).where(
            BackgroundJob.task_id == task.id,
        )
    )

    background_job = result.scalar_one()

    assert background_job.task_id == task.id
    assert background_job.job_type == "orchestration"
    assert background_job.status == BackgroundJobStatus.QUEUED
    assert background_job.attempt == 0
    assert background_job.max_attempts == 3

    assert len(fake_redis.enqueued) == 1

    queue_name, payload = fake_redis.enqueued[0]

    assert queue_name == "repopilot:jobs"
    assert str(background_job.id) in payload
    assert str(task.id) in payload
    assert '"job_type": "orchestration"' in payload
    assert '"attempt": 0' in payload


@pytest.mark.asyncio
async def test_start_orchestration_unknown_task_returns_404(
    api_client: AsyncClient,
) -> None:
    task_id = uuid4()

    response = await api_client.post(
        f"/api/v1/tasks/{task_id}/run",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Task {task_id} was not found."
    )


@pytest.mark.asyncio
async def test_persistent_job_can_be_retrieved_by_id(
    db_session: AsyncSession,
) -> None:
    task = await create_task(db_session)

    from agents.jobs.models import Job, JobType
    from apps.api.app.services.background_job import (
        create_background_job,
        get_background_job,
    )

    job = Job(
        id=uuid4(),
        job_type=JobType.ORCHESTRATION,
        task_id=task.id,
    )

    await create_background_job(
        db_session,
        job,
    )

    result = await get_background_job(
        db_session,
        job.id,
    )

    assert result is not None
    assert result.id == job.id
    assert result.task_id == task.id
    assert result.status == BackgroundJobStatus.QUEUED


@pytest.mark.asyncio
async def test_job_status_persistence_lifecycle(
    db_session: AsyncSession,
) -> None:
    task = await create_task(db_session)

    from agents.jobs.models import Job, JobType
    from apps.api.app.services.background_job import (
        create_background_job,
        get_background_job,
        mark_job_failed,
        mark_job_retrying,
        mark_job_running,
        mark_job_succeeded,
    )

    job = Job(
        id=uuid4(),
        job_type=JobType.ORCHESTRATION,
        task_id=task.id,
        attempt=0,
        max_attempts=3,
    )

    await create_background_job(
        db_session,
        job,
    )

    await mark_job_running(
        db_session,
        job,
    )

    current = await get_background_job(
        db_session,
        job.id,
    )

    assert current is not None
    assert current.status == BackgroundJobStatus.RUNNING
    assert current.started_at is not None

    await mark_job_retrying(
        db_session,
        job,
        "Temporary orchestration failure.",
    )

    current = await get_background_job(
        db_session,
        job.id,
    )

    assert current is not None
    assert current.status == BackgroundJobStatus.RETRYING
    assert current.error_message == (
        "Temporary orchestration failure."
    )
    assert current.attempt == 1

    retry_job = Job(
        id=job.id,
        job_type=job.job_type,
        task_id=job.task_id,
        attempt=1,
        max_attempts=job.max_attempts,
    )

    await mark_job_running(
        db_session,
        retry_job,
    )

    await mark_job_succeeded(
        db_session,
        retry_job,
    )

    current = await get_background_job(
        db_session,
        job.id,
    )

    assert current is not None
    assert current.status == BackgroundJobStatus.SUCCEEDED
    assert current.attempt == 1
    assert current.completed_at is not None
    assert current.error_message is None

    await mark_job_failed(
        db_session,
        retry_job,
        "Final failure.",
    )

    current = await get_background_job(
        db_session,
        job.id,
    )

    assert current is not None
    assert current.status == BackgroundJobStatus.FAILED
    assert current.error_message == "Final failure."


@pytest.mark.asyncio
async def test_job_id_and_task_id_are_uuid_values(
    db_session: AsyncSession,
) -> None:
    task = await create_task(db_session)

    from agents.jobs.models import Job, JobType
    from apps.api.app.services.background_job import create_background_job

    job = Job(
        id=uuid4(),
        job_type=JobType.ORCHESTRATION,
        task_id=task.id,
    )

    background_job = await create_background_job(
        db_session,
        job,
    )

    assert isinstance(background_job.id, UUID)
    assert isinstance(background_job.task_id, UUID)
    assert background_job.task_id == task.id
