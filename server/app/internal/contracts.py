"""Stable, provider-neutral ingestion contracts owned by AgentTrace."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class CanonicalSpan(BaseModel):
    """Wire-compatible canonical span accepted by the collector."""

    trace_id: str = Field(validation_alias=AliasChoices("trace_id", "traceId"))
    span_id: str = Field(validation_alias=AliasChoices("span_id", "spanId"))
    parent_span_id: str | None = Field(
        None, validation_alias=AliasChoices("parent_span_id", "parentSpanId")
    )
    name: str
    span_type: str = Field(
        "other", validation_alias=AliasChoices("span_type", "spanType")
    )
    status: str = "ok"
    start_ms: float = Field(
        0.0, validation_alias=AliasChoices("start_ms", "startTimeMs")
    )
    end_ms: float | None = Field(
        None, validation_alias=AliasChoices("end_ms", "endTimeMs")
    )
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "extra": "ignore"}


class CanonicalCostRecord(BaseModel):
    """Wire-compatible cost record accepted by the collector."""

    trace_id: str | None = Field(
        None, validation_alias=AliasChoices("trace_id", "traceId")
    )
    span_id: str | None = Field(
        None, validation_alias=AliasChoices("span_id", "spanId")
    )
    model: str
    provider: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = Field(
        0.0, validation_alias=AliasChoices("estimated_cost", "costUsd")
    )
    latency_ms: float = Field(
        0.0, validation_alias=AliasChoices("latency_ms", "latencyMs")
    )
    name: str | None = None
    feature: str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}

    def resolved_total_tokens(self) -> int:
        return self.total_tokens or self.prompt_tokens + self.completion_tokens
