"""Tests for the Span dataclass."""

from __future__ import annotations

from agenttrace.span import Span, SpanStatus, SpanType


class TestSpanCreation:
    """Tests for span initialization."""

    def test_default_span(self) -> None:
        span = Span()
        assert span.name == ""
        assert span.span_type == SpanType.CUSTOM
        assert span.status == SpanStatus.STARTED
        assert span.id is not None
        assert span.start_time is not None
        assert span.end_time is None
        assert span.duration_ms is None

    def test_span_with_params(self) -> None:
        span = Span(
            name="test_span",
            span_type=SpanType.LLM_CALL,
            run_id="run-123",
            metadata={"model": "gpt-4"},
        )
        assert span.name == "test_span"
        assert span.span_type == SpanType.LLM_CALL
        assert span.run_id == "run-123"
        assert span.metadata == {"model": "gpt-4"}


class TestSpanLifecycle:
    """Tests for span end and error transitions."""

    def test_end_sets_completed(self) -> None:
        span = Span(name="test")
        span.end(output="result")
        assert span.status == SpanStatus.COMPLETED
        assert span.output_data == "result"
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms >= 0

    def test_set_error(self) -> None:
        span = Span(name="test")
        span.set_error("something broke")
        assert span.status == SpanStatus.ERROR
        assert span.error == "something broke"
        assert span.end_time is not None
        assert span.duration_ms is not None

    def test_set_output_without_ending(self) -> None:
        span = Span(name="test")
        span.set_output("partial")
        assert span.output_data == "partial"
        assert span.status == SpanStatus.STARTED


class TestSpanSerialization:
    """Tests for span to_dict conversion."""

    def test_to_dict(self) -> None:
        span = Span(
            name="test",
            span_type=SpanType.TOOL_CALL,
            run_id="run-123",
        )
        span.end(output="done")

        d = span.to_dict()
        assert d["name"] == "test"
        assert d["span_type"] == "tool_call"
        assert d["status"] == "completed"
        assert d["run_id"] == "run-123"
        assert d["output_data"] == "done"
        assert d["start_time"] is not None
        assert d["end_time"] is not None
        assert d["duration_ms"] is not None

    def test_to_dict_with_optional_fields(self) -> None:
        span = Span(
            name="test",
            cost_usd=0.005,
            token_usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        )
        d = span.to_dict()
        assert d["cost_usd"] == 0.005
        assert d["token_usage"]["total_tokens"] == 150
