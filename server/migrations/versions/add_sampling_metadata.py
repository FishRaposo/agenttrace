"""Add deterministic sampling metadata to traces."""

from alembic import op
import sqlalchemy as sa


revision = "add_sampling_metadata"
down_revision = "add_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("traces", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("sampled", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(sa.Column("sampling_reason", sa.String(length=50)))


def downgrade() -> None:
    with op.batch_alter_table("traces", schema=None) as batch_op:
        batch_op.drop_column("sampling_reason")
        batch_op.drop_column("sampled")
