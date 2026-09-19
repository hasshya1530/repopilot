from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BackgroundJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    job_type: str
    status: str
    attempt: int
    max_attempts: int
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
