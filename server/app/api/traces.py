"""Traces API — endpoints for trace ingestion and retrieval."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import User, require_roles
from app.api.realtime import broadcast_trace
from app.config import settings
from app.db import get_session
from app.internal.rbac import Role
from app.internal.sampling import SamplingPolicy
from app.models.trace import Trace, TraceCreate, TraceResponse
from app.services.alerting import evaluate_rules
from app.services.audit import record_audit
from app.services.ingest_adapters import (
    CostRecordIngest,
    SharedSpanIngest,
    cost_record_to_trace_create,
    span_to_trace_create,
)
from app.services.trace_service import TraceService

router = APIRouter()


def _service(session: AsyncSession) -> TraceService:
    return TraceService(
        session,
        sampling_policy=SamplingPolicy(
            mode=settings.TRACE_SAMPLING_MODE,
            rate=settings.TRACE_SAMPLE_RATE,
            keep_errors=settings.TRACE_TAIL_KEEP_ERRORS,
            slow_threshold_ms=settings.TRACE_TAIL_SLOW_MS,
        ),
    )


async def _broadcast(trace: Trace) -> None:
    """Broadcast a freshly ingested trace to live WebSocket subscribers."""
    await broadcast_trace(
        {
            "id": trace.id,
            "run_id": trace.run_id,
            "span_id": trace.span_id,
            "span_type": trace.span_type,
            "name": trace.name,
            "status": trace.status,
            "duration_ms": trace.duration_ms,
            "cost_usd": trace.cost_usd,
            "timestamp": trace.start_time.isoformat() if trace.start_time else None,
            "sampled": trace.sampled,
            "sampling_reason": trace.sampling_reason,
        }
    )


@router.post("/traces", response_model=TraceResponse, status_code=201)
async def ingest_trace(
    trace_data: TraceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(Role.INGESTOR, Role.ADMIN)),  # noqa: B008
) -> Trace:
    """Ingest a new trace span from the SDK.

    Automatically updates the parent run's aggregate stats.

    Args:
        trace_data: The trace data to store.
        session: Async database session.

    Returns:
        The created trace record.
    """
    service = _service(session)
    trace = await service.ingest_trace(trace_data)
    await evaluate_rules(session)
    await record_audit(
        session,
        actor=current_user.username,
        action="trace.ingest",
        resource=f"run:{trace.run_id}",
        details={"span_id": trace.span_id},
    )
    await _broadcast(trace)
    return trace


@router.post("/traces/batch", response_model=list[TraceResponse], status_code=201)
async def ingest_traces_batch(
    trace_data_list: list[TraceCreate],
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(Role.INGESTOR, Role.ADMIN)),  # noqa: B008
) -> list[Trace]:
    """Ingest multiple trace spans in a single request.

    Updates parent run aggregate stats after all traces are inserted.

    Args:
        trace_data_list: List of trace data to store.
        session: Async database session.

    Returns:
        The created trace records.
    """
    service = _service(session)
    traces = await service.ingest_traces_batch(trace_data_list)
    await evaluate_rules(session)
    await record_audit(
        session,
        actor=current_user.username,
        action="trace.batch_ingest",
        resource="traces",
        details={"count": len(traces)},
    )
    for trace in traces:
        await _broadcast(trace)
    return traces


@router.get("/traces", response_model=list[TraceResponse])
async def list_traces(
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    span_type: Optional[str] = Query(None, description="Filter by span type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_roles(Role.VIEWER)),  # noqa: B008
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
    service = _service(session)
    return await service.list_traces(
        run_id=run_id, span_type=span_type, limit=limit, offset=offset
    )


@router.post("/traces/spans", response_model=list[TraceResponse], status_code=201)
async def ingest_shared_spans(
    spans: list[SharedSpanIngest],
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(Role.INGESTOR, Role.ADMIN)),  # noqa: B008
) -> list[Trace]:
    """Ingest spans in the canonical ``shared_core.tracing.Span`` shape.

    Accepts spans emitted by any ``shared_core``-based producer (e.g.
    ``hermes-agent-framework``). Each span's ``trace_id`` maps to a run, which is
    created on demand if it does not already exist. Cost is taken verbatim from
    span attributes — no pricing is recomputed.

    Args:
        spans: List of canonical shared_core spans.
        session: Async database session.

    Returns:
        The created trace records.
    """
    service = _service(session)
    trace_creates = [span_to_trace_create(s) for s in spans]
    traces = await service.ingest_spans(trace_creates)
    await evaluate_rules(session)
    await record_audit(
        session,
        actor=current_user.username,
        action="trace.canonical_ingest",
        resource="traces",
        details={"count": len(traces)},
    )
    for trace in traces:
        await _broadcast(trace)
    return traces


@router.post("/traces/costs", response_model=list[TraceResponse], status_code=201)
async def ingest_cost_records(
    records: list[CostRecordIngest],
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(Role.INGESTOR, Role.ADMIN)),  # noqa: B008
) -> list[Trace]:
    """Ingest LCM-style ``shared_core.tracing.CostRecord`` payloads.

    Each cost record is materialized as a single ``llm_call`` span carrying its
    verbatim ``estimated_cost`` and token usage, so it appears in the standard
    cost-attribution analytics. Missing runs are created on demand.

    Args:
        records: List of cost records.
        session: Async database session.

    Returns:
        The created trace records.
    """
    service = _service(session)
    trace_creates = [cost_record_to_trace_create(r) for r in records]
    traces = await service.ingest_spans(trace_creates)
    await evaluate_rules(session)
    await record_audit(
        session,
        actor=current_user.username,
        action="cost.ingest",
        resource="traces",
        details={"count": len(traces)},
    )
    for trace in traces:
        await _broadcast(trace)
    return traces


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_roles(Role.VIEWER)),  # noqa: B008
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
    service = _service(session)
    trace = await service.get_trace(trace_id)

    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
