"""Run model — SQLAlchemy model and Pydantic schemas for agent runs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator
from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Run(Base):
    """SQLAlchemy model for storing agent run records.

    Each run represents a complete agent execution from start to finish,
    aggregating cost and token data from its associated spans.

    Attributes:
        id: Unique run identifier.
        correlation_id: Optional correlation ID for multi-agent trace correlation.
        name: Human-readable run name.
        status: Current run status (running, completed, failed, cancelled).
        start_time: When the run started.
        end_time: When the run ended.
        total_cost: Aggregate cost in USD.
        total_tokens: Aggregate token count.
        span_count: Number of spans in this run.
        metadata: Arbitrary run-level metadata as JSON.
    """

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(36), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    start_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    span_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_metadata: Mapped[Optional[dict]] = mapped_column(
        "run_metadata", JSON, nullable=True
    )
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    feature: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )


class RunCreate(BaseModel):
    """Pydantic schema for creating a new run.

    Attributes:
        id: Optional client-provided run identifier.
        correlation_id: Optional correlation ID for multi-agent trace correlation.
        name: Human-readable run name.
        status: Initial run status.
        start_time: Run start timestamp.
        end_time: Run end timestamp (null if still running).
        total_cost: Aggregate cost in USD.
        total_tokens: Aggregate token count.
        span_count: Number of spans.
        metadata: Arbitrary run-level metadata.
    """

    id: Optional[str] = Field(None, description="Client-provided run identifier")
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for multi-agent trace correlation"
    )
    name: str = Field(..., description="Human-readable run name")
    status: str = Field("running", description="Initial run status")
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Run start time"
    )
    end_time: Optional[datetime] = Field(None, description="Run end time")
    total_cost: float = Field(0.0, description="Total cost in USD")
    total_tokens: int = Field(0, description="Total token count")
    span_count: int = Field(0, description="Number of spans")
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Run metadata",
        validation_alias=AliasChoices("metadata", "run_metadata"),
    )
    workflow_id: Optional[str] = Field(None, description="Workflow identifier")
    feature: Optional[str] = Field(None, description="Feature or component name")


class RunResponse(BaseModel):
    """Pydantic schema for run API responses.

    Supports conversion from both dict and ORM model via model_validator.
    """

    id: str
    correlation_id: Optional[str]
    name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    total_cost: float
    total_tokens: int
    span_count: int
    metadata: Optional[dict[str, Any]]
    workflow_id: Optional[str] = None
    feature: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def from_orm(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        if hasattr(data, "run_metadata"):
            return {
                "id": data.id,
                "correlation_id": data.correlation_id,
                "name": data.name,
                "status": data.status,
                "start_time": data.start_time,
                "end_time": data.end_time,
                "total_cost": data.total_cost,
                "total_tokens": data.total_tokens,
                "span_count": data.span_count,
                "metadata": data.run_metadata,
                "workflow_id": data.workflow_id,
                "feature": data.feature,
            }
        return data


class RunListResponse(BaseModel):
    """Pydantic schema for paginated run list responses.

    Attributes:
        runs: List of runs for the current page.
        total: Total number of runs.
        limit: Page size.
        offset: Current page offset.
    """

    runs: list[RunResponse] = Field(..., description="List of runs")
    total: int = Field(..., description="Total number of runs")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current page offset")
