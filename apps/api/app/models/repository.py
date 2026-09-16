from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.models.base import Base, TimestampMixin


class Repository(TimestampMixin, Base):
    __tablename__ = "repositories"

    __table_args__ = (
        UniqueConstraint(
            "github_repo_id",
            name="uq_repositories_github_repo_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(511),
        nullable=False,
        unique=True,
    )

    github_repo_id: Mapped[int] = mapped_column(
        nullable=False,
    )

    default_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="main",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_private: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    clone_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )
