from typing import Any
from uuid import UUID, uuid4

from agents.events.models import JobEvent, JobEventType
from agents.events.stream import RedisJobEventStream


class JobEventService:
    def __init__(self, stream: RedisJobEventStream) -> None:
        self._stream = stream

    async def publish(
        self,
        *,
        job_id: UUID,
        task_id: UUID,
        event_type: JobEventType,
        message: str,
        attempt: int,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        event = JobEvent.create(
            event_id=uuid4(),
            job_id=job_id,
            task_id=task_id,
            event_type=event_type,
            message=message,
            attempt=attempt,
            metadata=metadata,
        )

        return await self._stream.publish(event)

    async def read(
        self,
        job_id: UUID,
        *,
        last_id: str = "0-0",
        count: int = 100,
        block_ms: int = 5000,
    ) -> list[dict[str, Any]]:
        return await self._stream.read(
            str(job_id),
            last_id=last_id,
            count=count,
            block_ms=block_ms,
        )
