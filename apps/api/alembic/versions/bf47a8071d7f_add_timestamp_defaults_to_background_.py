"""add timestamp defaults to background jobs

Revision ID: bf47a8071d7f
Revises: 7d5392a4139d
Create Date: 2026-09-19 16:23:24.621869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf47a8071d7f'
down_revision: Union[str, Sequence[str], None] = '7d5392a4139d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
