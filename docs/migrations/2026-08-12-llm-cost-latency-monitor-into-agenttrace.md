# LLM Cost & Latency Monitor into AgentTrace

Date: 2026-08-12

## Provenance

- Source repository: https://github.com/FishRaposo/llm-cost-latency-monitor.git
- Source commit: `84ed463ed46301bcebe039f8069da6ffb20b520e`
- Destination repository: https://github.com/FishRaposo/agenttrace.git
- Destination branch: `portfolio/consolidation/agenttrace`
- Integration style: behavior port and adaptation; no source history, dependencies, or binaries copied.

## Selected source paths

| Source path | Selected behavior | Destination |
|---|---|---|
| `src/llm_monitor/reports.py` | UTC daily bucketing, LLM metric summaries, JSON/CSV rendering | `server/app/services/cost_reporting.py`, `server/app/api/costs.py` |
| `src/llm_monitor/storage.py` | Prompt-version cost grouping semantics, including `unversioned` | `server/app/services/cost_reporting.py`, existing `/api/costs/summary` |
| `tests/test_reports.py`, `tests/test_storage.py` | Day filtering, prompt grouping, empty/CSV behavior as reference cases | `server/tests/test_costs.py` API-level regression coverage |
| `frontend/src/components/PromptVersionBreakdown.tsx` | Prompt-version spend comparison | `dashboard/src/app/costs/page.tsx` |
| `frontend/src/components/DailyReportView.tsx` | Daily request/token/cost/latency/error table | `dashboard/src/app/costs/page.tsx` |
| `frontend/src/lib/api.ts`, `frontend/src/types/index.ts` | Typed daily-report client contract | `dashboard/src/lib/api.ts`, `dashboard/src/types/index.ts` |

The implementation composes AgentTrace's existing `Trace.cost_usd`, `Trace.token_usage`,
`Trace.duration_ms`, `Trace.error`, `Trace.model`, and `Trace.trace_metadata` fields. Only
`llm_call` traces participate in prompt-version and daily LLM reports; the existing unfiltered
cost summary continues to include every cost-bearing span. Prompt versions are read from
`metadata.prompt_version`, with missing or empty tags normalized to `unversioned`.

## Excluded source paths

- `src/llm_monitor/sdk.py`, `models.py`, `storage_db.py`, and the Alembic migration: AgentTrace already ingests traces and stores the required values; no SDK or schema fork is needed.
- `src/llm_monitor/pricing.py`: AgentTrace preserves ingested costs and does not recompute them in reporting.
- `src/llm_monitor/worker.py`: Celery scheduling is outside this deterministic on-request report port.
- `src/llm_monitor/budgets.py`: AgentTrace already has budget endpoints and models.
- `src/llm_monitor/main.py` endpoint paths: AgentTrace retains its `/api/costs/*` namespace rather than importing source endpoint contracts.
- `frontend/src/components/LogCallForm.tsx` and source ingestion UI: AgentTrace's SDK/exporter and trace endpoints remain the ingestion path.
- All `shared_core` source and imports in `sdk/`: the standalone AgentTrace SDK must not depend on `shared_core`; metric reuse is server-only.

## License status

The source commit contains an MIT License, copyright 2026 Operator Systems. This port adapts
behavior and small structural concepts rather than copying files verbatim. AgentTrace currently
has no tracked root `LICENSE` file, so public redistribution should not represent the combined
repository as license-complete until repository-level licensing and attribution are explicitly
resolved. This document preserves the source URL, exact commit, and license status.

## Archive gate

The source repository is **not archived by this task**. Archive `llm-cost-latency-monitor` only
after all of the following are true:

1. this destination commit is reviewed and merged into AgentTrace's intended default history;
2. server tests plus dashboard lint/typecheck/build pass in an environment with the locked dependencies;
3. JSON and CSV report output is exercised against persisted AgentTrace data;
4. portfolio inventory, links, and deployment references point to AgentTrace;
5. the source commit and MIT license remain recoverable, and the owner explicitly approves the archive action.

Until every gate passes, the source remains the authoritative recovery copy for excluded behavior.
