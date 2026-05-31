"""Span module — defines span types, statuses, and the Span dataclass."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class SpanType(str, Enum):
    """Types of operations that can be traced."""

    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    RETRIEVAL = "retrieval"
    CUSTOM = "custom"


class SpanStatus(str, Enum):
    """Lifecycle states of a span."""

    STARTED = "started"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Span:
    """Represents a single traced operation within a run.

    Attributes:
        id: Unique span identifier.
        run_id: Parent run identifier.
        name: Human-readable span name.
        span_type: Type of operation being traced.
        status: Current lifecycle state.
        input_data: Input payload for the operation.
        output_data: Output payload from the operation.
        metadata: Additional span-specific metadata.
        start_time: When the span started.
        end_time: When the span ended.
        duration_ms: Duration in milliseconds.
        cost_usd: Cost in USD (primarily for LLM spans).
        token_usage: Token consumption details.
        error: Error message if the span failed.
        parent_span_id: Parent span identifier for nesting.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: Optional[str] = None
    name: str = ""
    span_type: SpanType = SpanType.CUSTOM
    status: SpanStatus = SpanStatus.STARTED
    input_data: Any = None
    output_data: Any = None
    metadata: Optional[dict[str, Any]] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    cost_usd: Optional[float] = None
    token_usage: Optional[dict[str, int]] = None
    error: Optional[str] = None
    parent_span_id: Optional[str] = None

    def end(self, output: Any = None) -> None:
        """Mark the span as completed and record output.

        Args:
            output: The output data from the traced operation.
        """
        self.output_data = output
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = SpanStatus.COMPLETED

    def set_error(self, error: str) -> None:
        """Mark the span as errored.

        Args:
            error: Description of the error that occurred.
        """
        self.error = error
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = SpanStatus.ERROR

    def set_output(self, output: Any) -> None:
        """Set the output data without ending the span.

        Args:
            output: The output data to record.
        """
        self.output_data = output

    def to_dict(self) -> dict[str, Any]:
        """Convert the span to a dictionary for serialization.

        Returns:
            Dictionary representation of the span.
        """
        return {
            "id": self.id,
            "run_id": self.run_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "span_type": self.span_type.value,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "metadata": self.metadata,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "cost_usd": self.cost_usd,
            "token_usage": self.token_usage,
            "error": self.error,
        }
