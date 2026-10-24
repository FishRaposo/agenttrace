"""Bounded capture policy. Credential redaction is not comprehensive PII detection."""

from __future__ import annotations

import json
import re
from typing import Any

_SECRET = re.compile(
    r"api.?key|authorization|password|secret|credential|access.?token|refresh.?token|cookie",
    re.I,
)
_PATTERN = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|Bearer\s+[A-Za-z0-9._~+/-]{8,})",
    re.I,
)
_CONTENT_KEYS = frozenset(
    {
        "prompt",
        "prompts",
        "message",
        "messages",
        "query",
        "input",
        "inputs",
        "output",
        "outputs",
        "content",
        "instructions",
        "text",
        "response",
        "tool_input",
        "return_values",
        "document",
        "documents",
        "body",
        "payload",
        "args",
        "kwargs",
        "question",
        "answer",
        "completion",
    }
)


def _without_content(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: {
                "captured": False,
                "type": type(item).__name__,
                "size_bytes": len(json.dumps(item, default=str).encode()),
            }
            if key.lower() in _CONTENT_KEYS
            else _without_content(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_without_content(item) for item in value]
    return value


def redact(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[depth limit]"
    if isinstance(value, dict):
        return {
            str(k)[:200]: "[REDACTED]"
            if _SECRET.search(str(k))
            else redact(v, depth + 1)
            for k, v in list(value.items())[:100]
        }
    if isinstance(value, (list, tuple)):
        return [redact(v, depth + 1) for v in value[:100]]
    if isinstance(value, str):
        return _PATTERN.sub("[REDACTED]", value)[:4096]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact(str(value), depth + 1)


def capture_snapshot(
    payload: dict[str, Any], *, capture_content: bool = False
) -> dict[str, Any]:
    """Detach the payload, retaining identity and safe diagnostic fields."""
    safe = redact(payload)
    if not capture_content and safe.get("metadata"):
        safe["metadata"] = _without_content(safe["metadata"])
    summaries = {}
    for key in ("input_data", "output_data"):
        if key in safe:
            summaries[key] = {
                "type": type(payload.get(key)).__name__,
                "size_bytes": len(json.dumps(safe[key], default=str).encode()),
            }
            if not capture_content:
                safe[key] = None
    if summaries:
        metadata = safe.get("metadata") or {}
        metadata.setdefault(
            "capture",
            {
                "mode": "content_opt_in" if capture_content else "metadata_only",
                "summaries": summaries,
                "redaction": "credential_patterns_v1",
            },
        )
        safe["metadata"] = metadata
    return safe
