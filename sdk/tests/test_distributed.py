"""Tests for distributed tracing support."""

from __future__ import annotations

from agenttrace.distributed import ContextPropagator, DistributedTracer, TraceContext
from agenttrace.tracer import Tracer


class TestTraceContext:
    def test_roundtrip_w3c(self) -> None:
        ctx = TraceContext(trace_id="a" * 32, parent_id="b" * 16)
        header = ctx.to_traceparent()
        parsed = TraceContext.from_traceparent(header)
        assert parsed is not None
        assert parsed.trace_id == ctx.trace_id
        assert parsed.parent_id == ctx.parent_id

    def test_from_headers(self) -> None:
        ctx = TraceContext(trace_id="a" * 32, parent_id="b" * 16)
        headers = ctx.to_headers()
        parsed = TraceContext.from_headers(headers)
        assert parsed is not None
        assert parsed.trace_id == ctx.trace_id

    def test_invalid_header_returns_none(self) -> None:
        assert TraceContext.from_traceparent("invalid") is None


class TestContextPropagator:
    def test_w3c_inject_extract(self) -> None:
        prop = ContextPropagator("w3c")
        ctx = TraceContext(trace_id="a" * 32, parent_id="b" * 16)
        carrier = prop.inject(ctx, {})
        assert "traceparent" in carrier
        parsed = prop.extract(carrier)
        assert parsed is not None
        assert parsed.trace_id == ctx.trace_id

    def test_b3_inject_extract(self) -> None:
        prop = ContextPropagator("b3")
        ctx = TraceContext(trace_id="a" * 32, parent_id="b" * 16)
        carrier = prop.inject(ctx, {})
        assert "X-B3-TraceId" in carrier
        parsed = prop.extract(carrier)
        assert parsed is not None
        assert parsed.trace_id == ctx.trace_id


class TestDistributedTracer:
    def test_inject_context_without_active_run(self) -> None:
        tracer = Tracer()
        dt = DistributedTracer(tracer)
        headers = dt.inject_context({})
        assert headers == {}

    def test_start_span_with_context(self) -> None:
        tracer = Tracer()
        dt = DistributedTracer(tracer)

        with tracer.run("test"):
            span = dt.start_span_with_context(
                "incoming",
                {"traceparent": f"00-{'a' * 32}-{'b' * 16}-01"},
            )
            assert span is not None
            assert span.metadata is not None
            assert span.metadata.get("correlation_id") == "a" * 32

    def test_inject_extract_roundtrip(self) -> None:
        """inject_context must emit a valid traceparent that extract parses.

        run_id/span.id are dashed 36-char UUIDs; they must be normalized to
        32-/16-hex or to_traceparent emits an invalid header and
        from_traceparent returns None (cross-service correlation fails).
        """
        tracer = Tracer()
        dt = DistributedTracer(tracer)

        with tracer.run("test"):
            span = tracer.start_span("work")
            headers = dt.inject_context({})

            traceparent = headers.get("traceparent")
            assert traceparent is not None
            # Header must match the W3C 32-hex/16-hex shape.
            assert TraceContext.TRACEPARENT_REGEX.match(traceparent) is not None

            extracted = dt.propagator.extract(headers)
            assert extracted is not None
            # The injected trace id derives from the active run_id.
            import uuid

            assert extracted.trace_id == uuid.UUID(span.run_id).hex
            assert extracted.parent_id == uuid.UUID(span.id).hex[:16]
