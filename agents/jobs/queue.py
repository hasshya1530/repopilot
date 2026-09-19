from __future__ import annotations

import json
from uuid import UUID

from redis.asyncio import Redis

from agents.jobs.models import Job, JobType


class RedisJobQueue:
    """Redis-backed queue for RepoPilot background jobs."""

    def __init__(
        self,
        redis: Redis,
        *,
        queue_name: str = "repopilot:jobs",
    ) -> None:
        self._redis = redis
        self._queue_name = queue_name

    async def enqueue(self, job: Job) -> None:
        payload = {
            "id": str(job.id),
            "job_type": job.job_type.value,
            "task_id": str(job.task_id),
            "attempt": job.attempt,
            "max_attempts": job.max_attempts,
        }

        await self._redis.rpush(
            self._queue_name,
            json.dumps(payload),
        )

    async def dequeue(
        self,
        *,
        timeout: int = 5,
    ) -> Job | None:
        try:
            result = await self._redis.blpop(
                self._queue_name,
                timeout=timeout,
            )
        except TimeoutError:
            # Some Redis client/socket configurations raise a timeout
            # instead of returning None when BLPOP reaches its timeout.
            return None

        if result is None:
            return None

        _, raw_payload = result

        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8")

        payload = json.loads(raw_payload)

        return Job(
            id=UUID(payload["id"]),
            job_type=JobType(payload["job_type"]),
            task_id=UUID(payload["task_id"]),
            attempt=int(payload["attempt"]),
            max_attempts=int(payload["max_attempts"]),
        )
