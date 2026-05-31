"""Alerting API — cost threshold monitoring."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.run import Run

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
        select(Run).where(Run.total_cost > run_cost_threshold)
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
