from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.models.base import Base, TimestampMixin


class TaskStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentType(StrEnum):
    ORCHESTRATOR = "orchestrator"
    REPOSITORY = "repository"
    RETRIEVAL = "retrieval"
    ARCHITECTURE = "architecture"
    CODING = "coding"
    TESTING = "testing"
    DEBUGGER = "debugger"
    REVIEWER = "reviewer"


class TaskStep(TimestampMixin, Base):
    __tablename__ = "task_steps"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    agent_type: Mapped[AgentType] = mapped_column(
        String(32),
        nullable=False,
    )

    status: Mapped[TaskStepStatus] = mapped_column(
        String(32),
        nullable=False,
        default=TaskStepStatus.PENDING,
        index=True,
    )

    input_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    output_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
