"""Tests for shared_core convergence ingestion paths and adapters.

Covers the cross-service ingestion endpoints (canonical ``shared_core`` spans and
LCM-style cost records) and the adapter unit logic that normalizes them, plus the
shared_core ``Span``/``CostRecord`` round-trip to prove wire compatibility.
"""

from __future__ import annotations

import time

import pytest
from app.services.ingest_adapters import (
    CostRecordIngest,
    SharedSpanIngest,
    cost_record_to_trace_create,
    map_span_status,
    map_span_type,
    span_to_trace_create,
)
from httpx import AsyncClient
from shared_core.tracing import CostRecord, Span, SpanStatus, SpanType


# --------------------------------------------------------------------------- #
# Adapter unit tests                                                          #
# --------------------------------------------------------------------------- #
def test_map_span_type_known_and_unknown() -> None:
    assert map_span_type("llm") == "llm_call"
    assert map_span_type("tool") == "tool_call"
    assert map_span_type("retrieval") == "retrieval"
    assert map_span_type("decision") == "decision"
    assert map_span_type("other") == "custom"
    # Unknown passes through unchanged (forward compatible)
    assert map_span_type("mystery") == "mystery"


def test_map_span_status_known_and_unknown() -> None:
    assert map_span_status("ok") == "completed"
    assert map_span_status("error") == "error"
    assert map_span_status("weird") == "weird"


def test_span_to_trace_create_lifts_attributes() -> None:
    ingest = SharedSpanIngest(
        trace_id="trace-1",
        span_id="span-1",
        name="gpt-4o call",
        span_type="llm",
        status="ok",
        start_ms=1000.0,
        end_ms=1500.0,
        attributes={
            "cost_usd": 0.0123,
            "model": "gpt-4o",
            "provider": "openai",
            "feature": "summarize",
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            "extra": "kept",
        },
    )
    tc = span_to_trace_create(ingest)
    assert tc.run_id == "trace-1"
    assert tc.span_type == "llm_call"
    assert tc.status == "completed"
    assert tc.cost_usd == 0.0123
    assert tc.model == "gpt-4o"
    assert tc.provider == "openai"
    assert tc.feature == "summarize"
    assert tc.token_usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }
    assert tc.duration_ms == 500.0
    # Remaining attributes are preserved in metadata
    assert tc.metadata is not None and tc.metadata.get("extra") == "kept"


def test_span_to_trace_create_derives_token_usage_from_flat_fields() -> None:
    ingest = SharedSpanIngest(
        trace_id="t",
        span_id="s",
        name="call",
        span_type="llm",
        start_ms=0.0,
        end_ms=None,
        attributes={"prompt_tokens": 7, "completion_tokens": 3},
    )
    tc = span_to_trace_create(ingest)
    assert tc.token_usage == {
        "prompt_tokens": 7,
        "completion_tokens": 3,
        "total_tokens": 10,
    }
    # No end_ms -> no duration
    assert tc.duration_ms is None
    assert tc.end_time is None


def test_cost_record_to_trace_create_preserves_cost_verbatim() -> None:
    record = CostRecordIngest(
        trace_id="run-x",
        model="claude-3-5-sonnet",
        provider="anthropic",
        prompt_tokens=100,
        completion_tokens=50,
        estimated_cost=0.0042,
        latency_ms=250.0,
    )
    tc = cost_record_to_trace_create(record)
    assert tc.run_id == "run-x"
    assert tc.span_type == "llm_call"
    assert tc.cost_usd == 0.0042  # verbatim, not recomputed
    assert tc.model == "claude-3-5-sonnet"
    assert tc.provider == "anthropic"
    assert tc.token_usage == {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,  # derived
    }
    assert tc.duration_ms == 250.0


def test_cost_record_synthesizes_ids_when_absent() -> None:
    tc = cost_record_to_trace_create(CostRecordIngest(model="gpt-4"))
    assert tc.run_id.startswith("cost-")
    assert tc.span_id


def test_shared_core_span_round_trip() -> None:
    """A real shared_core.Span serializes into the ingest shape losslessly."""
    span = Span(
        trace_id="abc",
        name="retrieve docs",
        span_type=SpanType.RETRIEVAL,
        status=SpanStatus.OK,
        start_ms=10.0,
        end_ms=42.0,
        attributes={"k": "v"},
    )
    payload = span.to_dict()
    ingest = SharedSpanIngest.model_validate(payload)
    tc = span_to_trace_create(ingest)
    assert tc.span_type == "retrieval"
    assert tc.status == "completed"
    assert tc.duration_ms == 32.0


def test_shared_core_cost_record_round_trip() -> None:
    record = CostRecord(
        trace_id="t1",
        model="gpt-4o-mini",
        provider="openai",
        prompt_tokens=20,
        completion_tokens=8,
        total_tokens=28,
        estimated_cost=0.0009,
        latency_ms=120.0,
    )
    ingest = CostRecordIngest.model_validate(record.model_dump())
    tc = cost_record_to_trace_create(ingest)
    assert tc.cost_usd == 0.0009
    assert tc.token_usage["total_tokens"] == 28


# --------------------------------------------------------------------------- #
# Endpoint integration tests                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_ingest_shared_spans_endpoint_creates_run(client: AsyncClient) -> None:
    now_ms = time.time() * 1000.0
    span = Span(
        trace_id="hermes-trace-1",
        name="planner step",
        span_type=SpanType.DECISION,
        start_ms=now_ms,
        end_ms=now_ms + 80.0,
        attributes={"model": "gpt-4o", "provider": "openai", "cost_usd": 0.002},
    )
    resp = await client.post("/api/traces/spans", json=[span.to_dict()])
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["run_id"] == "hermes-trace-1"
    assert data[0]["span_type"] == "decision"

    # The run was auto-created and accrued the span's cost
    run_resp = await client.get("/api/runs/hermes-trace-1")
    assert run_resp.status_code == 200
    run = run_resp.json()
    assert run["span_count"] == 1
    assert run["total_cost"] == pytest.approx(0.002)


@pytest.mark.asyncio
async def test_ingest_cost_records_endpoint(client: AsyncClient) -> None:
    record = CostRecord(
        trace_id="lcm-run-1",
        model="claude-3-5-sonnet",
        provider="anthropic",
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        estimated_cost=0.015,
        latency_ms=400.0,
    )
    resp = await client.post("/api/traces/costs", json=[record.model_dump()])
    assert resp.status_code == 201
    data = resp.json()
    assert data[0]["cost_usd"] == pytest.approx(0.015)
    assert data[0]["model"] == "claude-3-5-sonnet"

    # Shows up in cost-by-model analytics
    by_model = await client.get("/api/costs/by-model")
    assert by_model.status_code == 200
    models = {row["model"]: row for row in by_model.json()}
    assert "claude-3-5-sonnet" in models


@pytest.mark.asyncio
async def test_ingest_shared_spans_empty_list(client: AsyncClient) -> None:
    resp = await client.post("/api/traces/spans", json=[])
    assert resp.status_code == 201
    assert resp.json() == []
