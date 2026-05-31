"""add correlation_id to runs

Revision ID: add_correlation_id
Revises: cff8a8f3f61d
Create Date: 2026-05-08 06:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_correlation_id'
down_revision: Union[str, Sequence[str], None] = 'cff8a8f3f61d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('runs', sa.Column('correlation_id', sa.String(36), nullable=True))
    op.create_index(op.f('ix_runs_correlation_id'), 'runs', ['correlation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_runs_correlation_id'), table_name='runs')
    op.drop_column('runs', 'correlation_id')
