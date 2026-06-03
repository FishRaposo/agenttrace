"""Tests for the TraceService business logic."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run
from app.services.trace_service import TraceService


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
        token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
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
