"""Tests for AgentTrace-owned canonical ingestion contracts."""

from __future__ import annotations

from app.internal.compat import normalize_cost_record, normalize_span
from app.internal.contracts import CanonicalCostRecord, CanonicalSpan
from app.internal.vendor_core.tracing import CostRecord, Span, SpanStatus, SpanType


def test_normalize_span_accepts_vendor_model_and_preserves_wire_shape() -> None:
    span = Span(
        trace_id="trace-1",
        span_id="span-1",
        name="lookup",
        span_type=SpanType.TOOL,
        status=SpanStatus.OK,
        start_ms=10.0,
        end_ms=25.0,
        attributes={"query": "agenttrace"},
    )

    normalized = normalize_span(span)

    assert isinstance(normalized, CanonicalSpan)
    assert normalized.model_dump(mode="json") == {
        "trace_id": "trace-1",
        "span_id": "span-1",
        "parent_span_id": None,
        "name": "lookup",
        "span_type": "tool",
        "status": "ok",
        "start_ms": 10.0,
        "end_ms": 25.0,
        "attributes": {"query": "agenttrace"},
    }


def test_normalize_span_accepts_mapping_and_normalizes_unknown_values() -> None:
    normalized = normalize_span(
        {
            "traceId": "trace-2",
            "spanId": "span-2",
            "name": "custom",
            "span_type": "unknown-kind",
            "status": "unknown-status",
            "start_ms": 0,
        }
    )

    assert normalized.span_type == "other"
    assert normalized.status == "ok"
    assert normalized.trace_id == "trace-2"


def test_normalize_cost_record_accepts_vendor_model() -> None:
    record = CostRecord(
        trace_id="trace-3",
        model="gpt-4o-mini",
        provider="openai",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        estimated_cost=0.001,
        latency_ms=42.0,
    )

    normalized = normalize_cost_record(record)

    assert isinstance(normalized, CanonicalCostRecord)
    assert normalized.model_dump(mode="json")["estimated_cost"] == 0.001
    assert normalized.total_tokens == 15


def test_compatible_camel_case_cost_record_is_normalized() -> None:
    normalized = normalize_cost_record(
        {
            "traceId": "trace-camel",
            "spanId": "span-camel",
            "model": "fixture-model",
            "promptTokens": 4,
            "completionTokens": 6,
            "estimatedCost": 0.12,
            "latencyMs": 9,
        }
    )

    assert normalized.trace_id == "trace-camel"
    assert normalized.resolved_total_tokens() == 10
    assert normalized.estimated_cost == 0.12
