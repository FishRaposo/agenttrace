"""Bounded worker; slow custom exporters cannot block application shutdown."""

from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any

from agenttrace.capture import capture_snapshot
from agenttrace.exporters.base import BaseExporter


class BoundedExporter(BaseExporter):
    def __init__(
        self,
        exporter: BaseExporter,
        *,
        capacity: int = 256,
        max_event_bytes: int = 64 * 1024,
        batch_size: int = 16,
        capture_content: bool = False,
    ) -> None:
        if capacity < 1 or batch_size < 1 or batch_size > 16 or max_event_bytes < 1:
            raise ValueError("Invalid exporter bounds")
        self.exporter = exporter
        self.max_event_bytes = max_event_bytes
        self.batch_size = batch_size
        self.capture_content = capture_content
        self._queue: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue(capacity)
        self._lock = threading.Lock()
        self._accepting = True
        self._stop = threading.Event()
        self._counts = {
            "queued": 0,
            "delivered": 0,
            "dropped": 0,
            "failed": 0,
            "retries": 0,
        }
        self._worker = threading.Thread(
            target=self._run, name="agenttrace-export", daemon=True
        )
        self._worker.start()

    def _enqueue(self, kind: str, payload: dict[str, Any]) -> None:
        try:
            snapshot = capture_snapshot(payload, capture_content=self.capture_content)
            size = len(json.dumps(snapshot, allow_nan=False).encode())
        except Exception:
            with self._lock:
                self._counts["dropped"] += 1
            return
        with self._lock:
            if not self._accepting or size > self.max_event_bytes:
                self._counts["dropped"] += 1
                return
            try:
                self._queue.put_nowait((kind, snapshot))
                self._counts["queued"] += 1
            except queue.Full:
                self._counts["dropped"] += 1

    def export_run(self, run_data: dict[str, Any]) -> None:
        self._enqueue("run", run_data)

    def export_span(self, span_data: dict[str, Any]) -> None:
        self._enqueue("span", span_data)

    def _run(self) -> None:
        while not self._stop.is_set() or not self._queue.empty():
            try:
                batch = [self._queue.get(timeout=0.02)]
            except queue.Empty:
                continue
            while len(batch) < self.batch_size:
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            failed = 0
            try:
                before = (
                    self.exporter.delivery_stats()
                    if hasattr(self.exporter, "delivery_stats")
                    else {}
                )
                for kind, payload in batch:
                    getattr(self.exporter, f"export_{kind}")(payload)
                self.exporter.flush()
                after = (
                    self.exporter.delivery_stats()
                    if hasattr(self.exporter, "delivery_stats")
                    else {}
                )
                failed = min(
                    len(batch), after.get("failed", 0) - before.get("failed", 0)
                )
                retries = after.get("retries", 0) - before.get("retries", 0)
            except Exception:
                failed, retries = len(batch), 0
            with self._lock:
                self._counts["failed"] += failed
                self._counts["delivered"] += len(batch) - failed
                self._counts["retries"] += retries
            for _ in batch:
                self._queue.task_done()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counts = dict(self._counts)
        counts["unfinished"] = counts["queued"] - counts["delivered"] - counts["failed"]
        counts["complete"] = (
            counts["unfinished"] == counts["dropped"] == counts["failed"] == 0
        )
        return counts

    def flush(self) -> None:
        self.flush_until()

    def flush_until(self, timeout: float = 5.0) -> dict[str, Any]:
        """Wait up to the deadline without counting unfinished events as delivered."""
        deadline = time.monotonic() + max(0, timeout)
        while self.snapshot()["unfinished"] and time.monotonic() < deadline:
            time.sleep(min(0.005, max(0, deadline - time.monotonic())))
        return self.snapshot()

    def close(self, timeout: float = 5.0) -> dict[str, Any]:
        with self._lock:
            self._accepting = False
        self._stop.set()
        return self.flush_until(timeout)
