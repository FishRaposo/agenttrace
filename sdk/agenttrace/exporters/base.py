"""Base exporter interface for trace data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseExporter(ABC):
    """Abstract base class for trace data exporters.

    Subclass this to create custom export destinations for trace data.
    Each exporter must implement methods for exporting runs, spans,
    and flushing buffered data.
    """

    def delivery_stats(self) -> dict[str, int]:
        """Optional cumulative transport accounting; empty means custom handoff only."""
        return {}

    def close(self, timeout: float = 5.0) -> dict[str, Any] | None:
        """Inline exporters flush; bounded exporters override the deadline."""
        self.flush()
        return None

    @abstractmethod
    def export_run(self, run_data: dict[str, Any]) -> None:
        """Export run-level trace data.

        Args:
            run_data: Dictionary containing run information.
        """
        ...

    @abstractmethod
    def export_span(self, span_data: dict[str, Any]) -> None:
        """Export span-level trace data.

        Args:
            span_data: Dictionary containing span information.
        """
        ...

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered trace data to the destination."""
        ...
