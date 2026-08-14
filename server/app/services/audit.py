"""Redacted, local audit logging."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.internal.vendor_core.logging import correlation_id_var
from app.models.audit import AuditLog

_SECRET_KEYS = {
    "password",
    "token",
    "access_token",
    "api_key",
    "secret",
    "authorization",
    "hashed_password",
}


def redact_metadata(value: Any) -> Any:
    """Recursively remove credentials and truncate oversized audit values."""
    if isinstance(value, Mapping):
        return {
            str(key): redact_metadata(item)
            for key, item in value.items()
            if str(key).lower() not in _SECRET_KEYS
        }
    if isinstance(value, list):
        return [redact_metadata(item) for item in value[:50]]
    if isinstance(value, str):
        return value[:1000]
    return value


async def record_audit(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    resource: str,
    details: Mapping[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    request_id = request_id or correlation_id_var.get()
    event = AuditLog(
        actor=actor,
        action=action,
        resource=resource,
        request_id=request_id,
        details=redact_metadata(dict(details or {})),
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    await session.flush()
    return event
