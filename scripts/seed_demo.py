"""Seed demo data into the AgentTrace server.

Generates deterministic, varied agent runs with realistic cost,
token, and latency distributions. Intended to be run against a
fresh server so the dashboard is never empty on first visit.

Usage:
    python scripts/seed_demo.py [--endpoint http://localhost:8000/api]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


MODELS = [
    {
        "provider": "openai",
        "model": "gpt-4",
        "prompt_rate": 0.03,
        "completion_rate": 0.06,
    },
    {
        "provider": "openai",
        "model": "gpt-4-turbo",
        "prompt_rate": 0.01,
        "completion_rate": 0.03,
    },
    {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "prompt_rate": 0.0015,
        "completion_rate": 0.002,
    },
    {
        "provider": "anthropic",
        "model": "claude-3-sonnet",
        "prompt_rate": 0.003,
        "completion_rate": 0.015,
    },
    {
        "provider": "anthropic",
        "model": "claude-3-haiku",
        "prompt_rate": 0.00025,
        "completion_rate": 0.00125,
    },
]

SPAN_TEMPLATES = [
    ("web_search", "tool_call", 0.05, 0.15, 50, 200, 0.02),
    ("parse_content", "tool_call", 0.03, 0.1, 100, 400, 0.01),
    ("synthesize_findings", "llm_call", 0.4, 1.2, 400, 800, 0.05),
    ("generate_questions", "llm_call", 0.2, 0.6, 200, 400, 0.03),
    ("choose_tool", "decision", 0.01, 0.03, 20, 60, 0.1),
    ("retrieve_docs", "retrieval", 0.08, 0.25, 150, 600, 0.03),
    ("rerank_results", "decision", 0.02, 0.08, 50, 200, 0.05),
]

RUN_NAMES = [
    "research_agent",
    "support_bot",
    "code_reviewer",
    "data_pipeline",
    "qa_runner",
    "multi_agent_research",
    "customer_onboarding",
    "doc_analyzer",
    "test_generator",
    "alert_classifier",
    "summary_writer",
    "knowledge_base_query",
]


def _post(url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    data = json.dumps(payload, default=str).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                return json.loads(resp.read().decode("utf-8"))
            return None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  HTTP {e.code}: {body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Request error: {e}", file=sys.stderr)
        return None


def _rnd(min_val: float, max_val: float) -> float:
    return round(random.uniform(min_val, max_val), 3)


def _rnd_int(min_val: int, max_val: int) -> int:
    return random.randint(min_val, max_val)


def _now(delta_seconds: float = 0.0) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=delta_seconds)).isoformat()


def create_run(
    endpoint: str,
    run_id: str,
    name: str,
    status: str,
    correlation_id: str | None = None,
) -> bool:
    payload = {
        "id": run_id,
        "name": name,
        "status": status,
        "start_time": _now(),
        "end_time": _now() if status != "running" else None,
        "total_cost": 0.0,
        "total_tokens": 0,
        "span_count": 0,
        "correlation_id": correlation_id,
        "metadata": {"seeded": True, "demo": True},
    }
    result = _post(f"{endpoint}/runs", payload)
    return result is not None


def create_trace(
    endpoint: str,
    run_id: str,
    span_id: str,
    name: str,
    span_type: str,
    model_info: dict[str, Any] | None,
    duration_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
    status: str,
    error: str | None = None,
    parent_span_id: str | None = None,
) -> bool:
    total_tokens = prompt_tokens + completion_tokens
    if model_info and status != "error":
        cost = round(
            (prompt_tokens / 1000) * model_info["prompt_rate"]
            + (completion_tokens / 1000) * model_info["completion_rate"],
            6,
        )
    else:
        cost = 0.0

    model: str | None = None
    provider: str | None = None
    if model_info:
        model = model_info["model"]
        provider = model_info["provider"]

    # Assign a feature to some spans for cost-by-feature breakdown
    features = ["research", "summarization", "qa", "code_gen", "analysis"]
    span_feature = random.choice(features) if span_type == "llm_call" else None

    payload = {
        "run_id": run_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "span_type": span_type,
        "name": name,
        "input_data": {"query": f"sample input for {name}"},
        "output_data": None if error else {"result": f"output from {name}"},
        "metadata": {
            "model": model,
            "provider": provider,
            "feature": span_feature,
        },
        "start_time": _now(),
        "end_time": _now() if status != "started" else None,
        "duration_ms": duration_ms,
        "cost_usd": cost,
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "status": status,
        "error": error,
        "model": model,
        "provider": provider,
        "feature": span_feature,
    }
    result = _post(f"{endpoint}/traces", payload)
    return result is not None


def seed(endpoint: str, count: int = 12) -> None:
    random.seed(42)
    print(f"Seeding {count} demo runs into {endpoint} ...")

    correlation_id = "workflow-research-001"
    multi_agent_runs: list[str] = []

    for i in range(count):
        run_id = f"demo-run-{i:03d}"
        name = RUN_NAMES[i % len(RUN_NAMES)]

        # Two correlated multi-agent runs
        corr: str | None = None
        if i == 5:
            corr = correlation_id
        elif i == 6:
            corr = correlation_id
            multi_agent_runs.append(run_id)

        status = "completed"
        error_rate = 0.15
        if random.random() < error_rate:
            status = "failed"

        if not create_run(endpoint, run_id, name, status, correlation_id=corr):
            print(f"  Failed to create run {run_id}, skipping.")
            continue

        num_spans = random.randint(3, 8)
        for s in range(num_spans):
            template = random.choice(SPAN_TEMPLATES)
            span_name, span_type, dur_min, dur_max, tok_min, tok_max, fail_rate = (
                template
            )

            span_status = "completed"
            span_error = None
            if status == "failed" and s == num_spans - 1:
                span_status = "error"
                span_error = "Simulated failure for demo purposes"
            elif random.random() < fail_rate:
                span_status = "error"
                span_error = "Simulated intermittent error"

            model_info = None
            if span_type == "llm_call":
                model_info = random.choice(MODELS)

            duration_ms = _rnd(dur_min, dur_max) * 1000
            prompt_tokens = _rnd_int(tok_min, tok_max)
            completion_tokens = _rnd_int(tok_min // 2, tok_max // 2)

            parent_span_id = None
            if s > 0 and random.random() < 0.4:
                parent_span_id = f"{run_id}-span-{s - 1:03d}"

            create_trace(
                endpoint=endpoint,
                run_id=run_id,
                span_id=f"{run_id}-span-{s:03d}",
                name=span_name,
                span_type=span_type,
                model_info=model_info,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                status=span_status,
                error=span_error,
                parent_span_id=parent_span_id,
            )

        print(f"  Run {run_id} ({name}) — {num_spans} spans")

    # Seed a demo budget
    budget_payload = {
        "name": "Monthly AI Spend",
        "scope": "global",
        "limit_usd": 5.0,
        "period": "monthly",
        "alert_threshold_pct": 80,
    }
    _post(f"{endpoint}/budgets", budget_payload)

    print(f"Done. {count} runs seeded.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed AgentTrace demo data")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/api",
        help="AgentTrace API base URL",
    )
    parser.add_argument(
        "--count", type=int, default=12, help="Number of runs to generate"
    )
    args = parser.parse_args()

    # Health check
    try:
        req = urllib.request.Request(
            f"{args.endpoint.replace('/api', '')}/health", method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print("Server is healthy.")
    except Exception:
        print(
            "Warning: Could not reach health endpoint. Server may not be running.",
            file=sys.stderr,
        )
        return 1

    seed(args.endpoint, count=args.count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
