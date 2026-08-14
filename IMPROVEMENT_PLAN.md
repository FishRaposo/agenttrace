# AgentTrace — Historical Improvement Plan

> Historical audit captured before the 2026-08-14 comprehensive finalization.
> Its bug claims and priorities are not current-state assertions; use the live
> code, tests, README, and `ROADMAP.md` for the delivered implementation.

> Comprehensive audit of bugs, inconsistencies, missing features, and growth opportunities.
> Priority levels: **P0** (broken/blocking), **P1** (high value), **P2** (polish), **P3** (long-term growth).

---

## 1. P0 — Broken Code & Critical Fixes

### 1.1 Example files use wrong API signatures

| File | Bug |
|------|-----|
| `examples/multi_agent_demo.py` | Calls `Tracer(exporter=exporter)` — constructor takes no args. Calls `tracer.generate_id()` — method doesn't exist. Uses `metadata={"correlation_id": ...}` and `workflow_id` instead of the `correlation_id` parameter. |
| `examples/langchain_example.py` | Calls `APIExporter(api_base_url=...)` — parameter is named `endpoint`. |

**Action:** Rewrite both examples to match the current SDK API. Add a CI step that runs them against the mock backend to prevent future drift.

### 1.2 Stale `backend/` directory

`backend/main.py` is a legacy in-memory prototype, superseded by `server/`. Creates confusion about which code is canonical.

**Action:** Delete `backend/` entirely. Update `ENTRYPOINTS.md` to remove all references.

### 1.3 Stale `dashboard/app/` directory

`dashboard/app/traces/page.tsx` is a leftover from before the refactor to `dashboard/src/`.

**Action:** Delete `dashboard/app/` entirely.

### 1.4 FAQ says OpenTelemetry not supported — but it is

`FAQ.md` says "Can I use this with OpenTelemetry? Not yet" while `sdk/agenttrace/exporters/otlp.py` is fully implemented.

**Action:** Update FAQ to document OTLP exporter usage with an example.

---

## 2. P1 — High-Value Fixes

### 2.1 Implement stub instrumentations

Three files raise `NotImplementedError`:

| File | Value |
|------|-------|
| `sdk/agenttrace/instrumentation/openai.py` | **Highest value** — SDK already has `@trace_openai` wrapper; auto-instrumentor would let users `auto_instrument("openai")` instead of decorating every call. Monkey-patch `openai.resources.chat.Completions.create`. |
| `sdk/agenttrace/instrumentation/llamaindex.py` | Subclass `BaseCallbackHandler` similar to the existing LangChain handler. |
| `sdk/agenttrace/instrumentation/fastapi.py` | Add middleware that creates a run per request and attaches trace context to response headers. |

### 2.2 In-memory auth store

`server/app/api/auth.py` uses `fake_users_db` — an in-memory dict that resets on restart. Not production-demo-able.

**Action:** Add a `users` table via Alembic migration. Hash passwords with bcrypt. Seed a demo user on startup.

### 2.3 TraceService partially used

`server/app/services/trace_service.py` exists as a clean service layer, but `server/app/api/traces.py` duplicates its logic inline instead of delegating.

**Action:** Refactor `traces.py` to call `TraceService` methods. Routes should handle HTTP concerns only; business logic belongs in the service.

### 2.4 Cost attribution columns duplicated

The `Trace` model stores `model`, `provider`, `feature` as explicit columns AND inside `trace_metadata` JSON. The API route extracts from metadata as fallback.

**Action:** Pick one approach. Recommended: keep explicit columns, add a Pydantic validator that populates them from metadata during trace creation, stop storing duplicates in metadata.

### 2.5 `SpanEntry` model defined but never used

`server/app/models/span.py` defines `SpanEntry` with its own `span_entries` table, but no route or service references it. All spans live inside the `traces` table's `spans` JSON column.

**Action:** Either migrate to the relational span model (enables span-level queries, indexing, pagination — higher value) or remove the dead model.

### 2.6 Run stats recalculated on every trace ingestion

`server/app/api/traces.py` recalculates `total_tokens`, `total_cost`, `span_count` by querying ALL traces for a run on every single ingestion. Expensive at scale.

**Action:** Increment the run's counters atomically (`run.total_tokens += trace.token_count`) instead of recalculating.

### 2.7 `datetime.utcnow()` deprecation

Multiple models use `datetime.utcnow` as default values. Deprecated in Python 3.12+.

**Action:** Replace all occurrences with `datetime.now(timezone.utc)` across `server/app/models/`.

### 2.8 Unnecessary `db/session.py` re-export

`server/app/db/session.py` just re-exports from `server/app/db/__init__.py`.

**Action:** Delete `session.py`, update any imports.

### 2.9 Docs reference unimplemented features

| File | Issue |
|------|-------|
| `SETUP.md` | References `start_span` and `tracer.export()` which don't exist in current API |
| `ENTRYPOINTS.md` | References `backend/` directory |
| `docs/SECURITY.md` | Mentions `gk-` prefix and rate limiting per API key — not implemented |
| `ARCHITECTURE.md` (root) | References Prometheus `/metrics` that only exists in legacy `backend/` |

**Action:** Rewrite each doc to match current implementation.

---

## 3. P2 — Polish & Depth

### 3.1 Add pagination to trace listing

The traces endpoint returns all traces for a run without pagination.

**Action:** Add `limit`/`offset` query parameters with default limit of 50.

### 3.2 Add rate limiting

No rate limiting exists beyond optional auth middleware.

**Action:** Add per-IP and per-API-key rate limiting using slowapi or a simple sliding window.

### 3.3 CORS origin validation

Currently `allow_origins=["*"]` in development.

**Action:** Make CORS origins configurable via environment variable (`CORS_ORIGINS`).

### 3.4 Structured logging

Server uses basic `logging` setup with no JSON output option.

**Action:** Add structlog with JSON formatter for production, text for development. Include trace_id and run_id in log context.

### 3.5 Graceful WebSocket shutdown

`server/app/api/realtime.py` has no graceful shutdown handling.

**Action:** Add lifespan-aware disconnect broadcasting and connection draining.

### 3.6 Database connection pooling

No explicit pool size or timeout configuration.

**Action:** Add `pool_size`, `max_overflow`, `pool_timeout` to `config.py` and pass to `create_async_engine`.

### 3.7 Wrapper guard pattern inconsistency

| Wrapper | Pattern |
|---------|---------|
| `tool_wrapper.py` | Checks `if span.end_time is None` before `end_span()` |
| `retrieval_wrapper.py` | Uses `finally:` unconditionally |
| `decision_wrapper.py` | Uses `finally:` unconditionally |
| `llm_wrapper.py` | Mixed approach |

**Action:** Standardize on `finally:` block approach (prevents leaked spans on unexpected exceptions).

### 3.8 Dashboard: real-time data fetching

Live tail page uses SSE, but other pages don't auto-refresh.

**Action:** Add SWR or React Query for data fetching with auto-refresh on the runs list and costs pages.

### 3.9 `# type: ignore[return-value]` in wrappers

5 wrapper files suppress type errors from the decorator pattern.

**Action:** Use `functools.wraps` with proper `ParamSpec` and `TypeVar` typing, or `@overload` to satisfy the type checker.

### 3.10 Tracer singleton confusion

`Tracer._instance` is declared but never used as the primary pattern. Both `get_current_tracer()` and direct instantiation are available.

**Action:** Either enforce the singleton pattern via `__new__` or remove `_instance` and document that multiple tracers are supported.

---

## 4. P3 — Growth & Long-Term

### 4.1 Phase 2 roadmap items

| Item | Description |
|------|-------------|
| Grafana dashboard JSON export | Generate a pre-built Grafana dashboard JSON from AgentTrace metrics |
| Trace diffing UI | API exists at `/api/diff` but dashboard doesn't expose it — add a "Compare Runs" button |
| Latency regression alerting | Detect when trace latency exceeds a configurable baseline |

### 4.2 Phase 3 roadmap items

| Item | Description |
|------|-------------|
| Batch ingestion | Accept multiple traces in a single POST request |
| Trace sampling | Export only a percentage of traces at high volume |
| Full distributed tracing | Add baggage propagation, cross-service span linking beyond correlation IDs |

### 4.3 Expand pricing tables

`cost_tracker.py` only covers 3 OpenAI + 3 Anthropic models. Missing GPT-4o, Claude 3.5 Sonnet, etc.

**Action:** Add recent models. Make pricing configurable via external JSON/YAML file so users can update without code changes.

### 4.4 Multi-tenant support

All runs and traces are global — no workspace isolation.

**Action:** Add `workspace_id` to runs and traces. Filter all queries by workspace. Map API keys to workspaces.

### 4.5 SDK publish

`pyproject.toml` defines `agenttrace` v0.1.0 but it's not published.

**Action:** Add a CI step that verifies the package builds correctly (`python -m build`). Optionally publish to TestPyPI.

### 4.6 Dashboard E2E test coverage

Current E2E tests cover home, nav, dark mode, filter, search, pagination. Missing: costs page, live tail page, run detail page.

**Action:** Add Playwright specs for costs (budget progress, charts), live tail (SSE connection), and run detail (timeline, diff, replay).

### 4.7 Hybrid LLM client enhancement

`hybrid_client.py` supports simulation or real mode only.

**Action:** Add multi-provider routing (try OpenAI first, fall back to Anthropic) with configurable provider priority.

---

## 5. Implementation Priority Order

```
 1. Delete backend/ and dashboard/app/                     (dead code removal)
 2. Fix example files to use correct API                   (broken demos)
 3. Update all stale documentation                         (FAQ, SETUP, ENTRYPOINTS, SECURITY, ARCHITECTURE)
 4. Fix datetime.utcnow() across all models                (Python 3.12 compat)
 5. Delete db/session.py, update imports                   (cleanup)
 6. Refactor traces.py to use TraceService                 (architecture consistency)
 7. Deduplicate cost attribution approach                  (data integrity)
 8. Implement OpenAI auto-instrumentation                  (highest-value stub)
 9. Replace in-memory auth with database-backed auth       (production readiness)
10. Add pagination, rate limiting, structured logging      (operational maturity)
11. Standardize wrapper guard patterns                     (code consistency)
12. Resolve or remove SpanEntry model                      (dead code decision)
13. Implement remaining Phase 2 roadmap items              (feature growth)
14. Implement Phase 3 roadmap items                        (long-term vision)
```
