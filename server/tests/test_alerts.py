"""Tests for the alerting endpoints (cost and latency rules)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


async def _ingest_span(
    client: AsyncClient, run_id: str, *, duration_ms: float, name: str
) -> None:
    await client.post(
        "/api/runs",
        json={
            "id": run_id,
            "name": "alert_run",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    await client.post(
        "/api/traces",
        json={
            "run_id": run_id,
            "span_id": f"{run_id}-{name}",
            "span_type": "llm_call",
            "name": name,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "status": "completed",
        },
    )


@pytest.mark.asyncio
async def test_cost_alerts_no_breach(client: AsyncClient) -> None:
    resp = await client.get("/api/alerts?daily_threshold=1000&per_run_threshold=1000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_alert"] is False
    assert data["expensive_runs"] == []


@pytest.mark.asyncio
async def test_latency_alert_fires_above_threshold(client: AsyncClient) -> None:
    await _ingest_span(client, "slow-run", duration_ms=8000.0, name="slow_span")
    await _ingest_span(client, "fast-run", duration_ms=50.0, name="fast_span")

    resp = await client.get("/api/alerts/latency?threshold_ms=5000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["latency_alert"] is True
    assert data["breaching_count"] == 1
    assert data["max_latency_ms"] == pytest.approx(8000.0)
    assert data["slow_spans"][0]["name"] == "slow_span"


@pytest.mark.asyncio
async def test_latency_alert_no_breach(client: AsyncClient) -> None:
    await _ingest_span(client, "ok-run", duration_ms=100.0, name="ok_span")
    resp = await client.get("/api/alerts/latency?threshold_ms=5000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["latency_alert"] is False
    assert data["breaching_count"] == 0
    assert data["slow_spans"] == []


@pytest.mark.asyncio
async def test_latency_alert_rejects_nonpositive_threshold(client: AsyncClient) -> None:
    resp = await client.get("/api/alerts/latency?threshold_ms=0")
    assert resp.status_code == 422
