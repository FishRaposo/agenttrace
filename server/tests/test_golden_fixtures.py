"""Smoke-check the checked-in compatibility contract fixtures."""

from __future__ import annotations

import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def test_golden_fixture_set_is_complete_and_valid() -> None:
    expected = {
        "sdk-costs.json",
        "replay-payload.json",
        "run-trace-responses.json",
        "canonical-round-trips.json",
        "alert-decisions.json",
        "auth-database.json",
        "otlp-response.json",
        "dashboard-demo.json",
        "portfolio-evidence.json",
    }
    actual = {path.name for path in GOLDEN_DIR.glob("*.json")}
    assert expected <= actual

    for name in expected:
        with (GOLDEN_DIR / name).open(encoding="utf-8") as handle:
            value = json.load(handle)
        assert isinstance(value, dict), name


def test_golden_fixture_contracts_keep_required_wire_sections() -> None:
    with (GOLDEN_DIR / "run-trace-responses.json").open(encoding="utf-8") as handle:
        responses = json.load(handle)
    assert {"run", "trace"} <= responses.keys()
    assert {"id", "status", "total_cost"} <= responses["run"].keys()
    assert {"run_id", "span_id", "span_type", "sampled"} <= responses["trace"].keys()

    with (GOLDEN_DIR / "otlp-response.json").open(encoding="utf-8") as handle:
        otlp = json.load(handle)
    assert otlp["resourceSpans"][0]["scopeSpans"][0]["spans"]
