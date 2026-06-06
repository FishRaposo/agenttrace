"""Span model — Pydantic schemas for hierarchical spans.

Note: Spans are stored as JSON inside the Trace model's ``spans`` column.
The SpanEntry SQLAlchemy model was removed — all span data lives in traces.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


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
