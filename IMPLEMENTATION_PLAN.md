# Implementation Plan

## Phase 1 — Core Foundation

**Goal**: Working end-to-end trace pipeline from SDK to storage.

### Tasks
- [x] Implement `Span` dataclass with full lifecycle (start, end, error, to_dict)
- [x] Implement `Tracer` class with run and span management
- [x] Implement `RunContext` with context variable nesting
- [x] Implement `JSONLExporter` with file-based append
- [x] Build FastAPI server with `/api/traces` and `/api/runs` endpoints
- [x] SQLAlchemy models for Run, Span, Trace
- [x] Async database session with SQLite support
- [x] Basic run listing in dashboard

**Deliverable**: Record a run, export to JSONL, list runs via API.

## Phase 2 — Intelligence & Observability

**Goal**: Automatic instrumentation and rich dashboard.

### Tasks
- [x] `trace_llm` wrapper capturing model, tokens, cost, latency
- [x] `trace_tool` wrapper capturing tool name, input, output, errors
- [x] Cost calculation service (per-run, per-span-type)
- [x] Token usage aggregation
- [x] `APIExporter` with retry and backoff
- [x] Run detail page with span timeline
- [x] Span detail component with I/O inspection
- [x] Cost breakdown chart (recharts)
- [x] Token usage visualization

**Deliverable**: Run an agent, see full trace with costs and tokens in dashboard.

## Phase 3 — Polish & Extensibility

**Goal**: Production-ready with advanced features.

### Tasks
- [x] PostgreSQL support with migrations
- [x] OpenTelemetry OTLP exporter
- [x] Run filtering and search
- [x] Multi-agent trace correlation
- [x] Streaming trace updates
- [x] Cost alerting thresholds
- [x] Trace diffing between runs
- [x] Prompt replay from recorded inputs
- [x] Dashboard dark mode
- [x] Comprehensive error handling edge cases

**Deliverable**: Production-deployable system with full observability suite.
