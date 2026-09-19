"""add background jobs

Revision ID: 7d5392a4139d
Revises: 30199e05c57d
Create Date: 2026-09-19 15:40:45.324385
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7d5392a4139d"
down_revision: str | Sequence[str] | None = "30199e05c57d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "job_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "attempt",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_background_jobs_task_id",
        "background_jobs",
        ["task_id"],
    )

    op.create_index(
        "ix_background_jobs_job_type",
        "background_jobs",
        ["job_type"],
    )

    op.create_index(
        "ix_background_jobs_status",
        "background_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_background_jobs_status",
        table_name="background_jobs",
    )

    op.drop_index(
        "ix_background_jobs_job_type",
        table_name="background_jobs",
    )

    op.drop_index(
        "ix_background_jobs_task_id",
        table_name="background_jobs",
    )

    op.drop_table("background_jobs")
