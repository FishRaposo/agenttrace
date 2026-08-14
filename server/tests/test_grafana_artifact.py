"""Static Grafana artifact validation."""

import json
from pathlib import Path


def test_grafana_dashboard_has_expected_observability_panels() -> None:
    path = (
        Path(__file__).parents[2]
        / "monitoring"
        / "grafana"
        / "agenttrace-overview.json"
    )
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    titles = {panel["title"] for panel in dashboard["panels"]}
    assert {
        "Trace throughput",
        "Latency p95",
        "Estimated cost",
        "Error rate",
        "Sampled traces",
    } <= titles
