"""Tests for cost analytics and budget endpoints."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


async def _create_cost_trace(
    client: AsyncClient,
    *,
    run_id: str,
    span_id: str,
    start_time: str,
    cost_usd: float,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    prompt_version: str | None,
    span_type: str = "llm_call",
    status: str = "completed",
    error: str | None = None,
) -> None:
    metadata = {}
    if prompt_version is not None:
        metadata["prompt_version"] = prompt_version

    response = await client.post(
        "/api/traces",
        json={
            "run_id": run_id,
            "span_id": span_id,
            "span_type": span_type,
            "name": span_id,
            "metadata": metadata,
            "start_time": start_time,
            "duration_ms": duration_ms,
            "cost_usd": cost_usd,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "status": status,
            "error": error,
            "model": "gpt-4o",
            "provider": "openai",
            "feature": "summarize",
        },
    )
    assert response.status_code == 201


async def _seed_prompt_costs(client: AsyncClient) -> None:
    response = await client.post(
        "/api/runs",
        json={
            "id": "prompt-cost-run",
            "name": "prompt-cost-run",
            "status": "completed",
            "start_time": datetime(2026, 8, 10, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201

    await _create_cost_trace(
        client,
        run_id="prompt-cost-run",
        span_id="v1-morning",
        start_time="2026-08-10T09:00:00+00:00",
        cost_usd=0.01,
        prompt_tokens=10,
        completion_tokens=5,
        duration_ms=100.0,
        prompt_version="v1",
    )
    await _create_cost_trace(
        client,
        run_id="prompt-cost-run",
        span_id="v1-afternoon-error",
        start_time="2026-08-10T15:00:00+00:00",
        cost_usd=0.02,
        prompt_tokens=20,
        completion_tokens=10,
        duration_ms=300.0,
        prompt_version="v1",
        status="error",
        error="provider timeout",
    )
    await _create_cost_trace(
        client,
        run_id="prompt-cost-run",
        span_id="v2-next-day",
        start_time="2026-08-11T11:00:00+00:00",
        cost_usd=0.03,
        prompt_tokens=30,
        completion_tokens=15,
        duration_ms=200.0,
        prompt_version="v2",
    )
    await _create_cost_trace(
        client,
        run_id="prompt-cost-run",
        span_id="unversioned",
        start_time="2026-08-11T12:00:00+00:00",
        cost_usd=0.04,
        prompt_tokens=40,
        completion_tokens=20,
        duration_ms=250.0,
        prompt_version=None,
    )
    await _create_cost_trace(
        client,
        run_id="prompt-cost-run",
        span_id="tool-not-an-llm-request",
        start_time="2026-08-10T10:00:00+00:00",
        cost_usd=0.5,
        prompt_tokens=0,
        completion_tokens=0,
        duration_ms=50.0,
        prompt_version="v1",
        span_type="tool_call",
    )


@pytest.mark.asyncio
async def test_cost_summary(client: AsyncClient) -> None:
    response = await client.get("/api/costs/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_cost" in data
    assert "total_tokens" in data
    assert "total_spans" in data
    assert "by_provider" in data
    assert "by_model" in data
    assert "by_feature" in data


@pytest.mark.asyncio
async def test_cost_summary_aggregates_and_filters_prompt_versions(
    client: AsyncClient,
) -> None:
    """Dropping metadata grouping or ignoring the filter must break this test."""
    await _seed_prompt_costs(client)

    response = await client.get("/api/costs/summary")
    assert response.status_code == 200
    assert response.json()["by_prompt_version"] == {
        "unversioned": 0.04,
        "v1": 0.03,
        "v2": 0.03,
    }

    filtered = await client.get("/api/costs/summary?prompt_version=v1")
    assert filtered.status_code == 200
    assert filtered.json() == {
        "total_cost": 0.03,
        "total_tokens": 45,
        "total_spans": 2,
        "by_provider": {"openai": 0.03},
        "by_model": {"gpt-4o": 0.03},
        "by_feature": {"summarize": 0.03},
        "by_prompt_version": {"v1": 0.03},
    }


@pytest.mark.asyncio
async def test_cost_timeseries(client: AsyncClient) -> None:
    response = await client.get("/api/costs/timeseries?granularity=day&days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "day"
    assert "data" in data


@pytest.mark.asyncio
async def test_cost_by_model(client: AsyncClient) -> None:
    response = await client.get("/api/costs/by-model")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_cost_projection(client: AsyncClient) -> None:
    response = await client.get("/api/costs/projection")
    assert response.status_code == 200
    data = response.json()
    assert "daily_burn" in data
    assert "monthly_projection" in data


@pytest.mark.asyncio
async def test_daily_cost_report_is_deterministic_and_filters_llm_traces(
    client: AsyncClient,
) -> None:
    """Changing row order, metric math, or LLM-only filtering must break this test."""
    await _seed_prompt_costs(client)

    first = await client.get(
        "/api/costs/reports/daily?day=2026-08-10&format=json"
    )
    second = await client.get(
        "/api/costs/reports/daily?day=2026-08-10&format=json"
    )

    assert first.status_code == 200
    assert first.content == second.content
    assert first.json() == {
        "days": {
            "2026-08-10": {
                "total_requests": 2,
                "total_tokens": 45,
                "input_tokens": 30,
                "output_tokens": 15,
                "estimated_cost": 0.03,
                "average_latency_ms": 200.0,
                "p50_latency_ms": 200.0,
                "p95_latency_ms": 290.0,
                "p99_latency_ms": 298.0,
                "error_rate": 0.5,
                "cost_by_model": {"gpt-4o": 0.03},
                "cost_by_prompt_version": {"v1": 0.03},
            }
        },
        "day": "2026-08-10",
    }

    csv_response = await client.get(
        "/api/costs/reports/daily?day=2026-08-10&format=csv"
    )
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert rows == [
        {
            "day": "2026-08-10",
            "total_requests": "2",
            "total_tokens": "45",
            "input_tokens": "30",
            "output_tokens": "15",
            "estimated_cost": "0.03",
            "average_latency_ms": "200.0",
            "p50_latency_ms": "200.0",
            "p95_latency_ms": "290.0",
            "p99_latency_ms": "298.0",
            "error_rate": "0.5",
        }
    ]


@pytest.mark.asyncio
async def test_daily_cost_report_prompt_filter_has_sorted_days_and_totals(
    client: AsyncClient,
) -> None:
    """Removing exact prompt filtering or deterministic day ordering must fail."""
    await _seed_prompt_costs(client)

    response = await client.get(
        "/api/costs/reports/daily?prompt_version=v1&format=json"
    )

    assert response.status_code == 200
    report = response.json()
    assert list(report["days"]) == ["2026-08-10"]
    assert report["prompt_version"] == "v1"
    assert report["totals"] == report["days"]["2026-08-10"]


@pytest.mark.asyncio
async def test_daily_cost_report_buckets_timezone_offsets_by_utc_day(
    client: AsyncClient,
) -> None:
    """Using the source timezone's calendar day instead of UTC must fail."""
    response = await client.post(
        "/api/runs",
        json={
            "id": "timezone-report-run",
            "name": "timezone-report-run",
            "status": "completed",
            "start_time": "2026-08-10T23:00:00-03:00",
        },
    )
    assert response.status_code == 201

    await _create_cost_trace(
        client,
        run_id="timezone-report-run",
        span_id="west-of-utc",
        start_time="2026-08-10T23:30:00-03:00",
        cost_usd=0.01,
        prompt_tokens=10,
        completion_tokens=5,
        duration_ms=100.0,
        prompt_version="timezone-v1",
    )
    await _create_cost_trace(
        client,
        run_id="timezone-report-run",
        span_id="east-of-utc",
        start_time="2026-08-11T04:30:00+03:00",
        cost_usd=0.02,
        prompt_tokens=20,
        completion_tokens=10,
        duration_ms=200.0,
        prompt_version="timezone-v1",
    )

    report = await client.get(
        "/api/costs/reports/daily?prompt_version=timezone-v1&format=json"
    )
    assert report.status_code == 200
    assert list(report.json()["days"]) == ["2026-08-11"]
    assert report.json()["days"]["2026-08-11"]["total_requests"] == 2

    prior_day = await client.get(
        "/api/costs/reports/daily?day=2026-08-10"
        "&prompt_version=timezone-v1&format=json"
    )
    assert prior_day.status_code == 200
    assert prior_day.json()["days"] == {}


@pytest.mark.asyncio
async def test_budget_lifecycle(client: AsyncClient) -> None:
    # Create
    create_resp = await client.post(
        "/api/budgets",
        json={
            "name": "Test Budget",
            "scope": "global",
            "limit_usd": 10.0,
            "period": "monthly",
            "alert_threshold_pct": 80,
        },
    )
    assert create_resp.status_code == 201
    budget = create_resp.json()
    budget_id = budget["id"]

    # List
    list_resp = await client.get("/api/budgets")
    assert list_resp.status_code == 200
    budgets = list_resp.json()
    assert any(b["id"] == budget_id for b in budgets)

    # Status
    status_resp = await client.get(f"/api/budgets/{budget_id}/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert status["budget_id"] == budget_id
    assert "percent_used" in status

    # Delete
    del_resp = await client.delete(f"/api/budgets/{budget_id}")
    assert del_resp.status_code == 204

    # Verify gone
    get_resp = await client.get(f"/api/budgets/{budget_id}")
    assert get_resp.status_code == 404
