"""Trace service — business logic for trace and run operations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run, RunListResponse, RunResponse
from app.models.trace import Trace, TraceCreate, TraceResponse


class TraceService:
    """Service layer for trace ingestion, querying, and analytics.

    Encapsulates business logic for working with runs and traces,
    including cost calculation and token aggregation.

    Args:
        session: Async SQLAlchemy session for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ingest_trace(self, trace_data: TraceCreate) -> Trace:
        """Ingest a new trace record and update run stats incrementally.

        Args:
            trace_data: Validated trace creation payload.

        Returns:
            The persisted Trace record.
        """
        trace = Trace(
            id=str(uuid.uuid4()),
            run_id=trace_data.run_id,
            span_id=trace_data.span_id,
            parent_span_id=trace_data.parent_span_id,
            span_type=trace_data.span_type,
            name=trace_data.name,
            input_data=trace_data.input_data,
            output_data=trace_data.output_data,
            trace_metadata=trace_data.metadata,
            start_time=trace_data.start_time,
            end_time=trace_data.end_time,
            duration_ms=trace_data.duration_ms,
            cost_usd=trace_data.cost_usd,
            token_usage=trace_data.token_usage,
            status=trace_data.status,
            error=trace_data.error,
            model=trace_data.model,
            provider=trace_data.provider,
            feature=trace_data.feature,
        )
        self._session.add(trace)
        await self._session.flush()

        # Increment run stats atomically
        await self._increment_run_stats(
            run_id=trace_data.run_id,
            cost=trace_data.cost_usd or 0.0,
            tokens=(trace_data.token_usage or {}).get("total_tokens", 0),
        )
        return trace

    async def ingest_traces_batch(self, trace_data_list: list[TraceCreate]) -> list[Trace]:
        """Ingest multiple traces and update run stats incrementally.

        Args:
            trace_data_list: List of validated trace creation payloads.

        Returns:
            The persisted Trace records.
        """
        traces: list[Trace] = []
        run_deltas: dict[str, tuple[float, int]] = {}

        for trace_data in trace_data_list:
            trace = Trace(
                id=str(uuid.uuid4()),
                run_id=trace_data.run_id,
                span_id=trace_data.span_id,
                parent_span_id=trace_data.parent_span_id,
                span_type=trace_data.span_type,
                name=trace_data.name,
                input_data=trace_data.input_data,
                output_data=trace_data.output_data,
                trace_metadata=trace_data.metadata,
                start_time=trace_data.start_time,
                end_time=trace_data.end_time,
                duration_ms=trace_data.duration_ms,
                cost_usd=trace_data.cost_usd,
                token_usage=trace_data.token_usage,
                status=trace_data.status,
                error=trace_data.error,
                model=trace_data.model,
                provider=trace_data.provider,
                feature=trace_data.feature,
            )
            self._session.add(trace)
            traces.append(trace)

            # Aggregate deltas per run
            cost = trace_data.cost_usd or 0.0
            tokens = (trace_data.token_usage or {}).get("total_tokens", 0)
            prev_cost, prev_tokens, prev_count = run_deltas.get(trace_data.run_id, (0.0, 0, 0))
            run_deltas[trace_data.run_id] = (prev_cost + cost, prev_tokens + tokens, prev_count + 1)

        await self._session.flush()

        # Apply incremental updates per run
        for run_id, (cost_delta, token_delta, count_delta) in run_deltas.items():
            await self._increment_run_stats(run_id, cost_delta, token_delta, count_delta)

        return traces

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
        stmt = (
            select(Run)
            .where(Run.id == run_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        run = result.scalar_one_or_none()
        if run is not None:
            run.total_cost += cost
            run.total_tokens += tokens
            run.span_count += count

    async def get_run_traces(self, run_id: str) -> list[Trace]:
        """Retrieve all traces for a given run.

        Args:
            run_id: The run identifier.

        Returns:
            List of Trace records ordered by start_time.
        """
        stmt = (
            select(Trace)
            .where(Trace.run_id == run_id)
            .order_by(Trace.start_time.asc())
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

    async def list_runs(
        self, limit: int = 20, offset: int = 0
    ) -> RunListResponse:
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
