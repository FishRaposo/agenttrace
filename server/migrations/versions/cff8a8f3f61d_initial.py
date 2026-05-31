"""initial

Revision ID: cff8a8f3f61d
Revises: 
Create Date: 2026-05-08 03:13:51.622317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cff8a8f3f61d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("span_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_runs_correlation_id", "runs", ["correlation_id"])

    op.create_table(
        "traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("span_id", sa.String(36), nullable=False),
        sa.Column("span_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trace_input", sa.JSON(), nullable=True),
        sa.Column("trace_output", sa.JSON(), nullable=True),
        sa.Column("trace_metadata", sa.JSON(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="started"),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_traces_run_id", "traces", ["run_id"])
    op.create_unique_constraint("uq_traces_span_id", "traces", ["span_id"])
    op.create_index("ix_traces_start_time", "traces", ["start_time"])

    op.create_table(
        "span_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("parent_span_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("span_type", sa.String(50), nullable=False),
        sa.Column("span_input_data", sa.JSON(), nullable=True),
        sa.Column("span_output_data", sa.JSON(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="started"),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_span_entries_trace_id", "span_entries", ["trace_id"])
    op.create_index("ix_span_entries_parent_span_id", "span_entries", ["parent_span_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("span_entries")
    op.drop_table("traces")
    op.drop_table("runs")
