"""Additive durable ingestion cursor and bundled execution records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class IngestionEvent(Base):
    __tablename__ = "ingestion_events"
    __table_args__ = {"sqlite_autoincrement": True}

    cursor: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    span_id: Mapped[str] = mapped_column(String(36), unique=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cohort_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class PortfolioExecution(Base):
    __tablename__ = "portfolio_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    scenario: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    # A nullable UNIQUE slot enforces one reserved active execution.
    active_slot: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    cohort_id: Mapped[str] = mapped_column(String(36), unique=True)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=20)
    run_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    application_outcomes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    delivery: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def response(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "scenario": self.scenario,
            "status": self.status,
            "cohort_id": self.cohort_id,
            "progress": {"completed": self.completed, "total": self.total},
            "run_ids": self.run_ids,
            "application_outcomes": self.application_outcomes,
            "delivery": self.delivery,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
