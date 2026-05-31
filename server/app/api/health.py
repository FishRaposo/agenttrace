"""Health check API."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter()
_start_time = time.time()


@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Health check endpoint.

    Args:
        session: Async database session.

    Returns:
        Dictionary with health status and database connectivity.
    """
    try:
        await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "version": "0.1.0",
            "uptime": round(time.time() - _start_time, 2),
        }
    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "version": "0.1.0",
            "uptime": round(time.time() - _start_time, 2),
        }
