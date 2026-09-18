"""change github pr id to bigint

Revision ID: 30199e05c57d
Revises: 81a45db21e7d
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "30199e05c57d"
down_revision: str | Sequence[str] | None = "81a45db21e7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "pull_requests",
        "github_pr_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "pull_requests",
        "github_pr_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
