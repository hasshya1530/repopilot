from uuid import uuid4

import pytest

from agents.jobs.models import Job, JobType
from agents.jobs.queue import RedisJobQueue


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


@pytest.mark.asyncio
async def test_enqueue_and_dequeue_round_trip() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis, queue_name="test:jobs")

    job = Job(
        id=uuid4(),
        job_type=JobType.ORCHESTRATION,
        task_id=uuid4(),
        max_attempts=3,
    )

    await queue.enqueue(job)

    result = await queue.dequeue(timeout=1)

    assert result == job


@pytest.mark.asyncio
async def test_dequeue_returns_none_when_queue_is_empty() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis, queue_name="test:jobs")

    result = await queue.dequeue(timeout=1)

    assert result is None
