"""OpenTelemetry OTLP exporter for AgentTrace spans."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

try:
    import urllib.request

    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False

from agenttrace.exporters.base import BaseExporter

logger = logging.getLogger(__name__)

_NANOS_PER_SECOND = 1_000_000_000


def _to_nanos(dt_str: str) -> int:
    """Convert ISO 8601 datetime string to Unix nanoseconds.

    Args:
        dt_str: ISO 8601 datetime string.

    Returns:
        Integer nanoseconds since Unix epoch.
    """
    from datetime import datetime, timezone

    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * _NANOS_PER_SECOND)
    except Exception:
        return 0


def _span_to_otlp(span_data: dict[str, Any], service_name: str) -> dict[str, Any]:
    """Convert AgentTrace span to OTLP span format.

    Args:
        span_data: AgentTrace span dictionary.
        service_name: Service name for the resource.

    Returns:
        OTLP-compatible span dictionary.
    """
    start_ns = _to_nanos(span_data.get("start_time", ""))
    end_ns = (
        _to_nanos(span_data.get("end_time", "")) if span_data.get("end_time") else None
    )

    attrs = [
        {
            "key": "span.type",
            "value": {"stringValue": span_data.get("span_type", "custom")},
        },
        {
            "key": "span.status",
            "value": {"stringValue": span_data.get("status", "unknown")},
        },
    ]
    if span_data.get("cost_usd") is not None:
        attrs.append(
            {"key": "cost.usd", "value": {"doubleValue": span_data["cost_usd"]}}
        )
    if span_data.get("token_usage"):
        tu = span_data["token_usage"]
        attrs.append(
            {
                "key": "tokens.total",
                "value": {"intValue": str(tu.get("total_tokens", 0))},
            }
        )
    if span_data.get("error"):
        attrs.append(
            {"key": "error.message", "value": {"stringValue": span_data["error"]}}
        )

    return {
        "traceId": _id_to_hex(span_data.get("run_id", ""), 32),
        "spanId": _id_to_hex(span_data.get("id", ""), 16),
        "parentSpanId": _id_to_hex(span_data.get("parent_span_id"), 16)
        if span_data.get("parent_span_id")
        else "",
        "name": span_data.get("name", "unknown"),
        "kind": 1,
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(end_ns) if end_ns else str(start_ns),
        "attributes": attrs,
        "status": {"code": 2 if span_data.get("status") == "error" else 1},
    }


def _id_to_hex(id_str: Optional[str], length: int) -> str:
    """Convert a UUID to a hex ID for OTLP.

    Args:
        id_str: UUID string.
        length: Desired hex length.

    Returns:
        Hex string padded to length.
    """
    if not id_str:
        return "0" * length
    hex_id = id_str.replace("-", "")
    return hex_id[:length].ljust(length, "0")


class OTLPExporter(BaseExporter):
    """Exports AgentTrace spans as OTLP to an OpenTelemetry collector.

    Sends traces in OTLP JSON format over HTTP. Zero dependencies beyond
    the Python standard library.

    Args:
        endpoint: OTLP collector traces endpoint.
        service_name: Service name for the resource.
        buffer_size: Number of spans to buffer before sending.
        max_retries: Maximum retry attempts.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4318/v1/traces",
        service_name: Optional[str] = None,
        buffer_size: int = 50,
        max_retries: int = 3,
        timeout: float = 10.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._service_name = service_name or os.environ.get(
            "OTEL_SERVICE_NAME", "agenttrace"
        )
        self._buffer_size = buffer_size
        self._max_retries = max_retries
        self._timeout = timeout
        self._span_buffer: list[dict[str, Any]] = []

    def export_run(self, run_data: dict[str, Any]) -> None:
        """Export run data as an OTLP scope span.

        Args:
            run_data: Run dictionary to convert and buffer.
        """
        start_ns = _to_nanos(run_data.get("start_time", ""))
        end_ns = (
            _to_nanos(run_data.get("end_time", ""))
            if run_data.get("end_time")
            else None
        )

        attrs: list[dict[str, Any]] = [
            {
                "key": "run.name",
                "value": {"stringValue": run_data.get("name", "unknown")},
            },
            {
                "key": "run.status",
                "value": {"stringValue": run_data.get("status", "unknown")},
            },
            {
                "key": "run.span_count",
                "value": {"intValue": str(run_data.get("span_count", 0))},
            },
        ]
        if run_data.get("correlation_id"):
            attrs.append(
                {
                    "key": "run.correlation_id",
                    "value": {"stringValue": run_data["correlation_id"]},
                }
            )
        if run_data.get("total_cost"):
            attrs.append(
                {
                    "key": "run.total_cost",
                    "value": {"doubleValue": run_data["total_cost"]},
                }
            )
        if run_data.get("total_tokens"):
            attrs.append(
                {
                    "key": "run.total_tokens",
                    "value": {"intValue": str(run_data["total_tokens"])},
                }
            )

        otlp_span: dict[str, Any] = {
            "traceId": _id_to_hex(run_data.get("id", ""), 32),
            "spanId": _id_to_hex(run_data.get("id", ""), 16),
            "parentSpanId": "",
            "name": f"run:{run_data.get('name', 'unknown')}",
            "kind": 1,
            "startTimeUnixNano": str(start_ns),
            "endTimeUnixNano": str(end_ns) if end_ns else str(start_ns),
            "attributes": attrs,
            "status": {"code": 2 if run_data.get("status") == "failed" else 1},
        }

        self._span_buffer.append(otlp_span)

        if len(self._span_buffer) >= self._buffer_size:
            self._flush()

    def export_span(self, span_data: dict[str, Any]) -> None:
        """Buffer a span for OTLP export.

        Args:
            span_data: Span dictionary to convert and buffer.
        """
        otlp_span = _span_to_otlp(span_data, self._service_name)
        self._span_buffer.append(otlp_span)

        if len(self._span_buffer) >= self._buffer_size:
            self._flush()

    def _flush(self) -> None:
        """Send buffered spans as an OTLP batch."""
        if not self._span_buffer:
            return

        payload = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": self._service_name},
                            }
                        ]
                    },
                    "scopeSpans": [{"spans": list(self._span_buffer)}],
                }
            ]
        }

        self._span_buffer.clear()
        self._send_with_retry(payload)

    def _send_with_retry(self, payload: dict[str, Any], attempt: int = 0) -> bool:
        """Send OTLP payload with retry logic.

        Args:
            payload: OTLP JSON payload.
            attempt: Current retry attempt.

        Returns:
            True if successful, False otherwise.
        """
        if not _HAS_URLLIB:
            logger.error("urllib not available; cannot export OTLP")
            return False

        try:
            data = json.dumps(payload, default=str).encode("utf-8")
            req = urllib.request.Request(
                self._endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return 200 <= resp.status < 300
        except Exception as e:
            if attempt < self._max_retries - 1:
                backoff = 2**attempt
                logger.warning(
                    "OTLP export failed (attempt %d/%d): %s. Retrying in %ds",
                    attempt + 1,
                    self._max_retries,
                    str(e),
                    backoff,
                )
                time.sleep(backoff)
                return self._send_with_retry(payload, attempt + 1)
            logger.error(
                "OTLP export failed after %d attempts: %s",
                self._max_retries,
                str(e),
            )
            return False

    def flush(self) -> None:
        """Flush all buffered spans to the OTLP collector."""
        self._flush()
