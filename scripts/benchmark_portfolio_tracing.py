"""Measure this host's synthetic workload; no production-scale claim.

Uses20warmup and100measured requests,3repeats per condition and concurrency.
The HTTP condition requires a dedicated collector with documented rate limits.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from agenttrace.exporters.base import BaseExporter
from agenttrace.portfolio import PRICING_REVISION, SCENARIO_REVISION, run_workload


class LocalExporter(BaseExporter):
    """Real local serialization without filesystem/network timing noise."""

    def __init__(self) -> None:
        self.events = 0

    def export_run(self, run: dict) -> None:
        json.dumps(run)
        self.events += 1

    def export_span(self, span: dict) -> None:
        json.dumps(span)
        self.events += 1

    def flush(self) -> None:
        pass


async def measure(condition: str, concurrency: int, endpoint: str, repeat: int) -> dict:
    observations = []
    deliveries = []
    started = time.perf_counter()
    # One full cohort warms caches/workers; exclude its observations and time.
    for batch in range(6):
        if batch == 1:
            started = time.perf_counter()
        kwargs = {"concurrency": concurrency, "tracing": condition != "disabled"}
        if condition == "http":
            kwargs["endpoint"] = endpoint
        else:
            kwargs["exporter"] = LocalExporter()
        result = await run_workload("incident", **kwargs)
        if batch:
            observations.extend(result["request_observations"])
            deliveries.append(result["delivery"])
    elapsed = time.perf_counter() - started
    durations = sorted(float(row["duration_ms"]) for row in observations)
    outcomes = {
        key: sum(row["outcome"] == key for row in observations)
        for key in ("completed", "failed", "cancelled")
    }
    return {
        "condition": condition,
        "concurrency": concurrency,
        "repeat": repeat,
        "warmup_requests": 20,
        "measured_requests": len(observations),
        "elapsed_seconds": elapsed,
        "throughput_requests_per_second": len(observations) / elapsed,
        "p50_ms": statistics.median(durations),
        "p95_ms": durations[94],
        "application_outcomes": outcomes,
        "deliveries": deliveries,
        "request_observations": observations,
    }


async def benchmark(args: argparse.Namespace) -> dict:
    results = []
    for repeat in range(1, 4):
        for concurrency in (1, 20):
            for condition in ("disabled", "local", "http"):
                result = await measure(condition, concurrency, args.endpoint, repeat)
                results.append(result)
                print(
                    f"{condition} c={concurrency} repeat={repeat}: "
                    f"p95={result['p95_ms']:.3f}ms n={result['measured_requests']}",
                    flush=True,
                )
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "scenario_revision": SCENARIO_REVISION,
        "pricing_revision": PRICING_REVISION,
        "provenance": "real host timing; synthetic application/provider/token/pricing values",
        "queue": {
            "capacity": 256,
            "event_bytes": 65536,
            "batch_size": 16,
            "http_timeout_seconds": 2,
            "attempts": 2,
            "policy": "drop_newest",
        },
        "collector": {
            "endpoint": args.endpoint,
            "rate_limit_per_minute": args.collector_rate_limit,
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8300")
    parser.add_argument(
        "--collector-rate-limit",
        type=int,
        required=True,
        help="Actual dedicated collector limit; metadata, not configuration",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/portfolio/tracing-benchmark.json"),
    )
    args = parser.parse_args()
    result = asyncio.run(benchmark(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".sha256").write_text(
        f"{digest}  {args.output.name}\n", encoding="utf-8"
    )
    complete = all(
        delivery.get("complete")
        for row in result["results"]
        for delivery in row["deliveries"]
        if row["condition"] != "disabled"
    )
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
