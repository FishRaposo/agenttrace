"""HTTP API exporter for trace data."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from agenttrace.capture import redact
from agenttrace.exporters.base import BaseExporter

_HAS_URLLIB = True

logger = logging.getLogger(__name__)


class APIExporter(BaseExporter):
    """Exports trace data to a remote trace collection server via HTTP.

    Uses urllib for zero-dependency HTTP requests. Data is buffered
    and sent in batches. Failed requests are retried with exponential
    backoff.

    Args:
        endpoint: Base URL of the trace server API.
        buffer_size: Number of entries to buffer before sending.
        max_retries: Maximum number of retry attempts per request.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/api/traces",
        buffer_size: int = 50,
        max_retries: int = 2,
        timeout: float = 2.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._api_base_url = self._normalize_api_base_url(endpoint)
        self._runs_url = f"{self._api_base_url}/runs"
        self._traces_url = f"{self._api_base_url}/traces"
        self._traces_batch_url = f"{self._api_base_url}/traces/batch"
        self._buffer_size = buffer_size
        self._max_retries = max_retries
        self._timeout = timeout
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._run_buffer: list[dict[str, Any]] = []
        self._span_buffer: list[dict[str, Any]] = []
        self._delivery = {"delivered": 0, "failed": 0, "retries": 0}

    @staticmethod
    def _normalize_api_base_url(endpoint: str) -> str:
        """Return the base `/api` URL from either `/api` or `/api/traces`."""
        stripped = endpoint.rstrip("/")
        if stripped.endswith("/traces") or stripped.endswith("/runs"):
            return stripped.rsplit("/", 1)[0]
        return stripped

    @staticmethod
    def _span_payload(span_data: dict[str, Any]) -> dict[str, Any]:
        """Convert SDK span dictionaries to the server trace create schema."""
        payload = dict(span_data)
        if "span_id" not in payload and "id" in payload:
            payload["span_id"] = payload.pop("id")
        return payload

    def _send_request(self, url: str, data: Any, attempt: int = 0) -> bool:
        """Send an HTTP POST request with retry logic.

        Args:
            url: Target URL.
            data: JSON-serializable payload.
            attempt: Current retry attempt number.

        Returns:
            True if the request succeeded, False otherwise.
        """
        if not _HAS_URLLIB:
            logger.error("urllib not available; cannot export traces via HTTP")
            return False

        try:
            payload = json.dumps(redact(data), default=str).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers=self._headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return 200 <= resp.status < 300
        except Exception as e:
            if (
                isinstance(e, urllib.error.HTTPError)
                and 400 <= e.code < 500
                and e.code not in (408, 429)
            ):
                return False
            if attempt < self._max_retries - 1:
                self._delivery["retries"] += 1
                backoff = min(0.05 * 2**attempt, 0.2)
                logger.warning(
                    "Export failed (attempt %d/%d): %s. Retrying in %ds",
                    attempt + 1,
                    self._max_retries,
                    str(e),
                    backoff,
                )
                time.sleep(backoff)
                return self._send_request(url, data, attempt + 1)
            logger.error(
                "Export failed after %d attempts: %s", self._max_retries, str(e)
            )
            return False

    def _flush_runs(self) -> None:
        """Send all buffered run data to the server."""
        if not self._run_buffer:
            return

        for run_data in self._run_buffer:
            success = self._send_request(self._runs_url, run_data)
            self._delivery["delivered" if success else "failed"] += 1

        self._run_buffer.clear()

    def _flush_spans(self) -> None:
        """Send all buffered span data to the server via batch endpoint."""
        if not self._span_buffer:
            return

        payloads = [self._span_payload(s) for s in self._span_buffer]
        if len(payloads) == 1:
            success = self._send_request(self._traces_url, payloads[0])
        else:
            success = self._send_request(self._traces_batch_url, payloads)

        self._delivery["delivered" if success else "failed"] += len(payloads)
        self._span_buffer.clear()

    def export_run(self, run_data: dict[str, Any]) -> None:
        """Export run data to the trace server.

        Args:
            run_data: Dictionary containing run information.
        """
        self._run_buffer.append(run_data)
        if len(self._run_buffer) >= self._buffer_size:
            self._flush_runs()

    def export_span(self, span_data: dict[str, Any]) -> None:
        """Export span data to the trace server.

        Args:
            span_data: Dictionary containing span information.
        """
        self._span_buffer.append(span_data)
        if len(self._span_buffer) >= self._buffer_size:
            self._flush_spans()

    def flush(self) -> None:
        """Flush all buffered data to the trace server."""
        self._flush_runs()
        self._flush_spans()

    def delivery_stats(self) -> dict[str, int]:
        return dict(self._delivery)
