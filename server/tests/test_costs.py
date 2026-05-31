"""Tests for cost analytics and budget endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


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
async def test_budget_lifecycle(client: AsyncClient) -> None:
    # Create
    create_resp = await client.post("/api/budgets", json={
        "name": "Test Budget",
        "scope": "global",
        "limit_usd": 10.0,
        "period": "monthly",
        "alert_threshold_pct": 80,
    })
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
