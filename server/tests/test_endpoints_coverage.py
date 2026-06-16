"""Broad endpoint coverage — success and error paths for under-tested routes."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


async def _make_run(client: AsyncClient, name: str = "r", **extra: object) -> str:
    payload = {
        "name": name,
        "status": "completed",
        "start_time": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    resp = await client.post("/api/runs", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


# --------------------------------------------------------------------------- #
# Root + health                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "AgentTrace Server"
    assert "version" in body


@pytest.mark.asyncio
async def test_health_reports_database_connected(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "uptime" in data


# --------------------------------------------------------------------------- #
# Stats                                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_stats_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 0
    assert data["total_cost"] == 0.0
    assert data["avg_duration_ms"] == 0.0


@pytest.mark.asyncio
async def test_stats_aggregates_runs(client: AsyncClient) -> None:
    await _make_run(client, "a", total_cost=1.5, total_tokens=100)
    await _make_run(client, "b", total_cost=2.5, total_tokens=200)
    resp = await client.get("/api/stats")
    data = resp.json()
    assert data["total_runs"] == 2
    assert data["total_cost"] == pytest.approx(4.0)
    assert data["total_tokens"] == 300


# --------------------------------------------------------------------------- #
# Traces                                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_trace_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/traces/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_traces_filtered_by_span_type(client: AsyncClient) -> None:
    run_id = await _make_run(client, "filtered")
    for span_type in ("llm_call", "tool_call"):
        await client.post(
            "/api/traces",
            json={
                "run_id": run_id,
                "span_id": f"{run_id}-{span_type}",
                "span_type": span_type,
                "name": span_type,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
            },
        )
    resp = await client.get("/api/traces?span_type=tool_call")
    assert resp.status_code == 200
    rows = resp.json()
    assert all(r["span_type"] == "tool_call" for r in rows)
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_list_traces_validates_limit(client: AsyncClient) -> None:
    resp = await client.get("/api/traces?limit=9999")
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Diff                                                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_diff_runs_not_found(client: AsyncClient) -> None:
    run_id = await _make_run(client, "exists")
    resp = await client.get(f"/api/diff/runs?run_id_1={run_id}&run_id_2=missing")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_diff_runs_missing_query_params(client: AsyncClient) -> None:
    resp = await client.get("/api/diff/runs")
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Replay                                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_replay_run_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/replay/runs/missing")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Runs delete error path                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_delete_missing_run_returns_404(client: AsyncClient) -> None:
    resp = await client.delete("/api/runs/never-existed")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Auth                                                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_auth_register_login_me_flow(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "s3cret-pw"},
    )
    assert reg.status_code == 201
    assert reg.json()["username"] == "alice"

    # Duplicate registration is rejected
    dup = await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "other"},
    )
    assert dup.status_code == 400

    token_resp = await client.post(
        "/api/auth/token",
        data={"username": "alice", "password": "s3cret-pw"},
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


@pytest.mark.asyncio
async def test_auth_login_bad_password(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "correct-pw"},
    )
    resp = await client.post(
        "/api/auth/token",
        data={"username": "bob", "password": "wrong-pw"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_rejects_invalid_token(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
