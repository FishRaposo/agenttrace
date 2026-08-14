"""Runs API — endpoints for run management."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import User, require_roles
from app.db import get_session
from app.internal.rbac import Role
from app.models.run import Run, RunCreate, RunListResponse, RunResponse
from app.models.trace import Trace, TraceResponse
from app.services.audit import record_audit

router = APIRouter()


@router.post("/runs", response_model=RunResponse, status_code=201)
async def create_run(
    run_data: RunCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(Role.INGESTOR, Role.ADMIN)),  # noqa: B008
) -> Run:
    """Create or update an agent run.

    Args:
        run_data: The run data to create.
        session: Async database session.

    Returns:
        The created run record.
    """
    if run_data.id is not None:
        existing = await session.get(Run, run_data.id)
        if existing is not None:
            existing.correlation_id = run_data.correlation_id
            existing.name = run_data.name
            existing.status = run_data.status
            existing.start_time = run_data.start_time
            existing.end_time = run_data.end_time
            existing.total_cost = run_data.total_cost
            existing.total_tokens = run_data.total_tokens
            existing.span_count = run_data.span_count
            existing.run_metadata = run_data.metadata
            await session.flush()
            return existing

    run_values = {
        "correlation_id": run_data.correlation_id,
        "name": run_data.name,
        "status": run_data.status,
        "start_time": run_data.start_time,
        "end_time": run_data.end_time,
        "total_cost": run_data.total_cost,
        "total_tokens": run_data.total_tokens,
        "span_count": run_data.span_count,
        "run_metadata": run_data.metadata,
    }
    if run_data.id is not None:
        run_values["id"] = run_data.id

    run = Run(**run_values)

    session.add(run)
    await session.flush()
    return run


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by run name"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_roles(Role.VIEWER)),  # noqa: B008
) -> RunListResponse:
    """List runs with pagination, status filtering, name search, and
    correlation ID filtering.

    Args:
        status: Optional status filter.
        search: Optional name search (case-insensitive partial match).
        correlation_id: Optional correlation ID filter for multi-agent trace
            correlation.
        limit: Maximum number of runs per page.
        offset: Page offset.
        session: Async database session.

    Returns:
        Paginated list of runs.
    """
    count_stmt = select(func.count()).select_from(Run)
    list_stmt = select(Run).order_by(Run.start_time.desc())

    if status is not None:
        count_stmt = count_stmt.where(Run.status == status)
        list_stmt = list_stmt.where(Run.status == status)

    if search is not None:
        search_pattern = f"%{search}%"
        count_stmt = count_stmt.where(Run.name.ilike(search_pattern))
        list_stmt = list_stmt.where(Run.name.ilike(search_pattern))

    if correlation_id is not None:
        count_stmt = count_stmt.where(Run.correlation_id == correlation_id)
        list_stmt = list_stmt.where(Run.correlation_id == correlation_id)

    total = (await session.execute(count_stmt)).scalar() or 0
    result = await session.execute(list_stmt.limit(limit).offset(offset))
    runs = list(result.scalars().all())

    return RunListResponse(
        runs=[RunResponse.model_validate(run) for run in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_roles(Role.VIEWER)),  # noqa: B008
) -> Run:
    """Get a specific run by its ID.

    Args:
        run_id: The unique run identifier.
        session: Async database session.

    Returns:
        The run record.

    Raises:
        HTTPException: If the run is not found.
    """
    stmt = select(Run).where(Run.id == run_id)
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/spans", response_model=list[TraceResponse])
async def get_run_spans(
    run_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_roles(Role.VIEWER)),  # noqa: B008
) -> list[Trace]:
    """Get trace spans for a specific run with pagination.

    Args:
        run_id: The run identifier.
        limit: Maximum number of results.
        offset: Result offset for pagination.
        session: Async database session.

    Returns:
        List of traces belonging to the run.
    """
    stmt = (
        select(Trace)
        .where(Trace.run_id == run_id)
        .order_by(Trace.start_time.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN)),  # noqa: B008
) -> None:
    """Delete a run and all associated traces.

    Args:
        run_id: The run identifier to delete.
        session: Async database session.

    Raises:
        HTTPException: If the run is not found.
    """
    stmt = select(Run).where(Run.id == run_id)
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    await session.execute(delete(Trace).where(Trace.run_id == run_id))
    await session.delete(run)
    await record_audit(
        session,
        actor=current_user.username,
        action="run.delete",
        resource=f"run:{run_id}",
    )
