from uuid import UUID

from pydantic import BaseModel

from apps.api.app.models.task import TaskStatus


class OrchestrationStartResponse(BaseModel):
    task_id: UUID
    status: TaskStatus
    message: str


class OrchestrationStatusResponse(BaseModel):
    task_id: UUID
    status: TaskStatus
    summary: str | None = None
    pull_request_id: UUID | None = None
    error: str | None = None
