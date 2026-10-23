"""Credential-free concurrent workload shared by the CLI and local collector launcher.

Provider answers, usage and prices are synthetic; overlap and telemetry are real.
"""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from collections import Counter
from typing import Any, Callable

from agenttrace.exporters.api_exporter import APIExporter
from agenttrace.exporters.base import BaseExporter
from agenttrace.exporters.bounded import BoundedExporter
from agenttrace.span import SpanType
from agenttrace.tracer import Tracer

SCENARIO_REVISION = "agenttrace-portfolio-2026-10-23-v1"
PRICING_REVISION = "illustrative-2026-10-23-v1"


def list_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "id": scenario,
            "name": name,
            "description": description,
            "expected_outcomes": {
                "completed": completed,
                "failed": failed,
                "cancelled": 1,
            },
            "request_count": 20,
            "scenario_revision": SCENARIO_REVISION,
            "pricing_revision": PRICING_REVISION,
        }
        for scenario, name, description, completed, failed in [
            (
                "incident",
                "Overlapping incident",
                "Find a retrieval failure, provider timeout and cancellation.",
                17,
                2,
            ),
            (
                "repaired",
                "Retrieval repaired",
                "Retrieval is repaired; timeout and cancellation remain.",
                18,
                1,
            ),
        ]
    ]


async def run_workload(  # noqa: C901 - fixed scenario lifecycle and outcomes
    scenario: str,
    *,
    endpoint: str | None = None,
    exporter: BaseExporter | None = None,
    cohort_id: str | None = None,
    progress: Callable[..., Any] | None = None,
    concurrency: int = 20,
    tracing: bool = True,
) -> dict[str, Any]:  # noqa: C901 - fixed scenario lifecycle and outcomes
    if scenario not in ("incident", "repaired"):
        raise ValueError("Unknown bundled scenario")
    if concurrency not in range(1, 21):
        raise ValueError("Concurrency must be between 1 and 20")
    cohort_id = str(uuid.UUID(cohort_id)) if cohort_id else str(uuid.uuid4())
    if tracing and exporter is None and endpoint is None:
        raise ValueError("A local exporter or collector endpoint is required")
    transport = exporter or (
        APIExporter(endpoint=endpoint.rstrip("/") + "/api/traces", buffer_size=16)
        if endpoint
        else None
    )
    bounded = BoundedExporter(transport) if tracing and transport else None
    tracer = Tracer()
    if bounded:
        tracer.set_exporter(bounded)
    semaphore = asyncio.Semaphore(concurrency)
    observations: list[dict[str, Any]] = []
    run_ids: list[str] = []
    metadata = {
        "cohort_id": cohort_id,
        "scenario": scenario,
        "scenario_revision": SCENARIO_REVISION,
        "pricing_revision": PRICING_REVISION,
        "execution_origin": "bundled_local_workload",
        "provider_origin": "synthetic",
        "usage_origin": "synthetic",
        "pricing_origin": "illustrative",
    }

    async def application(index: int) -> None:
        async def stage(key: str, kind: SpanType, action: Callable[[], Any]) -> None:
            if tracing:
                with tracer.span(
                    key,
                    kind,
                    metadata={
                        **metadata,
                        "case_id": f"request-{index + 1:02d}",
                        "stage_key": key,
                        "attempt": 1,
                        "provider": "synthetic",
                        "model": "fixture-model-v1",
                        "operation": "chat" if kind == SpanType.LLM_CALL else key,
                    },
                ) as span:
                    await asyncio.sleep(0.001 + index % 3 * 0.0005)
                    action()
                    if kind == SpanType.LLM_CALL:
                        span.token_usage = {
                            "prompt_tokens": 120,
                            "completion_tokens": 40,
                            "total_tokens": 160,
                        }
                        span.cost_usd = 0.0002
                    span.set_output({"result": "synthetic response"})
            else:
                await asyncio.sleep(0.001 + index % 3 * 0.0005)
                action()

        def retrieval() -> None:
            if scenario == "incident" and index == 17:
                raise LookupError(
                    "Knowledge index version mismatch; no matching source"
                )

        def provider() -> None:
            if index == 18:
                raise TimeoutError(
                    "Synthetic provider timed out at its declared request deadline"
                )
            if index == 19:
                raise asyncio.CancelledError("Request cancelled by caller")

        await stage("retrieve", SpanType.RETRIEVAL, retrieval)
        await stage("answer", SpanType.LLM_CALL, provider)
        await stage("validate", SpanType.DECISION, lambda: None)

    async def request(index: int) -> None:
        async with semaphore:
            started = time.perf_counter()
            outcome, run_id = "completed", None
            try:
                if tracing:
                    with tracer.run(
                        f"Knowledge request {index + 1:02d}",
                        metadata={**metadata, "case_id": f"request-{index + 1:02d}"},
                        correlation_id=str(
                            uuid.uuid5(uuid.UUID(cohort_id), f"request-{index + 1:02d}")
                        ),
                    ) as run:
                        run_id = run.id
                        run_ids.append(run.id)
                        await application(index)
                else:
                    await application(index)
            except asyncio.CancelledError:
                outcome = "cancelled"
            except (LookupError, TimeoutError):
                outcome = "failed"
            observations.append(
                {
                    "case_id": f"request-{index + 1:02d}",
                    "run_id": run_id,
                    "outcome": outcome,
                    "duration_ms": (time.perf_counter() - started) * 1000,
                }
            )
            if progress:
                result = progress(len(observations), run_id, outcome)
                if inspect.isawaitable(result):
                    await result

    try:
        await asyncio.gather(*(request(index) for index in range(20)))
    finally:
        delivery = (
            await asyncio.to_thread(bounded.close, 15.0)
            if bounded
            else {
                "queued": 0,
                "delivered": 0,
                "dropped": 0,
                "failed": 0,
                "retries": 0,
                "unfinished": 0,
                "complete": True,
            }
        )
    outcomes = Counter(item["outcome"] for item in observations)
    return {
        "cohort_id": cohort_id,
        "scenario": scenario,
        "scenario_revision": SCENARIO_REVISION,
        "pricing_revision": PRICING_REVISION,
        "run_ids": run_ids,
        "application_outcomes": {
            name: outcomes[name] for name in ("completed", "failed", "cancelled")
        },
        "delivery": delivery,
        "provenance": metadata,
        "request_observations": sorted(observations, key=lambda item: item["case_id"]),
    }


def main() -> int:
    """Installed-module entry point. Only the explicit local collector is contacted."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario", choices=("incident", "repaired"), default="incident"
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Collector base URL, e.g. http://127.0.0.1:8300",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run_workload(args.scenario, endpoint=args.endpoint))
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["delivery"]["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
