"""JSONL file exporter for trace data."""

from __future__ import annotations

import json
import os
from typing import Any

from agenttrace.exporters.base import BaseExporter


class JSONLExporter(BaseExporter):
    """Exports trace data to a JSONL (JSON Lines) file.

    Each run and span is appended as a single JSON line. Data is buffered
    in memory and written to disk when the buffer is full or on flush.

    Args:
        path: File path for the JSONL output.
        buffer_size: Number of entries to buffer before writing to disk.
    """

    def __init__(self, path: str = "traces.jsonl", buffer_size: int = 10) -> None:
        self._path = path
        self._buffer_size = buffer_size
        self._buffer: list[str] = []

    def _write_buffer(self) -> None:
        """Write buffered entries to the JSONL file."""
        if not self._buffer:
            return

        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(self._path, "a", encoding="utf-8") as f:
            for line in self._buffer:
                f.write(line + "\n")

        self._buffer.clear()

    def _add_to_buffer(self, data: dict[str, Any]) -> None:
        """Add a data entry to the buffer and flush if needed.

        Args:
            data: Dictionary to serialize and buffer.
        """
        line = json.dumps(data, default=str)
        self._buffer.append(line)

        if len(self._buffer) >= self._buffer_size:
            self._write_buffer()

    def export_run(self, run_data: dict[str, Any]) -> None:
        """Export run data to the JSONL file.

        Args:
            run_data: Dictionary containing run information.
        """
        entry = {"type": "run", "data": run_data}
        self._add_to_buffer(entry)

    def export_span(self, span_data: dict[str, Any]) -> None:
        """Export span data to the JSONL file.

        Args:
            span_data: Dictionary containing span information.
        """
        entry = {"type": "span", "data": span_data}
        self._add_to_buffer(entry)

    def flush(self) -> None:
        """Flush all buffered data to the JSONL file."""
        self._write_buffer()
