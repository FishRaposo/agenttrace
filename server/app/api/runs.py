"""Runs API — endpoints for run management."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import User, require_roles
from app.core.capture import bounded, sanitize
from app.db import begin_span_write, get_session
from app.internal.rbac import Role
from app.models.delivery import IngestionEvent
from app.models.run import Run, RunCreate, RunListResponse, RunResponse
from app.models.trace import Trace, TraceResponse
from app.services.audit import record_audit
from app.services.trace_service import _normalize_utc

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
    run_id = run_data.id
    existing = await session.get(Run, run_id) if run_id else None
    if existing is None:
        run = Run(
            id=run_id,
            name=sanitize(run_data.name),
            status=run_data.status,
            start_time=_normalize_utc(run_data.start_time),
            end_time=_normalize_utc(run_data.end_time),
            correlation_id=sanitize(run_data.correlation_id),
            total_cost=run_data.total_cost,
            total_tokens=run_data.total_tokens,
            span_count=run_data.span_count,
            run_metadata=bounded(run_data.metadata),
            workflow_id=run_data.workflow_id,
            feature=run_data.feature,
        )
        await begin_span_write(session, run_id)
        try:
            async with session.begin_nested():
                session.add(run)
                await session.flush()
            existing = run
        except IntegrityError:
            existing = await session.get(Run, run_id, populate_existing=True)
            if existing is None:
                raise
    merged = await _merge_run(session, existing, run_data)
    await session.commit()
    return merged


async def _merge_run(session: AsyncSession, existing: Run, incoming: RunCreate) -> Run:
    """Use database conditions so delayed concurrent roots cannot reopen runs."""
    terminal = Run.status.in_(["completed", "failed", "cancelled", "error"])
    count = (
        select(func.count())
        .select_from(Trace)
        .where(Trace.run_id == existing.id)
        .scalar_subquery()
    )
    cost = (
        select(func.coalesce(func.sum(Trace.cost_usd), 0.0))
        .where(Trace.run_id == existing.id)
        .scalar_subquery()
    )
    tokens = (
        select(
            func.coalesce(func.sum(Trace.token_usage["total_tokens"].as_integer()), 0)
        )
        .where(Trace.run_id == existing.id)
        .scalar_subquery()
    )
    start = _normalize_utc(incoming.start_time) or incoming.start_time
    await session.execute(
        update(Run)
        .where(Run.id == existing.id)
        .values(
            status=case((terminal, Run.status), else_=incoming.status),
            end_time=case(
                (terminal, Run.end_time), else_=_normalize_utc(incoming.end_time)
            ),
            start_time=case((Run.start_time > start, start), else_=Run.start_time),
            name=sanitize(incoming.name),
            correlation_id=sanitize(incoming.correlation_id)
            if incoming.correlation_id is not None
            else Run.correlation_id,
            run_metadata=bounded(
                {**(existing.run_metadata or {}), **(incoming.metadata or {})}
            )
            if incoming.metadata is not None
            else Run.run_metadata,
            workflow_id=incoming.workflow_id
            if incoming.workflow_id is not None
            else Run.workflow_id,
            feature=incoming.feature if incoming.feature is not None else Run.feature,
            total_cost=case(
                (count > 0, cost), (terminal, Run.total_cost), else_=incoming.total_cost
            ),
            total_tokens=case(
                (count > 0, tokens),
                (terminal, Run.total_tokens),
                else_=incoming.total_tokens,
            ),
            span_count=case(
                (count > 0, count),
                (terminal, Run.span_count),
                else_=incoming.span_count,
            ),
        )
    )
    await session.refresh(existing)
    return existing


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    status: Optional[str] = Query(None, description="Filter by status"),
    cohort_id: str | None = Query(None),
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

    if cohort_id is not None:
        condition = Run.run_metadata["cohort_id"].as_string() == cohort_id
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

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

    await session.execute(
        delete(IngestionEvent).where(
            IngestionEvent.trace_id.in_(select(Trace.id).where(Trace.run_id == run_id))
        )
    )
    await session.execute(delete(Trace).where(Trace.run_id == run_id))
    await session.delete(run)
    await record_audit(
        session,
        actor=current_user.username,
        action="run.delete",
        resource=f"run:{run_id}",
    )
