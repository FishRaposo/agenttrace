"""Tests for the traces API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


async def test_create_run(client: AsyncClient) -> None:
    response = await client.post(
        "/api/runs",
        json={
            "name": "test_run",
            "correlation_id": "workflow-123",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "metadata": {"source": "test"},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_run"
    assert data["correlation_id"] == "workflow-123"
    assert data["status"] == "running"
    assert data["metadata"] == {"source": "test"}


async def test_create_run_updates_existing_sdk_run(client: AsyncClient) -> None:
    run_id = "sdk-run-upsert"
    start_resp = await client.post(
        "/api/runs",
        json={
            "id": run_id,
            "name": "sdk_run",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert start_resp.status_code == 201

    end_resp = await client.post(
        "/api/runs",
        json={
            "id": run_id,
            "name": "sdk_run",
            "status": "completed",
            "start_time": start_resp.json()["start_time"],
            "end_time": datetime.now(timezone.utc).isoformat(),
            "total_cost": 0.01,
            "total_tokens": 100,
            "span_count": 1,
        },
    )

    assert end_resp.status_code == 201
    data = end_resp.json()
    assert data["id"] == run_id
    assert data["status"] == "completed"


async def test_list_runs(client: AsyncClient) -> None:
    await client.post(
        "/api/runs",
        json={
            "name": "run_1",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )

    response = await client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["runs"]) >= 1


async def test_get_run(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/runs",
        json={
            "name": "run_detail",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run_id = create_resp.json()["id"]

    response = await client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "run_detail"


async def test_get_nonexistent_run(client: AsyncClient) -> None:
    response = await client.get("/api/runs/nonexistent-id")
    assert response.status_code == 404


async def test_ingest_trace(client: AsyncClient) -> None:
    create_run = await client.post(
        "/api/runs",
        json={
            "name": "trace_run",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run_id = create_run.json()["id"]

    response = await client.post(
        "/api/traces",
        json={
            "run_id": run_id,
            "span_id": "span-001",
            "span_type": "llm_call",
            "name": "gpt-4 call",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "duration_ms": 1500.0,
            "cost_usd": 0.003,
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "gpt-4 call"
    assert data["cost_usd"] == 0.003


async def test_ingest_trace_accepts_sdk_span_payload(client: AsyncClient) -> None:
    create_run = await client.post(
        "/api/runs",
        json={
            "id": "run-from-sdk",
            "name": "sdk_run",
            "correlation_id": "workflow-123",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "metadata": {"agent": "research"},
        },
    )
    assert create_run.status_code == 201
    assert create_run.json()["metadata"] == {"agent": "research"}

    response = await client.post(
        "/api/traces",
        json={
            "run_id": "run-from-sdk",
            "span_id": "span-from-sdk",
            "span_type": "tool_call",
            "name": "web_search",
            "input_data": {"args": "('query',)", "kwargs": "{}"},
            "output_data": {"results": []},
            "metadata": {"tool_name": "web_search"},
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 42.0,
            "status": "completed",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["span_id"] == "span-from-sdk"
    assert data["metadata"] == {"tool_name": "web_search"}


async def test_ingest_traces_batch(client: AsyncClient) -> None:
    create_run = await client.post(
        "/api/runs",
        json={
            "name": "batch_run",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run_id = create_run.json()["id"]

    response = await client.post(
        "/api/traces/batch",
        json=[
            {
                "run_id": run_id,
                "span_id": "span-batch-1",
                "span_type": "llm_call",
                "name": "call 1",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "cost_usd": 0.001,
                "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
            {
                "run_id": run_id,
                "span_id": "span-batch-2",
                "span_type": "tool_call",
                "name": "call 2",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "cost_usd": 0.002,
                "token_usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            },
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "call 1"
    assert data[1]["name"] == "call 2"

    # Verify run aggregates were updated
    run_resp = await client.get(f"/api/runs/{run_id}")
    run_data = run_resp.json()
    assert run_data["total_cost"] == 0.003
    assert run_data["total_tokens"] == 45
    assert run_data["span_count"] == 2


async def test_list_traces_by_run(client: AsyncClient) -> None:
    response = await client.get("/api/traces")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_delete_run(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/runs",
        json={
            "name": "to_delete",
            "status": "completed",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run_id = create_resp.json()["id"]

    response = await client.delete(f"/api/runs/{run_id}")
    assert response.status_code == 204
