"""Diff API — endpoints for comparing runs and traces."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.internal.rbac import Role
from app.models.run import Run
from app.models.trace import Trace

router = APIRouter(dependencies=[Depends(require_roles(Role.VIEWER))])


@router.get("/diff/runs")
async def diff_runs(
    run_id_1: str = Query(..., description="First run ID to compare"),
    run_id_2: str = Query(..., description="Second run ID to compare"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Compare two runs and return their differences.

    Args:
        run_id_1: First run identifier.
        run_id_2: Second run identifier.
        session: Async database session.

    Returns:
        Dictionary with comparison results including cost difference,
        token difference, span differences, and timing differences.

    Raises:
        HTTPException: If either run is not found.
    """
    stmt1 = select(Run).where(Run.id == run_id_1)
    stmt2 = select(Run).where(Run.id == run_id_2)

    result1 = await session.execute(stmt1)
    result2 = await session.execute(stmt2)

    run1 = result1.scalar_one_or_none()
    run2 = result2.scalar_one_or_none()

    if run1 is None or run2 is None:
        raise HTTPException(status_code=404, detail="One or both runs not found")

    # Get spans for both runs
    spans_stmt1 = (
        select(Trace).where(Trace.run_id == run_id_1).order_by(Trace.start_time.asc())
    )
    spans_stmt2 = (
        select(Trace).where(Trace.run_id == run_id_2).order_by(Trace.start_time.asc())
    )

    spans_result1 = await session.execute(spans_stmt1)
    spans_result2 = await session.execute(spans_stmt2)

    spans1 = list(spans_result1.scalars().all())
    spans2 = list(spans_result2.scalars().all())

    # Calculate differences
    cost_diff = run2.total_cost - run1.total_cost
    token_diff = run2.total_tokens - run1.total_tokens
    span_count_diff = run2.span_count - run1.span_count

    # Calculate duration difference
    duration1 = (
        (run1.end_time - run1.start_time).total_seconds() if run1.end_time else 0
    )
    duration2 = (
        (run2.end_time - run2.start_time).total_seconds() if run2.end_time else 0
    )
    duration_diff = duration2 - duration1

    # Compare spans by name and type
    span_names1 = {(s.name, s.span_type) for s in spans1}
    span_names2 = {(s.name, s.span_type) for s in spans2}

    only_in_run1 = list(span_names1 - span_names2)
    only_in_run2 = list(span_names2 - span_names1)
    common_spans = list(span_names1 & span_names2)

    # Find span differences for common spans
    span_differences = []
    for name, span_type in common_spans:
        span1 = next(
            (s for s in spans1 if s.name == name and s.span_type == span_type), None
        )
        span2 = next(
            (s for s in spans2 if s.name == name and s.span_type == span_type), None
        )

        if span1 and span2:
            diff = {
                "name": name,
                "span_type": span_type,
                "duration_diff": (span2.duration_ms or 0) - (span1.duration_ms or 0),
                "cost_diff": (span2.cost_usd or 0) - (span1.cost_usd or 0),
                "status_changed": span1.status != span2.status,
                "status_1": span1.status,
                "status_2": span2.status,
            }
            if (
                diff["duration_diff"] != 0
                or diff["cost_diff"] != 0
                or diff["status_changed"]
            ):
                span_differences.append(diff)

    return {
        "run1": {
            "id": run1.id,
            "name": run1.name,
            "status": run1.status,
            "total_cost": run1.total_cost,
            "total_tokens": run1.total_tokens,
            "span_count": run1.span_count,
            "start_time": run1.start_time.isoformat(),
            "end_time": run1.end_time.isoformat() if run1.end_time else None,
        },
        "run2": {
            "id": run2.id,
            "name": run2.name,
            "status": run2.status,
            "total_cost": run2.total_cost,
            "total_tokens": run2.total_tokens,
            "span_count": run2.span_count,
            "start_time": run2.start_time.isoformat(),
            "end_time": run2.end_time.isoformat() if run2.end_time else None,
        },
        "differences": {
            "cost_diff": cost_diff,
            "token_diff": token_diff,
            "span_count_diff": span_count_diff,
            "duration_diff": duration_diff,
        },
        "spans": {
            "only_in_run1": only_in_run1,
            "only_in_run2": only_in_run2,
            "common_count": len(common_spans),
            "differences": span_differences,
        },
    }
