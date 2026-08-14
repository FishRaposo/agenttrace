"""Deterministic, persisted local alert evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertEvent, AlertRule
from app.models.run import Run
from app.models.trace import Trace


async def _upsert_event(
    session: AsyncSession,
    *,
    rule: AlertRule,
    value: float,
    breached: bool,
    message: str,
    details: dict[str, Any],
) -> None:
    dedup_key = f"{rule.kind}:{rule.id}"
    result = await session.execute(
        select(AlertEvent).where(
            AlertEvent.rule_id == rule.id, AlertEvent.dedup_key == dedup_key
        )
    )
    event = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if event is None and breached:
        session.add(
            AlertEvent(
                rule_id=rule.id,
                dedup_key=dedup_key,
                state="open",
                value=value,
                message=message,
                details=details,
                first_seen=now,
                last_seen=now,
            )
        )
        return
    if event is None:
        return
    event.value = value
    event.details = details
    event.message = message
    event.last_seen = now
    if breached:
        if event.state == "resolved":
            event.state = "open"
            event.acknowledged_at = None
    elif event.state in {"open", "acknowledged"}:
        event.state = "resolved"


async def evaluate_rules(session: AsyncSession) -> None:
    """Evaluate all enabled rules and update their deduplicated events."""
    rules = list(
        (
            await session.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))
        ).scalars()
    )
    for rule in rules:
        if rule.kind == "latency":
            value = float(
                (
                    await session.execute(
                        select(func.coalesce(func.max(Trace.duration_ms), 0.0))
                    )
                ).scalar()
                or 0.0
            )
            details = {"threshold_ms": rule.threshold}
            message = f"Maximum latency is {value:.2f}ms"
        elif rule.kind == "run_cost":
            value = float(
                (
                    await session.execute(
                        select(func.coalesce(func.max(Run.total_cost), 0.0))
                    )
                ).scalar()
                or 0.0
            )
            details = {"threshold_usd": rule.threshold}
            message = f"Maximum run cost is ${value:.6f}"
        else:
            value = float(
                (
                    await session.execute(
                        select(func.coalesce(func.sum(Run.total_cost), 0.0))
                    )
                ).scalar()
                or 0.0
            )
            details = {"threshold_usd": rule.threshold}
            message = f"Total cost is ${value:.6f}"
        await _upsert_event(
            session,
            rule=rule,
            value=value,
            breached=value > rule.threshold,
            message=message,
            details=details,
        )
    await session.flush()


async def acknowledge_event(session: AsyncSession, event_id: str) -> AlertEvent | None:
    event = await session.get(AlertEvent, event_id)
    if event is None:
        return None
    event.state = "acknowledged"
    event.acknowledged_at = datetime.now(timezone.utc)
    await session.flush()
    return event
