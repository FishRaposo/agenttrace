"""Tracer module — central orchestrator for tracing agent runs and spans."""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from enum import Enum
from threading import RLock, get_ident
from typing import Any, Optional

from agenttrace.capture import capture_snapshot
from agenttrace.context import RunContext
from agenttrace.exporters.base import BaseExporter
from agenttrace.span import Span, SpanStatus, SpanType


def _context_owner():
    try:
        return (get_ident(), asyncio.current_task())
    except RuntimeError:
        return (get_ident(), None)


class RunStatus(str, Enum):
    """Status of a run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class _RunState:
    """Internal state tracker for an active run.

    Attributes:
        id: Unique run identifier.
        name: Human-readable run name.
        status: Current run status.
        start_time: When the run started.
        end_time: When the run ended.
        metadata: Run-level metadata.
        spans: List of spans recorded in this run.
    """

    def __init__(
        self,
        run_id: str,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        self.id: str = run_id
        self.correlation_id: Optional[str] = correlation_id
        self.name: str = name
        self.status: RunStatus = RunStatus.RUNNING
        self.start_time: datetime = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.metadata: Optional[dict[str, Any]] = metadata
        self.spans: list[Span] = []
        self.lock = RLock()
        self.closed = False
        self.owner = _context_owner()
        self.exported_spans: set[str] = set()

    def to_dict(self) -> dict[str, Any]:
        """Convert run state to a dictionary for serialization.

        Returns:
            Dictionary representation of the run.
        """
        return {
            "id": self.id,
            "correlation_id": self.correlation_id,
            "name": self.name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_cost": sum(s.cost_usd or 0.0 for s in self.spans),
            "total_tokens": sum(
                (s.token_usage or {}).get("total_tokens", 0) for s in self.spans
            ),
            "span_count": len(self.spans),
            "metadata": self.metadata,
        }


class Tracer:
    """Central tracer for recording agent runs and their spans.

    The Tracer manages the lifecycle of runs and spans, coordinates
    exporters, and provides context-manager support for ergonomic usage.

    Multiple tracer instances are supported — create one per workflow
    or use a single global tracer as needed.

    Attributes:
        exporter: The configured exporter for trace data.
    """

    _instance: Optional[Tracer] = None

    def __init__(
        self, sample_rate: float = 1.0, *, capture_content: bool = False
    ) -> None:
        self._exporter: Optional[BaseExporter] = None
        self._run_var: ContextVar[Optional[_RunState]] = ContextVar(
            f"run-{id(self)}", default=None
        )
        self._stack_var: ContextVar[tuple[Span, ...]] = ContextVar(
            f"stack-{id(self)}", default=()
        )
        self._tokens: ContextVar[Any] = ContextVar(f"tokens-{id(self)}", default=None)
        self._sampled_var: ContextVar[bool] = ContextVar(
            f"sampled-{id(self)}", default=True
        )
        self.capture_content = capture_content
        self._sample_rate = max(0.0, min(1.0, sample_rate))

    @property
    def _current_run(self) -> Optional[_RunState]:
        return self._run_var.get()

    @property
    def _span_stack(self) -> tuple[Span, ...]:
        return self._stack_var.get()

    def _export(self, kind: str, payload: dict[str, Any]) -> None:
        if self._exporter is None or not self._sampled_var.get():
            return
        try:
            safe = capture_snapshot(payload, capture_content=self.capture_content)
            getattr(self._exporter, f"export_{kind}")(safe)
        except Exception:
            logging.getLogger(__name__).warning(
                "Telemetry export failed", exc_info=True
            )

    def set_exporter(self, exporter: BaseExporter) -> None:
        """Set the exporter used to write trace data.

        Args:
            exporter: An instance of a BaseExporter subclass.
        """
        self._exporter = exporter

    def start_run(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> _RunContext:
        """Start a new trace run.

        Args:
            name: A human-readable name for the run.
            metadata: Optional metadata to attach to the run.
            correlation_id: Optional correlation ID for multi-agent trace correlation.

        Returns:
            A context manager for the run.

        Raises:
            RuntimeError: If a run is already in progress.
        """
        if self._current_run is not None:
            raise RuntimeError(
                "A run is already in progress. End the current run first."
            )

        run_id = str(uuid.uuid4())
        # Head-based deterministic sampling
        run_state = _RunState(
            run_id=run_id, name=name, metadata=metadata, correlation_id=correlation_id
        )
        run_token = self._run_var.set(run_state)
        stack_token = self._stack_var.set(())
        sampled_token = self._sampled_var.set(self._is_sampled(run_id))
        global_tokens = RunContext.bind(run_id, metadata, correlation_id)
        self._tokens.set((run_token, stack_token, sampled_token, global_tokens))
        self._export("run", run_state.to_dict())

        return _RunContext(tracer=self, run_state=run_state)

    def _is_sampled(self, run_id: str) -> bool:
        """Deterministic head-based sampling decision.

        Uses the first 8 hex chars of an MD5 hash of the run ID
        to generate a uniform value in [0, 1). Traces are kept when
        this value is less than the configured sample_rate.

        Args:
            run_id: The run identifier.

        Returns:
            True if the run should be traced, False otherwise.
        """
        if self._sample_rate >= 1.0:
            return True
        if self._sample_rate <= 0.0:
            return False
        import hashlib

        digest = hashlib.md5(run_id.encode()).hexdigest()
        value = int(digest[:8], 16) / 0xFFFFFFFF
        return value < self._sample_rate

    def start_span(
        self,
        name: str,
        span_type: SpanType = SpanType.CUSTOM,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Span:
        """Start a new span within the current run.

        Args:
            name: A human-readable name for the span.
            span_type: The type of operation being traced.
            metadata: Optional metadata to attach to the span.

        Returns:
            The newly created Span.

        Raises:
            RuntimeError: If no run is currently active.
        """
        if self._current_run is None:
            raise RuntimeError("No active run. Call start_run() first.")

        parent_id: Optional[str] = None
        if self._span_stack:
            parent_id = self._span_stack[-1].id

        span = Span(
            run_id=self._current_run.id,
            name=name,
            span_type=span_type,
            metadata=metadata,
            parent_span_id=parent_id,
        )

        with self._current_run.lock:
            if self._current_run.closed:
                raise RuntimeError("Run is closed; late spans are rejected")
            self._current_run.spans.append(span)
        self._stack_var.set((*self._span_stack, span))
        RunContext.set_current_span(span)

        return span

    def end_span(self, span: Span) -> None:
        """End a span and export it.

        Args:
            span: The span to end.

        Raises:
            RuntimeError: If the span is not the current active span.
        """
        if not self._span_stack or self._span_stack[-1].id != span.id:
            raise RuntimeError("Span mismatch. Spans must be ended in LIFO order.")

        run = self._current_run
        if run is None:
            raise RuntimeError("Run is closed; late spans are rejected")
        with run.lock:
            if run.closed:
                raise RuntimeError("Run is closed; late spans are rejected")
            self._stack_var.set(self._span_stack[:-1])
            RunContext.set_current_span(
                self._span_stack[-1] if self._span_stack else None
            )
            self._export("span", span.to_dict())
            run.exported_spans.add(span.id)

    def end_run(self, status: RunStatus = RunStatus.COMPLETED) -> None:
        """End the current run.

        Args:
            status: The final status of the run.

        Raises:
            RuntimeError: If no run is currently active.
        """
        if self._current_run is None:
            raise RuntimeError("No active run to end.")

        run = self._current_run
        if run.owner != _context_owner():
            raise RuntimeError("Only the originating context can close its root")
        tokens = self._tokens.get()
        try:
            with run.lock:
                if run.closed:
                    raise RuntimeError("Run is already closed")
                run.status = status
                run.end_time = datetime.now(timezone.utc)
                for span in run.spans:
                    if span.status == SpanStatus.STARTED:
                        span.set_error("Run ended before span completed")
                        if status == RunStatus.CANCELLED:
                            span.status = SpanStatus.CANCELLED
                    if span.id not in run.exported_spans:
                        self._export("span", span.to_dict())
                        run.exported_spans.add(span.id)
                run.closed = True
                self._export("run", run.to_dict())
        finally:
            if tokens:
                run_token, stack_token, sampled_token, global_tokens = tokens
                self._run_var.reset(run_token)
                self._stack_var.reset(stack_token)
                self._sampled_var.reset(sampled_token)
                RunContext.restore(global_tokens)
                self._tokens.set(None)

    def flush(self) -> None:
        """Flush any buffered trace data to the exporter."""
        if self._exporter is not None:
            try:
                self._exporter.flush()
            except Exception:
                logging.getLogger(__name__).warning(
                    "Telemetry flush failed", exc_info=True
                )

    def close(self, timeout: float = 5.0) -> Optional[dict[str, Any]]:
        """Stop bounded delivery; inline exporters retain synchronous flush."""
        if self._exporter is not None and hasattr(self._exporter, "close"):
            try:
                return self._exporter.close(timeout=timeout)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Telemetry close failed", exc_info=True
                )
                return None
        self.flush()
        return None

    def add_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Log an event within the current run.

        Events are attached to the current span if one is active,
        otherwise to the run's metadata trail.

        Args:
            event_type: Event identifier.
            payload: Event data.
        """
        if self._current_run is None:
            return

        from datetime import datetime, timezone

        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        # Attach to current span if active
        if self._span_stack:
            span = self._span_stack[-1]
            if span.metadata is None:
                span.metadata = {}
            span.metadata.setdefault("events", []).append(event)
        else:
            # Attach to run metadata
            if self._current_run.metadata is None:
                self._current_run.metadata = {}
            self._current_run.metadata.setdefault("events", []).append(event)

    def run(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> _RunContext:
        """Alias for start_run() for ergonomic usage.

        Args:
            name: A human-readable name for the run.
            metadata: Optional metadata to attach to the run.
            correlation_id: Optional correlation ID for multi-agent trace correlation.

        Returns:
            A context manager for the run.
        """
        return self.start_run(
            name=name, metadata=metadata, correlation_id=correlation_id
        )

    def span(
        self,
        name: str,
        span_type: SpanType = SpanType.CUSTOM,
        metadata: Optional[dict[str, Any]] = None,
    ) -> _SpanContext:
        """Create a context-managed span.

        Args:
            name: A human-readable name for the span.
            span_type: The type of operation being traced.
            metadata: Optional metadata to attach to the span.

        Returns:
            A context manager for the span.
        """
        return _SpanContext(
            tracer=self, name=name, span_type=span_type, metadata=metadata
        )


class _RunContext:
    """Context manager for a run.

    Automatically ends the run when the context exits.

    Args:
        tracer: The parent Tracer instance.
        run_state: The internal run state.
    """

    def __init__(self, tracer: Tracer, run_state: _RunState) -> None:
        self._tracer = tracer
        self._run_state = run_state

    def __enter__(self) -> _RunState:
        return self._run_state

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        status = (
            RunStatus.CANCELLED
            if exc_type is not None and issubclass(exc_type, asyncio.CancelledError)
            else RunStatus.FAILED
            if exc_type is not None
            else RunStatus.COMPLETED
        )
        self._tracer.end_run(status=status)


class _SpanContext:
    """Context manager for a span.

    Automatically ends the span when the context exits.

    Args:
        tracer: The parent Tracer instance.
        name: Span name.
        span_type: Span type.
        metadata: Optional span metadata.
    """

    def __init__(
        self,
        tracer: Tracer,
        name: str,
        span_type: SpanType,
        metadata: Optional[dict[str, Any]],
    ) -> None:
        self._tracer = tracer
        self._name = name
        self._span_type = span_type
        self._metadata = metadata
        self._span: Optional[Span] = None
        self._root: Optional[_RunState] = None

    def __enter__(self) -> Span:
        self._span = self._tracer.start_span(
            name=self._name, span_type=self._span_type, metadata=self._metadata
        )
        self._root = self._tracer._current_run
        return self._span

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._span is not None and self._root is not None:
            with self._root.lock:
                if self._root.closed:
                    # The owner already finalized/exported this unfinished child.
                    # Automatic cleanup must preserve the application's outcome.
                    stack = self._tracer._span_stack
                    if stack and stack[-1] is self._span:
                        self._tracer._stack_var.set(stack[:-1])
                    if RunContext.get_current_run_id() == self._root.id:
                        remaining = self._tracer._span_stack
                        RunContext.set_current_span(
                            remaining[-1] if remaining else None
                        )
                    return
                self._finish(exc_type, exc_val)

    def _finish(self, exc_type: Any, exc_val: Any) -> None:
        if self._span is not None:
            if exc_type is not None:
                self._span.set_error(str(exc_val))
                if issubclass(exc_type, asyncio.CancelledError):
                    self._span.status = SpanStatus.CANCELLED
            else:
                self._span.end()
            self._tracer.end_span(self._span)


def get_current_tracer() -> Tracer:
    """Get or create the global tracer instance.

    Returns:
        The global Tracer singleton.
    """
    if Tracer._instance is None:
        Tracer._instance = Tracer()
    return Tracer._instance


def set_current_tracer(tracer: Tracer) -> None:
    """Set the global tracer instance.

    Args:
        tracer: The Tracer instance to use as the global default.
    """
    Tracer._instance = tracer
