# AgentTrace Roadmap

## Phase 1 — Core (Complete)
- [x] Python tracing SDK with `Tracer`, `Span`, `SpanType`
- [x] FastAPI ingestion backend with SQLite/PostgreSQL
- [x] Next.js trace dashboard with run list and detail views
- [x] Docker Compose with healthchecks and auto-migrate

## Phase 2 — FinOps & Debugging (Complete)
- [x] Cost tracking per trace/span with `CostTracker`
- [x] Cost analytics API (`/api/costs/*`) — summary, timeseries, breakdowns
- [x] Budget model with alert thresholds (`/api/budgets`)
- [x] `/costs` dashboard page with charts and budget progress bars
- [x] `/live` SSE tail page for real-time span streaming
- [x] Waterfall timeline with cost overlay and collapsible nested spans
- [x] Trace diffing UI (run comparison tab)
- [x] Prompt replay tab on run detail

## Phase 3 — Integrations (Complete)
- [x] `trace_openai()` and `trace_anthropic()` provider wrappers
- [x] Hybrid client (`AGENTTRACE_LLM_MODE=sim|real`)
- [x] LangChain callback handler with auto-instrumentation
- [x] Multi-agent demo with `correlation_id`
- [x] Batch ingestion endpoint (`POST /api/traces/batch`)
- [x] Buffered API exporter using batch endpoint

## Phase 4 — Scale & Production
- [ ] OTLP export (OpenTelemetry compatibility)
- [ ] Trace sampling (head-based / tail-based)
- [ ] Redis-based realtime pub/sub for multi-instance deployments
- [ ] Grafana dashboard JSON
- [ ] Alerting on latency regression and cost spikes
- [ ] RBAC (user roles and team scoping)
- [ ] Audit log for compliance
