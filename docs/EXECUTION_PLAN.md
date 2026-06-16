# Execution Plan

This document records how AgentTrace was raised to the comprehensive bar, the
do-no-harm rules that governed every change, and the convergence items that were
safely adopted versus deferred.

## Goals (this pass)

1. **Expand the test suites** to comprehensive coverage (success + error paths)
   for under-tested server endpoints, with the SDK's 84 tests untouched.
2. **Polish the dashboard** — a visible demo-mode fallback so the UI works with
   no backend, loading / empty / error states, an `ErrorBoundary`, component
   tests (vitest), and a Playwright smoke spec.
3. **Adopt `shared_core` convergence items** for the server *only where cleanly
   safe*, gated so no numeric output changes.
4. **Expand the docs** to the comprehensive bar with Mermaid diagrams.

## Do-no-harm rules

- The SDK stays **`shared_core`-free** and its public API stable (`pip install
  agenttrace` must keep working standalone).
- The full existing suite (Python **and** TypeScript) must pass at the same or a
  higher count after changes.
- `ruff check` + `ruff format --check` stay clean.
- **Any change that alters a numeric output (scores, costs, similarity) must be
  golden-output-gated**: pin the current value in a test first, then refactor so
  the test still passes. If it cannot be kept identical, the change is *not* made
  and is recorded as a follow-up.

## Baseline (before changes)

| Suite | Count | Gate |
|-------|-------|------|
| SDK (`sdk/tests`) | 84 passing | `ruff` clean |
| Server (`server/tests`) | 26 passing | `ruff` clean |
| Dashboard | tsc clean, `next build` green, Playwright spec present | — |

## Work performed

### Priority 1 — tests, frontend, docs (low-risk)

- **Server tests** expanded from 26 to a comprehensive set covering: the new
  ingestion/alert/OTLP endpoints, plus previously under-covered routes (stats,
  diff errors, replay 404, trace 404, auth register/login/me + failure paths,
  health, trace-type filtering, validation 422s) and new `TraceService` unit
  tests (`ensure_run_exists`, `ingest_spans`).
- **Dashboard polish:** added a demo-mode fallback in the API client
  (`src/lib/api.ts` + `src/lib/demoData.ts`) that serves bundled fixtures on a
  GET network error and flips a `demoMode` singleton; a visible
  `DemoModeBanner`; vitest + Testing Library wired up with component tests for
  `ErrorBoundary`, `DemoModeBanner`, `CostBreakdown`, `TokenUsage`, the demo
  resolver, and the API fallback; and a Playwright `demo-mode.spec.ts` smoke
  test. The existing `ErrorBoundary` and loading/empty/error states were kept.
- **Docs:** expanded `SECURITY.md`, `failure-modes.md`, `design-decisions.md`,
  and `roadmap.md` with Mermaid diagrams; added this `EXECUTION_PLAN.md`. The
  already-comprehensive `architecture/c4.md` and `ARCHITECTURE.md` were left as
  the canonical architecture references.

### Priority 2 — convergence (only where cleanly safe)

| Item | Status | Notes |
|------|--------|-------|
| Ingest canonical `shared_core.tracing.Span` (hermes shape) | **Adopted** | `POST /api/traces/spans` via `SharedSpanIngest` adapter. Span type/status mapped; unknown values pass through. |
| Ingest LCM-style `shared_core.tracing.CostRecord` | **Adopted** | `POST /api/traces/costs`; cost taken **verbatim**, materialized as an `llm_call` span. |
| Simple alerting rule (latency / cost threshold) | **Adopted** | `GET /api/alerts/latency` added; existing `GET /api/alerts` (cost) kept unchanged. |
| OTLP-style export endpoint (best-effort) | **Adopted** | `GET`/`POST /api/otlp/v1/traces` (JSON subset). Round-trips cost/token attributes. |
| Server cost computation → `shared_core.pricing` | **Deferred** | Would change pinned numeric cost outputs. Requires a golden-output gate first; not done in this pass to honor do-no-harm. |
| Couple the SDK to `shared_core` | **Will not do** | The SDK must stay standalone (`pip install agenttrace`). |

### Why the pricing convergence was deferred

The server's cost analytics currently sum the `cost_usd` values stored on each
trace (computed upstream by the SDK's `CostTracker.PRICING`). Re-deriving cost
from `shared_core.pricing` on the server would risk diverging from the SDK's
table for any model whose entries differ, changing the values returned by
`/api/costs/*` and `/api/stats`. Per the do-no-harm rule, that change is only
safe behind a golden-output test that pins the exact current numbers first —
recorded here as a follow-up rather than attempted blind. The new ingestion
adapters deliberately take inbound cost **verbatim** for the same reason.

## Verification gate

```bash
# Python (repo .venv: shared-core editable + SDK editable + server[dev])
ruff check server/app server/tests sdk/agenttrace examples
ruff format --check server/app server/tests sdk/agenttrace examples
pytest sdk/tests        # 84
pytest server/tests     # expanded, all green

# Dashboard
cd dashboard
npm install
npx tsc --noEmit
npx vitest run
npx next build
```

All gates must be green; a failing command is never reported as passing.
