"""Context module — manages current run and span state via context variables."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from agenttrace.span import Span

_current_run_id: ContextVar[Optional[str]] = ContextVar("current_run_id", default=None)
_current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)
_current_run_metadata: ContextVar[Optional[dict]] = ContextVar(
    "current_run_metadata", default=None
)
_current_correlation_id: ContextVar[Optional[str]] = ContextVar(
    "current_correlation_id", default=None
)


class RunContext:
    """Manages context state for the current active run.

    Provides static methods to get and set the current run ID, active span,
    and run metadata using Python context variables for thread-safe and
    asyncio-safe state management.
    """

    @staticmethod
    def set_current_run(run_id: str, metadata: Optional[dict] = None) -> None:
        """Set the current active run.

        Args:
            run_id: The unique identifier of the active run.
            metadata: Optional metadata associated with the run.
        """
        _current_run_id.set(run_id)
        _current_run_metadata.set(metadata)

    @staticmethod
    def get_current_run_id() -> Optional[str]:
        """Get the current active run ID.

        Returns:
            The current run ID, or None if no run is active.
        """
        return _current_run_id.get()

    @staticmethod
    def get_current_run_metadata() -> Optional[dict]:
        """Get the current run metadata.

        Returns:
            The current run metadata dictionary, or None.
        """
        return _current_run_metadata.get()

    @staticmethod
    def set_current_span(span: Optional[Span]) -> None:
        """Set the current active span.

        Args:
            span: The span to set as current, or None to clear.
        """
        _current_span.set(span)

    @staticmethod
    def get_current_span() -> Optional[Span]:
        """Get the current active span.

        Returns:
            The current span, or None if no span is active.
        """
        return _current_span.get()

    @staticmethod
    def set_current_correlation_id(correlation_id: str | None) -> None:
        """Set the current correlation ID for distributed tracing.

        Args:
            correlation_id: Correlation ID string, or None to clear.
        """
        _current_correlation_id.set(correlation_id)

    @staticmethod
    def get_current_correlation_id() -> Optional[str]:
        """Get the current correlation ID.

        Returns:
            The current correlation ID, or None.
        """
        return _current_correlation_id.get()

    @staticmethod
    def clear() -> None:
        """Clear all context state."""
        _current_run_id.set(None)
        _current_span.set(None)
        _current_run_metadata.set(None)
        _current_correlation_id.set(None)
