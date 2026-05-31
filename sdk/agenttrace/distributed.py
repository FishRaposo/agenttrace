"""Distributed tracing support for cross-service tracing.

Propagates trace context across service boundaries using
W3C Trace Context standard.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from agenttrace.context import RunContext


class TraceContext:
    """W3C Trace Context propagation.

    Handles traceparent and tracestate headers for
    distributed tracing across services.
    """

    TRACEPARENT_REGEX = re.compile(
        r"^(?P<version>[0-9a-f]{2})-"
        r"(?P<trace_id>[0-9a-f]{32})-"
        r"(?P<parent_id>[0-9a-f]{16})-"
        r"(?P<flags>[0-9a-f]{2})$"
    )

    def __init__(
        self,
        trace_id: str | None = None,
        parent_id: str | None = None,
        trace_flags: int = 1,
        version: int = 0,
    ) -> None:
        """Initialize trace context.

        Args:
            trace_id: Trace ID (hex string).
            parent_id: Parent span ID (hex string).
            trace_flags: Trace flags (1 = sampled).
            version: Trace context version.
        """
        self.trace_id = trace_id or self._generate_trace_id()
        self.parent_id = parent_id or self._generate_span_id()
        self.trace_flags = trace_flags
        self.version = version

    @staticmethod
    def _generate_trace_id() -> str:
        import uuid
        return uuid.uuid4().hex

    @staticmethod
    def _generate_span_id() -> str:
        import uuid
        return uuid.uuid4().hex[:16]

    def to_traceparent(self) -> str:
        return (
            f"{self.version:02x}-"
            f"{self.trace_id}-"
            f"{self.parent_id}-"
            f"{self.trace_flags:02x}"
        )

    @classmethod
    def from_traceparent(cls, header: str) -> Optional["TraceContext"]:
        match = cls.TRACEPARENT_REGEX.match(header)
        if not match:
            return None
        return cls(
            version=int(match.group("version"), 16),
            trace_id=match.group("trace_id"),
            parent_id=match.group("parent_id"),
            trace_flags=int(match.group("flags"), 16),
        )

    def to_headers(self) -> dict[str, str]:
        return {
            "traceparent": self.to_traceparent(),
            "tracestate": f"agenttrace=vendor{self.parent_id}",
        }

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> Optional["TraceContext"]:
        traceparent = headers.get("traceparent") or headers.get("Traceparent")
        if not traceparent:
            return None
        return cls.from_traceparent(traceparent)


class ContextPropagator:
    """Propagates trace context across service boundaries.

    Supports W3C Trace Context and B3 (Zipkin).
    """

    def __init__(self, format: str = "w3c") -> None:
        self.format = format

    def inject(self, trace_context: TraceContext, carrier: dict[str, str]) -> dict[str, str]:
        if self.format == "w3c":
            carrier.update(trace_context.to_headers())
        elif self.format == "b3":
            carrier["X-B3-TraceId"] = trace_context.trace_id
            carrier["X-B3-SpanId"] = trace_context.parent_id
            carrier["X-B3-Sampled"] = "1" if trace_context.trace_flags & 1 else "0"
        return carrier

    def extract(self, carrier: dict[str, str]) -> Optional[TraceContext]:
        if self.format == "w3c":
            return TraceContext.from_headers(carrier)
        elif self.format == "b3":
            trace_id = carrier.get("X-B3-TraceId")
            span_id = carrier.get("X-B3-SpanId")
            sampled = carrier.get("X-B3-Sampled") == "1"
            if trace_id and span_id:
                return TraceContext(
                    trace_id=trace_id,
                    parent_id=span_id,
                    trace_flags=1 if sampled else 0,
                )
        return None


class DistributedTracer:
    """Tracer with distributed tracing support.

    Automatically propagates trace context in HTTP requests
    and extracts context from incoming requests.
    """

    def __init__(self, tracer: Any) -> None:
        self.tracer = tracer
        self.propagator = ContextPropagator("w3c")

    def start_span_with_context(
        self,
        name: str,
        headers: dict[str, str],
        **kwargs: Any,
    ) -> Any:
        """Start span with extracted context from headers.

        Uses the extracted correlation_id (trace_id) and parent span
        from W3C/B3 headers, passing them into span metadata.
        """
        context = self.propagator.extract(headers)

        if context:
            metadata = kwargs.setdefault("metadata", {})
            metadata["correlation_id"] = context.trace_id
            metadata["parent_span_id"] = context.parent_id
            # Also set in RunContext so downstream spans inherit it
            RunContext.set_current_correlation_id(context.trace_id)

        return self.tracer.start_span(name, **kwargs)

    def inject_context(self, headers: dict[str, str]) -> dict[str, str]:
        """Inject current trace context into headers.

        Uses the active span's run_id as trace_id and span id as parent_id.
        """
        current_span = RunContext.get_current_span()
        if current_span:
            # Use run_id as distributed trace id, span.id as parent
            trace_id = RunContext.get_current_correlation_id() or getattr(current_span, "run_id", None)
            span_id = getattr(current_span, "id", None)
            if trace_id and span_id:
                context = TraceContext(trace_id=trace_id, parent_id=span_id)
                return self.propagator.inject(context, headers)
        return headers


async def make_traced_request(
    client: Any,
    method: str,
    url: str,
    tracer: DistributedTracer,
    **kwargs: Any,
) -> Any:
    """Make HTTP request with trace context."""
    headers = kwargs.get("headers", {})
    headers = tracer.inject_context(headers)
    kwargs["headers"] = headers
    return await client.request(method, url, **kwargs)
