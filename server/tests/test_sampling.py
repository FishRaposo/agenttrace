"""Deterministic trace sampling contract tests."""

from app.internal.sampling import SamplingPolicy, TailSamplingBuffer


def test_sampling_off_keeps_every_trace() -> None:
    policy = SamplingPolicy(mode="off", rate=0.0)

    decision = policy.decide(trace_id="trace-1", status="completed", duration_ms=1.0)

    assert decision.sampled is True
    assert decision.reason == "disabled"


def test_head_sampling_is_stable_for_the_same_trace_id() -> None:
    policy = SamplingPolicy(mode="head", rate=0.5)

    first = policy.decide(trace_id="trace-stable", status="completed", duration_ms=1.0)
    second = policy.decide(trace_id="trace-stable", status="completed", duration_ms=1.0)

    assert first == second
    assert first.reason == "head_rate"


def test_sampling_key_is_documented_as_trace_level() -> None:
    policy = SamplingPolicy(mode="head", rate=0.5)

    first_span = policy.decide(trace_id="run-stable", status="started")
    second_span = policy.decide(trace_id="run-stable", status="completed")

    assert first_span.sampled == second_span.sampled


def test_tail_sampling_keeps_errors_and_slow_spans() -> None:
    policy = SamplingPolicy(
        mode="tail", rate=0.0, keep_errors=True, slow_threshold_ms=100.0
    )

    error = policy.decide(trace_id="trace-error", status="error", duration_ms=1.0)
    slow = policy.decide(trace_id="trace-slow", status="completed", duration_ms=101.0)

    assert error.sampled is True
    assert error.reason == "tail_error"
    assert slow.sampled is True
    assert slow.reason == "tail_slow"


def test_tail_buffer_flushes_a_complete_run_with_one_decision() -> None:
    buffer = TailSamplingBuffer(SamplingPolicy(mode="tail", rate=0.0))

    assert buffer.add("run-1", "first", status="started") is None
    assert buffer.pending_runs == ("run-1",)
    flushed = buffer.add("run-1", "terminal", status="error", terminal=True)

    assert flushed is not None
    assert [item for item, _ in flushed] == ["first", "terminal"]
    assert all(decision.sampled for _, decision in flushed)
    assert all(decision.reason == "tail_error" for _, decision in flushed)
    assert buffer.pending_runs == ()


def test_tail_buffer_timeout_discards_incomplete_runs_by_default() -> None:
    buffer = TailSamplingBuffer(SamplingPolicy(mode="tail", rate=1.0))
    assert buffer.add("run-2", "first", status="started") is None

    flushed = buffer.flush("run-2")

    assert len(flushed) == 1
    assert flushed[0][0] == "first"
    assert flushed[0][1].sampled is False
    assert flushed[0][1].reason == "tail_timeout_discard"
