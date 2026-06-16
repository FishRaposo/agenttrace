"""Replay API — endpoints for prompt replay from recorded inputs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.run import Run
from app.models.trace import Trace

router = APIRouter()


@router.get("/replay/runs/{run_id}")
async def get_replay_data(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get replay data for a run, including all LLM prompts and inputs.

    Args:
        run_id: The run identifier.
        session: Async database session.

    Returns:
        Dictionary with replay data including all spans with input/output
        that can be used to replay the run.

    Raises:
        HTTPException: If the run is not found.
    """
    run_stmt = select(Run).where(Run.id == run_id)
    run_result = await session.execute(run_stmt)
    run = run_result.scalar_one_or_none()

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    spans_stmt = (
        select(Trace).where(Trace.run_id == run_id).order_by(Trace.start_time.asc())
    )
    spans_result = await session.execute(spans_stmt)
    spans = list(spans_result.scalars().all())

    replay_steps = []
    for span in spans:
        step = {
            "id": span.id,
            "name": span.name,
            "span_type": span.span_type,
            "input_data": span.input_data,
            "output_data": span.output_data,
            "metadata": span.trace_metadata,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "status": span.status,
            "error": span.error,
        }
        replay_steps.append(step)

    return {
        "run": {
            "id": run.id,
            "name": run.name,
            "status": run.status,
            "start_time": run.start_time.isoformat(),
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "metadata": run.run_metadata,
        },
        "steps": replay_steps,
        "total_steps": len(replay_steps),
    }
