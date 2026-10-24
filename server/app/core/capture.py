"""Bounded credential redaction for new storage and historical presentation.

This deliberately does not claim comprehensive PII detection.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

_SECRET_KEY = re.compile(
    r"password|authorization|api.?key|access.?token|refresh.?token|^token$|private.?key|secret|cookie|credential",
    re.I,
)
_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{8,})\b"),
)


def sanitize(value: Any, *, depth: int = 0) -> Any:
    """Return a detached, bounded JSON value, redacting supported credentials."""
    if depth >= 8:
        return "[DEPTH LIMIT]"
    if isinstance(value, Mapping):
        return {
            str(key)[:255]: "[REDACTED]"
            if _SECRET_KEY.search(str(key))
            else sanitize(item, depth=depth + 1)
            for key, item in list(value.items())[:100]
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, str):
        for pattern in _PATTERNS:
            value = pattern.sub("[REDACTED]", value)
        return value[:4000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize(str(value), depth=depth)


def bounded(value: Any) -> Any:
    result = sanitize(value)
    if len(json.dumps(result, default=str).encode()) > 65536:
        return {"capture": "omitted", "reason": "serialized payload exceeds 64 KiB"}
    return result


def present(value: Any) -> Any:
    """Redact bounded text in owned read models without truncating result rows.

    Redacted dictionary labels receive collision suffixes rather than discarding
    distinct groups and their costs. This is intentionally not applied to auth.
    """
    if isinstance(value, str):
        return sanitize(value)
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            label = sanitize(str(key))
            unique, suffix = label, 2
            while unique in result:
                unique = f"{label} ({suffix})"
                suffix += 1
            result[unique] = present(item)
        return result
    if isinstance(value, (list, tuple)):
        return [present(item) for item in value]
    return value
