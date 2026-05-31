"""Add cost attribution columns to traces and runs, plus budgets table.

Revision ID: add_cost_attribution_columns
Revises: add_correlation_id_to_runs
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_cost_attribution_columns"
down_revision = "add_correlation_id_to_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to traces using batch alter for SQLite compatibility
    with op.batch_alter_table("traces", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parent_span_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("model", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("provider", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("feature", sa.String(length=100), nullable=True))
        batch_op.create_index("ix_traces_model", ["model"], unique=False)
        batch_op.create_index("ix_traces_provider", ["provider"], unique=False)
        batch_op.create_index("ix_traces_feature", ["feature"], unique=False)

    # Add columns to runs
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("workflow_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("feature", sa.String(length=100), nullable=True))
        batch_op.create_index("ix_runs_workflow_id", ["workflow_id"], unique=False)
        batch_op.create_index("ix_runs_feature", ["feature"], unique=False)

    # Create budgets table
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("scope_value", sa.String(length=255), nullable=True),
        sa.Column("limit_usd", sa.Float(), nullable=False),
        sa.Column("period", sa.String(length=50), nullable=False),
        sa.Column("alert_threshold_pct", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("budgets")

    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.drop_index("ix_runs_feature")
        batch_op.drop_index("ix_runs_workflow_id")
        batch_op.drop_column("feature")
        batch_op.drop_column("workflow_id")

    with op.batch_alter_table("traces", schema=None) as batch_op:
        batch_op.drop_index("ix_traces_feature")
        batch_op.drop_index("ix_traces_provider")
        batch_op.drop_index("ix_traces_model")
        batch_op.drop_column("feature")
        batch_op.drop_column("provider")
        batch_op.drop_column("model")
        batch_op.drop_column("parent_span_id")
