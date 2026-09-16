from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.models.base import Base, TimestampMixin


class FileChangeOperation(StrEnum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


class FileChange(TimestampMixin, Base):
    __tablename__ = "file_changes"

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

    file_path: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        index=True,
    )

    operation: Mapped[FileChangeOperation] = mapped_column(
        String(32),
        nullable=False,
    )

    before_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    after_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    diff: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    before_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    after_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    line_additions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    line_deletions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
