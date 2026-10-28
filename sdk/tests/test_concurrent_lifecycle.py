"""Shared tracers must isolate roots while retaining intentional child ownership."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

import pytest
from agenttrace.context import RunContext
from agenttrace.exporters.base import BaseExporter
from agenttrace.tracer import Tracer


class Recorder(BaseExporter):
    def __init__(self):
        self.runs = []
        self.spans = []

    def export_run(self, data):
        self.runs.append(data)

    def export_span(self, data):
        self.spans.append(data)

    def flush(self):
        pass


@pytest.mark.parametrize("count", [2, 20])
def test_overlapping_requests_use_one_tracer_without_crossing_roots(count):
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)

    async def request(index):
        with tracer.run(str(index)) as run:
            with tracer.span("request") as span:
                await asyncio.sleep(0)
                assert RunContext.get_current_run_id() == run.id
                assert span.run_id == run.id
        return run.id

    async def main():
        return await asyncio.gather(*(request(i) for i in range(count)))

    assert len(set(asyncio.run(main()))) == count
    assert len(recorder.spans) == count
    assert all(r["span_count"] == 1 for r in recorder.runs if r["end_time"])


def test_children_and_propagated_threads_share_root_not_sibling_stack():
    tracer = Tracer()

    async def child():
        with tracer.span("child") as span:
            await asyncio.sleep(0)
        return span

    async def main():
        with tracer.run("root") as run:
            with tracer.span("parent") as parent:
                children = await asyncio.gather(child(), child())
                with ThreadPoolExecutor(1) as pool:
                    thread_span = pool.submit(
                        copy_context().run, lambda: child_sync(tracer)
                    ).result()
                assert {s.parent_span_id for s in [*children, thread_span]} == {
                    parent.id
                }
        assert len(run.spans) == 4

    asyncio.run(main())


def child_sync(tracer):
    with tracer.span("thread") as span:
        return span


def test_separate_tracer_restores_enclosing_context_and_export_errors_are_nonfatal():
    class Broken(Recorder):
        def export_run(self, data):
            raise ValueError("telemetry unavailable")

        def export_span(self, data):
            raise ValueError("telemetry unavailable")

    outer, inner = Tracer(), Tracer()
    inner.set_exporter(Broken())
    with outer.run("outer") as root:
        with outer.span("parent") as parent:
            with inner.run("inner"):
                with inner.span("inner-stage"):
                    pass
            assert RunContext.get_current_run_id() == root.id
            assert RunContext.get_current_span() is parent


def test_cancelled_root_and_unfinished_child_are_terminal():
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)

    async def main():
        with pytest.raises(asyncio.CancelledError):
            with tracer.run("cancel"):
                tracer.start_span("unfinished")
                raise asyncio.CancelledError()

    asyncio.run(main())
    assert recorder.runs[-1]["status"] == "cancelled"
    assert recorder.spans[-1]["status"] == "cancelled"


def test_child_cannot_add_span_after_root_has_closed():
    tracer = Tracer()

    async def main():
        gate = asyncio.Event()

        async def child():
            await gate.wait()
            with pytest.raises(RuntimeError, match="closed"):
                tracer.start_span("late")

        with tracer.run("root"):
            task = asyncio.create_task(child())
        gate.set()
        await task

    asyncio.run(main())


def test_child_cannot_close_parent_root_or_leave_it_unusable():
    tracer = Tracer()

    async def child():
        with pytest.raises(RuntimeError, match="originating"):
            tracer.end_run()

    async def main():
        with tracer.run("root") as root:
            await asyncio.create_task(child())
            with tracer.span("still-usable"):
                pass
        assert root.status.value == "completed"

    asyncio.run(main())


@pytest.mark.parametrize("propagation", ["task", "thread"])
def test_inherited_context_cannot_end_another_contexts_span(propagation):
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)

    def attempt(parent):
        with pytest.raises(RuntimeError, match="originating context"):
            tracer.end_span(parent)
        with tracer.span("owned-child") as child:
            assert child.parent_span_id == parent.id

    async def main():
        with tracer.run("root"):
            with tracer.span("parent") as parent:
                if propagation == "task":

                    async def child():
                        attempt(parent)

                    await asyncio.create_task(child())
                else:
                    with ThreadPoolExecutor(1) as pool:
                        await asyncio.wrap_future(
                            pool.submit(copy_context().run, attempt, parent)
                        )
                assert parent.status.value == "started"
                assert [span["name"] for span in recorder.spans] == ["owned-child"]
        assert [span["name"] for span in recorder.spans] == ["owned-child", "parent"]
        assert len({span["id"] for span in recorder.spans}) == 2

    asyncio.run(main())


def test_inherited_context_manager_exit_cannot_mutate_parent_span():
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)

    async def main():
        with tracer.run("root"):
            context = tracer.span("parent")
            with context as parent:
                before = parent.to_dict()

                async def child():
                    with pytest.raises(RuntimeError, match="originating context"):
                        context.__exit__(
                            ValueError, ValueError("foreign failure"), None
                        )

                await asyncio.create_task(child())
                assert parent.to_dict() == before
        assert recorder.spans[0]["status"] == "completed"
        assert len(recorder.spans) == 1

    asyncio.run(main())


def test_sampling_is_isolated_across_overlapping_roots():
    recorder = Recorder()
    tracer = Tracer()
    tracer.set_exporter(recorder)
    tracer._is_sampled = lambda run_id: run_id.endswith("keep")
    from unittest.mock import patch

    async def request():
        with tracer.run("sample"):
            with tracer.span("stage"):
                await asyncio.sleep(0)

    async def main():
        with patch(
            "agenttrace.tracer.uuid.uuid4",
            side_effect=["root-keep", "span-one", "root-drop", "span-two"],
        ):
            await asyncio.gather(request(), request())

    asyncio.run(main())
    assert [span["run_id"] for span in recorder.spans] == ["root-keep"]
    assert len(recorder.runs) == 2


def test_error_callback_followed_by_finalization_retains_error():
    from agenttrace.instrumentation.langchain import AgentTraceCallbackHandler

    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)
    handler = AgentTraceCallbackHandler(tracer)
    with tracer.run("chain"):
        handler.on_chain_start({"name": "failed"}, {}, run_id="chain-id")
        handler.on_chain_error(ValueError("upstream failure"), run_id="chain-id")
    assert recorder.spans[0]["status"] == "error"


def test_cancelled_async_provider_span_is_not_marked_completed(monkeypatch):
    from types import SimpleNamespace

    from agenttrace.instrumentation.openai import OpenAIInstrumentor

    class Sync:
        def create(self, **kwargs):
            return None

    class Async:
        async def create(self, **kwargs):
            raise asyncio.CancelledError()

    fake = SimpleNamespace(
        resources=SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(Completions=Sync, AsyncCompletions=Async)
            )
        )
    )
    monkeypatch.setitem(__import__("sys").modules, "openai", fake)
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)
    instrumentor = OpenAIInstrumentor(tracer)
    instrumentor.instrument()

    async def main():
        with pytest.raises(asyncio.CancelledError):
            with tracer.run("provider-cancel"):
                await Async().create(model="fixture", messages=[])

    try:
        asyncio.run(main())
        tracer.flush()
    finally:
        instrumentor.uninstrument()
        tracer.close()
    assert recorder.spans[0]["status"] == "cancelled"


def test_sampling_decision_is_frozen_for_root_lifetime():
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)
    with tracer.run("selected"):
        tracer._sample_rate = 0.0
        with tracer.span("selected-stage"):
            pass
    with tracer.run("not-selected"):
        pass
    assert len(recorder.runs) == 2
    assert len(recorder.spans) == 1


@pytest.mark.parametrize("fails", [False, True])
def test_started_child_context_cleanup_after_root_close_preserves_application(fails):
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)

    async def main():
        entered, release = asyncio.Event(), asyncio.Event()
        child_contexts = []

        async def child():
            try:
                with tracer.span("background"):
                    entered.set()
                    await release.wait()
                    if fails:
                        raise ValueError("original application failure")
            finally:
                child_contexts.append(RunContext.get_current_span())
            return "application result"

        with tracer.run("root") as root:
            task = asyncio.create_task(child())
            await entered.wait()
        finalized = root.spans[0].to_dict()
        release.set()
        if fails:
            with pytest.raises(ValueError, match="original application failure"):
                await task
        else:
            assert await task == "application result"
        assert root.spans[0].to_dict() == finalized
        assert len(recorder.spans) == 1
        assert child_contexts == [None]
        with pytest.raises(RuntimeError):
            tracer.end_span(root.spans[0])

    asyncio.run(main())
