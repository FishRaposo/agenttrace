"""Explicit launches of bundled SDK scenarios; never browser-supplied code."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.internal.rbac import Role
from app.models.delivery import PortfolioExecution
from app.services import portfolio

router = APIRouter()


class LaunchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["incident", "repaired"]
    request_id: uuid.UUID


@router.get("/portfolio/scenarios", dependencies=[Depends(require_roles(Role.VIEWER))])
async def scenarios() -> dict:
    return portfolio.readiness()


@router.post(
    "/portfolio/executions",
    status_code=202,
    dependencies=[Depends(require_roles(Role.INGESTOR, Role.ADMIN))],
)
async def launch(
    body: LaunchRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    existing = (
        await session.execute(
            select(PortfolioExecution).where(
                PortfolioExecution.request_id == str(body.request_id)
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.scenario != body.scenario:
            raise HTTPException(
                409,
                {
                    "message": "Request ID already used for a different scenario",
                    "active_execution_id": existing.id,
                },
            )
        return existing.response()
    info = portfolio.readiness()
    if not info["ready"]:
        raise HTTPException(503, info["reason"])
    now = datetime.now(timezone.utc)
    job = PortfolioExecution(
        id=str(uuid.uuid4()),
        request_id=str(body.request_id),
        scenario=body.scenario,
        status="queued",
        active_slot=1,
        cohort_id=str(uuid.uuid4()),
        completed=0,
        total=20,
        run_ids=[],
        application_outcomes={},
        delivery={"complete": False},
        created_at=now,
        updated_at=now,
    )
    try:
        session.add(job)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        duplicate = (
            await session.execute(
                select(PortfolioExecution).where(
                    PortfolioExecution.request_id == str(body.request_id)
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None and duplicate.scenario == body.scenario:
            return duplicate.response()
        active = (
            await session.execute(
                select(PortfolioExecution).where(PortfolioExecution.active_slot == 1)
            )
        ).scalar_one_or_none()
        raise HTTPException(
            409,
            {
                "message": "An execution is active or the request ID conflicts",
                "active_execution_id": active.id
                if active
                else duplicate.id
                if duplicate
                else None,
            },
        ) from None
    response = job.response()
    portfolio.start_execution(job.id)
    return response


@router.get(
    "/portfolio/executions/{execution_id}",
    dependencies=[Depends(require_roles(Role.VIEWER))],
)
async def execution(
    execution_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    job = await session.get(PortfolioExecution, execution_id, populate_existing=True)
    if job is None:
        raise HTTPException(404, "Execution not found")
    return job.response()
