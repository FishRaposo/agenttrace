"""Trace service — business logic for trace and run operations."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capture import bounded, sanitize
from app.db import begin_span_write
from app.internal.sampling import SamplingPolicy
from app.models.delivery import IngestionEvent
from app.models.run import Run, RunListResponse, RunResponse
from app.models.trace import Trace, TraceCreate, TraceResponse


def _normalize_utc(value: datetime | None) -> datetime | None:
    """Normalize aware timestamps before timezone-naive database persistence."""
    if value is None or value.tzinfo is None or value.utcoffset() is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class TraceService:
    """Service layer for trace ingestion, querying, and analytics.

    Encapsulates business logic for working with runs and traces,
    including cost calculation and token aggregation.

    Args:
        session: Async SQLAlchemy session for database operations.
    """

    def __init__(
        self, session: AsyncSession, sampling_policy: SamplingPolicy | None = None
    ) -> None:
        self._session = session
        self._sampling_policy = sampling_policy or SamplingPolicy()
        self.new_trace_ids: set[str] = set()

    def _decision(self, trace_data: TraceCreate):
        return self._sampling_policy.decide(
            # Sampling is a trace/run decision: every span in one run must
            # receive the same deterministic head decision.
            trace_id=trace_data.run_id,
            status=trace_data.status,
            duration_ms=trace_data.duration_ms,
        )

    async def ingest_trace(self, trace_data: TraceCreate) -> Trace:
        """Persist a sanitized span exactly once, with a durable delivery cursor."""
        decision = self._decision(trace_data)
        fingerprint = hashlib.sha256(
            json.dumps(
                trace_data.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        trace = Trace(
            id=str(uuid.uuid4()),
            run_id=trace_data.run_id,
            span_id=trace_data.span_id,
            parent_span_id=trace_data.parent_span_id,
            span_type=trace_data.span_type,
            name=sanitize(trace_data.name),
            input_data=bounded(trace_data.input_data),
            output_data=bounded(trace_data.output_data),
            trace_metadata=bounded(trace_data.metadata),
            start_time=_normalize_utc(trace_data.start_time),
            end_time=_normalize_utc(trace_data.end_time),
            duration_ms=trace_data.duration_ms,
            cost_usd=trace_data.cost_usd,
            token_usage=trace_data.token_usage,
            status=trace_data.status,
            error=sanitize(trace_data.error),
            model=sanitize(trace_data.model),
            provider=sanitize(trace_data.provider),
            feature=sanitize(trace_data.feature),
            sampled=decision.sampled,
            sampling_reason=decision.reason,
        )
        if not decision.sampled:
            return trace
        await begin_span_write(self._session, trace_data.run_id)
        try:
            async with self._session.begin_nested():
                self._session.add(trace)
                await self._session.flush()
        except IntegrityError:
            existing = (
                await self._session.execute(
                    select(Trace).where(Trace.span_id == trace_data.span_id)
                )
            ).scalar_one_or_none()
            if existing is None:
                raise
            event = (
                await self._session.execute(
                    select(IngestionEvent).where(IngestionEvent.trace_id == existing.id)
                )
            ).scalar_one_or_none()
            if event is None or (
                event.payload_hash != fingerprint
                and not (
                    event.payload_hash is None and _same_saved_span(existing, trace)
                )
            ):
                raise HTTPException(409, "Conflicting span_id reuse") from None
            if event.payload_hash is None:
                event.payload_hash = fingerprint
                await self._session.flush()
            existing.delivery_cursor = event.cursor
            return existing
        metadata = trace.trace_metadata or {}
        event = IngestionEvent(
            trace_id=trace.id,
            span_id=trace.span_id,
            payload_hash=fingerprint,
            cohort_id=metadata.get("cohort_id"),
        )
        self._session.add(event)
        await self._session.flush()
        trace.delivery_cursor = event.cursor
        self.new_trace_ids.add(trace.id)
        await self._increment_run_stats(
            trace_data.run_id,
            trace_data.cost_usd or 0.0,
            (trace_data.token_usage or {}).get("total_tokens", 0),
        )
        return trace

    async def ingest_traces_batch(
        self, trace_data_list: list[TraceCreate]
    ) -> list[Trace]:
        """Use the same idempotent boundary for native and adapted batches."""
        return [await self.ingest_trace(item) for item in trace_data_list]

    async def ensure_run_exists(self, run_id: str, name: str | None = None) -> Run:
        """Return the run for ``run_id``, creating a placeholder if missing.

        Used by the cross-service ingestion path: spans emitted by external
        producers (e.g. ``hermes-agent-framework``) carry only a ``trace_id`` and
        may arrive before any explicit run record exists. This lazily materializes
        a ``running`` run so its aggregate stats can accumulate.

        Args:
            run_id: The run identifier (a shared_core ``trace_id``).
            name: Optional human-readable name for a freshly created run.

        Returns:
            The existing or newly created ``Run``.
        """
        run = await self._session.get(Run, run_id)
        if run is not None:
            return run
        run = Run(
            id=run_id,
            name=name or f"ingested-{run_id[:8]}",
            status="running",
        )
        await begin_span_write(self._session, run_id)
        try:
            async with self._session.begin_nested():
                self._session.add(run)
                await self._session.flush()
        except IntegrityError:
            winner = await self._session.get(Run, run_id, populate_existing=True)
            if winner is None:
                raise
            return winner
        return run

    async def ingest_spans(
        self,
        trace_data_list: list[TraceCreate],
        auto_create_runs: bool = True,
    ) -> list[Trace]:
        """Ingest spans from an external producer, optionally creating runs.

        This is the cross-service ingestion entry point used by the OTLP-style
        and shared-span endpoints. It guarantees a run record exists for every
        referenced ``run_id`` before delegating to the standard batch path, so
        aggregate stats are populated even when the producer never created a run.

        Args:
            trace_data_list: Validated trace payloads to ingest.
            auto_create_runs: When True, lazily create missing runs.

        Returns:
            The persisted ``Trace`` records.
        """
        if auto_create_runs:
            seen: set[str] = set()
            for td in trace_data_list:
                if td.run_id not in seen:
                    seen.add(td.run_id)
                    await self.ensure_run_exists(td.run_id, name=td.name)
        return await self.ingest_traces_batch(trace_data_list)

    async def _increment_run_stats(
        self, run_id: str, cost: float, tokens: int, count: int = 1
    ) -> None:
        """Atomically increment run aggregate stats.

        Args:
            run_id: The run to update.
            cost: Cost to add.
            tokens: Tokens to add.
            count: Span count to add (default 1).
        """
        await self._session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(
                total_cost=select(func.coalesce(func.sum(Trace.cost_usd), 0.0))
                .where(Trace.run_id == run_id)
                .scalar_subquery(),
                total_tokens=select(
                    func.coalesce(
                        func.sum(Trace.token_usage["total_tokens"].as_integer()), 0
                    )
                )
                .where(Trace.run_id == run_id)
                .scalar_subquery(),
                span_count=select(func.count())
                .select_from(Trace)
                .where(Trace.run_id == run_id)
                .scalar_subquery(),
            )
        )

    async def get_run_traces(self, run_id: str) -> list[Trace]:
        """Retrieve all traces for a given run.

        Args:
            run_id: The run identifier.

        Returns:
            List of Trace records ordered by start_time.
        """
        stmt = (
            select(Trace).where(Trace.run_id == run_id).order_by(Trace.start_time.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_run_with_spans(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve a run with all its associated spans.

        Args:
            run_id: The run identifier.

        Returns:
            Dictionary with run data and list of spans, or None if not found.
        """
        run_stmt = select(Run).where(Run.id == run_id)
        run_result = await self._session.execute(run_stmt)
        run = run_result.scalar_one_or_none()

        if run is None:
            return None

        spans = await self.get_run_traces(run_id)
        return {
            "run": RunResponse.model_validate(run).model_dump(),
            "spans": [TraceResponse.model_validate(s).model_dump() for s in spans],
        }

    async def list_runs(self, limit: int = 20, offset: int = 0) -> RunListResponse:
        """List runs with pagination.

        Args:
            limit: Maximum number of runs to return.
            offset: Pagination offset.

        Returns:
            Paginated run list response.
        """
        total = (
            await self._session.execute(select(func.count()).select_from(Run))
        ).scalar() or 0

        stmt = select(Run).order_by(Run.start_time.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        runs = list(result.scalars().all())

        return RunListResponse(
            runs=[RunResponse.model_validate(r) for r in runs],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def calculate_run_cost(self, run_id: str) -> float:
        """Calculate the total cost of a run from its traces.

        Args:
            run_id: The run identifier.

        Returns:
            Total cost in USD.
        """
        stmt = select(func.coalesce(func.sum(Trace.cost_usd), 0.0)).where(
            Trace.run_id == run_id
        )
        result = await self._session.execute(stmt)
        return float(result.scalar() or 0.0)

    async def calculate_run_tokens(self, run_id: str) -> dict[str, int]:
        """Aggregate token usage across all spans in a run.

        Args:
            run_id: The run identifier.

        Returns:
            Dictionary with prompt_tokens, completion_tokens, and total_tokens.
        """
        traces = await self.get_run_traces(run_id)
        prompt_tokens = 0
        completion_tokens = 0

        for trace in traces:
            if trace.token_usage:
                prompt_tokens += trace.token_usage.get("prompt_tokens", 0)
                completion_tokens += trace.token_usage.get("completion_tokens", 0)

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    async def list_traces(
        self,
        run_id: Optional[str] = None,
        span_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        cohort_id: str | None = None,
    ) -> list[Trace]:
        """List traces with optional filtering and pagination.

        Args:
            run_id: Optional run ID filter.
            span_type: Optional span type filter.
            limit: Maximum number of traces to return.
            offset: Pagination offset.

        Returns:
            List of Trace records ordered by start_time.
        """
        stmt = select(Trace)
        if run_id is not None:
            stmt = stmt.where(Trace.run_id == run_id)
        if cohort_id is not None:
            stmt = stmt.where(
                Trace.run_id.in_(
                    select(Run.id).where(
                        Run.run_metadata["cohort_id"].as_string() == cohort_id
                    )
                )
            )
        if span_type is not None:
            stmt = stmt.where(Trace.span_type == span_type)
        stmt = stmt.order_by(Trace.start_time.desc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a specific trace by its ID.

        Args:
            trace_id: The unique trace identifier.

        Returns:
            The Trace record or None if not found.
        """
        stmt = select(Trace).where(Trace.id == trace_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


def _same_saved_span(first: Trace, second: Trace) -> bool:
    """Compare migrated rows against their retained safe content, not a made-up hash."""
    fields = (
        "run_id",
        "span_id",
        "parent_span_id",
        "span_type",
        "name",
        "input_data",
        "output_data",
        "trace_metadata",
        "start_time",
        "end_time",
        "duration_ms",
        "cost_usd",
        "token_usage",
        "status",
        "error",
        "model",
        "provider",
        "feature",
    )
    for field in fields:
        left, right = getattr(first, field), getattr(second, field)
        if isinstance(left, datetime):
            left = _normalize_utc(left)
        if isinstance(right, datetime):
            right = _normalize_utc(right)
        if isinstance(left, (dict, list, str)):
            left = bounded(left)
        if isinstance(right, (dict, list, str)):
            right = bounded(right)
        if left != right:
            return False
    return True
