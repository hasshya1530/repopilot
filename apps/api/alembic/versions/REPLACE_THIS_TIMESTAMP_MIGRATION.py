"""add timestamp defaults to background jobs

Revision ID: REPLACE_WITH_GENERATED_REVISION
Revises: 7d5392a4139d
"""

from typing import Sequence

from alembic import op


revision: str = "REPLACE_WITH_GENERATED_REVISION"
down_revision: str | Sequence[str] | None = "7d5392a4139d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE background_jobs
        ALTER COLUMN created_at
        SET DEFAULT NOW()
        """
    )

    op.execute(
        """
        ALTER TABLE background_jobs
        ALTER COLUMN updated_at
        SET DEFAULT NOW()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE background_jobs
        ALTER COLUMN updated_at
        DROP DEFAULT
        """
    )

    op.execute(
        """
        ALTER TABLE background_jobs
        ALTER COLUMN created_at
        DROP DEFAULT
        """
    )
