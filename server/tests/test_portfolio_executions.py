"""Local workload launch boundaries, durable reservation and recovery."""

import uuid
from types import SimpleNamespace

from app.config import settings
from app.models.delivery import PortfolioExecution
from app.models.run import Run
from app.models.trace import Trace
from app.services import portfolio

from tests.conftest import test_session_factory as session_factory


async def test_launcher_is_explicitly_disabled_by_default(client):
    response = await client.get("/api/portfolio/scenarios")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["ready"] is False
    response = await client.post(
        "/api/portfolio/executions",
        json={"scenario": "incident", "request_id": str(uuid.uuid4())},
    )
    assert response.status_code == 503


async def test_launcher_rejects_untrusted_paths_and_invalid_request_ids(client):
    response = await client.post(
        "/api/portfolio/executions",
        json={
            "scenario": "../../scripts/custom.py",
            "request_id": "not-a-uuid",
            "code": "unsafe",
        },
    )
    assert response.status_code == 422


async def test_missing_telemetry_prevents_complete_delivery_claim(
    db_session, monkeypatch
):
    """Transport success cannot substitute for the complete persisted workload."""
    from datetime import datetime

    cohort = str(uuid.uuid4())
    job = PortfolioExecution(
        id="partial-job",
        request_id=str(uuid.uuid4()),
        scenario="incident",
        status="queued",
        active_slot=1,
        cohort_id=cohort,
        completed=0,
        total=20,
        run_ids=[],
        application_outcomes={},
        delivery={},
    )
    db_session.add(job)
    ids = []
    for index in range(20):
        run_id = f"partial-{index}"
        ids.append(run_id)
        db_session.add(
            Run(
                id=run_id,
                name=run_id,
                status="completed",
                run_metadata={
                    "cohort_id": cohort,
                    "case_id": f"request-{index + 1:02d}",
                },
            )
        )
    db_session.add(
        Trace(
            run_id=ids[0],
            span_id="partial-span",
            name="retrieve",
            span_type="retrieval",
            start_time=datetime(2026, 10, 23),
            status="completed",
        )
    )
    await db_session.commit()

    async def transport_success(*args, **kwargs):
        return {
            "run_ids": ids,
            "application_outcomes": {"completed": 17, "failed": 2, "cancelled": 1},
            "delivery": {"complete": True, "unfinished": 0},
        }

    monkeypatch.setattr(portfolio, "async_session_factory", session_factory)
    monkeypatch.setattr(
        portfolio,
        "workload_module",
        lambda: SimpleNamespace(run_workload=transport_success),
    )
    await portfolio._execute("partial-job")
    await db_session.refresh(job)
    assert job.status == "failed"
    assert job.delivery["complete"] is False


async def test_launch_deduplication_conflicts_and_restart_recovery(client, monkeypatch):
    """Reservation identity survives retries; restart never reruns the workload."""
    monkeypatch.setattr(settings, "PORTFOLIO_LAUNCH_ENABLED", True)
    scheduled = []
    monkeypatch.setattr(portfolio, "start_execution", scheduled.append)
    body = {"scenario": "incident", "request_id": str(uuid.uuid4())}
    first = await client.post("/api/portfolio/executions", json=body)
    assert first.status_code == 202
    job_id = first.json()["id"]
    duplicate = await client.post("/api/portfolio/executions", json=body)
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == job_id
    conflict = await client.post(
        "/api/portfolio/executions", json={**body, "scenario": "repaired"}
    )
    assert conflict.status_code == 409
    competing = await client.post(
        "/api/portfolio/executions",
        json={"scenario": "incident", "request_id": str(uuid.uuid4())},
    )
    assert competing.status_code == 409
    assert competing.json()["detail"]["active_execution_id"] == job_id
    assert scheduled == [job_id]
    monkeypatch.setattr(portfolio, "async_session_factory", session_factory)
    await portfolio.recover_interrupted()
    after = await client.get(f"/api/portfolio/executions/{job_id}")
    assert after.json()["status"] == "interrupted"
    assert after.json()["delivery"]["complete"] is False
    assert scheduled == [job_id]


async def test_concurrent_launch_reservation_is_database_atomic(client, monkeypatch):
    """Separate HTTP transactions cannot reserve two active execution slots."""
    import asyncio

    from app.db import get_session
    from app.main import app

    async def separate_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = separate_session
    monkeypatch.setattr(settings, "PORTFOLIO_LAUNCH_ENABLED", True)
    scheduled = []
    monkeypatch.setattr(portfolio, "start_execution", scheduled.append)
    responses = await asyncio.gather(
        *(
            client.post(
                "/api/portfolio/executions",
                json={"scenario": "incident", "request_id": str(uuid.uuid4())},
            )
            for _ in range(2)
        )
    )
    assert sorted(response.status_code for response in responses) == [202, 409]
    assert len(scheduled) == 1


async def test_viewer_can_inspect_but_not_launch(client):
    """The local launch path retains existing role authorization."""
    from app.api.auth import User, get_optional_user
    from app.internal.rbac import Role
    from app.main import app

    app.dependency_overrides[get_optional_user] = lambda: User(
        username="viewer", role=Role.VIEWER
    )
    assert (await client.get("/api/portfolio/scenarios")).status_code == 200
    response = await client.post(
        "/api/portfolio/executions",
        json={"scenario": "incident", "request_id": str(uuid.uuid4())},
    )
    assert response.status_code == 403
