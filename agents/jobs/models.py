from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class JobType(StrEnum):
    ORCHESTRATION = "orchestration"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass(frozen=True, slots=True)
class Job:
    id: UUID
    job_type: JobType
    task_id: UUID
    attempt: int = 0
    max_attempts: int = 3

    @property
    def has_attempts_remaining(self) -> bool:
        return self.attempt + 1 < self.max_attempts

    @property
    def next_attempt(self) -> int:
        return self.attempt + 1


@dataclass(frozen=True, slots=True)
class JobResult:
    job_id: UUID
    status: JobStatus
    attempt: int
    error: str | None = None
