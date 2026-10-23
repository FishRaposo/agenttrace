"""Check recorded connected/benchmark artifacts without rerunning side effects.

This verifies consistency of recorded observations, not third-party attestation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path


def verify_connected(report: dict) -> None:
    assert report["schema_version"] == 1
    all_ids: set[str] = set()
    for scenario, completed, spans in (("incident", 17, 56), ("repaired", 18, 58)):
        record = report["records"][scenario]
        execution, runs = record["execution"], record["runs"]
        assert execution["status"] == "completed" and execution["delivery"]["complete"]
        assert execution["application_outcomes"] == {
            "completed": completed,
            "failed": 19 - completed,
            "cancelled": 1,
        }
        assert len(runs) == len({row["id"] for row in runs}) == 20
        assert not all_ids.intersection(row["id"] for row in runs)
        all_ids.update(row["id"] for row in runs)
        assert sum(row["span_count"] for row in runs) == spans
        assert record["stats"]["total_runs"] == 20
        assert record["stats"]["total_tokens"] == completed * 160
        assert math.isclose(
            record["stats"]["total_cost"], completed * 0.0002, abs_tol=1e-10
        )
        for row in runs:
            meta = row["metadata"]
            assert meta["cohort_id"] == execution["cohort_id"]
            assert meta["provider_origin"] == meta["usage_origin"] == "synthetic"
            assert meta["pricing_origin"] == "illustrative"
            case = meta["case_id"]
            expected = (
                "cancelled"
                if case == "request-20"
                else "failed"
                if (
                    case == "request-19"
                    or scenario == "incident"
                    and case == "request-18"
                )
                else "completed"
            )
            assert row["status"] == expected
            playback = record["playbacks"][case]
            steps = playback["steps"]
            expected_stages = (
                ["retrieve"]
                if scenario == "incident" and case == "request-18"
                else (
                    ["retrieve", "answer"]
                    if case in ("request-19", "request-20")
                    else ["retrieve", "answer", "validate"]
                )
            )
            assert [step["name"] for step in steps] == expected_stages
            assert playback["total_steps"] == row["span_count"] == len(steps)
            assert (
                playback["playback_mode"] == "recorded" and not playback["reexecution"]
            )
            for step in steps:
                assert step["input_data"] is None and step["output_data"] is None
                assert step["metadata"]["cohort_id"] == execution["cohort_id"]


def verify_benchmark(report: dict) -> None:
    results = report["results"]
    assert len(results) == 18
    assert {(r["condition"], r["concurrency"], r["repeat"]) for r in results} == {
        (condition, concurrency, repeat)
        for condition in ("disabled", "local", "http")
        for concurrency in (1, 20)
        for repeat in (1, 2, 3)
    }
    for row in results:
        observations = row["request_observations"]
        assert row["warmup_requests"] == 20
        assert row["measured_requests"] == len(observations) == 100
        assert row["application_outcomes"] == {
            "completed": 85,
            "failed": 10,
            "cancelled": 5,
        }
        durations = sorted(item["duration_ms"] for item in observations)
        assert row["p50_ms"] == statistics.median(durations)
        assert row["p95_ms"] == durations[94]
        assert math.isclose(
            row["throughput_requests_per_second"], 100 / row["elapsed_seconds"]
        )
        assert all(result["complete"] for result in row["deliveries"])
        assert all(
            result["dropped"] == result["failed"] == result["unfinished"] == 0
            for result in row["deliveries"]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--connected",
        type=Path,
        default=Path("artifacts/portfolio/connected/report.json"),
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("artifacts/portfolio/tracing-benchmark.json"),
    )
    args = parser.parse_args()
    for path in (args.connected, args.benchmark):
        digest_line = path.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest_line
    verify_connected(json.loads(args.connected.read_text(encoding="utf-8")))
    verify_benchmark(json.loads(args.benchmark.read_text(encoding="utf-8")))
    print(
        "Connected scenario/provenance/stage/outcome totals and18benchmark conditions verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
