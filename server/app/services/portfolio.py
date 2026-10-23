"""Durable local execution of the SDK's fixed, credential-free workload."""

from __future__ import annotations

import asyncio
import importlib
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select, update

from app.config import settings
from app.db import async_session_factory
from app.models.delivery import PortfolioExecution
from app.models.run import Run
from app.models.trace import Trace

_tasks: set[asyncio.Task] = set()
logger = logging.getLogger(__name__)


def workload_module():
    """Keep SDK optional for collectors that only receive external traces."""
    return importlib.import_module("agenttrace.portfolio")


def readiness() -> dict[str, Any]:
    enabled = settings.PORTFOLIO_LAUNCH_ENABLED
    reason = "Set PORTFOLIO_LAUNCH_ENABLED=true for the local bundled launcher."
    try:
        module = workload_module()
        scenarios = module.list_scenarios()
    except (ImportError, AttributeError):
        return {
            "enabled": enabled,
            "ready": False,
            "reason": "Install the AgentTrace 0.2.0 SDK to launch bundled workloads.",
            "scenarios": [],
        }
    address = urlsplit(settings.PORTFOLIO_COLLECTOR_URL)
    local = (
        address.scheme == "http"
        and address.hostname in {"127.0.0.1", "localhost", "::1"}
        and address.path in {"", "/"}
        and not address.username
        and not address.password
        and not address.query
        and not address.fragment
    )
    ready = (
        enabled
        and local
        and (not settings.AUTH_REQUIRED or bool(settings.PORTFOLIO_AUTH_TOKEN))
    )
    if enabled and not local:
        reason = "Local launches require a configured loopback HTTP collector URL."
    elif enabled and settings.AUTH_REQUIRED and not settings.PORTFOLIO_AUTH_TOKEN:
        reason = "Authenticated launches require a configured internal ingestor token."
    elif ready:
        reason = "Ready; provider responses, usage and prices are synthetic."
    return {
        "enabled": enabled,
        "ready": ready,
        "reason": reason,
        "scenarios": scenarios,
    }


async def recover_interrupted() -> None:
    """Release only abandoned launch slots; never redispatch side effects."""
    async with async_session_factory() as session:
        await session.execute(
            update(PortfolioExecution)
            .where(PortfolioExecution.active_slot == 1)
            .values(
                status="interrupted",
                active_slot=None,
                error="Restart interrupted execution. Explicit new launch required.",
                delivery={"complete": False, "unfinished": None},
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()


def start_execution(execution_id: str) -> None:
    task = asyncio.create_task(_execute(execution_id))
    _tasks.add(task)
    task.add_done_callback(_finished)


def _finished(task: asyncio.Task) -> None:
    _tasks.discard(task)
    if not task.cancelled():
        error = task.exception()
        if error is not None:
            logger.error(
                "Execution state could not be persisted; restart recovery required",
                exc_info=(type(error), error, error.__traceback__),
            )


async def stop_executions() -> None:
    pending = tuple(_tasks)
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


async def _execute(execution_id: str) -> None:
    progress_lock = asyncio.Lock()

    async def progress(completed_count: int, run_id: str, outcome: str) -> None:
        async with progress_lock:
            async with async_session_factory() as session:
                job = await session.get(PortfolioExecution, execution_id)
                if job is None or job.active_slot is None:
                    return
                job.completed = max(job.completed, completed_count)
                job.run_ids = list(dict.fromkeys([*job.run_ids, run_id]))
                counts = dict(job.application_outcomes)
                key = (
                    "cancelled"
                    if outcome == "cancelled"
                    else "completed"
                    if outcome == "completed"
                    else "failed"
                )
                counts[key] = counts.get(key, 0) + 1
                job.application_outcomes = counts
                job.updated_at = datetime.now(timezone.utc)
                await session.commit()

    try:
        async with async_session_factory() as session:
            job = await session.get(PortfolioExecution, execution_id)
            if job is None:
                return
            job.status = "running"
            scenario, cohort_id = job.scenario, job.cohort_id
            await session.commit()
        exporter = None
        if settings.PORTFOLIO_AUTH_TOKEN:
            api_exporter = importlib.import_module("agenttrace.exporters.api_exporter")
            exporter = api_exporter.APIExporter(
                endpoint=settings.PORTFOLIO_COLLECTOR_URL.rstrip("/") + "/api/traces",
                buffer_size=16,
                headers={"Authorization": "Bearer " + settings.PORTFOLIO_AUTH_TOKEN},
            )
        result = await workload_module().run_workload(
            scenario,
            endpoint=settings.PORTFOLIO_COLLECTOR_URL,
            exporter=exporter,
            cohort_id=cohort_id,
            progress=progress,
        )
        async with async_session_factory() as session:
            job = await session.get(PortfolioExecution, execution_id)
            if job is None:
                return
            job.run_ids = result["run_ids"]
            job.completed = len(job.run_ids)
            job.application_outcomes = result["application_outcomes"]
            job.delivery = result["delivery"]
            recorded = (
                (
                    await session.execute(
                        select(Run).where(
                            Run.run_metadata["cohort_id"].as_string() == cohort_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            spans = (
                (
                    await session.execute(
                        select(Trace).where(Trace.run_id.in_(job.run_ids))
                    )
                )
                .scalars()
                .all()
            )
            complete = _complete_recording(job, recorded, spans)
            job.delivery = {
                **job.delivery,
                "complete": complete,
                "recorded_runs": len(recorded),
                "recorded_spans": len(spans),
            }
            job.status = "completed" if complete else "failed"
            job.error = (
                None
                if complete
                else "Telemetry incomplete; inspect partial traces before a new launch."
            )
            job.active_slot = None
            job.updated_at = datetime.now(timezone.utc)
            await session.commit()
    except BaseException as exc:
        if not isinstance(exc, asyncio.CancelledError):
            logger.exception("Bundled execution infrastructure failed")
        async with async_session_factory() as session:
            job = await session.get(PortfolioExecution, execution_id)
            if job is not None:
                job.status = (
                    "interrupted"
                    if isinstance(exc, asyncio.CancelledError)
                    else "failed"
                )
                job.error = (
                    "Execution interrupted; partial traces retained."
                    if isinstance(exc, asyncio.CancelledError)
                    else "Execution failed; inspect logs and partial telemetry."
                )
                job.delivery = {**job.delivery, "complete": False}
                job.active_slot = None
                job.updated_at = datetime.now(timezone.utc)
                await session.commit()
        if isinstance(exc, asyncio.CancelledError):
            raise


def _complete_recording(job, recorded, spans):
    """Check fixed scenario contracts against storage, independently of delivery."""
    expected_counts = {
        "completed": 17 if job.scenario == "incident" else 18,
        "failed": 2 if job.scenario == "incident" else 1,
        "cancelled": 1,
    }
    by_case = {(run.run_metadata or {}).get("case_id"): run for run in recorded}
    if (
        not job.delivery.get("complete")
        or len(recorded) != 20
        or len(by_case) != 20
        or set(job.run_ids) != {run.id for run in recorded}
        or job.application_outcomes != expected_counts
    ):
        return False
    for index in range(1, 21):
        run = by_case.get(f"request-{index:02d}")
        retrieval_failed = index == 18 and job.scenario == "incident"
        expected_status = (
            "cancelled"
            if index == 20
            else "failed"
            if index == 19 or retrieval_failed
            else "completed"
        )
        expected_stages = (
            {"retrieve"}
            if retrieval_failed
            else {"retrieve", "answer"}
            if index >= 19
            else {"retrieve", "answer", "validate"}
        )
        if run is None or run.status != expected_status:
            return False
        case_spans = [span for span in spans if span.run_id == run.id]
        if (
            run.span_count != len(case_spans)
            or abs(run.total_cost - sum(span.cost_usd or 0 for span in case_spans))
            > 1e-9
            or run.total_tokens
            != sum(
                (span.token_usage or {}).get("total_tokens", 0) for span in case_spans
            )
        ):
            return False
        actual_stages = [
            (span.trace_metadata or {}).get("stage_key") for span in case_spans
        ]
        if (
            len(actual_stages) != len(expected_stages)
            or set(actual_stages) != expected_stages
            or any(
                span.status not in {"completed", "error", "cancelled"}
                for span in case_spans
            )
        ):
            return False
    return True
