# AGENTS.md — agenttrace

## What This Is

AgentTrace is an observability + deterministic-replay layer for agentic AI workflows.
Three deployable parts: an installable **tracing SDK**, a **FastAPI collector server**,
and a **Next.js dashboard**. Migrated out of `General Projects/` onto the `shared_core`
standard (server only — the SDK stays standalone).

## Layout (three-part)

```
agenttrace/
├── sdk/                          # installable Python package `agenttrace` — STANDALONE
│   ├── agenttrace/               #   tracer, span, exporters, instrumentation, wrappers,
│   │                             #   cost_tracker, hybrid_client, distributed
│   ├── tests/                    #   standalone SDK test suite
│   └── pyproject.toml            #   must NOT depend on shared_core (pip-installable on its own)
├── server/                       # FastAPI collector — shared_core-backed
│   ├── app/
│   │   ├── main.py               #   app wiring (shared_core middleware + rate limit + error handler)
│   │   ├── config.py             #   Settings(BaseAppConfig)
│   │   ├── core/logging.py       #   delegates to shared_core.logging
│   │   ├── db/__init__.py        #   AsyncDatabaseManager engine + local DeclarativeBase
│   │   ├── api/                  #   12 routers (traces, runs, stats, costs, budgets, alerts,
│   │   │                         #     diff, replay, realtime WS, stream SSE, health, auth)
│   │   ├── models/  services/  auth.py  # cost_reporting is server-only
│   ├── tests/                    #   server API/service test suite
│   ├── migrations/  Dockerfile  pyproject.toml  requirements.txt
├── dashboard/                    # Next.js 14 + recharts — KEPT as-is
├── examples/run_demo.py          # offline SDK tracing demo (JSONL export)
├── scripts/  data/  docs/
├── docker-compose.yml            # agenttrace_postgres + agenttrace_redis + server + dashboard
├── Makefile  ruff.toml  pyrightconfig.json
└── .github/workflows/ci.yml
```

## The SDK is standalone (do not change this)

`sdk/agenttrace` is the product's core value and is published independently. It **must not
import `shared_core`** so it stays a lightweight `pip install agenttrace`. Optional
integrations (openai/anthropic/langchain/llamaindex/fastapi) are imported lazily as
availability probes (`# noqa: F401`). The instrumentation modules import `Tracer` from
`agenttrace.tracer` (not `agenttrace`) to avoid a package-init import cycle.

## shared-core adoption (server only)

| Bespoke (server, before) | Now |
|---|---|
| `Settings(BaseSettings)` | `Settings(BaseAppConfig)` (keeps domain fields; sqlite default) |
| `core/logging.py` (stdlib JSON) | delegates to `shared_core.logging.setup_logging` |
| `core/rate_limit.py` (in-memory) | `shared_core.ratelimit.RateLimiter` + `RateLimitMiddleware` (in-memory fallback; Redis-ready) |
| `db/__init__.py` engine | `shared_core.database.AsyncDatabaseManager` (keeps local `Base`, sqlite repair, demo seed) |
| catch-all 500 handler only | + `shared_core.errors.application_error_handler` + `RequestLoggingMiddleware` (correlation IDs) |

**Preserved domain value:** the entire SDK; the server's replay + run-diff endpoints, WS
streaming + SSE, `TraceService` run-stat math, JWT auth, cost-attribution columns,
prompt-version cost filtering, and deterministic daily JSON/CSV cost reports.

## Commands

```bash
make install      # pip install -e ../shared-core; pip install -e sdk; pip install -e 'server[dev]'; dashboard npm install
make test         # sdk-test + server-test
make sdk-test     # standalone SDK tests
make server-test  # server tests
make lint         # ruff check server/app sdk/agenttrace examples ...
make format       # ruff format ...
make typecheck    # pyright server/app sdk/agenttrace
make docker-up    # pgvector + redis + server + dashboard
make demo         # offline SDK tracing demo (writes data/demo_traces.jsonl)
```

Local verification uses `.venv` at the repo root (shared-core editable + SDK editable +
`server[dev]`). The SDK is verified standalone; the server with shared-core.

## Current State

The server adopts `shared_core` for config/logging/errors/DB, rate limiting, and server-side
LLM metric rollups. Prompt versions remain trace metadata, so the standalone SDK and database
schema do not gain a new dependency or field. The cost dashboard exposes prompt-version spend
and daily report filtering. The last pre-port commit recorded 151 passing SDK/server tests; this
checkout's new focused tests require the development dependencies described under Commands.
Default DB is SQLite (`sqlite+aiosqlite`); compose uses Postgres.

## Follow-ups (not done now)

- Consolidate cost pricing: the server can converge on `shared_core.pricing`, but the SDK's
  `CostTracker.PRICING` must stay SDK-local (the SDK can't import `shared_core`).
- Let `hermes-agent-framework` emit `shared_core.tracing.Span` objects the collector ingests.
- Server Docker image installs shared-core via its public git URL (workspace packaging gap).

## When to Update This AGENTS.md

- SDK public API changes, or the SDK gains/loses a `shared_core` dependency (it must stay free)
- Server shared-core adoption surface changes
- Makefile targets, docker-compose services, or CI steps change
