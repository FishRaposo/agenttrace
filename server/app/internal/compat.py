"""Normalization adapters for canonical trace and cost producer objects."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from app.internal.contracts import CanonicalCostRecord, CanonicalSpan


def _value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return dict(value.model_dump(mode="json"))
    if hasattr(value, "dict"):
        return dict(value.dict())
    return dict(vars(value))


def normalize_span(value: Any) -> CanonicalSpan:
    """Normalize a mapping, Pydantic model, or compatible span object."""
    raw = _mapping(value)
    normalized = {
        "trace_id": raw.get("trace_id", raw.get("traceId")),
        "span_id": raw.get("span_id", raw.get("spanId")),
        "parent_span_id": raw.get("parent_span_id", raw.get("parentSpanId")),
        "name": raw.get("name", "span"),
        "span_type": _value(raw.get("span_type", raw.get("spanType", "other"))),
        "status": _value(raw.get("status", "ok")),
        "start_ms": raw.get("start_ms", raw.get("startTimeMs", 0.0)),
        "end_ms": raw.get("end_ms", raw.get("endTimeMs")),
        "attributes": dict(raw.get("attributes", raw.get("metadata")) or {}),
    }
    if normalized["span_type"] not in {"llm", "tool", "retrieval", "decision", "other"}:
        normalized["span_type"] = "other"
    if normalized["status"] not in {"ok", "error"}:
        normalized["status"] = "ok"
    return CanonicalSpan.model_validate(normalized)


def normalize_cost_record(value: Any) -> CanonicalCostRecord:
    """Normalize a mapping, Pydantic model, or compatible cost object."""
    raw = _mapping(value)
    return CanonicalCostRecord.model_validate(
        {
            "trace_id": raw.get("trace_id", raw.get("traceId")),
            "span_id": raw.get("span_id", raw.get("spanId")),
            "model": raw.get("model", "unknown"),
            "provider": raw.get("provider"),
            "prompt_tokens": raw.get("prompt_tokens", raw.get("promptTokens", 0)),
            "completion_tokens": raw.get(
                "completion_tokens", raw.get("completionTokens", 0)
            ),
            "total_tokens": raw.get("total_tokens", raw.get("totalTokens", 0)),
            "estimated_cost": raw.get(
                "estimated_cost", raw.get("estimatedCost", raw.get("costUsd", 0.0))
            ),
            "latency_ms": raw.get("latency_ms", raw.get("latencyMs", 0.0)),
            "name": raw.get("name"),
            "feature": raw.get("feature"),
        }
    )
