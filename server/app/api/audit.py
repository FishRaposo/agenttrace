"""Administrator-only audit log API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import User, require_roles
from app.db import get_session
from app.internal.rbac import Role
from app.models.audit import AuditLog, AuditLogResponse

router = APIRouter()


@router.get("/audit", response_model=list[AuditLogResponse])
async def list_audit_events(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_roles(Role.ADMIN)),  # noqa: B008
) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
