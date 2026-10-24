"""Delivery counters must describe real completion, saturation and permanent errors."""

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from agenttrace.exporters.api_exporter import APIExporter
from agenttrace.exporters.bounded import BoundedExporter
from agenttrace.exporters.otlp import OTLPExporter, _span_to_otlp
from agenttrace.tracer import Tracer

from tests.test_concurrent_lifecycle import Recorder


def test_saturation_deadline_mutation_and_secret_capture():
    gate, entered = threading.Event(), threading.Event()

    class Blocked(Recorder):
        def export_span(self, data):
            entered.set()
            gate.wait(2)
            super().export_span(data)

    target = Blocked()
    exporter = BoundedExporter(target, capacity=1, batch_size=1, capture_content=True)
    payload = {
        "id": "one",
        "input_data": {"api_key": "private", "prompt": "Bearer abcdefghijklmnop"},
        "metadata": {"nested": [1]},
    }
    exporter.export_span(payload)
    assert entered.wait(1)
    payload["metadata"]["nested"].append(2)
    exporter.export_span({"id": "two"})
    exporter.export_span({"id": "three"})
    started = time.monotonic()
    pending = exporter.close(timeout=0.01)
    assert time.monotonic() - started < 0.2
    assert pending["unfinished"] == 2
    assert pending["dropped"] == 1 and not pending["complete"]
    exporter.export_span({"id": "closed"})
    gate.set()
    final = exporter.flush_until(2)
    assert final["delivered"] == 2 and final["dropped"] == 2
    assert target.spans[0]["metadata"]["nested"] == [1]
    assert target.spans[0]["input_data"] == {
        "api_key": "[REDACTED]",
        "prompt": "[REDACTED]",
    }


def test_default_capture_exports_summary_not_raw_content():
    recorder = Recorder()
    tracer = Tracer()
    tracer.set_exporter(recorder)
    with tracer.run("safe"):
        with tracer.span("operation", metadata={"password": "private"}) as span:
            span.input_data = {"prompt": "customer content"}
            span.set_output("generated content")
    exported = recorder.spans[0]
    assert exported["input_data"] is None and exported["output_data"] is None
    assert exported["metadata"]["capture"]["mode"] == "metadata_only"
    assert exported["metadata"]["password"] == "[REDACTED]"
    assert "customer content" not in str(exported)


def test_default_capture_does_not_leak_wrapper_content_via_metadata():
    recorder = Recorder()
    tracer = Tracer()
    tracer.set_exporter(recorder)
    with tracer.run("chain"):
        with tracer.span(
            "chain",
            metadata={
                "inputs": {"question": "private question"},
                "prompts": ["private prompt"],
                "model": "fixture",
            },
        ):
            tracer.add_event("agent_action", {"tool_input": "private tool input"})
    rendered = str(recorder.spans)
    assert "private question" not in rendered
    assert "private prompt" not in rendered
    assert "private tool input" not in rendered
    assert recorder.spans[0]["metadata"]["model"] == "fixture"


@pytest.mark.parametrize(
    "http_status,attempts", [(422, 1), (401, 1), (503, 2), (429, 2), (201, 1)]
)
def test_http_delivery_counts_retries_and_permanent_failures(http_status, attempts):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(http_status)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        api = APIExporter(endpoint=f"http://127.0.0.1:{server.server_port}/api/traces")
        exporter = BoundedExporter(api)
        exporter.export_span({"id": "test", "run_id": "root"})
        result = exporter.close(3)
        assert len(calls) == attempts
        assert result["retries"] == attempts - 1
        assert result["delivered"] == (1 if http_status == 201 else 0)
        assert result["failed"] == (0 if http_status == 201 else 1)
        assert result["complete"] is (http_status == 201)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(1)


def test_oversized_event_drops_and_custom_failure_is_not_delivered():
    exporter = BoundedExporter(Recorder(), max_event_bytes=8)
    exporter.export_run({"id": "large event"})
    assert exporter.close(1)["dropped"] == 1

    class Broken(Recorder):
        def flush(self):
            raise OSError("storage offline")

    exporter = BoundedExporter(Broken())
    exporter.export_run({"id": "root"})
    result = exporter.close(1)
    assert result["failed"] == 1 and result["delivered"] == 0


def test_genai_subset_retains_legacy_attributes():
    span = _span_to_otlp(
        {
            "span_type": "llm_call",
            "metadata": {"provider": "synthetic", "model": "fixture"},
            "token_usage": {
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            },
        },
        "example",
    )
    attrs = {
        item["key"]: next(iter(item["value"].values())) for item in span["attributes"]
    }
    assert attrs["gen_ai.operation.name"] == "chat"
    assert attrs["gen_ai.provider.name"] == "synthetic"
    assert attrs["gen_ai.request.model"] == attrs["gen_ai.response.model"] == "fixture"
    assert attrs["gen_ai.usage.input_tokens"] == "12"
    assert attrs["gen_ai.usage.output_tokens"] == "3"
    assert attrs["tokens.total"] == "15" and attrs["span.type"] == "llm_call"


def test_otlp_wire_keeps_nested_attribute_schema():
    import json

    payloads = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payloads.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        exporter = OTLPExporter(
            endpoint=f"http://127.0.0.1:{server.server_port}/v1/traces"
        )
        exporter.export_span(
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "run_id": "22222222-2222-2222-2222-222222222222",
                "name": "chat",
                "span_type": "llm_call",
                "metadata": {"provider": "synthetic", "model": "fixture"},
            }
        )
        exporter.flush()
        attrs = payloads[0]["resourceSpans"][0]["scopeSpans"][0]["spans"][0][
            "attributes"
        ]
        assert {item["key"]: item["value"] for item in attrs}[
            "gen_ai.provider.name"
        ] == {"stringValue": "synthetic"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(1)


@pytest.mark.parametrize("terminal", ["completed", "cancelled"])
def test_otlp_exports_root_once_when_terminal_with_run_metadata(terminal):
    import json

    from agenttrace.span import SpanType
    from agenttrace.tracer import RunStatus

    payloads = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payloads.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        exporter = OTLPExporter(
            endpoint=f"http://127.0.0.1:{server.server_port}/v1/traces"
        )
        tracer = Tracer()
        tracer.set_exporter(exporter)
        tracer.start_run(
            "root",
            metadata={"cohort_id": "fixture-cohort"},
            correlation_id="fixture-correlation",
        )
        with tracer.span(
            "answer",
            SpanType.LLM_CALL,
            metadata={"provider": "synthetic", "model": "fixture"},
        ) as span:
            span.token_usage = {
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            }
        tracer.end_run(RunStatus(terminal))
        tracer.flush()
        spans = payloads[0]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 2
        assert len({span["spanId"] for span in spans}) == 2
        root = next(span for span in spans if span["name"] == "run:root")
        attrs = {
            item["key"]: next(iter(item["value"].values()))
            for item in root["attributes"]
        }
        assert attrs["run.status"] == terminal
        assert attrs["run.span_count"] == "1"
        assert attrs["run.correlation_id"] == "fixture-correlation"
        assert json.loads(attrs["agenttrace.metadata"])["cohort_id"] == "fixture-cohort"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(1)
