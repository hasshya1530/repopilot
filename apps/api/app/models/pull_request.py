from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.models.base import Base, TimestampMixin


class PullRequestStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    MERGED = "merged"
    CLOSED = "closed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PullRequest(TimestampMixin, Base):
    __tablename__ = "pull_requests"

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

    github_pr_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
    )

    pr_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    target_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[PullRequestStatus] = mapped_column(
        String(32),
        nullable=False,
        default=PullRequestStatus.DRAFT,
        index=True,
    )

    approval_status: Mapped[ApprovalStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )

    github_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    review_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    merge_commit_sha: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
