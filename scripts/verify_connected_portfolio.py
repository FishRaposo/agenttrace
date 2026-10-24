"""Verify real local SDK/collector persistence through HTTP, without API mocks.

Use only a disposable collector. Launches both bundled scenarios explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


def request(endpoint: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        endpoint + path,
        data=data,
        headers={"Content-Type": "application/json", "Connection": "close"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def execute(endpoint: str, scenario: str) -> dict:
    body = {"scenario": scenario, "request_id": str(uuid.uuid4())}
    status, launched = request(endpoint, "/api/portfolio/executions", body)
    assert status == 202, (status, launched)
    repeated_status, repeated = request(endpoint, "/api/portfolio/executions", body)
    assert repeated_status in (200, 202) and repeated["id"] == launched["id"], repeated
    conflict_status, conflict = request(
        endpoint,
        "/api/portfolio/executions",
        {**body, "scenario": "repaired" if scenario == "incident" else "incident"},
    )
    assert conflict_status == 409, conflict
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        _, result = request(endpoint, f"/api/portfolio/executions/{launched['id']}")
        if result["status"] in ("completed", "failed", "interrupted"):
            break
        time.sleep(0.2)
    else:
        raise AssertionError(f"execution deadline: {result}")
    assert result["status"] == "completed", result
    expected = {
        "completed": 17 if scenario == "incident" else 18,
        "failed": 2 if scenario == "incident" else 1,
        "cancelled": 1,
    }
    assert result["application_outcomes"] == expected, result
    assert result["delivery"]["complete"], result
    assert len(result["run_ids"]) == len(set(result["run_ids"])) == 20, result
    return result


def verify(endpoint: str) -> dict:
    status, scenarios = request(endpoint, "/api/portfolio/scenarios")
    assert status == 200 and scenarios["ready"], scenarios
    incident = execute(endpoint, "incident")
    repaired = execute(endpoint, "repaired")
    records = {}
    for name, execution in (("incident", incident), ("repaired", repaired)):
        cohort = execution["cohort_id"]
        status, runs = request(endpoint, f"/api/runs?cohort_id={cohort}&limit=100")
        assert status == 200, runs
        rows = runs["runs"] if isinstance(runs, dict) else runs
        assert len(rows) == 20, runs
        assert {row["id"] for row in rows} == set(execution["run_ids"]), runs
        _, stats = request(endpoint, f"/api/stats?cohort_id={cohort}")
        assert stats["total_runs"] == 20, stats
        assert stats["total_tokens"] == sum(row["total_tokens"] for row in rows), stats
        assert sum(row["span_count"] for row in rows) == (
            56 if name == "incident" else 58
        ), rows
        playbacks = {}
        for row in rows:
            case_id = row["metadata"]["case_id"]
            expected_status = (
                "cancelled"
                if case_id == "request-20"
                else "failed"
                if case_id == "request-19"
                or (name == "incident" and case_id == "request-18")
                else "completed"
            )
            assert row["status"] == expected_status, row
            _, playback = request(endpoint, f"/api/replay/runs/{row['id']}")
            assert playback["run"]["id"] == row["id"], playback
            assert (
                playback["total_steps"] == len(playback["steps"]) == row["span_count"]
            ), playback
            playbacks[case_id] = playback
        _, after = request(endpoint, f"/api/stats?cohort_id={cohort}")
        assert after == stats, "recorded playback must have no effects"
        _, cost = request(endpoint, f"/api/costs/summary?cohort_id={cohort}")
        records[name] = {
            "execution": execution,
            "runs": rows,
            "stats": stats,
            "costs": cost,
            "playbacks": playbacks,
        }
    before = next(
        row
        for row in records["incident"]["runs"]
        if row["metadata"]["case_id"] == "request-18"
    )
    after = next(
        row
        for row in records["repaired"]["runs"]
        if row["metadata"]["case_id"] == "request-18"
    )
    status, comparison = request(
        endpoint, f"/api/diff/runs?run_id_1={before['id']}&run_id_2={after['id']}"
    )
    assert status == 200 and comparison["aligned_stages"], comparison
    return {
        "schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "provenance": "real HTTP, shared bundled synthetic workload, persisted collector records",
        "scenarios": scenarios,
        "records": records,
        "retrieval_comparison": comparison,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8300")
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/portfolio/connected/report.json")
    )
    args = parser.parse_args()
    report = verify(args.endpoint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".sha256").write_text(
        f"{digest}  {args.output.name}\n", encoding="utf-8"
    )
    print(
        f"Connected workload/persistence/playback/cohort checks passed: {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
