"""repair missing code chunks table

Revision ID: 9f2c6a1b4d7e
Revises: bf47a8071d7f
Create Date: 2026-09-19

Repairs schema drift where the historical code_chunks migrations are
recorded as applied but the physical table is missing.
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "9f2c6a1b4d7e"
down_revision: str | Sequence[str] | None = "bf47a8071d7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Restore code_chunks when the table is missing."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    table_exists = op.get_bind().execute(
        sa.text("SELECT to_regclass('public.code_chunks')")
    ).scalar()

    if table_exists is not None:
        return

    op.create_table(
        "code_chunks",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("file_path", sa.String(length=2048), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("symbol_name", sa.String(length=512), nullable=False),
        sa.Column("symbol_type", sa.String(length=50), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("parent", sa.String(length=512), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=768),
            nullable=True,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "repository_id",
            "commit_sha",
            "file_path",
            "start_line",
            "end_line",
            "symbol_name",
            "symbol_type",
            name="uq_code_chunks_repository_commit_symbol",
        ),
    )

    op.create_index(
        "ix_code_chunks_content_hash",
        "code_chunks",
        ["content_hash"],
        unique=False,
    )

    op.create_index(
        "ix_code_chunks_repository_id",
        "code_chunks",
        ["repository_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the repaired code_chunks table."""
    table_exists = op.get_bind().execute(
        sa.text("SELECT to_regclass('public.code_chunks')")
    ).scalar()

    if table_exists is None:
        return

    op.drop_index(
        "ix_code_chunks_repository_id",
        table_name="code_chunks",
    )
    op.drop_index(
        "ix_code_chunks_content_hash",
        table_name="code_chunks",
    )
    op.drop_table("code_chunks")
