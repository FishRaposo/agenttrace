"""Benchmark script — measure trace ingestion throughput.

Usage:
    AGENTTRACE_API_URL=http://localhost:8000/api python scripts/benchmark.py
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import urllib.request
import urllib.error
import json

API_URL = os.getenv("AGENTTRACE_API_URL", "http://localhost:8000/api")


def _post(path: str, payload: dict) -> tuple[int, float]:
    url = f"{API_URL}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, time.perf_counter() - start
    except urllib.error.HTTPError as e:
        return e.code, time.perf_counter() - start


def create_run(name: str) -> str:
    status, latency = _post(
        "/runs",
        {
            "name": name,
            "status": "completed",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    return f"run-{name}"


def ingest_trace(run_id: str, span_id: str) -> float:
    _, latency = _post(
        "/traces",
        {
            "run_id": run_id,
            "span_id": span_id,
            "span_type": "llm_call",
            "name": "benchmark-span",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "duration_ms": 150.0,
            "cost_usd": 0.001,
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        },
    )
    return latency


def ingest_batch(run_id: str, batch_size: int) -> float:
    traces = [
        {
            "run_id": run_id,
            "span_id": f"batch-span-{i}",
            "span_type": "llm_call",
            "name": "benchmark-batch",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "duration_ms": 150.0,
            "cost_usd": 0.001,
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        for i in range(batch_size)
    ]
    _, latency = _post("/traces/batch", traces)
    return latency


def benchmark() -> None:
    print("=" * 50)
    print("AgentTrace Ingestion Benchmark")
    print("=" * 50)

    # Check server health
    try:
        req = urllib.request.Request(f"{API_URL.replace('/api', '')}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                print("Server not healthy. Exiting.")
                sys.exit(1)
    except Exception as e:
        print(f"Cannot reach server: {e}")
        sys.exit(1)

    # Warmup
    print("\n[Warmup] Creating 1 run + 10 traces...")
    run_id = f"bench-{int(time.time())}"
    create_run(run_id)
    for i in range(10):
        ingest_trace(run_id, f"warmup-{i}")
    print("Warmup complete.")

    # Single trace throughput
    print("\n[Single Trace] 100 sequential requests...")
    start = time.perf_counter()
    latencies = [ingest_trace(run_id, f"seq-{i}") for i in range(100)]
    total = time.perf_counter() - start
    print(f"  Total time: {total:.2f}s")
    print(f"  Throughput: {100 / total:.1f} traces/sec")
    print(f"  Avg latency: {sum(latencies) / len(latencies) * 1000:.1f}ms")
    print(
        f"  P95 latency: {sorted(latencies)[int(len(latencies) * 0.95)] * 1000:.1f}ms"
    )

    # Concurrent trace throughput
    print("\n[Concurrent] 10 workers x 50 traces = 500 traces...")
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [
            pool.submit(ingest_trace, run_id, f"concurrent-{i}") for i in range(500)
        ]
        latencies = [f.result() for f in futures]
    total = time.perf_counter() - start
    print(f"  Total time: {total:.2f}s")
    print(f"  Throughput: {500 / total:.1f} traces/sec")
    print(f"  Avg latency: {sum(latencies) / len(latencies) * 1000:.1f}ms")
    print(
        f"  P95 latency: {sorted(latencies)[int(len(latencies) * 0.95)] * 1000:.1f}ms"
    )

    # Batch throughput
    print("\n[Batch] 10 batches x 50 traces = 500 traces...")
    start = time.perf_counter()
    latencies = [ingest_batch(run_id, 50) for _ in range(10)]
    total = time.perf_counter() - start
    print(f"  Total time: {total:.2f}s")
    print(f"  Throughput: {500 / total:.1f} traces/sec")
    print(f"  Avg batch latency: {sum(latencies) / len(latencies) * 1000:.1f}ms")

    # Cleanup
    print("\n[Cleanup] Deleting benchmark run...")
    req = urllib.request.Request(f"{API_URL}/runs/{run_id}", method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"  Deleted (status={resp.status})")
    except urllib.error.HTTPError as e:
        print(f"  Delete failed: {e.code}")

    print("\n" + "=" * 50)
    print("Benchmark complete")
    print("=" * 50)


if __name__ == "__main__":
    benchmark()
