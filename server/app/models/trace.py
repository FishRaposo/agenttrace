"""Trace model — SQLAlchemy model and Pydantic schemas for trace data."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator
from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Trace(Base):
    """SQLAlchemy model for storing trace data.

    Each trace record represents a single span captured from an agent run.

    Attributes:
        id: Unique trace identifier.
        run_id: The run this trace belongs to.
        span_id: The span identifier from the SDK.
        span_type: Type of operation (llm_call, tool_call, etc.).
        name: Human-readable span name.
        input_data: Input payload as JSON.
        output_data: Output payload as JSON.
        metadata: Additional metadata as JSON.
        start_time: When the span started.
        end_time: When the span ended.
        duration_ms: Duration in milliseconds.
        cost_usd: Cost in USD.
        token_usage: Token usage details as JSON.
        status: Span status (started, completed, error).
        error: Error message if the span failed.
    """

    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    span_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    span_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_data: Mapped[Optional[dict]] = mapped_column(
        "trace_input", JSON, nullable=True
    )
    output_data: Mapped[Optional[dict]] = mapped_column(
        "trace_output", JSON, nullable=True
    )
    trace_metadata: Mapped[Optional[dict]] = mapped_column(
        "trace_metadata", JSON, nullable=True
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    token_usage: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # Cost-attribution columns
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    provider: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    feature: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    sampled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sampling_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class TraceCreate(BaseModel):
    """Pydantic schema for creating a new trace.

    Attributes:
        run_id: The run this trace belongs to.
        span_id: Unique span identifier.
        span_type: Type of operation.
        name: Span name.
        input_data: Input payload.
        output_data: Output payload.
        metadata: Additional metadata.
        start_time: Start timestamp.
        end_time: End timestamp.
        duration_ms: Duration in milliseconds.
        cost_usd: Cost in USD.
        token_usage: Token usage details.
        status: Span status.
        error: Error message.
    """

    run_id: str = Field(..., description="Parent run identifier")
    span_id: str = Field(..., description="Unique span identifier")
    span_type: str = Field(..., description="Type of operation")
    name: str = Field(..., description="Human-readable span name")
    input_data: Optional[Any] = Field(None, description="Input payload")
    output_data: Optional[Any] = Field(None, description="Output payload")
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Additional metadata",
        validation_alias=AliasChoices("metadata", "trace_metadata"),
    )
    start_time: datetime = Field(..., description="Span start time")
    end_time: Optional[datetime] = Field(None, description="Span end time")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    cost_usd: Optional[float] = Field(None, description="Cost in USD")
    token_usage: Optional[dict[str, int]] = Field(None, description="Token usage")
    status: str = Field("started", description="Span status")
    error: Optional[str] = Field(None, description="Error message")
    parent_span_id: Optional[str] = Field(None, description="Parent span ID")
    model: Optional[str] = Field(None, description="LLM model name")
    provider: Optional[str] = Field(None, description="LLM provider")
    feature: Optional[str] = Field(None, description="Feature or workflow component")
    sampled: bool = Field(True, description="Whether the span was retained by sampling")
    sampling_reason: Optional[str] = Field(
        None, description="Deterministic sampling decision reason"
    )

    @model_validator(mode="before")
    @classmethod
    def extract_cost_attribution(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        meta = data.get("metadata") or {}
        if not isinstance(meta, dict):
            return data
        # Populate from metadata if not explicitly set
        for field in ("model", "provider", "feature"):
            if data.get(field) is None and meta.get(field):
                data[field] = meta[field]
        # Remove duplicated keys from metadata
        for field in ("model", "provider", "feature"):
            meta.pop(field, None)
        return data


class TraceResponse(BaseModel):
    """Pydantic schema for trace API responses.

    Supports conversion from both dict and ORM model via model_validator.
    """

    id: str
    run_id: str
    span_id: str
    span_type: str
    name: str
    input_data: Optional[Any]
    output_data: Optional[Any]
    metadata: Optional[dict[str, Any]]
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    cost_usd: Optional[float]
    token_usage: Optional[dict[str, int]]
    status: str
    error: Optional[str]
    parent_span_id: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    feature: Optional[str] = None
    sampled: bool = True
    sampling_reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def from_source(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        if hasattr(data, "trace_metadata"):
            return {
                "id": data.id,
                "run_id": data.run_id,
                "span_id": data.span_id,
                "parent_span_id": data.parent_span_id,
                "span_type": data.span_type,
                "name": data.name,
                "input_data": data.input_data,
                "output_data": data.output_data,
                "metadata": data.trace_metadata,
                "start_time": data.start_time,
                "end_time": data.end_time,
                "duration_ms": data.duration_ms,
                "cost_usd": data.cost_usd,
                "token_usage": data.token_usage,
                "status": data.status,
                "error": data.error,
                "model": data.model,
                "provider": data.provider,
                "feature": data.feature,
                "sampled": data.sampled,
                "sampling_reason": data.sampling_reason,
            }
        return data
