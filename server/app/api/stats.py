"""Stats API — endpoints for aggregated dashboard statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import User, require_roles
from app.db import get_session
from app.internal.rbac import Role
from app.models.run import Run
from app.models.trace import Trace

router = APIRouter()


@router.get("/stats")
async def get_stats(
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_roles(Role.VIEWER)),  # noqa: B008
) -> dict:
    total_runs_result = await session.execute(select(func.count()).select_from(Run))
    total_runs = total_runs_result.scalar() or 0

    total_cost_result = await session.execute(
        select(func.coalesce(func.sum(Run.total_cost), 0.0))
    )
    total_cost = float(total_cost_result.scalar() or 0.0)

    total_tokens_result = await session.execute(
        select(func.coalesce(func.sum(Run.total_tokens), 0))
    )
    total_tokens = int(total_tokens_result.scalar() or 0)

    avg_duration_result = await session.execute(
        select(func.coalesce(func.avg(Trace.duration_ms), 0.0)).where(
            Trace.duration_ms.isnot(None)
        )
    )
    avg_duration_ms = float(avg_duration_result.scalar() or 0.0)

    return {
        "total_runs": total_runs,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "avg_duration_ms": avg_duration_ms,
    }
