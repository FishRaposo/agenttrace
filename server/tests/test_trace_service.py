"""Tests for the TraceService business logic."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from app.models.run import Run
from app.services.trace_service import TraceService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def trace_service(db_session: AsyncSession) -> TraceService:
    return TraceService(session=db_session)


async def test_list_runs_empty(trace_service: TraceService) -> None:
    result = await trace_service.list_runs(limit=10, offset=0)
    assert result.total == 0
    assert result.runs == []


async def test_list_runs_with_data(
    trace_service: TraceService, db_session: AsyncSession
) -> None:
    run = Run(
        name="test_run",
        status="completed",
        start_time=datetime.now(timezone.utc),
        total_cost=0.005,
        total_tokens=100,
        span_count=2,
    )
    db_session.add(run)
    await db_session.flush()

    result = await trace_service.list_runs(limit=10, offset=0)
    assert result.total == 1
    assert result.runs[0].name == "test_run"


async def test_calculate_run_cost(
    trace_service: TraceService, db_session: AsyncSession
) -> None:
    run = Run(
        name="cost_run",
        status="completed",
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.flush()

    from app.models.trace import Trace

    t1 = Trace(
        run_id=run.id,
        span_id="span-1",
        span_type="llm_call",
        name="call1",
        start_time=datetime.now(timezone.utc),
        cost_usd=0.003,
        status="completed",
    )
    t2 = Trace(
        run_id=run.id,
        span_id="span-2",
        span_type="llm_call",
        name="call2",
        start_time=datetime.now(timezone.utc),
        cost_usd=0.002,
        status="completed",
    )
    db_session.add_all([t1, t2])
    await db_session.flush()

    cost = await trace_service.calculate_run_cost(run.id)
    assert cost == pytest.approx(0.005)


async def test_calculate_run_tokens(
    trace_service: TraceService, db_session: AsyncSession
) -> None:
    run = Run(
        name="token_run",
        status="completed",
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.flush()

    from app.models.trace import Trace

    t1 = Trace(
        run_id=run.id,
        span_id="span-1",
        span_type="llm_call",
        name="call1",
        start_time=datetime.now(timezone.utc),
        token_usage={
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
        status="completed",
    )
    db_session.add(t1)
    await db_session.flush()

    tokens = await trace_service.calculate_run_tokens(run.id)
    assert tokens["prompt_tokens"] == 100
    assert tokens["completion_tokens"] == 50
    assert tokens["total_tokens"] == 150


async def test_get_run_with_spans_not_found(trace_service: TraceService) -> None:
    result = await trace_service.get_run_with_spans("nonexistent")
    assert result is None


async def test_ensure_run_exists_creates_placeholder(
    trace_service: TraceService,
) -> None:
    run = await trace_service.ensure_run_exists("brand-new-trace")
    assert run.id == "brand-new-trace"
    assert run.status == "running"
    # Idempotent: a second call returns the same row without duplicating it.
    again = await trace_service.ensure_run_exists("brand-new-trace")
    assert again.id == run.id


async def test_ensure_run_exists_returns_existing(
    trace_service: TraceService, db_session: AsyncSession
) -> None:
    existing = Run(
        id="known-run",
        name="known",
        status="completed",
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(existing)
    await db_session.flush()

    fetched = await trace_service.ensure_run_exists("known-run")
    assert fetched.name == "known"
    assert fetched.status == "completed"


async def test_ingest_spans_auto_creates_runs_and_accrues_stats(
    trace_service: TraceService,
) -> None:
    from app.models.trace import TraceCreate

    payloads = [
        TraceCreate(
            run_id="auto-run",
            span_id="auto-span-1",
            span_type="llm_call",
            name="call-1",
            start_time=datetime.now(timezone.utc),
            cost_usd=0.01,
            token_usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            status="completed",
        ),
        TraceCreate(
            run_id="auto-run",
            span_id="auto-span-2",
            span_type="tool_call",
            name="call-2",
            start_time=datetime.now(timezone.utc),
            cost_usd=0.02,
            status="completed",
        ),
    ]
    traces = await trace_service.ingest_spans(payloads)
    assert len(traces) == 2

    run = await trace_service.ensure_run_exists("auto-run")
    assert run.span_count == 2
    assert run.total_cost == pytest.approx(0.03)
    assert run.total_tokens == 15
