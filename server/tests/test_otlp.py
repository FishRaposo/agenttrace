"""Tests for the OTLP-style export/ingest interop endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


async def _create_run_with_span(client: AsyncClient, run_id: str) -> None:
    await client.post(
        "/api/runs",
        json={
            "id": run_id,
            "name": "otlp_run",
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    await client.post(
        "/api/traces",
        json={
            "run_id": run_id,
            "span_id": f"{run_id}-span",
            "span_type": "llm_call",
            "name": "gpt-4o call",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 12.5,
            "cost_usd": 0.003,
            "status": "completed",
            "model": "gpt-4o",
            "provider": "openai",
            "token_usage": {
                "prompt_tokens": 5,
                "completion_tokens": 3,
                "total_tokens": 8,
            },
        },
    )


@pytest.mark.asyncio
async def test_otlp_export_shape(client: AsyncClient) -> None:
    await _create_run_with_span(client, "otlp-export-1")

    resp = await client.get("/api/otlp/v1/traces?run_id=otlp-export-1")
    assert resp.status_code == 200
    doc = resp.json()
    assert "resourceSpans" in doc
    resource = doc["resourceSpans"][0]
    spans = resource["scopeSpans"][0]["spans"]
    assert len(spans) == 1
    span = spans[0]
    assert span["traceId"] == "otlp-export-1"
    assert span["spanId"] == "otlp-export-1-span"
    assert span["status"]["code"] == 1  # OK

    # Cost/model attributes are surfaced as OTLP KeyValue attributes
    keys = {a["key"] for a in span["attributes"]}
    assert "agenttrace.cost_usd" in keys
    assert "llm.model" in keys
    assert "llm.usage.total_tokens" in keys


@pytest.mark.asyncio
async def test_otlp_export_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/otlp/v1/traces")
    assert resp.status_code == 200
    spans = resp.json()["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert spans == []


@pytest.mark.asyncio
async def test_otlp_ingest_round_trip(client: AsyncClient) -> None:
    """Export from one run, push the OTLP doc back, and verify it re-ingests."""
    await _create_run_with_span(client, "otlp-src")
    exported = (await client.get("/api/otlp/v1/traces?run_id=otlp-src")).json()

    # Rewrite the traceId so the push creates a fresh run
    span = exported["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    span["traceId"] = "otlp-dst"
    span["spanId"] = "otlp-dst-span"

    push = await client.post("/api/otlp/v1/traces", json=exported)
    assert push.status_code == 200
    assert push.json()["partialSuccess"]["acceptedSpans"] == 1

    # The re-ingested run preserves the cost verbatim
    run = (await client.get("/api/runs/otlp-dst")).json()
    assert run["total_cost"] == pytest.approx(0.003)


@pytest.mark.asyncio
async def test_otlp_ingest_empty_request(client: AsyncClient) -> None:
    resp = await client.post("/api/otlp/v1/traces", json={"resourceSpans": []})
    assert resp.status_code == 200
    assert resp.json()["partialSuccess"]["acceptedSpans"] == 0


@pytest.mark.asyncio
async def test_otlp_ingest_preserves_resource_scope_events_and_links(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/otlp/v1/traces",
        json={
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "deployment.environment",
                                "value": {"stringValue": "test"},
                            }
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {
                                "name": "fixture.instrumentation",
                                "version": "1.2.3",
                            },
                            "spans": [
                                {
                                    "traceId": "otlp-rich",
                                    "spanId": "otlp-rich-span",
                                    "name": "rich-span",
                                    "startTimeUnixNano": "1700000000000000000",
                                    "endTimeUnixNano": "1700000001000000000",
                                    "events": [
                                        {
                                            "name": "cache.hit",
                                            "timeUnixNano": "1700000000500000000",
                                            "attributes": [],
                                        }
                                    ],
                                    "links": [
                                        {
                                            "traceId": "linked-trace",
                                            "spanId": "linked-span",
                                        }
                                    ],
                                    "attributes": [],
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    )

    assert response.status_code == 200
    stored = (await client.get("/api/traces?run_id=otlp-rich")).json()[0]
    assert stored["metadata"]["otlp.resource.deployment.environment"] == "test"
    assert stored["metadata"]["otlp.scope.name"] == "fixture.instrumentation"
    assert stored["metadata"]["otlp.events"][0]["name"] == "cache.hit"
    assert stored["metadata"]["otlp.links"][0]["traceId"] == "linked-trace"
