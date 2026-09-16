from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.models.base import Base, TimestampMixin


class TestRunStatus(StrEnum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


class TestRun(TimestampMixin, Base):
    __tablename__ = "test_runs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    agent_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    command: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    status: Mapped[TestRunStatus] = mapped_column(
        String(32),
        nullable=False,
        default=TestRunStatus.RUNNING,
        index=True,
    )

    exit_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    stdout: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    stderr: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    working_directory: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
