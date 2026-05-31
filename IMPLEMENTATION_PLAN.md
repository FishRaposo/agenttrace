# Implementation Plan

## Phase 1 — Core Foundation (Complete)

**Goal**: Working end-to-end trace pipeline from SDK to storage.

### Tasks
- [x] Implement `Span` dataclass with full lifecycle (start, end, error, to_dict)
- [x] Implement `Tracer` class with run and span management
- [x] Implement `RunContext` with context variable nesting
- [x] Implement `JSONLExporter` with file-based append
- [x] Build FastAPI server with `/api/traces` and `/api/runs` endpoints
- [x] SQLAlchemy models for Run, Span, Trace
- [x] Async database session with SQLite/PostgreSQL support
- [x] Basic run listing in dashboard

**Deliverable**: Record a run, export to JSONL, list runs via API.

## Phase 2 — FinOps & Debugging (Complete)

**Goal**: Cost tracking, budget alerts, and rich debugging UI.

### Tasks
- [x] `trace_llm` wrapper capturing model, tokens, cost, latency
- [x] `trace_tool` wrapper capturing tool name, input, output, errors
- [x] Cost analytics API (`/api/costs/*`) — summary, timeseries, breakdowns
- [x] Budget model with alert thresholds (`/api/budgets`)
- [x] `/costs` dashboard page with Recharts charts and budget status
- [x] `/live` SSE tail page for real-time span streaming
- [x] Waterfall timeline with cost overlay, error highlighting, nested spans
- [x] Run detail page with compare (diff) and replay tabs
- [x] Cost breakdown and token usage visualizations

**Deliverable**: Run an agent, see full trace with costs, budgets, and live tail.

## Phase 3 — Integrations & Scale (Complete)

**Goal**: Provider-aware wrappers, hybrid client, batch ingestion.

### Tasks
- [x] `trace_openai()` and `trace_anthropic()` provider-specific wrappers
- [x] `HybridLLMClient` (`AGENTTRACE_LLM_MODE=sim|real`)
- [x] LangChain callback handler with auto-instrumentation
- [x] Multi-agent demo with `correlation_id`
- [x] Batch ingestion endpoint (`POST /api/traces/batch`)
- [x] Buffered API exporter using batch endpoint
- [x] PostgreSQL support with Alembic migrations
- [x] Docker Compose with healthchecks, auto-migrate, auto-seed
- [x] Deploy guide (`docs/DEPLOYMENT.md`)
- [x] Benchmark script (`scripts/benchmark.py`)

**Deliverable**: Production-deployable system with provider wrappers and high-throughput batch export.

## Phase 4 — Future

- [ ] OTLP export (OpenTelemetry compatibility)
- [ ] Trace sampling (head-based / tail-based)
- [ ] Redis-based realtime pub/sub for multi-instance deployments
- [ ] Grafana dashboard JSON
- [ ] Alerting on latency regression and cost spikes
- [ ] RBAC (user roles and team scoping)
- [ ] Audit log for compliance
