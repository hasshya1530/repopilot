"""set code chunk embedding dimension

Revision ID: 390a9755c440
Revises: 13fa0ebf6980
Create Date: 2026-09-17 00:23:54.321881

"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "390a9755c440"
down_revision: str | Sequence[str] | None = "13fa0ebf6980"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Set the code chunk embedding dimension to 768."""
    op.alter_column(
        "code_chunks",
        "embedding",
        existing_type=Vector(),
        type_=Vector(768),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Remove the fixed embedding dimension."""
    op.alter_column(
        "code_chunks",
        "embedding",
        existing_type=Vector(768),
        type_=Vector(),
        existing_nullable=True,
    )
