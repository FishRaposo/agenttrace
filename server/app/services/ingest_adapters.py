"""Ingestion adapters — convert canonical trace primitives into AgentTrace records.

The collector accepts spans emitted by any compatible producer and cost records
using the canonical trace contract. These adapters
normalize the canonical shapes into the server's :class:`~app.models.trace.TraceCreate`
schema so they flow through the same ``TraceService`` ingestion path as native SDK
spans, with no change to the stored representation.

Design goals:

* **Lossless where it matters** — token usage, cost, latency, model/provider and
  the originating ``trace_id`` are all preserved.
* **No new numeric behavior** — cost is taken verbatim from the inbound record;
  the adapters never recompute pricing, so existing golden cost outputs are
  untouched.
* **Stable span vocabulary** — canonical span types/statuses
  are mapped onto AgentTrace's existing vocabulary so the dashboard and analytics
  continue to work unchanged.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.internal.compat import normalize_cost_record, normalize_span
from app.internal.contracts import CanonicalCostRecord, CanonicalSpan
from app.models.trace import TraceCreate

# Canonical span type -> AgentTrace span_type vocabulary.
_SPAN_TYPE_MAP: dict[str, str] = {
    "llm": "llm_call",
    "tool": "tool_call",
    "retrieval": "retrieval",
    "decision": "decision",
    "other": "custom",
}

# Canonical span status -> AgentTrace span status vocabulary.
_SPAN_STATUS_MAP: dict[str, str] = {
    "ok": "completed",
    "error": "error",
}


def map_span_type(span_type: str) -> str:
    """Map a canonical ``shared_core`` span type to AgentTrace's vocabulary.

    Unknown values pass through unchanged so the collector stays forward
    compatible with span types it does not yet model.

    Args:
        span_type: The inbound ``shared_core.tracing.SpanType`` value.

    Returns:
        The corresponding AgentTrace span type string.
    """
    return _SPAN_TYPE_MAP.get(span_type, span_type)


def map_span_status(status: str) -> str:
    """Map a canonical ``shared_core`` span status to AgentTrace's vocabulary.

    Args:
        status: The inbound ``shared_core.tracing.SpanStatus`` value.

    Returns:
        The corresponding AgentTrace status string.
    """
    return _SPAN_STATUS_MAP.get(status, status)


SharedSpanIngest = CanonicalSpan
CostRecordIngest = CanonicalCostRecord


class _LegacySpanDoc:
    """Documentation marker for the retained ``SharedSpanIngest`` alias.

    The alias accepts the exact JSON produced by canonical producer objects.
    """


def _ms_to_datetime(value: float) -> datetime:
    """Convert epoch milliseconds to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)


def span_to_trace_create(span: SharedSpanIngest | Any) -> TraceCreate:
    """Convert a canonical span into a :class:`TraceCreate`.

    Cost, token usage, model, provider and feature are lifted out of the span
    ``attributes`` bag when present (the convention used by canonical
    producers), and otherwise left ``None``. No cost is computed here.

    Args:
        span: The validated inbound span.

    Returns:
        A ``TraceCreate`` ready for ``TraceService.ingest_trace``.
    """
    span = normalize_span(span)
    attrs = dict(span.attributes or {})

    cost_usd = attrs.pop("cost_usd", None)
    if cost_usd is None:
        cost_usd = attrs.pop("estimated_cost", None)

    token_usage = attrs.pop("token_usage", None)
    if token_usage is None:
        prompt = attrs.pop("prompt_tokens", None)
        completion = attrs.pop("completion_tokens", None)
        total = attrs.pop("total_tokens", None)
        if prompt is not None or completion is not None or total is not None:
            prompt = int(prompt or 0)
            completion = int(completion or 0)
            resolved_total = int(total) if total is not None else prompt + completion
            token_usage = {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": resolved_total,
            }

    model = attrs.pop("model", None)
    provider = attrs.pop("provider", None)
    feature = attrs.pop("feature", None)

    start_time = _ms_to_datetime(span.start_ms)
    end_time = _ms_to_datetime(span.end_ms) if span.end_ms is not None else None
    duration_ms = (span.end_ms - span.start_ms) if span.end_ms is not None else None

    return TraceCreate(
        run_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        span_type=map_span_type(span.span_type),
        name=span.name,
        input_data=attrs.get("input") or attrs.get("input_data"),
        output_data=attrs.get("output") or attrs.get("output_data"),
        metadata=attrs or None,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        cost_usd=float(cost_usd) if cost_usd is not None else None,
        token_usage=token_usage,
        status=map_span_status(span.status),
        error=attrs.get("error"),
        model=model,
        provider=provider,
        feature=feature,
        sampled=True,
        sampling_reason=None,
    )


class _LegacyCostDoc:
    """Documentation marker for the retained ``CostRecordIngest`` alias.

    A cost record is materialized as a single ``llm_call`` span so it shows up
    in the same cost-attribution analytics as native traces.
    """


def cost_record_to_trace_create(record: CostRecordIngest | Any) -> TraceCreate:
    """Convert a canonical cost record into a :class:`TraceCreate`.

    The record becomes an ``llm_call`` span carrying the verbatim ``estimated_cost``
    and token usage. ``total_tokens`` falls back to ``prompt + completion`` when not
    provided. No pricing math runs here — the inbound cost is authoritative.

    Args:
        record: The validated inbound cost record.

    Returns:
        A ``TraceCreate`` for ``TraceService.ingest_trace``.
    """
    import uuid

    record = normalize_cost_record(record)
    total = record.resolved_total_tokens()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(milliseconds=record.latency_ms)

    return TraceCreate(
        run_id=record.trace_id or f"cost-{uuid.uuid4().hex}",
        span_id=record.span_id or uuid.uuid4().hex,
        parent_span_id=None,
        span_type="llm_call",
        name=record.name or f"{record.model} invocation",
        input_data=None,
        output_data=None,
        metadata=None,
        start_time=start_time,
        end_time=end_time,
        duration_ms=record.latency_ms,
        cost_usd=record.estimated_cost,
        token_usage={
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": total,
        },
        status="completed",
        error=None,
        model=record.model,
        provider=record.provider,
        feature=record.feature,
        sampled=True,
        sampling_reason=None,
    )
