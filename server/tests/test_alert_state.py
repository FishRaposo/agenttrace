"""Persisted alert-rule and event state tests."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_latency_rule_deduplicates_and_can_be_acknowledged(
    client: AsyncClient,
) -> None:
    rule = await client.post(
        "/api/alerts/rules",
        json={"name": "slow spans", "kind": "latency", "threshold": 100.0},
    )
    assert rule.status_code == 201
    rule_id = rule.json()["id"]

    for run_id in ("alert-state-1", "alert-state-2"):
        await client.post(
            "/api/runs",
            json={
                "id": run_id,
                "name": run_id,
                "status": "running",
                "start_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        await client.post(
            "/api/traces",
            json={
                "run_id": run_id,
                "span_id": f"{run_id}-span",
                "span_type": "tool_call",
                "name": "slow-tool",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "duration_ms": 250.0,
                "status": "completed",
            },
        )

    events = (await client.get("/api/alerts/events")).json()
    matching = [event for event in events if event["rule_id"] == rule_id]
    assert len(matching) == 1
    assert matching[0]["state"] == "open"

    acknowledged = await client.post(f"/api/alerts/events/{matching[0]['id']}/ack")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["state"] == "acknowledged"
