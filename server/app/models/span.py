"""Span model — SQLAlchemy model and Pydantic schemas for hierarchical spans."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SpanEntry(Base):
    """SQLAlchemy model for storing hierarchical span data.

    Supports parent-child relationships between spans for nested
    operation tracing.

    Attributes:
        id: Unique span entry identifier.
        trace_id: Parent trace identifier.
        parent_span_id: Parent span for nesting (null for top-level).
        name: Human-readable span name.
        span_type: Type of operation.
        input_data: Input payload as JSON.
        output_data: Output payload as JSON.
        start_time: When the span started.
        end_time: When the span ended.
        duration_ms: Duration in milliseconds.
        status: Span status.
        error: Error message if the span failed.
    """

    __tablename__ = "span_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    parent_span_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    span_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_data: Mapped[Optional[dict]] = mapped_column("span_input_data", JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column("span_output_data", JSON, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SpanCreate(BaseModel):
    """Pydantic schema for creating a new span entry.

    Attributes:
        trace_id: Parent trace identifier.
        parent_span_id: Parent span identifier for nesting.
        name: Span name.
        span_type: Type of operation.
        input_data: Input payload.
        output_data: Output payload.
        start_time: Start timestamp.
        end_time: End timestamp.
        duration_ms: Duration in milliseconds.
        status: Span status.
        error: Error message.
    """

    trace_id: str = Field(..., description="Parent trace identifier")
    parent_span_id: Optional[str] = Field(None, description="Parent span for nesting")
    name: str = Field(..., description="Human-readable span name")
    span_type: str = Field(..., description="Type of operation")
    input_data: Optional[Any] = Field(None, description="Input payload")
    output_data: Optional[Any] = Field(None, description="Output payload")
    start_time: datetime = Field(..., description="Span start time")
    end_time: Optional[datetime] = Field(None, description="Span end time")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    status: str = Field("started", description="Span status")
    error: Optional[str] = Field(None, description="Error message")


class SpanResponse(BaseModel):
    """Pydantic schema for span API responses.

    Attributes:
        id: Database record ID.
        trace_id: Parent trace identifier.
        parent_span_id: Parent span identifier.
        name: Span name.
        span_type: Type of operation.
        input_data: Input payload.
        output_data: Output payload.
        start_time: Start timestamp.
        end_time: End timestamp.
        duration_ms: Duration in milliseconds.
        status: Span status.
        error: Error message.
    """

    id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: str
    input_data: Optional[Any]
    output_data: Optional[Any]
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    status: str
    error: Optional[str]

    model_config = {"from_attributes": True}
