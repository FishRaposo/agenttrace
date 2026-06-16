"""OTLP-style export API — best-effort OpenTelemetry trace interop.

Exposes stored AgentTrace spans in the OTLP/JSON ``ResourceSpans`` shape so the
collector can be scraped by OpenTelemetry-aware tooling, and accepts an OTLP/JSON
``ExportTraceServiceRequest`` push so OTel SDKs can forward spans into AgentTrace.

This is intentionally a *best-effort* subset of the OTLP spec (no protobuf, no
gRPC, nanosecond timestamps as numeric strings, a flat single-scope layout). It
preserves AgentTrace cost/token attribution as OTLP span attributes, and maps
inbound OTLP spans back onto the native ingestion path without recomputing any
numeric values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import User, get_optional_user
from app.db import get_session
from app.models.trace import Trace, TraceCreate
from app.services.trace_service import TraceService

router = APIRouter()

# OTLP status_code enum: 0=UNSET, 1=OK, 2=ERROR.
_OTLP_STATUS = {
    "completed": 1,
    "started": 0,
    "error": 2,
}
_OTLP_STATUS_REVERSE = {1: "completed", 0: "started", 2: "error"}

# OTLP span kind: 1=INTERNAL, 3=CLIENT.
_OTLP_KIND = {"llm_call": 3, "tool_call": 3, "retrieval": 3}


def _to_unix_nano(dt: Optional[datetime]) -> str:
    """Convert a datetime to an OTLP unix-nanosecond string ("0" when absent)."""
    if dt is None:
        return "0"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return str(int(dt.timestamp() * 1_000_000_000))


def _attr(key: str, value: Any) -> dict[str, Any]:
    """Build an OTLP KeyValue attribute, choosing the value type by Python type."""
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)}}


def _trace_to_otlp_span(trace: Trace) -> dict[str, Any]:
    """Render a stored ``Trace`` as an OTLP/JSON span object."""
    attributes: list[dict[str, Any]] = [_attr("agenttrace.span_type", trace.span_type)]
    if trace.cost_usd is not None:
        attributes.append(_attr("agenttrace.cost_usd", trace.cost_usd))
    if trace.model:
        attributes.append(_attr("llm.model", trace.model))
    if trace.provider:
        attributes.append(_attr("llm.provider", trace.provider))
    if trace.feature:
        attributes.append(_attr("agenttrace.feature", trace.feature))
    if trace.token_usage:
        for k, v in trace.token_usage.items():
            if isinstance(v, int):
                attributes.append(_attr(f"llm.usage.{k}", v))

    span: dict[str, Any] = {
        "traceId": trace.run_id,
        "spanId": trace.span_id,
        "name": trace.name,
        "kind": _OTLP_KIND.get(trace.span_type, 1),
        "startTimeUnixNano": _to_unix_nano(trace.start_time),
        "endTimeUnixNano": _to_unix_nano(trace.end_time),
        "attributes": attributes,
        "status": {"code": _OTLP_STATUS.get(trace.status, 0)},
    }
    if trace.parent_span_id:
        span["parentSpanId"] = trace.parent_span_id
    if trace.error:
        span["status"]["message"] = trace.error
    return span


@router.get("/otlp/v1/traces")
async def export_otlp_traces(
    run_id: Optional[str] = Query(None, description="Filter to a single run/trace"),
    limit: int = Query(200, ge=1, le=1000, description="Maximum spans"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Export stored spans in OTLP/JSON ``ResourceSpans`` form (best-effort).

    Args:
        run_id: Optional trace/run filter.
        limit: Maximum spans to include.
        session: Async database session.

    Returns:
        An OTLP ``{"resourceSpans": [...]}`` document.
    """
    stmt = select(Trace)
    if run_id is not None:
        stmt = stmt.where(Trace.run_id == run_id)
    stmt = stmt.order_by(Trace.start_time.asc()).limit(limit)
    result = await session.execute(stmt)
    traces = list(result.scalars().all())

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _attr("service.name", "agenttrace"),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "agenttrace.collector", "version": "0.1.0"},
                        "spans": [_trace_to_otlp_span(t) for t in traces],
                    }
                ],
            }
        ]
    }


class OTLPKeyValue(BaseModel):
    """A single OTLP attribute key/value pair (subset of value types)."""

    key: str
    value: dict[str, Any] = Field(default_factory=dict)


class OTLPSpan(BaseModel):
    """An inbound OTLP/JSON span (best-effort subset)."""

    traceId: str
    spanId: str
    parentSpanId: Optional[str] = None
    name: str = "span"
    kind: int = 1
    startTimeUnixNano: Optional[str] = None
    endTimeUnixNano: Optional[str] = None
    attributes: list[OTLPKeyValue] = Field(default_factory=list)
    status: dict[str, Any] = Field(default_factory=dict)


class OTLPScopeSpans(BaseModel):
    """An OTLP ``scopeSpans`` group."""

    spans: list[OTLPSpan] = Field(default_factory=list)


class OTLPResourceSpans(BaseModel):
    """An OTLP ``resourceSpans`` group."""

    scopeSpans: list[OTLPScopeSpans] = Field(default_factory=list)


class OTLPExportRequest(BaseModel):
    """An OTLP/JSON ``ExportTraceServiceRequest`` (best-effort subset)."""

    resourceSpans: list[OTLPResourceSpans] = Field(default_factory=list)


def _attr_value(kv: OTLPKeyValue) -> Any:
    """Unwrap an OTLP AnyValue into a plain Python value."""
    v = kv.value
    if "stringValue" in v:
        return v["stringValue"]
    if "intValue" in v:
        try:
            return int(v["intValue"])
        except (TypeError, ValueError):
            return v["intValue"]
    if "doubleValue" in v:
        return v["doubleValue"]
    if "boolValue" in v:
        return v["boolValue"]
    return None


def _nano_to_datetime(value: Optional[str]) -> Optional[datetime]:
    """Convert an OTLP unix-nanosecond string to a UTC datetime."""
    if not value or value == "0":
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1_000_000_000, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _otlp_span_to_trace_create(span: OTLPSpan) -> TraceCreate:
    """Convert an inbound OTLP span into a :class:`TraceCreate`."""
    attrs = {kv.key: _attr_value(kv) for kv in span.attributes}

    span_type = attrs.get("agenttrace.span_type", "custom")
    cost = attrs.get("agenttrace.cost_usd")
    model = attrs.get("llm.model")
    provider = attrs.get("llm.provider")
    feature = attrs.get("agenttrace.feature")

    token_usage: dict[str, int] = {}
    for k, v in attrs.items():
        if k.startswith("llm.usage.") and isinstance(v, int):
            token_usage[k.removeprefix("llm.usage.")] = v

    start = _nano_to_datetime(span.startTimeUnixNano) or datetime.now(timezone.utc)
    end = _nano_to_datetime(span.endTimeUnixNano)
    duration = (end - start).total_seconds() * 1000.0 if end else None

    status_code = (span.status or {}).get("code", 0)

    return TraceCreate(
        run_id=span.traceId,
        span_id=span.spanId,
        parent_span_id=span.parentSpanId,
        span_type=str(span_type),
        name=span.name,
        input_data=None,
        output_data=None,
        metadata=None,
        start_time=start,
        end_time=end,
        duration_ms=duration,
        cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
        token_usage=token_usage or None,
        status=_OTLP_STATUS_REVERSE.get(status_code, "completed"),
        error=(span.status or {}).get("message"),
        model=str(model) if model else None,
        provider=str(provider) if provider else None,
        feature=str(feature) if feature else None,
    )


@router.post("/otlp/v1/traces", status_code=200)
async def ingest_otlp_traces(
    body: OTLPExportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """Accept an OTLP/JSON export push and ingest its spans (best-effort).

    Mirrors the OTLP HTTP collector contract: returns a ``partialSuccess`` object
    reporting how many spans were accepted. Missing runs are created on demand;
    no numeric values are recomputed.

    Args:
        body: The OTLP export request.
        session: Async database session.

    Returns:
        An OTLP-style response with the accepted span count.
    """
    trace_creates: list[TraceCreate] = []
    for resource in body.resourceSpans:
        for scope in resource.scopeSpans:
            for span in scope.spans:
                trace_creates.append(_otlp_span_to_trace_create(span))

    service = TraceService(session)
    traces = await service.ingest_spans(trace_creates) if trace_creates else []

    return {
        "partialSuccess": {
            "acceptedSpans": len(traces),
            "rejectedSpans": 0,
            "errorMessage": "",
        }
    }
