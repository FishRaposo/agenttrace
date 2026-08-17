"""Ordered audit events, recursive redaction, and replay into AgentTrace."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from agenttrace.issue_pr.models import AuditEvent

_SECRET_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "private_key",
    "secret",
    "token",
}
_SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[^\s]+"),
    re.compile(r"(?i)(token\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{8,})\b"),
)


class TraceLike(Protocol):
    def add_event(self, event_type: str, payload: dict[str, Any]) -> None: ...


AuditSink = Callable[[AuditEvent], object]


class AgentTraceAuditSink:
    """Forward already-redacted audit events to an existing AgentTrace tracer."""

    def __init__(self, tracer: TraceLike, prefix: str = "issue_pr") -> None:
        self.tracer = tracer
        self.prefix = prefix.rstrip(".")

    def __call__(self, event: AuditEvent) -> None:
        self.tracer.add_event(
            f"{self.prefix}.{event.action}",
            {
                "sequence": event.sequence,
                "timestamp": event.timestamp,
                "details": event.details,
            },
        )


class AuditTrail:
    """Append-only ordered events that can be serialized and replayed."""

    def __init__(
        self,
        events: Iterable[AuditEvent] = (),
        sinks: Sequence[AuditSink] = (),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._events = [_copy_event(event) for event in events]
        self._validate_sequence()
        self._sinks = list(sinks)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(_copy_event(event) for event in self._events)

    def record(
        self, action: str, details: Mapping[str, Any] | None = None
    ) -> AuditEvent:
        event = AuditEvent(
            sequence=len(self._events) + 1,
            action=action,
            details=_redact(dict(details or {})),
            timestamp=self._clock().astimezone(timezone.utc).isoformat(),
        )
        self._events.append(event)
        for sink in self._sinks:
            sink(_copy_event(event))
        return _copy_event(event)

    def to_json(self) -> str:
        return json.dumps(
            [
                {
                    "sequence": event.sequence,
                    "action": event.action,
                    "details": _redact(event.details),
                    "timestamp": event.timestamp,
                }
                for event in self._events
            ],
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, payload: str) -> AuditTrail:
        values = json.loads(payload)
        if not isinstance(values, list):
            raise ValueError("audit trail must be an array")
        events = []
        for value in values:
            if not isinstance(value, Mapping):
                raise ValueError("audit event must be an object")
            event = AuditEvent.from_dict(value)
            events.append(
                AuditEvent(
                    sequence=event.sequence,
                    action=event.action,
                    details=_redact(event.details),
                    timestamp=event.timestamp,
                )
            )
        return cls(events=events)

    def replay(self, sinks: Sequence[AuditSink]) -> None:
        """Emit stored events in their original order without mutation."""
        for event in self._events:
            for sink in sinks:
                sink(_copy_event(event))

    def _validate_sequence(self) -> None:
        sequences = [event.sequence for event in self._events]
        expected = list(range(1, len(self._events) + 1))
        if sequences != expected:
            raise ValueError("audit event sequence must be contiguous from 1")


def _redact(value: Any, key: str | None = None) -> Any:
    if key is not None and key.lower() in _SECRET_KEYS:
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        result = value
        for pattern in _SECRET_PATTERNS:
            result = pattern.sub(_redact_match, result)
        return result
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return repr(value)


def _redact_match(match: re.Match[str]) -> str:
    prefix = match.group(1) if match.lastindex else ""
    return f"{prefix}[REDACTED]"


def _copy_event(event: AuditEvent) -> AuditEvent:
    return AuditEvent(
        sequence=event.sequence,
        action=event.action,
        details=_redact(event.details),
        timestamp=event.timestamp,
    )
