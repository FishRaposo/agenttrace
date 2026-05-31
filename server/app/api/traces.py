"""Traces API — endpoints for trace ingestion and retrieval."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.run import Run
from app.models.trace import Trace, TraceCreate, TraceResponse
from app.api.auth import get_optional_user, User

router = APIRouter()


@router.post("/traces", response_model=TraceResponse, status_code=201)
async def ingest_trace(
    trace_data: TraceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_optional_user),
) -> Trace:
    """Ingest a new trace span from the SDK.

    Automatically updates the parent run's aggregate stats.

    Args:
        trace_data: The trace data to store.
        session: Async database session.

    Returns:
        The created trace record.
    """
    trace = Trace(
        id=str(uuid.uuid4()),
        run_id=trace_data.run_id,
        span_id=trace_data.span_id,
        span_type=trace_data.span_type,
        name=trace_data.name,
        input_data=trace_data.input_data,
        output_data=trace_data.output_data,
        trace_metadata=trace_data.metadata,
        start_time=trace_data.start_time,
        end_time=trace_data.end_time,
        duration_ms=trace_data.duration_ms,
        cost_usd=trace_data.cost_usd,
        token_usage=trace_data.token_usage,
        status=trace_data.status,
        error=trace_data.error,
    )
    session.add(trace)

    await session.flush()

    traces_result = await session.execute(
        select(Trace.cost_usd, Trace.token_usage).where(Trace.run_id == trace_data.run_id)
    )
    traces = traces_result.all()
    total_cost = sum(cost or 0.0 for cost, _ in traces)
    total_tokens = sum((usage or {}).get("total_tokens", 0) for _, usage in traces)

    stmt = (
        update(Run)
        .where(Run.id == trace_data.run_id)
        .values(
            total_cost=total_cost,
            total_tokens=total_tokens,
            span_count=len(traces),
        )
    )
    await session.execute(stmt)
    return trace


@router.get("/traces", response_model=list[TraceResponse])
async def list_traces(
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    span_type: Optional[str] = Query(None, description="Filter by span type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    session: AsyncSession = Depends(get_session),
) -> list[Trace]:
    """List traces with optional filtering.

    Args:
        run_id: Optional run ID filter.
        span_type: Optional span type filter.
        limit: Maximum number of results.
        offset: Result offset for pagination.
        session: Async database session.

    Returns:
        List of matching trace records.
    """
    stmt = select(Trace)
    if run_id is not None:
        stmt = stmt.where(Trace.run_id == run_id)
    if span_type is not None:
        stmt = stmt.where(Trace.span_type == span_type)
    stmt = stmt.order_by(Trace.start_time.desc()).limit(limit).offset(offset)

    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
) -> Trace:
    """Get a specific trace by its ID.

    Args:
        trace_id: The unique trace identifier.
        session: Async database session.

    Returns:
        The trace record.

    Raises:
        HTTPException: If the trace is not found.
    """
    stmt = select(Trace).where(Trace.id == trace_id)
    result = await session.execute(stmt)
    trace = result.scalar_one_or_none()

    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
