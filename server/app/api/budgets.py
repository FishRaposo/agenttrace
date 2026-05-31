"""Budgets API — cost threshold definitions and status checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.budget import Budget, BudgetCreate, BudgetResponse, BudgetStatusResponse
from app.models.trace import Trace

router = APIRouter()


@router.post("/budgets", response_model=BudgetResponse, status_code=201)
async def create_budget(
    data: BudgetCreate,
    session: AsyncSession = Depends(get_session),
) -> Budget:
    """Create a new budget definition."""
    budget = Budget(
        name=data.name,
        scope=data.scope,
        scope_value=data.scope_value,
        limit_usd=data.limit_usd,
        period=data.period,
        alert_threshold_pct=data.alert_threshold_pct,
    )
    session.add(budget)
    await session.flush()
    return budget


@router.get("/budgets", response_model=list[BudgetResponse])
async def list_budgets(
    session: AsyncSession = Depends(get_session),
) -> list[Budget]:
    """List all budgets."""
    result = await session.execute(select(Budget).order_by(Budget.created_at.desc()))
    return list(result.scalars().all())


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    session: AsyncSession = Depends(get_session),
) -> Budget:
    """Get a single budget by ID."""
    budget = await session.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.delete("/budgets/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a budget."""
    budget = await session.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    await session.delete(budget)


@router.get("/budgets/{budget_id}/status", response_model=BudgetStatusResponse)
async def get_budget_status(
    budget_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check current spend against a budget and compute projection."""
    budget = await session.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Determine time window for the budget period
    now = datetime.now(timezone.utc)
    if budget.period == "daily":
        since = now - timedelta(days=1)
    elif budget.period == "weekly":
        since = now - timedelta(weeks=1)
    else:
        since = now - timedelta(days=30)

    # Build cost query based on scope
    cost_stmt = select(func.coalesce(func.sum(Trace.cost_usd), 0.0)).where(Trace.start_time >= since)
    if budget.scope == "provider" and budget.scope_value:
        cost_stmt = cost_stmt.where(Trace.provider == budget.scope_value)
    elif budget.scope == "model" and budget.scope_value:
        cost_stmt = cost_stmt.where(Trace.model == budget.scope_value)
    elif budget.scope == "feature" and budget.scope_value:
        cost_stmt = cost_stmt.where(Trace.feature == budget.scope_value)

    cost_result = await session.execute(cost_stmt)
    current_cost = float(cost_result.scalar() or 0.0)

    percent_used = (current_cost / budget.limit_usd * 100) if budget.limit_usd > 0 else 0.0
    alert_triggered = percent_used >= budget.alert_threshold_pct
    breached = current_cost >= budget.limit_usd

    # Monthly projection (always compute trailing 7d burn)
    since_7d = now - timedelta(days=7)
    projection_stmt = select(func.coalesce(func.sum(Trace.cost_usd), 0.0)).where(Trace.start_time >= since_7d)
    if budget.scope == "provider" and budget.scope_value:
        projection_stmt = projection_stmt.where(Trace.provider == budget.scope_value)
    elif budget.scope == "model" and budget.scope_value:
        projection_stmt = projection_stmt.where(Trace.model == budget.scope_value)
    elif budget.scope == "feature" and budget.scope_value:
        projection_stmt = projection_stmt.where(Trace.feature == budget.scope_value)

    proj_result = await session.execute(projection_stmt)
    cost_7d = float(proj_result.scalar() or 0.0)
    daily_burn = cost_7d / 7.0
    projected_monthly = daily_burn * 30.0

    return {
        "budget_id": budget.id,
        "name": budget.name,
        "limit_usd": budget.limit_usd,
        "current_cost": round(current_cost, 6),
        "remaining": round(max(0.0, budget.limit_usd - current_cost), 6),
        "percent_used": round(percent_used, 2),
        "alert_triggered": alert_triggered,
        "breached": breached,
        "projected_monthly": round(projected_monthly, 6),
    }
