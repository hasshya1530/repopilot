from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class JobEventType(StrEnum):
    QUEUED = "job.queued"
    STARTED = "job.started"
    PROGRESS = "job.progress"
    RETRYING = "job.retrying"
    SUCCEEDED = "job.succeeded"
    FAILED = "job.failed"


@dataclass(frozen=True, slots=True)
class JobEvent:
    event_id: UUID
    job_id: UUID
    task_id: UUID
    event_type: JobEventType
    message: str
    attempt: int
    created_at: datetime
    metadata: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        *,
        event_id: UUID,
        job_id: UUID,
        task_id: UUID,
        event_type: JobEventType,
        message: str,
        attempt: int,
        metadata: dict[str, Any] | None = None,
    ) -> "JobEvent":
        return cls(
            event_id=event_id,
            job_id=job_id,
            task_id=task_id,
            event_type=event_type,
            message=message,
            attempt=attempt,
            created_at=datetime.now(UTC),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_id"] = str(self.event_id)
        payload["job_id"] = str(self.job_id)
        payload["task_id"] = str(self.task_id)
        payload["event_type"] = self.event_type.value
        payload["created_at"] = self.created_at.isoformat()
        return payload
