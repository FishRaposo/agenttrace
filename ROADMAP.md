# AgentTrace roadmap

## Delivered local engineering

- Python SDK with deterministic simulation, decorators, provider wrappers,
  JSONL/API exporters, replay payloads, and SDK-local cost tracking.
- FastAPI collector with SQLite by default, optional PostgreSQL, self-contained
  server packaging, canonical ingestion adapters, cost reports, run diffing,
  replay, and dashboard compatibility routes.
- OTLP HTTP/JSON resource and scope metadata, span attributes, events, links,
  status, timestamps, export, and tolerant ingest.
- Deterministic head/tail sampling, including stable SHA-256 decisions,
  error/slow overrides, buffered-run semantics, timeout disposition, and
  additive sampling metadata.
- In-memory realtime transport with optional Redis adapter behind the existing
  WebSocket/SSE facades.
- Persisted cost/latency alert rules and deduplicated event state with
  acknowledgement and legacy response parity.
- Single-tenant `admin`, `ingestor`, and `viewer` roles plus redacted audit logs.
- Portable Grafana dashboard JSON and a credential-free evidence bundle with
  golden output and SHA-256 verification.
- Dependency-free, safety-bounded issue-to-draft-PR SDK workflow with
  deterministic providers, sandbox/Git/test guards, approval, draft-only intent,
  ordered audit/trace events, and replay.
- Clean SDK/server wheel install paths, Ruff/Pyright gates, frontend CI,
  dependency scans, and provenance/attribution documentation.

## Deliberately deferred product surfaces

These remain outside the portfolio slice and should not become hidden runtime
requirements:

- hosted/team tenancy, workspace workflows, and hosted scheduling;
- Slack, Discord, webhook, or other external notification delivery;
- OTLP protobuf/gRPC;
- mandatory Redis, PostgreSQL, Grafana, or a hosted database;
- live GitHub/LLM/persistence/worker adapters and server-hosted issue-to-PR routes;
- cross-repository changes to `aria-agent`.

## Future evidence-gated work

Any future expansion should begin with a baseline capture and golden-output
fixture, then preserve the offline demo and the public response contract. The
portfolio-wide procedure is recorded in the hub's
`portfolio-inventory/FINALIZATION_STANDARD.md`.
