"""Integration tests for end-to-end workflows."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient


async def test_correlation_id_flow(client: AsyncClient) -> None:
    """Test that correlation_id is properly stored and filtered."""
    # Create a run with correlation_id
    correlation_id = "test-correlation-123"
    response = await client.post(
        "/api/runs",
        json={
            "name": "run_with_correlation",
            "correlation_id": correlation_id,
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201
    run = response.json()
    assert run["correlation_id"] == correlation_id

    # Create another run with the same correlation_id
    response = await client.post(
        "/api/runs",
        json={
            "name": "run_with_same_correlation",
            "correlation_id": correlation_id,
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201

    # Create a run without correlation_id
    response = await client.post(
        "/api/runs",
        json={
            "name": "run_without_correlation",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201

    # Filter by correlation_id
    response = await client.get(f"/api/runs?correlation_id={correlation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for run in data["runs"]:
        assert run["correlation_id"] == correlation_id


async def test_run_diff_flow(client: AsyncClient) -> None:
    """Test the run diffing functionality."""
    # Create two runs
    run1_resp = await client.post(
        "/api/runs",
        json={
            "name": "run_for_diff_1",
            "status": "completed",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run1_id = run1_resp.json()["id"]

    run2_resp = await client.post(
        "/api/runs",
        json={
            "name": "run_for_diff_2",
            "status": "completed",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run2_id = run2_resp.json()["id"]

    # Add traces to both runs
    await client.post(
        "/api/traces",
        json={
            "run_id": run1_id,
            "span_id": "span-1",
            "span_type": "llm_call",
            "name": "gpt-4",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "duration_ms": 1000.0,
            "cost_usd": 0.01,
            "token_usage": {
                "prompt_tokens": 60,
                "completion_tokens": 40,
                "total_tokens": 100,
            },
        },
    )

    await client.post(
        "/api/traces",
        json={
            "run_id": run2_id,
            "span_id": "span-2",
            "span_type": "llm_call",
            "name": "gpt-4",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "duration_ms": 2000.0,
            "cost_usd": 0.02,
            "token_usage": {
                "prompt_tokens": 120,
                "completion_tokens": 80,
                "total_tokens": 200,
            },
        },
    )

    # Get diff
    response = await client.get(f"/api/diff/runs?run_id_1={run1_id}&run_id_2={run2_id}")
    assert response.status_code == 200
    diff = response.json()

    assert diff["run1"]["id"] == run1_id
    assert diff["run2"]["id"] == run2_id
    assert diff["differences"]["cost_diff"] == 0.01
    assert diff["differences"]["token_diff"] == 100


async def test_replay_data_flow(client: AsyncClient) -> None:
    """Test the replay data endpoint."""
    # Create a run
    run_resp = await client.post(
        "/api/runs",
        json={
            "name": "run_for_replay",
            "status": "completed",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run_id = run_resp.json()["id"]

    # Add some traces
    await client.post(
        "/api/traces",
        json={
            "run_id": run_id,
            "span_id": "span-1",
            "span_type": "llm_call",
            "name": "gpt-4",
            "input_data": {"prompt": "Hello"},
            "output_data": {"completion": "Hi there!"},
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "duration_ms": 1000.0,
        },
    )

    await client.post(
        "/api/traces",
        json={
            "run_id": run_id,
            "span_id": "span-2",
            "span_type": "tool_call",
            "name": "search",
            "input_data": {"query": "test"},
            "output_data": {"results": []},
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "duration_ms": 500.0,
        },
    )

    # Get replay data
    response = await client.get(f"/api/replay/runs/{run_id}")
    assert response.status_code == 200
    replay = response.json()

    assert replay["run"]["id"] == run_id
    assert replay["total_steps"] == 2
    assert len(replay["steps"]) == 2

    # Verify step data
    step1 = replay["steps"][0]
    assert step1["input_data"] == {"prompt": "Hello"}
    assert step1["output_data"] == {"completion": "Hi there!"}


async def test_alerts_flow(client: AsyncClient) -> None:
    """Test cost alerting functionality."""
    # Create a run with high cost
    await client.post(
        "/api/runs",
        json={
            "name": "expensive_run",
            "status": "completed",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "total_cost": 100.0,
        },
    )

    # Check alerts
    response = await client.get(
        "/api/alerts?daily_threshold=10.0&per_run_threshold=5.0"
    )
    assert response.status_code == 200
    alerts = response.json()

    assert alerts["daily_threshold_exceeded"] is True
    assert alerts["daily_alert"] is True
    assert len(alerts["expensive_runs"]) >= 1


async def test_streaming_flow(client: AsyncClient) -> None:
    """Test the SSE streaming endpoint."""
    # Create a run
    run_resp = await client.post(
        "/api/runs",
        json={
            "name": "run_for_streaming",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    run_id = run_resp.json()["id"]

    # Add a trace
    await client.post(
        "/api/traces",
        json={
            "run_id": run_id,
            "span_id": "span-1",
            "span_type": "llm_call",
            "name": "gpt-4",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        },
    )

    # In-process httpx ASGI transport buffers streaming responses until the
    # body completes, so verify registration without consuming the infinite SSE.
    # Use the OpenAPI schema (version-robust: FastAPI's include_router no longer
    # flattens sub-router routes into app.routes).
    from app.main import app

    schema = app.openapi()
    assert "/api/stream/traces" in schema["paths"]
    assert "get" in schema["paths"]["/api/stream/traces"]
