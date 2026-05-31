"""AgentTrace FastAPI backend for trace ingestion and retrieval."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

app = FastAPI(title="AgentTrace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

trace_store: list[dict] = []


class SpanIngest(BaseModel):
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start_time: float
    end_time: float | None
    duration_ms: float | None
    tags: dict[str, Any]
    events: list[dict]


@app.post("/api/traces")
async def ingest_trace(spans: list[SpanIngest]):
    for span in spans:
        trace_store.append(span.model_dump())
    return {"ingested": len(spans)}


@app.get("/api/traces")
async def list_traces(trace_id: str | None = None):
    traces = trace_store
    if trace_id:
        traces = [t for t in traces if t["trace_id"] == trace_id]
    return {"traces": traces[-100:]}


@app.get("/api/traces/{trace_id}/diff")
async def diff_trace(trace_id: str, against: str):
    current = [t for t in trace_store if t["trace_id"] == trace_id]
    baseline = [t for t in trace_store if t["trace_id"] == against]
    return {
        "current": current,
        "baseline": baseline,
        "diff": {
            "span_count_delta": len(current) - len(baseline),
            "duration_delta": sum(s["duration_ms"] or 0 for s in current) - sum(s["duration_ms"] or 0 for s in baseline),
        },
    }


@app.get("/metrics")
async def prometheus_metrics():
    total_spans = len(trace_store)
    avg_duration = sum(s["duration_ms"] or 0 for s in trace_store) / max(total_spans, 1)
    lines = [
        f"# HELP agenttrace_spans_total Total ingested spans",
        f"# TYPE agenttrace_spans_total counter",
        f"agenttrace_spans_total {total_spans}",
        f"# HELP agenttrace_span_duration_ms Average span duration",
        f"# TYPE agenttrace_span_duration_ms gauge",
        f"agenttrace_span_duration_ms {avg_duration:.2f}",
    ]
    return "\n".join(lines)
