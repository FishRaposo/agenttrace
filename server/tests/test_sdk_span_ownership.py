"""SDK ownership produces one immutable delivery per span at the real collector."""

import asyncio

import pytest

tracing = pytest.importorskip("agenttrace.tracer")
exporters = pytest.importorskip("agenttrace.exporters.base")


class Recorder(exporters.BaseExporter):
    def __init__(self):
        self.runs = []
        self.spans = []

    def export_run(self, data):
        self.runs.append(data)

    def export_span(self, data):
        self.spans.append(data)

    def flush(self):
        pass


@pytest.mark.asyncio
async def test_inherited_parent_cannot_create_conflicting_duplicate_delivery(client):
    tracer, recorder = tracing.Tracer(), Recorder()
    tracer.set_exporter(recorder)

    with tracer.run("ownership-boundary"):
        with tracer.span("parent") as parent:

            async def child():
                with pytest.raises(RuntimeError, match="originating context"):
                    tracer.end_span(parent)
                with tracer.span("child"):
                    await asyncio.sleep(0)

            await asyncio.create_task(child())

    terminal = recorder.runs[-1]
    assert len(recorder.spans) == len({span["id"] for span in recorder.spans}) == 2
    assert (await client.post("/api/runs", json=terminal)).status_code == 201
    for span in recorder.spans:
        payload = {**span, "span_id": span["id"]}
        assert (await client.post("/api/traces", json=payload)).status_code == 201
        assert (await client.post("/api/traces", json=payload)).status_code == 201
        conflicting = {**payload, "name": "altered-event"}
        assert (await client.post("/api/traces", json=conflicting)).status_code == 409
    saved = (await client.get(f"/api/runs/{terminal['id']}")).json()
    assert saved["span_count"] == 2
    assert saved["total_cost"] == 0
    assert saved["total_tokens"] == 0
