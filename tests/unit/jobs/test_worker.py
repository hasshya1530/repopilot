from uuid import uuid4

import pytest

from agents.jobs.models import Job, JobStatus, JobType
from agents.jobs.queue import RedisJobQueue
from agents.jobs.retry import RetryPolicy
from agents.jobs.worker import JobWorker


class FakeRedis:
    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    async def rpush(self, queue_name: str, payload: str) -> None:
        self.items.append((queue_name, payload))

    async def blpop(
        self,
        queue_name: str,
        timeout: int,
    ) -> tuple[str, str] | None:
        for index, item in enumerate(self.items):
            if item[0] == queue_name:
                return self.items.pop(index)

        return None


def make_job(
    *,
    attempt: int = 0,
    max_attempts: int = 3,
) -> Job:
    return Job(
        id=uuid4(),
        job_type=JobType.ORCHESTRATION,
        task_id=uuid4(),
        attempt=attempt,
        max_attempts=max_attempts,
    )


@pytest.mark.asyncio
async def test_worker_dispatches_job() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis, queue_name="test:jobs")

    job = make_job()
    await queue.enqueue(job)

    handled: list[Job] = []

    async def handler(received_job: Job) -> None:
        handled.append(received_job)

    worker = JobWorker(queue, poll_timeout=1)

    worker.register_handler(
        JobType.ORCHESTRATION.value,
        handler,
    )

    result = await worker.process_once()

    assert result == JobStatus.SUCCEEDED
    assert handled == [job]


@pytest.mark.asyncio
async def test_worker_returns_none_when_queue_is_empty() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis, queue_name="test:jobs")

    worker = JobWorker(queue, poll_timeout=1)

    result = await worker.process_once()

    assert result is None


@pytest.mark.asyncio
async def test_worker_fails_when_handler_is_missing() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis, queue_name="test:jobs")

    job = make_job()
    await queue.enqueue(job)

    worker = JobWorker(queue, poll_timeout=1)

    result = await worker.process_once()

    assert result == JobStatus.FAILED


@pytest.mark.asyncio
async def test_worker_retries_failed_job() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis, queue_name="test:jobs")

    job = make_job()

    await queue.enqueue(job)

    calls: list[Job] = []

    async def handler(received_job: Job) -> None:
        calls.append(received_job)
        raise RuntimeError("temporary failure")

    worker = JobWorker(
        queue,
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay_seconds=0,
            max_delay_seconds=0,
        ),
        poll_timeout=1,
    )

    worker.register_handler(
        JobType.ORCHESTRATION.value,
        handler,
    )

    result = await worker.process_once()

    assert result == JobStatus.RETRYING
    assert calls == [job]

    retry_job = await queue.dequeue(timeout=1)

    assert retry_job is not None
    assert retry_job.id == job.id
    assert retry_job.attempt == 1
    assert retry_job.max_attempts == 3


@pytest.mark.asyncio
async def test_worker_fails_after_final_attempt() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis, queue_name="test:jobs")

    job = make_job(
        attempt=2,
        max_attempts=3,
    )

    await queue.enqueue(job)

    async def handler(_: Job) -> None:
        raise RuntimeError("permanent failure")

    worker = JobWorker(
        queue,
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay_seconds=0,
            max_delay_seconds=0,
        ),
        poll_timeout=1,
    )

    worker.register_handler(
        JobType.ORCHESTRATION.value,
        handler,
    )

    result = await worker.process_once()

    assert result == JobStatus.FAILED

    assert await queue.dequeue(timeout=1) is None
