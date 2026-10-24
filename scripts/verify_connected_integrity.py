"""Real HTTP retries, durable late delivery and SDK OTLP interoperability.

Run only against a disposable, credential-free loopback collector.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from agenttrace import Tracer
from agenttrace.exporters.otlp import OTLPExporter
from agenttrace.span import SpanType

from verify_connected_portfolio import request


def first_event(endpoint: str, cohort: str, cursor: int) -> dict:
    with urlopen(
        f"{endpoint}/api/stream/traces?cohort_id={cohort}&cursor={cursor}", timeout=10
    ) as response:
        for raw in response:
            if raw.startswith(b"data: "):
                return json.loads(raw[6:])
    raise AssertionError("Stream ended before a stored event was delivered")


def verify(endpoint: str) -> dict:
    cohort, run_id, span_id = (str(uuid.uuid4()) for _ in range(3))
    now = datetime.now(timezone.utc).isoformat()
    root = {
        "id": run_id,
        "name": "HTTP integrity probe",
        "start_time": now,
        "status": "running",
        "metadata": {"cohort_id": cohort},
    }
    with ThreadPoolExecutor(max_workers=20) as pool:
        statuses = list(
            pool.map(lambda _: request(endpoint, "/api/runs", root)[0], range(20))
        )
    assert statuses == [201] * 20, statuses
    span = {
        "run_id": run_id,
        "span_id": span_id,
        "span_type": "tool_call",
        "name": "delivery-probe",
        "start_time": now,
        "end_time": now,
        "status": "completed",
        "cost_usd": 0.01,
        "token_usage": {"total_tokens": 10},
        "metadata": {"cohort_id": cohort},
        "input_data": {"api_key": "synthetic-sensitive-value"},
    }
    status, first = request(endpoint, "/api/traces", span)
    assert status == 201 and first["input_data"]["api_key"] == "[REDACTED]", first
    _, before = request(endpoint, f"/api/stats?cohort_id={cohort}")
    for _ in range(3):
        status, duplicate = request(endpoint, "/api/traces", span)
        assert status == 201 and duplicate["id"] == first["id"], duplicate
    _, after = request(endpoint, f"/api/stats?cohort_id={cohort}")
    assert after == before, (before, after)
    status, conflict = request(
        endpoint, "/api/traces", {**span, "name": "conflicting-content"}
    )
    assert status == 409, conflict
    first_delivery = first_event(endpoint, cohort, 0)
    assert first_delivery["span_id"] == span_id
    # A new arrival whose application timestamp predates the resume cursor.
    late_id = str(uuid.uuid4())
    late = {
        **span,
        "span_id": late_id,
        "name": "late-arrival",
        "start_time": "2000-01-01T00:00:00+00:00",
        "end_time": "2000-01-01T00:00:00+00:00",
    }
    assert request(endpoint, "/api/traces", late)[0] == 201
    late_delivery = first_event(endpoint, cohort, first_delivery["delivery_cursor"])
    assert late_delivery["span_id"] == late_id
    assert late_delivery["delivery_cursor"] > first_delivery["delivery_cursor"]
    request(endpoint, "/api/runs", {**root, "status": "completed", "end_time": now})
    request(endpoint, "/api/runs", root)
    _, terminal = request(endpoint, f"/api/runs/{run_id}")
    assert terminal["status"] == "completed" and terminal["span_count"] == 2, terminal
    assert terminal["total_tokens"] == 20 and abs(terminal["total_cost"] - 0.02) < 1e-10

    sink = OTLPExporter(endpoint=f"{endpoint}/api/otlp/v1/traces")
    tracer = Tracer()
    tracer.set_exporter(sink)
    try:
        with tracer.run(
            "SDK JSON interoperability", metadata={"provider_origin": "synthetic"}
        ) as run:
            with tracer.span(
                "chat",
                SpanType.LLM_CALL,
                metadata={
                    "operation": "chat",
                    "provider": "synthetic",
                    "model": "fixture-v1",
                    "response_model": "fixture-v1",
                },
            ) as operation:
                operation.token_usage = {
                    "prompt_tokens": 7,
                    "completion_tokens": 3,
                    "total_tokens": 10,
                }
                raise asyncio.CancelledError("Synthetic caller cancellation")
    except asyncio.CancelledError:
        pass
    tracer.flush()
    assert sink.delivery_stats()["failed"] == 0, sink.delivery_stats()
    _, stored = request(endpoint, f"/api/runs/{run.id.replace('-', '')}/spans")
    mapped = next(row for row in stored if row["name"] == "chat")
    assert mapped["provider"] == "synthetic" and mapped["model"] == "fixture-v1", mapped
    assert mapped["token_usage"] == {
        "prompt_tokens": 7,
        "completion_tokens": 3,
        "total_tokens": 10,
    }
    assert mapped["status"] == "cancelled", mapped
    assert mapped["metadata"]["gen_ai.operation.name"] == "chat", mapped
    _, otlp_run = request(endpoint, f"/api/runs/{run.id.replace('-', '')}")
    assert otlp_run["status"] == "cancelled", otlp_run
    return {
        "cohort_id": cohort,
        "concurrent_root_statuses": statuses,
        "identical_retries": 3,
        "conflict_status": status,
        "first_delivery": first_delivery,
        "late_delivery": late_delivery,
        "terminal": terminal,
        "otlp_delivery": sink.delivery_stats(),
        "otlp_run": otlp_run,
        "otlp_spans": stored,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8300")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/portfolio/connected/integrity.json"),
    )
    args = parser.parse_args()
    report = verify(args.endpoint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "Actual HTTP idempotency/root race/terminal aggregates/late SSE/SDK OTLP passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
