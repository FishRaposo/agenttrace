"""Durable SSE delivery ordered by ingestion, never by span start time."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.auth import require_roles
from app.core.capture import sanitize
from app.db import async_session_factory
from app.internal.rbac import Role
from app.models.delivery import IngestionEvent
from app.models.run import Run
from app.models.trace import Trace

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_roles(Role.VIEWER))])


async def resolve_cursor(session, cursor=None, last_id=None, last_seen_time=None):
    """Resolve new numeric and legacy trace-ID/time resume inputs."""
    if cursor:
        try:
            value = int(cursor)
            if value < 0:
                raise ValueError
            return value
        except (ValueError, TypeError):
            raise HTTPException(422, "cursor must be a nonnegative integer") from None
    if last_id:
        if str(last_id).isdigit():
            return int(last_id)
        value = (
            await session.execute(
                select(IngestionEvent.cursor).where(IngestionEvent.trace_id == last_id)
            )
        ).scalar_one_or_none()
        if value is not None:
            return value
    if last_seen_time:
        try:
            timestamp = datetime.fromisoformat(last_seen_time).replace(tzinfo=None)
        except (TypeError, ValueError):
            raise HTTPException(422, "Invalid legacy resume timestamp") from None
        return (
            await session.execute(
                select(func.max(IngestionEvent.cursor))
                .join(Trace, Trace.id == IngestionEvent.trace_id)
                .where(Trace.start_time <= timestamp)
            )
        ).scalar() or 0
    return 0


async def read_events(session, cursor, cohort_id=None, limit=100):
    stmt = (
        select(IngestionEvent, Trace, Run.run_metadata)
        .join(Trace, Trace.id == IngestionEvent.trace_id)
        .outerjoin(Run, Run.id == Trace.run_id)
        .where(IngestionEvent.cursor > cursor)
    )
    if cohort_id is not None:
        stmt = stmt.where(
            (IngestionEvent.cohort_id == cohort_id)
            | (Run.run_metadata["cohort_id"].as_string() == cohort_id)
        )
    result = await session.execute(stmt.order_by(IngestionEvent.cursor).limit(limit))
    return [
        {
            "id": trace.id,
            "run_id": trace.run_id,
            "span_id": trace.span_id,
            "span_type": trace.span_type,
            "name": sanitize(trace.name),
            "status": trace.status,
            "duration_ms": trace.duration_ms,
            "cost_usd": trace.cost_usd,
            "delivery_cursor": event.cursor,
            "cohort_id": event.cohort_id or (run_metadata or {}).get("cohort_id"),
            "timestamp": trace.start_time.isoformat(),
        }
        for event, trace, run_metadata in result.all()
    ]


@router.get("/stream/traces")
async def stream_traces(request: Request) -> StreamingResponse:
    cohort_id = request.query_params.get("cohort_id")
    async with async_session_factory() as session:
        cursor = await resolve_cursor(
            session,
            request.query_params.get("cursor"),
            request.query_params.get("last_id") or request.headers.get("last-event-id"),
            request.query_params.get("last_seen_time"),
        )

    async def event_generator():
        nonlocal cursor
        while not await request.is_disconnected():
            try:
                async with async_session_factory() as session:
                    events = await read_events(session, cursor, cohort_id)
                for event in events:
                    cursor = event["delivery_cursor"]
                    yield f"id: {cursor}\ndata: {json.dumps(event, default=str)}\n\n"
                if not events:
                    yield ": heartbeat\n\n"
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("SSE polling failed", exc_info=True)
                yield 'event: error\ndata: {"error":"collector_unavailable"}\n\n'
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
