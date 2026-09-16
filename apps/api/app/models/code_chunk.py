from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.models.base import Base, TimestampMixin


class CodeChunk(TimestampMixin, Base):
    __tablename__ = "code_chunks"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    repository_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    symbol_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    symbol_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    start_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    end_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    parent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    commit_sha: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "commit_sha",
            "file_path",
            "start_line",
            "end_line",
            name="uq_code_chunks_repository_commit_location",
        ),
        Index(
            "ix_code_chunks_repository_id",
            "repository_id",
        ),
        Index(
            "ix_code_chunks_content_hash",
            "content_hash",
        ),
    )
