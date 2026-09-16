from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.api.app.models.task import TaskStatus


class TaskCreate(BaseModel):
    repository_id: UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    external_issue_id: int | None = None
    issue_number: int | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    external_issue_id: int | None
    issue_number: int | None
    title: str
    description: str | None
    status: TaskStatus
    branch_name: str | None
    error_message: str | None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
