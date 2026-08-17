# AGENTS.md — agenttrace

## What This Is

AgentTrace is an observability and deterministic-replay layer for agentic AI
workflows. It has three deployables: a standalone tracing SDK, a self-contained
FastAPI collector, and a Next.js dashboard.

## Layout

```
agenttrace/
├── sdk/                          # installable package `agenttrace` — standalone
├── server/                       # FastAPI collector and internal compatibility layer
│   ├── app/internal/vendor_core/ # pinned server-only vendor subset
│   ├── app/api/                  # traces, runs, costs, alerts, OTLP, replay, realtime
│   ├── app/models/ services/     # persistence and domain logic
│   ├── tests/                    # API and service tests
│   └── migrations/ Dockerfile pyproject.toml requirements.txt
├── dashboard/                    # Next.js dashboard with offline demo fixtures
├── examples/ scripts/ docs/      # demos, evidence tooling, and project documentation
├── Makefile ruff.toml pyrightconfig.json
└── .github/workflows/ci.yml
```

## SDK boundary

`sdk/agenttrace` is published independently and must not import server code. Its
optional provider integrations remain lazy, and its local `CostTracker.PRICING`
table is intentionally independent from server pricing. The dependency-free
`agenttrace.issue_pr` package owns the absorbed, safety-bounded issue-to-draft-PR
workflow. It must stop at explicit approval, remain draft-only, and never make a
network call through its default adapters.

## Server boundary

The server owns the compatibility layer under `server/app/internal/`. It vendors
only the modules needed for configuration, database access, errors, logging, rate
limiting, tracing, LLM metrics, pricing, Redis helpers, and HTTP clients. Runtime
imports must use the `app.internal` namespace. Do not add sibling checkouts,
Git-installed dependencies, or runtime imports from an external compatibility
package.

Canonical span and cost adapters accept dictionaries, Pydantic models, and
compatible producer objects. Keep existing ingestion keys and compatibility
aliases stable. Do not modify `aria-agent` for this integration.

## Commands

```bash
make install      # install SDK/server dev extras and dashboard with npm ci
make test         # SDK + server tests
make sdk-test     # standalone SDK tests
make server-test  # server tests
make dashboard-test
make lint         # Ruff check
make format       # Ruff format
make typecheck    # Pyright
make evidence     # deterministic offline portfolio evidence
make forbidden-scan
make package      # build SDK and server wheels
make docker-up    # optional PostgreSQL + Redis + server + dashboard
make demo         # offline SDK tracing demo
```

The default path uses SQLite, in-memory realtime publication, bundled demo data,
and no credentials or network-backed evaluations. Redis, PostgreSQL, Grafana, and
real provider credentials are opt-in.

## Delivered engineering surface

The SDK provides a deterministic issue-to-plan workflow, sandbox-contained edits,
protected-branch and bounded-test guards, ordered audit/trace events, replay, and a
draft-only approval boundary. The server provides deterministic head/tail sampling, JSON OTLP resource/scope/
event/link support, persisted cost and latency alerts, local `admin`/`ingestor`/
`viewer` roles, redacted audit logs, optional Redis realtime transport, and a
reproducible evidence fixture. Existing replay, run-diff, cost reporting,
WebSocket/SSE, JWT, and SDK ingestion behavior remains compatible.

## Deliberate product deferrals

Hosted/team tenancy, external alert delivery and scheduling, OTLP protobuf/gRPC,
real GitHub/LLM/persistence/worker providers for issue-to-PR automation, and
server routes for that workflow remain deferred. Keep those boundaries explicit
in roadmap and security documentation.

## When to update this file

- SDK public API or standalone dependency changes;
- server compatibility, sampling, alert, RBAC, audit, or OTLP behavior changes;
- Makefile targets, Docker Compose services, package metadata, or CI changes;
- a new deferred boundary or provenance source is introduced.
