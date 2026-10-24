"""Diff API — endpoints for comparing runs and traces."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.core.capture import present
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

    def stages(spans):
        counts = {}
        indexed = {}
        for span in spans:
            metadata = span.trace_metadata or {}
            source_stage = metadata.get("stage_key")
            stage = (
                source_stage
                if isinstance(source_stage, str) and source_stage
                else f"{span.span_type}:{span.name}"
            )
            counts[stage] = counts.get(stage, 0) + 1
            key = (
                stage,
                _ordinal(metadata.get("occurrence"), counts[stage]),
                _ordinal(metadata.get("attempt"), 1),
            )
            if key in indexed:
                occurrence = counts[stage]
                while (stage, occurrence, key[2]) in indexed:
                    occurrence += 1
                key = (stage, occurrence, key[2])
            indexed[key] = span
        return indexed

    stages1, stages2 = stages(spans1), stages(spans2)
    common = sorted(stages1.keys() & stages2.keys())
    aligned = []
    for key in common:
        first, second = stages1[key], stages2[key]
        aligned.append(
            {
                "stage_key": key[0],
                "occurrence": key[1],
                "attempt": key[2],
                "name": first.name,
                "span_type": first.span_type,
                "span_id_1": first.span_id,
                "span_id_2": second.span_id,
                "duration_diff": (second.duration_ms or 0) - (first.duration_ms or 0),
                "cost_diff": (second.cost_usd or 0) - (first.cost_usd or 0),
                "status_changed": first.status != second.status,
                "status_1": first.status,
                "status_2": second.status,
            }
        )
    unmatched = {
        "only_in_run1": [
            {"stage_key": k[0], "occurrence": k[1], "attempt": k[2]}
            for k in sorted(stages1.keys() - stages2.keys())
        ],
        "only_in_run2": [
            {"stage_key": k[0], "occurrence": k[1], "attempt": k[2]}
            for k in sorted(stages2.keys() - stages1.keys())
        ],
    }
    revision1 = (run1.run_metadata or {}).get("scenario_revision")
    revision2 = (run2.run_metadata or {}).get("scenario_revision")
    revision1 = revision1 if isinstance(revision1, str) and revision1 else None
    revision2 = revision2 if isinstance(revision2, str) and revision2 else None
    compatible = revision1 == revision2 if revision1 and revision2 else None
    compatibility = {
        "compatible": compatible,
        "reason": "matching scenario revisions"
        if compatible
        else "scenario revisions differ"
        if compatible is False
        else "historical scenario revision unknown",
        "scenario_revision_1": revision1,
        "scenario_revision_2": revision2,
    }
    only_in_run1 = [
        (stages1[k].name, stages1[k].span_type)
        for k in sorted(stages1.keys() - stages2.keys())
    ]
    only_in_run2 = [
        (stages2[k].name, stages2[k].span_type)
        for k in sorted(stages2.keys() - stages1.keys())
    ]
    span_differences = [
        item
        for item in aligned
        if item["duration_diff"] or item["cost_diff"] or item["status_changed"]
    ]
    result = {
        "aligned_stages": aligned,
        "unmatched_stages": unmatched,
        "compatibility": compatibility,
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
            "common_count": len(common),
            "differences": span_differences,
        },
    }

    return present(result)


def _ordinal(value: Any, fallback: int) -> int:
    return (
        value
        if isinstance(value, int)
        and not isinstance(value, bool)
        and 1 <= value <= 1000000
        else fallback
    )
