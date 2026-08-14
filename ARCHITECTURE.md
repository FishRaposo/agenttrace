# AgentTrace architecture

AgentTrace is a three-part, offline-first observability system:

```text
SDK (standalone) -> FastAPI collector -> SQLite by default / PostgreSQL optional
       |                    |                    |
       +--> JSONL/API       +--> replay/diff      +--> Next.js dashboard
                            +--> OTLP HTTP/JSON
                            +--> in-memory/Redis realtime
                            +--> alerts, RBAC, audit, evidence
```

## Boundaries

The SDK records runs and spans without importing the server. The server owns
canonical compatibility contracts and a pinned vendored infrastructure subset
under `server/app/internal/`. The dashboard reads the stable API and has a
visibly labeled fixture-backed demo path when the API is offline.

## Span model

- `run_id` identifies a complete agent execution;
- `span_id` and `parent_span_id` form the operation tree;
- `span_type` covers LLM, tool, decision, retrieval, and custom work;
- metadata includes model/provider/feature, OTLP resource/scope data, and
  provider usage where available;
- `cost_usd`, token usage, duration, status, and additive sampling metadata
  support FinOps and retention analysis.

## Operational layers

- **Sampling:** stable SHA-256 head decisions and buffered tail decisions;
- **Realtime:** in-memory publication by default, optional Redis adapter behind
  existing WebSocket/SSE routes;
- **Alerts:** persisted local cost/latency rules and deduplicated state;
- **Access:** single-tenant admin/ingestor/viewer roles and redacted audit log;
- **Evidence:** canonical report, manifest, Markdown explanation, and checksums.

OTLP protobuf/gRPC, hosted/team workflows, hosted scheduling, external
notification services, and mandatory infrastructure dependencies remain deferred.
