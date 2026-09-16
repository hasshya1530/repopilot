"""update code chunk uniqueness

Revision ID: 81a45db21e7d
Revises: 390a9755c440
Create Date: 2026-09-17 01:10:46.912203

"""

from collections.abc import Sequence

from alembic import op

revision: str = "81a45db21e7d"
down_revision: str | Sequence[str] | None = "390a9755c440"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("uq_code_chunks_repository_commit_location"),
        "code_chunks",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_code_chunks_repository_commit_symbol",
        "code_chunks",
        [
            "repository_id",
            "commit_sha",
            "file_path",
            "start_line",
            "end_line",
            "symbol_name",
            "symbol_type",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_code_chunks_repository_commit_symbol",
        "code_chunks",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_code_chunks_repository_commit_location"),
        "code_chunks",
        [
            "repository_id",
            "commit_sha",
            "file_path",
            "start_line",
            "end_line",
        ],
        postgresql_nulls_not_distinct=False,
    )
