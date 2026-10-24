"""Regression protection for durable, safe collector delivery."""

from app.models.trace import Trace
from sqlalchemy import func, select


def payload(span_id="delivery-one", run_id="delivery-run", **changes):
    value = {
        "run_id": run_id,
        "span_id": span_id,
        "name": "retrieval",
        "span_type": "retrieval",
        "start_time": "2026-10-23T12:00:00Z",
        "status": "completed",
        "cost_usd": 0.002,
        "token_usage": {"total_tokens": 30},
    }
    return value | changes


async def test_identical_delivery_is_idempotent_and_conflict_is_409(client, db_session):
    """A transport retry must not double charge or fail with UNIQUE errors."""
    await client.post("/api/runs", json={"id": "delivery-run", "name": "delivery"})
    first = await client.post("/api/traces", json=payload())
    second = await client.post("/api/traces", json=payload())
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    run = (await client.get("/api/runs/delivery-run")).json()
    assert (run["span_count"], run["total_tokens"], run["total_cost"]) == (1, 30, 0.002)
    assert (
        await db_session.execute(select(func.count()).select_from(Trace))
    ).scalar() == 1
    conflict = await client.post("/api/traces", json=payload(cost_usd=5))
    assert conflict.status_code == 409


async def test_delayed_start_cannot_reopen_or_overwrite_recorded_aggregates(client):
    """Root export ordering cannot undo completion or authoritative spans."""
    await client.post("/api/runs", json={"id": "delivery-run", "name": "delivery"})
    await client.post("/api/traces", json=payload())
    await client.post(
        "/api/runs",
        json={
            "id": "delivery-run",
            "name": "delivery",
            "status": "completed",
            "end_time": "2026-10-23T12:00:01Z",
            "total_cost": 99,
            "span_count": 99,
        },
    )
    response = await client.post(
        "/api/runs",
        json={"id": "delivery-run", "name": "delivery", "status": "running"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert response.json()["span_count"] == 1
    assert response.json()["total_cost"] == 0.002


async def test_credentials_redacted_before_storage_and_historical_presentation(
    client, db_session
):
    """New persisted credentials and old response bodies cannot leak secrets."""
    response = await client.post(
        "/api/traces",
        json=payload(
            input_data={
                "api_key": "private-value",
                "message": "Authorization: Bearer abcdefghijklmno",
            },
            metadata={"cohort_id": "safe-cohort"},
        ),
    )
    assert response.status_code == 201
    stored = (await db_session.execute(select(Trace))).scalar_one()
    assert "private-value" not in str(stored.input_data)
    assert "abcdefghijklmno" not in str(stored.input_data)
    stored.input_data = {"password": "historical-secret"}
    await db_session.flush()
    shown = await client.get(f"/api/traces/{stored.id}")
    assert "historical-secret" not in shown.text
    playback = await client.get("/api/replay/runs/delivery-run")
    assert "historical-secret" not in playback.text


async def test_cohort_filters_runs_statistics_and_costs(client):
    """A selected cohort cannot include another cohort's cost or history."""
    for cohort, amount in [("selected", 0.002), ("other", 1.0)]:
        await client.post(
            "/api/runs",
            json={"id": cohort, "name": cohort, "metadata": {"cohort_id": cohort}},
        )
        await client.post(
            "/api/traces",
            json=payload(
                span_id=cohort,
                run_id=cohort,
                cost_usd=amount,
                metadata={"cohort_id": cohort},
            ),
        )
    assert (await client.get("/api/runs?cohort_id=selected")).json()["total"] == 1
    stats = (await client.get("/api/stats?cohort_id=selected")).json()
    assert stats["total_runs"] == 1
    assert stats["total_cost"] == 0.002
    costs = (await client.get("/api/costs/summary?cohort_id=selected")).json()
    assert costs["total_spans"] == 1
    assert costs["total_cost"] == 0.002


async def test_diff_aligns_repeated_stages_and_revision_compatibility(client):
    """Repeated stage names must not collapse to the first matching span."""
    for run in ["before", "after"]:
        await client.post(
            "/api/runs",
            json={
                "id": run,
                "name": run,
                "metadata": {"scenario_revision": "revision-one"},
            },
        )
        for occurrence in [1, 2]:
            await client.post(
                "/api/traces",
                json=payload(
                    span_id=f"{run}-{occurrence}",
                    run_id=run,
                    metadata={"stage_key": "retrieve", "occurrence": occurrence},
                    status="error"
                    if run == "before" and occurrence == 2
                    else "completed",
                ),
            )
    result = (await client.get("/api/diff/runs?run_id_1=before&run_id_2=after")).json()
    assert len(result["aligned_stages"]) == 2
    assert result["aligned_stages"][1]["status_1"] == "error"
    assert result["aligned_stages"][1]["status_2"] == "completed"
    assert result["compatibility"]["compatible"] is True


async def test_ingestion_cursor_follows_delivery_not_span_start_time(client):
    """A late exported span must remain resumable despite its earlier start."""
    recent = await client.post(
        "/api/traces", json=payload(span_id="recent", start_time="2026-10-23T13:00:00Z")
    )
    late = await client.post(
        "/api/traces", json=payload(span_id="late", start_time="2026-10-23T11:00:00Z")
    )
    assert "delivery_cursor" in recent.json()
    assert late.json()["delivery_cursor"] > recent.json()["delivery_cursor"]


async def test_genai_json_attributes_retain_provider_model_usage(client):
    """The actual SDK GenAI mapping must not lose cost or usage in the collector."""
    attrs = {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "synthetic",
        "gen_ai.request.model": "request-model",
        "gen_ai.response.model": "response-model",
        "gen_ai.usage.input_tokens": 7,
        "gen_ai.usage.output_tokens": 3,
        "span.type": "llm_call",
        "cost.usd": 0.001,
    }
    span = {
        "traceId": "genai-run",
        "spanId": "genai-span",
        "name": "generate",
        "startTimeUnixNano": "1792756800000000000",
        "attributes": [
            {
                "key": key,
                "value": {"intValue": str(value)}
                if isinstance(value, int)
                else {"doubleValue": value}
                if isinstance(value, float)
                else {"stringValue": value},
            }
            for key, value in attrs.items()
        ],
        "status": {"code": 1},
    }
    response = await client.post(
        "/api/otlp/v1/traces",
        json={"resourceSpans": [{"scopeSpans": [{"spans": [span]}]}]},
    )
    assert response.status_code == 200
    trace = (await client.get("/api/runs/genai-run/spans")).json()[0]
    assert trace["provider"] == "synthetic"
    assert trace["model"] == "response-model"
    assert trace["token_usage"] == {
        "prompt_tokens": 7,
        "completion_tokens": 3,
        "total_tokens": 10,
    }
    assert trace["cost_usd"] == 0.001


async def test_final_root_before_first_span_does_not_double_count(client):
    """Bounded export may deliver a terminal root before its buffered spans."""
    await client.post(
        "/api/runs",
        json={
            "id": "delivery-run",
            "name": "root-first",
            "status": "completed",
            "span_count": 1,
            "total_cost": 0.002,
            "total_tokens": 30,
        },
    )
    await client.post("/api/traces", json=payload())
    run = (await client.get("/api/runs/delivery-run")).json()
    assert (run["span_count"], run["total_tokens"], run["total_cost"]) == (1, 30, 0.002)


async def test_durable_resume_reads_late_spans_and_legacy_ids(client, db_session):
    """The cursor resumes actual storage insertion order, including old starts."""
    from app.api.stream import read_events, resolve_cursor

    first = (
        await client.post(
            "/api/traces",
            json=payload(
                span_id="first",
                start_time="2026-10-23T13:00:00Z",
                metadata={"cohort_id": "selected"},
            ),
        )
    ).json()
    late = (
        await client.post(
            "/api/traces",
            json=payload(
                span_id="late",
                start_time="2026-10-23T11:00:00Z",
                metadata={"cohort_id": "selected"},
            ),
        )
    ).json()
    await client.post(
        "/api/traces", json=payload(span_id="other", metadata={"cohort_id": "other"})
    )
    cursor = await resolve_cursor(db_session, last_id=first["id"])
    assert cursor == first["delivery_cursor"]
    events = await read_events(db_session, cursor, "selected")
    assert [event["id"] for event in events] == [late["id"]]
    assert events[0]["delivery_cursor"] > cursor
    assert await resolve_cursor(db_session, cursor=str(cursor)) == cursor


async def test_migration_preserves_historical_rows_and_backfills_cursor(tmp_path):
    """Startup adds tables/cursors without rewriting historical trace content."""
    from app.db import Base, _repair_sqlite_schema
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    database = tmp_path / "legacy.db"
    legacy_engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    try:
        async with legacy_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("DROP TABLE portfolio_executions"))
            await conn.execute(text("DROP TABLE ingestion_events"))
            await conn.execute(
                text(
                    "INSERT INTO runs "
                    "(id,name,status,start_time,total_cost,total_tokens,span_count) "
                    "VALUES ('legacy','historical','completed','2026-01-01',0.1,12,1)"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO traces "
                    "(id,run_id,span_id,span_type,name,start_time,status,sampled,"
                    "trace_metadata) VALUES ('old-trace','legacy','old-span',"
                    "'custom','old','2026-01-01','completed',1,NULL)"
                )
            )
        async with legacy_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_repair_sqlite_schema)
            await conn.run_sync(_repair_sqlite_schema)
            assert (
                await conn.execute(
                    text("SELECT name,total_tokens FROM runs WHERE id='legacy'")
                )
            ).one() == ("historical", 12)
            assert (
                await conn.execute(
                    text("SELECT trace_id,payload_hash FROM ingestion_events")
                )
            ).one() == ("old-trace", None)
            assert (
                await conn.execute(text("SELECT COUNT(*) FROM traces"))
            ).scalar() == 1
    finally:
        await legacy_engine.dispose()
    # Real close: Windows permits deleting the fresh database without GC hacks.
    database.unlink()


async def test_concurrent_root_creation_is_idempotent(client):
    """Concurrent root exports cannot surface UNIQUE errors to the SDK."""
    import asyncio

    from app.db import get_session
    from app.main import app

    from tests.conftest import test_session_factory

    async def separate_session():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = separate_session
    body = {"id": "racing-root", "name": "racing", "start_time": "2026-10-23T12:00:00Z"}
    responses = await asyncio.gather(
        *(client.post("/api/runs", json=body) for _ in range(20)),
        return_exceptions=True,
    )
    assert all(
        not isinstance(response, BaseException) and response.status_code == 201
        for response in responses
    )
    assert (await client.get("/api/runs")).json()["total"] == 1


async def test_duplicate_spans_in_one_batch_publish_once(client, monkeypatch):
    """A duplicated batch entry cannot emit duplicate live notifications."""
    import app.api.traces as routes

    published = []

    async def publish(value):
        published.append(value)

    monkeypatch.setattr(routes, "broadcast_trace", publish)
    response = await client.post("/api/traces/batch", json=[payload(), payload()])
    assert response.status_code == 201
    assert response.json()[0]["id"] == response.json()[1]["id"]
    assert len(published) == 1


async def test_conflicting_batch_rolls_back_all_new_rows(client):
    """SQLite savepoints must not commit a first row before batch validation."""
    from app.db import get_session
    from app.main import app

    from tests.conftest import test_session_factory

    async def separate_session():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = separate_session
    response = await client.post(
        "/api/traces/batch", json=[payload(), payload(cost_usd=99)]
    )
    assert response.status_code == 409
    assert (await client.get("/api/traces")).json() == []


async def test_otlp_root_retains_cancellation_and_cohort_metadata(client):
    """OTLP terminal root semantics cannot become a permanently running run."""
    import json

    attrs = {
        "run.status": "cancelled",
        "run.name": "cancelled request",
        "run.correlation_id": "correlation-proof",
        "agenttrace.metadata": json.dumps(
            {
                "cohort_id": "otlp-cohort",
                "case_id": "request-20",
                "api_key": "hidden-secret",
            }
        ),
    }
    span = {
        "traceId": "otlp-cancelled",
        "spanId": "otlp-root",
        "name": "run:cancelled",
        "startTimeUnixNano": "1792756800000000000",
        "endTimeUnixNano": "1792756800100000000",
        "attributes": [
            {"key": key, "value": {"stringValue": value}}
            for key, value in attrs.items()
        ],
        "status": {"code": 1},
    }
    response = await client.post(
        "/api/otlp/v1/traces",
        json={"resourceSpans": [{"scopeSpans": [{"spans": [span]}]}]},
    )
    assert response.status_code == 200
    run = (await client.get("/api/runs/otlp-cancelled")).json()
    assert run["status"] == "cancelled"
    assert run["correlation_id"] == "correlation-proof"
    assert run["metadata"]["cohort_id"] == "otlp-cohort"
    assert "hidden-secret" not in str(run)


async def test_ingestion_cannot_acknowledge_before_storage_commit(
    client, db_session, monkeypatch
):
    """A failed SQLite commit must produce failure rather than a successful ACK."""
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    async def broken_commit():
        raise RuntimeError("injected storage commit failure")

    monkeypatch.setattr(db_session, "commit", broken_commit)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as request:
        response = await request.post("/api/traces", json=payload())
    assert response.status_code == 500


async def test_cohort_live_filter_uses_run_metadata_when_span_has_none(
    client, db_session
):
    """Run-only cohort producers must agree across history and live delivery."""
    from app.api.stream import read_events

    await client.post(
        "/api/runs",
        json={
            "id": "delivery-run",
            "name": "run-only cohort",
            "metadata": {"cohort_id": "selected"},
        },
    )
    response = await client.post("/api/traces", json=payload())
    events = await read_events(db_session, 0, "selected")
    assert [item["id"] for item in events] == [response.json()["id"]]


async def test_historical_identical_retry_uses_saved_content_without_new_effects(
    client, db_session
):
    """A pre-upgrade trace with unknown original hash can still be retried safely."""
    from app.models.delivery import IngestionEvent

    await client.post("/api/traces", json=payload())
    event = (await db_session.execute(select(IngestionEvent))).scalar_one()
    event.payload_hash = None
    await db_session.commit()
    response = await client.post("/api/traces", json=payload())
    assert response.status_code == 201
    assert (
        await db_session.execute(select(func.count()).select_from(Trace))
    ).scalar() == 1


async def test_diff_redacts_historical_names_without_rewriting_storage(
    client, db_session
):
    """Comparison must enforce the same historical credential presentation policy."""
    from datetime import datetime

    from app.models.run import Run

    for run_id in ("old-one", "old-two"):
        db_session.add(
            Run(id=run_id, name="Bearer historicalsecret123456", status="completed")
        )
        db_session.add(
            Trace(
                run_id=run_id,
                span_id=run_id,
                span_type="custom",
                name="Bearer historicalsecret123456",
                start_time=datetime(2026, 10, 23),
                status="completed",
                trace_metadata={"stage_key": "Bearer historicalsecret123456"},
            )
        )
    await db_session.commit()
    response = await client.get("/api/diff/runs?run_id_1=old-one&run_id_2=old-two")
    assert response.status_code == 200
    assert "historicalsecret123456" not in response.text
    assert (
        await db_session.get(Run, "old-one")
    ).name == "Bearer historicalsecret123456"


async def test_diff_normalizes_invalid_ordinals_without_collapsing_stages(
    client, db_session
):
    """Accepted arbitrary metadata must not crash or merge repeated stages."""
    from datetime import datetime

    from app.models.run import Run

    values = [None, "invalid", True, -1, 10**30, 1, 1]
    for run_id in ("ordinals-one", "ordinals-two"):
        db_session.add(Run(id=run_id, name=run_id, status="completed"))
        for index, value in enumerate(values):
            db_session.add(
                Trace(
                    run_id=run_id,
                    span_id=f"{run_id}-{index}",
                    span_type="retrieval",
                    name="retrieve",
                    start_time=datetime(2026, 10, 23, 12, 0, index),
                    status="completed",
                    trace_metadata={
                        "stage_key": "retrieve",
                        "occurrence": value,
                        "attempt": value,
                    },
                )
            )
    await db_session.commit()
    response = await client.get(
        "/api/diff/runs?run_id_1=ordinals-one&run_id_2=ordinals-two"
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["aligned_stages"]) == len(values)
    assert result["unmatched_stages"] == {"only_in_run1": [], "only_in_run2": []}
    assert all(
        1 <= item["occurrence"] <= 1000000 and 1 <= item["attempt"] <= 1000000
        for item in result["aligned_stages"]
    )


async def test_cost_presentation_redacts_historical_labels_and_preserves_totals(
    client, db_session
):
    """Every connected cost read surface must hide historical credential labels."""
    from datetime import datetime, timezone

    from app.models.run import Run

    secrets = ("historicalcostsecret111111", "historicalcostsecret222222")
    for index, secret in enumerate(secrets):
        label = "Bearer " + secret
        run_id = f"cost-history-{index}"
        db_session.add(
            Run(
                id=run_id,
                name=label,
                status="completed",
                total_cost=0.01 * (index + 1),
                run_metadata={"cohort_id": "old-costs"},
            )
        )
        db_session.add(
            Trace(
                run_id=run_id,
                span_id=run_id,
                span_type="llm_call",
                name="old",
                start_time=datetime.now(timezone.utc),
                status="completed",
                model=label,
                provider=label,
                feature=label,
                cost_usd=0.01 * (index + 1),
                trace_metadata={"prompt_version": label},
            )
        )
    await db_session.commit()
    for path in (
        "/api/costs/summary",
        "/api/costs/summary?cohort_id=old-costs",
        "/api/costs/by-model",
        "/api/costs/by-provider",
        "/api/costs/by-feature",
        "/api/costs/top-runs",
        "/api/costs/timeseries",
        "/api/costs/projection",
        "/api/costs/reports/daily",
        "/api/costs/reports/daily?format=csv",
    ):
        response = await client.get(path)
        assert response.status_code == 200
        assert all(secret not in response.text for secret in secrets), path
    summary = (await client.get("/api/costs/summary")).json()
    assert summary["total_cost"] == 0.03
    assert len(summary["by_model"]) == 2
    assert sum(summary["by_model"].values()) == 0.03
    models = (await client.get("/api/costs/by-model")).json()
    assert len(models) == 2
    assert sum(item["total_cost"] for item in models) == 0.03
    assert (await db_session.get(Run, "cost-history-0")).name == "Bearer " + secrets[0]
