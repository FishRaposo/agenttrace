"""Add durable ingestion cursors and bundled local execution reservations."""

from alembic import op
import sqlalchemy as sa

revision = "add_delivery_executions"
down_revision = "add_alert_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_events",
        sa.Column("cursor", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trace_id", sa.String(36), nullable=False, unique=True),
        sa.Column("span_id", sa.String(36), nullable=False, unique=True),
        sa.Column("payload_hash", sa.String(64), nullable=True),
        sa.Column("cohort_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_ingestion_events_trace_id", "ingestion_events", ["trace_id"])
    op.create_index("ix_ingestion_events_cohort_id", "ingestion_events", ["cohort_id"])
    op.execute(
        sa.text(
            "INSERT INTO ingestion_events (trace_id, span_id, created_at) "
            "SELECT id, span_id, CURRENT_TIMESTAMP FROM traces ORDER BY start_time, id"
        )
    )
    op.create_table(
        "portfolio_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False, unique=True),
        sa.Column("scenario", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("active_slot", sa.Integer(), nullable=True, unique=True),
        sa.Column("cohort_id", sa.String(36), nullable=False, unique=True),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("run_ids", sa.JSON(), nullable=False),
        sa.Column("application_outcomes", sa.JSON(), nullable=False),
        sa.Column("delivery", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("portfolio_executions")
    op.drop_table("ingestion_events")
