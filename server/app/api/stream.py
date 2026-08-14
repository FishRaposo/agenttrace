"""Streaming API — Server-Sent Events for live trace updates."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.auth import require_roles
from app.db import async_session_factory
from app.internal.rbac import Role
from app.models.trace import Trace

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_roles(Role.VIEWER))])


@router.get("/stream/traces")
async def stream_traces(request: Request) -> StreamingResponse:
    """Stream new traces via Server-Sent Events.

    Polls the database periodically and pushes new trace events
    to connected clients. Clients send 'last_seen_time' and 'last_id'
    query parameters to resume from a known position.

    Args:
        request: The incoming HTTP request.

    Returns:
        A streaming SSE response.
    """
    last_id = request.query_params.get("last_id", "")
    last_seen_time_str = request.query_params.get("last_seen_time", "")

    if last_seen_time_str:
        try:
            last_seen_time = datetime.fromisoformat(last_seen_time_str)
        except (ValueError, TypeError):
            last_seen_time = datetime.min.replace(tzinfo=timezone.utc)
    else:
        last_seen_time = datetime.min.replace(tzinfo=timezone.utc)

    async def event_generator():
        nonlocal last_seen_time, last_id
        while True:
            if await request.is_disconnected():
                break

            try:
                async with async_session_factory() as session:
                    stmt = (
                        select(Trace)
                        .where(
                            (Trace.start_time > last_seen_time)
                            | (
                                (Trace.start_time == last_seen_time)
                                & (Trace.id > last_id)
                            )
                        )
                        .order_by(Trace.start_time.asc(), Trace.id.asc())
                        .limit(10)
                    )
                    result = await session.execute(stmt)
                    traces = list(result.scalars().all())

                    for trace in traces:
                        last_seen_time = trace.start_time
                        last_id = trace.id
                        payload = {
                            "id": trace.id,
                            "run_id": trace.run_id,
                            "span_id": trace.span_id,
                            "span_type": trace.span_type,
                            "name": trace.name,
                            "status": trace.status,
                            "duration_ms": trace.duration_ms,
                            "cost_usd": trace.cost_usd,
                        }
                        yield (
                            f"id: {trace.id}\n"
                            f"data: {json.dumps(payload, default=str)}\n\n"
                        )
            except Exception:
                logger.warning("SSE polling error", exc_info=True)

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
