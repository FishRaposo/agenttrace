"""Cost analytics API — endpoints for FinOps dashboards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.trace import Trace
from app.models.run import Run

router = APIRouter()


def _token_sum(token_usage: dict | None) -> int:
    if not token_usage:
        return 0
    return token_usage.get("total_tokens", 0) or 0


@router.get("/costs/summary")
async def get_cost_summary(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return total cost, token, and span counts plus per-dimension breakdowns."""
    total_cost_result = await session.execute(
        select(func.coalesce(func.sum(Trace.cost_usd), 0.0))
    )
    total_cost = float(total_cost_result.scalar() or 0.0)

    total_spans = await session.execute(select(func.count()).select_from(Trace))
    total_spans_count = total_spans.scalar() or 0

    # Compute token totals in Python for SQLite compatibility
    traces_result = await session.execute(select(Trace.token_usage))
    total_tokens = sum(_token_sum(row[0]) for row in traces_result.all())

    # By provider
    provider_stmt = (
        select(Trace.provider, func.coalesce(func.sum(Trace.cost_usd), 0.0))
        .where(Trace.provider.isnot(None))
        .group_by(Trace.provider)
        .order_by(func.sum(Trace.cost_usd).desc())
    )
    provider_result = await session.execute(provider_stmt)
    by_provider = {row[0]: round(float(row[1]), 6) for row in provider_result.all()}

    # By model
    model_stmt = (
        select(Trace.model, func.coalesce(func.sum(Trace.cost_usd), 0.0))
        .where(Trace.model.isnot(None))
        .group_by(Trace.model)
        .order_by(func.sum(Trace.cost_usd).desc())
    )
    model_result = await session.execute(model_stmt)
    by_model = {row[0]: round(float(row[1]), 6) for row in model_result.all()}

    # By feature
    feature_stmt = (
        select(Trace.feature, func.coalesce(func.sum(Trace.cost_usd), 0.0))
        .where(Trace.feature.isnot(None))
        .group_by(Trace.feature)
        .order_by(func.sum(Trace.cost_usd).desc())
    )
    feature_result = await session.execute(feature_stmt)
    by_feature = {row[0]: round(float(row[1]), 6) for row in feature_result.all()}

    return {
        "total_cost": round(total_cost, 6),
        "total_tokens": total_tokens,
        "total_spans": total_spans_count,
        "by_provider": by_provider,
        "by_model": by_model,
        "by_feature": by_feature,
    }


@router.get("/costs/timeseries")
async def get_cost_timeseries(
    granularity: str = Query("day", description="day or hour"),
    days: int = Query(30, ge=1, le=90, description="Number of days back"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return cost and tokens aggregated by time bucket."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Fetch traces since date and aggregate in Python for SQLite compatibility
    stmt = select(Trace).where(Trace.start_time >= since).order_by(Trace.start_time.asc())
    result = await session.execute(stmt)
    traces = list(result.scalars().all())

    from collections import defaultdict
    buckets: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "spans": 0})

    for t in traces:
        if t.start_time is None:
            continue
        if granularity == "hour":
            key = t.start_time.strftime("%Y-%m-%dT%H:00")
        else:
            key = t.start_time.strftime("%Y-%m-%d")
        buckets[key]["cost"] += t.cost_usd or 0.0
        buckets[key]["tokens"] += _token_sum(t.token_usage)
        buckets[key]["spans"] += 1

    data = [
        {"bucket": k, "cost": round(v["cost"], 6), "tokens": v["tokens"], "spans": v["spans"]}
        for k, v in sorted(buckets.items())
    ]

    return {"granularity": granularity, "data": data}


@router.get("/costs/by-model")
async def get_cost_by_model(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return cost breakdown per model."""
    stmt = (
        select(Trace)
        .where(Trace.model.isnot(None))
    )
    result = await session.execute(stmt)
    traces = list(result.scalars().all())

    from collections import defaultdict
    stats: dict[str, dict] = defaultdict(lambda: {"total_cost": 0.0, "total_tokens": 0, "span_count": 0, "latency_sum": 0.0})

    for t in traces:
        model = t.model or "unknown"
        stats[model]["total_cost"] += t.cost_usd or 0.0
        stats[model]["total_tokens"] += _token_sum(t.token_usage)
        stats[model]["span_count"] += 1
        stats[model]["latency_sum"] += t.duration_ms or 0.0

    return [
        {
            "model": k,
            "total_cost": round(v["total_cost"], 6),
            "total_tokens": v["total_tokens"],
            "span_count": v["span_count"],
            "avg_latency_ms": round(v["latency_sum"] / max(v["span_count"], 1), 2),
        }
        for k, v in sorted(stats.items(), key=lambda x: x[1]["total_cost"], reverse=True)
    ]


@router.get("/costs/by-provider")
async def get_cost_by_provider(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return cost breakdown per provider."""
    stmt = (
        select(
            Trace.provider,
            func.coalesce(func.sum(Trace.cost_usd), 0.0).label("total_cost"),
            func.count().label("span_count"),
        )
        .where(Trace.provider.isnot(None))
        .group_by(Trace.provider)
        .order_by(func.sum(Trace.cost_usd).desc())
    )
    result = await session.execute(stmt)
    return [
        {
            "provider": row.provider,
            "total_cost": round(float(row.total_cost), 6),
            "span_count": int(row.span_count),
        }
        for row in result.all()
    ]


@router.get("/costs/by-feature")
async def get_cost_by_feature(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return cost breakdown per feature."""
    stmt = (
        select(
            Trace.feature,
            func.coalesce(func.sum(Trace.cost_usd), 0.0).label("total_cost"),
            func.count().label("span_count"),
        )
        .where(Trace.feature.isnot(None))
        .group_by(Trace.feature)
        .order_by(func.sum(Trace.cost_usd).desc())
    )
    result = await session.execute(stmt)
    return [
        {
            "feature": row.feature,
            "total_cost": round(float(row.total_cost), 6),
            "span_count": int(row.span_count),
        }
        for row in result.all()
    ]


@router.get("/costs/top-runs")
async def get_top_expensive_runs(
    limit: int = Query(10, ge=1, le=50, description="Number of runs"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return most expensive runs by total cost."""
    stmt = (
        select(Run)
        .order_by(Run.total_cost.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    runs = list(result.scalars().all())
    return [
        {
            "id": r.id,
            "name": r.name,
            "total_cost": round(r.total_cost, 6),
            "total_tokens": r.total_tokens,
            "span_count": r.span_count,
            "status": r.status,
            "start_time": r.start_time.isoformat() if r.start_time else None,
        }
        for r in runs
    ]


@router.get("/costs/projection")
async def get_cost_projection(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Calculate burn rate and monthly projection from trailing 7 days."""
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)
    since_30d = datetime.now(timezone.utc) - timedelta(days=30)

    cost_7d_result = await session.execute(
        select(func.coalesce(func.sum(Trace.cost_usd), 0.0))
        .where(Trace.start_time >= since_7d)
    )
    cost_7d = float(cost_7d_result.scalar() or 0.0)

    cost_30d_result = await session.execute(
        select(func.coalesce(func.sum(Trace.cost_usd), 0.0))
        .where(Trace.start_time >= since_30d)
    )
    cost_30d = float(cost_30d_result.scalar() or 0.0)

    daily_burn = cost_7d / 7.0
    monthly_projection = daily_burn * 30.0

    return {
        "trailing_7d_cost": round(cost_7d, 6),
        "trailing_30d_cost": round(cost_30d, 6),
        "daily_burn": round(daily_burn, 6),
        "monthly_projection": round(monthly_projection, 6),
    }
