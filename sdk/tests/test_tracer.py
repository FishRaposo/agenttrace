"""Tests for the Tracer class."""

from __future__ import annotations

import pytest
from agenttrace.span import SpanStatus, SpanType
from agenttrace.tracer import RunStatus, Tracer


class TestTracerRunLifecycle:
    """Tests for starting and ending runs."""

    def test_start_run_returns_context(self, tracer: Tracer) -> None:
        ctx = tracer.start_run("test_run")
        assert ctx is not None

    def test_start_run_sets_current_run_id(self, tracer: Tracer) -> None:
        tracer.start_run("test_run")
        from agenttrace.context import RunContext

        assert RunContext.get_current_run_id() is not None

    def test_end_run_clears_context(self, tracer: Tracer) -> None:
        tracer.start_run("test_run")
        tracer.end_run(RunStatus.COMPLETED)
        from agenttrace.context import RunContext

        assert RunContext.get_current_run_id() is None

    def test_cannot_start_two_runs(self, tracer: Tracer) -> None:
        tracer.start_run("first")
        with pytest.raises(RuntimeError, match="already in progress"):
            tracer.start_run("second")
        tracer.end_run()

    def test_cannot_end_without_run(self, tracer: Tracer) -> None:
        with pytest.raises(RuntimeError, match="No active run"):
            tracer.end_run()

    def test_run_context_manager(self, tracer: Tracer) -> None:
        with tracer.run("ctx_run") as run:
            assert run.name == "ctx_run"
        from agenttrace.context import RunContext

        assert RunContext.get_current_run_id() is None

    def test_run_context_manager_on_exception(self, tracer: Tracer) -> None:
        try:
            with tracer.run("failing_run") as _run:
                raise ValueError("boom")
        except ValueError:
            pass
        from agenttrace.context import RunContext

        assert RunContext.get_current_run_id() is None


class TestTracerSpanLifecycle:
    """Tests for starting and ending spans."""

    def test_start_span_without_run_raises(self, tracer: Tracer) -> None:
        with pytest.raises(RuntimeError, match="No active run"):
            tracer.start_span("test")

    def test_start_span_within_run(self, tracer: Tracer) -> None:
        tracer.start_run("test_run")
        span = tracer.start_span("my_span", SpanType.LLM_CALL)
        assert span.name == "my_span"
        assert span.span_type == SpanType.LLM_CALL
        assert span.status == SpanStatus.STARTED
        tracer.end_run()

    def test_end_span_completes(self, tracer: Tracer) -> None:
        tracer.start_run("test_run")
        span = tracer.start_span("my_span")
        span.end(output="done")
        tracer.end_span(span)
        assert span.status == SpanStatus.COMPLETED
        assert span.output_data == "done"
        tracer.end_run()

    def test_nested_spans(self, tracer: Tracer) -> None:
        tracer.start_run("test_run")
        outer = tracer.start_span("outer")
        inner = tracer.start_span("inner")
        assert inner.parent_span_id == outer.id
        inner.end(output="inner_done")
        tracer.end_span(inner)
        outer.end(output="outer_done")
        tracer.end_span(outer)
        tracer.end_run()

    def test_span_context_manager(self, tracer: Tracer) -> None:
        with tracer.run("test_run"):
            with tracer.span("my_span", SpanType.TOOL_CALL) as span:
                span.set_output("result")
            assert span.status == SpanStatus.COMPLETED

    def test_span_mismatch_raises(self, tracer: Tracer) -> None:
        tracer.start_run("test_run")
        span1 = tracer.start_span("first")
        _span2 = tracer.start_span("second")
        with pytest.raises(RuntimeError, match="Span mismatch"):
            tracer.end_span(span1)
        tracer.end_run()


class TestTracerWithExporter:
    """Tests for tracer-exporter integration."""

    def test_run_exports_to_jsonl(
        self, tracer_with_jsonl: Tracer, jsonl_path: str
    ) -> None:
        tracer_with_jsonl.start_run("exported_run")
        tracer_with_jsonl.end_run()
        tracer_with_jsonl.flush()

        import json

        with open(jsonl_path, "r") as f:
            lines = f.readlines()
        assert len(lines) >= 1
        data = json.loads(lines[0])
        assert data["type"] == "run"

    def test_span_exports_to_jsonl(
        self, tracer_with_jsonl: Tracer, jsonl_path: str
    ) -> None:
        tracer_with_jsonl.start_run("exported_run")
        span = tracer_with_jsonl.start_span("my_span")
        span.end(output="result")
        tracer_with_jsonl.end_span(span)
        tracer_with_jsonl.end_run()
        tracer_with_jsonl.flush()

        import json

        with open(jsonl_path, "r") as f:
            lines = f.readlines()
        span_lines = [
            json.loads(ln) for ln in lines if json.loads(ln)["type"] == "span"
        ]
        assert len(span_lines) >= 1
