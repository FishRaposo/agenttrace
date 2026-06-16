"""Alerting API — cost threshold monitoring."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.run import Run
from app.models.trace import Trace

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    daily_cost_threshold: Annotated[
        float,
        Query(
            alias="daily_threshold",
            description="Daily cost threshold in USD",
        ),
    ] = 1.0,
    run_cost_threshold: Annotated[
        float,
        Query(
            alias="per_run_threshold",
            description="Per-run cost threshold in USD",
        ),
    ] = 0.50,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check for cost threshold breaches.

    Returns runs that exceed per-run cost threshold and whether
    daily aggregate cost exceeds the daily threshold.

    Args:
        daily_cost_threshold: Alert if daily cost exceeds this.
        run_cost_threshold: Alert per-run cost exceeds this.
        session: Async database session.

    Returns:
        Dictionary with alert status and exceeded runs.
    """
    result = await session.execute(select(func.coalesce(func.sum(Run.total_cost), 0.0)))
    total_cost = float(result.scalar() or 0.0)

    expensive_runs_stmt = (
        select(Run)
        .where(Run.total_cost > run_cost_threshold)
        .order_by(Run.total_cost.desc())
        .limit(20)
    )
    expensive_runs_result = await session.execute(expensive_runs_stmt)
    expensive_runs = list(expensive_runs_result.scalars().all())

    daily_threshold_exceeded = total_cost > daily_cost_threshold

    return {
        "daily_threshold_usd": daily_cost_threshold,
        "run_threshold_usd": run_cost_threshold,
        "total_cost": round(total_cost, 4),
        "daily_alert": daily_threshold_exceeded,
        "daily_threshold_exceeded": daily_threshold_exceeded,
        "expensive_runs": [
            {
                "id": r.id,
                "name": r.name,
                "cost": r.total_cost,
                "start_time": r.start_time.isoformat() if r.start_time else None,
            }
            for r in expensive_runs
        ],
    }


@router.get("/alerts/latency")
async def get_latency_alerts(
    latency_threshold_ms: Annotated[
        float,
        Query(
            alias="threshold_ms",
            description="Span latency threshold in milliseconds",
            gt=0,
        ),
    ] = 5000.0,
    limit: Annotated[
        int,
        Query(description="Maximum breaching spans to return", ge=1, le=200),
    ] = 50,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check for spans whose latency exceeds a threshold.

    Surfaces the slowest spans above ``latency_threshold_ms`` so operators can
    set a simple latency SLO alert. Spans with no recorded duration are ignored.

    Args:
        latency_threshold_ms: Alert when a span's ``duration_ms`` exceeds this.
        limit: Maximum number of breaching spans to return.
        session: Async database session.

    Returns:
        Dictionary with alert status, the breaching span count, and the slowest
        offending spans.
    """
    breaching_stmt = (
        select(Trace)
        .where(Trace.duration_ms.isnot(None))
        .where(Trace.duration_ms > latency_threshold_ms)
        .order_by(Trace.duration_ms.desc())
        .limit(limit)
    )
    breaching_result = await session.execute(breaching_stmt)
    breaching = list(breaching_result.scalars().all())

    max_latency_result = await session.execute(
        select(func.coalesce(func.max(Trace.duration_ms), 0.0))
    )
    max_latency = float(max_latency_result.scalar() or 0.0)

    return {
        "latency_threshold_ms": latency_threshold_ms,
        "latency_alert": len(breaching) > 0,
        "breaching_count": len(breaching),
        "max_latency_ms": round(max_latency, 2),
        "slow_spans": [
            {
                "id": s.id,
                "run_id": s.run_id,
                "span_id": s.span_id,
                "name": s.name,
                "span_type": s.span_type,
                "duration_ms": s.duration_ms,
                "model": s.model,
            }
            for s in breaching
        ],
    }
