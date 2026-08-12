"""Deterministic prompt-version cost aggregation and daily reporting."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import Any, Iterable

from shared_core.llmmetrics import LLMMetrics

from app.models.trace import Trace


CSV_FIELDS = [
    "day",
    "total_requests",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "estimated_cost",
    "average_latency_ms",
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "error_rate",
]


def prompt_version(trace: Trace) -> str:
    """Return a trace's prompt version, normalizing missing tags."""
    metadata = trace.trace_metadata or {}
    value = metadata.get("prompt_version")
    return str(value) if value not in (None, "") else "unversioned"


def filter_prompt_version(
    traces: Iterable[Trace], version: str | None
) -> list[Trace]:
    """Filter LLM traces by exact prompt version when a version is supplied."""
    rows = list(traces)
    if version is None:
        return rows
    return [
        trace
        for trace in rows
        if trace.span_type == "llm_call" and prompt_version(trace) == version
    ]


def prompt_version_costs(traces: Iterable[Trace]) -> dict[str, float]:
    """Aggregate LLM-call cost by prompt version with stable key ordering."""
    costs: dict[str, float] = defaultdict(float)
    for trace in traces:
        if trace.span_type == "llm_call":
            costs[prompt_version(trace)] += trace.cost_usd or 0.0
    return {key: round(costs[key], 6) for key in sorted(costs)}


def _record(metrics: LLMMetrics, trace: Trace) -> None:
    usage = trace.token_usage or {}
    metrics.record(
        model=trace.model or "unknown",
        prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
        completion_tokens=int(usage.get("completion_tokens", 0) or 0),
        latency_ms=float(trace.duration_ms or 0.0),
        prompt_version=prompt_version(trace),
        error=trace.error if trace.error else None,
        cost_usd=trace.cost_usd or 0.0,
    )


def _stable_summary(metrics: LLMMetrics) -> dict[str, Any]:
    summary = metrics.summary()
    for field in ("cost_by_model", "cost_by_prompt_version"):
        values = summary[field]
        summary[field] = {key: values[key] for key in sorted(values)}
    return summary


def build_daily_report(
    traces: Iterable[Trace],
    *,
    day: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic UTC daily report from stored LLM traces."""
    filtered = filter_prompt_version(traces, version)
    llm_traces = [trace for trace in filtered if trace.span_type == "llm_call"]

    buckets: dict[str, list[Trace]] = defaultdict(list)
    for trace in llm_traces:
        key = trace.start_time.strftime("%Y-%m-%d")
        if day is None or key == day:
            buckets[key].append(trace)

    days: dict[str, Any] = {}
    for key in sorted(buckets):
        metrics = LLMMetrics()
        for trace in sorted(buckets[key], key=lambda item: (item.start_time, item.id)):
            _record(metrics, trace)
        days[key] = _stable_summary(metrics)

    report: dict[str, Any] = {"days": days}
    if day is not None:
        report["day"] = day
    else:
        totals = LLMMetrics()
        for trace in sorted(llm_traces, key=lambda item: (item.start_time, item.id)):
            _record(totals, trace)
        report["totals"] = _stable_summary(totals)
    if version is not None:
        report["prompt_version"] = version
    return report


def report_to_csv(report: dict[str, Any]) -> str:
    """Render a daily report as deterministic RFC-compatible CSV text."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for day, summary in sorted(report.get("days", {}).items()):
        row = {"day": day}
        row.update({field: summary.get(field, 0) for field in CSV_FIELDS[1:]})
        writer.writerow(row)
    return output.getvalue()
