"""Traces API — endpoints for trace ingestion and retrieval."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.trace import Trace, TraceCreate, TraceResponse
from app.api.auth import get_optional_user, User
from app.api.realtime import broadcast_trace
from app.services.trace_service import TraceService

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
    service = TraceService(session)
    trace = await service.ingest_trace(trace_data)

    # Broadcast to WebSocket clients
    await broadcast_trace({
        "id": trace.id,
        "run_id": trace.run_id,
        "span_id": trace.span_id,
        "span_type": trace.span_type,
        "name": trace.name,
        "status": trace.status,
        "duration_ms": trace.duration_ms,
        "cost_usd": trace.cost_usd,
        "timestamp": trace.start_time.isoformat() if trace.start_time else None,
    })

    return trace


@router.post("/traces/batch", response_model=list[TraceResponse], status_code=201)
async def ingest_traces_batch(
    trace_data_list: list[TraceCreate],
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_optional_user),
) -> list[Trace]:
    """Ingest multiple trace spans in a single request.

    Updates parent run aggregate stats after all traces are inserted.

    Args:
        trace_data_list: List of trace data to store.
        session: Async database session.

    Returns:
        The created trace records.
    """
    service = TraceService(session)
    traces = await service.ingest_traces_batch(trace_data_list)

    # Broadcast each trace
    for trace in traces:
        await broadcast_trace({
            "id": trace.id,
            "run_id": trace.run_id,
            "span_id": trace.span_id,
            "span_type": trace.span_type,
            "name": trace.name,
            "status": trace.status,
            "duration_ms": trace.duration_ms,
            "cost_usd": trace.cost_usd,
            "timestamp": trace.start_time.isoformat() if trace.start_time else None,
        })

    return traces


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
