# Failure modes

AgentTrace is designed to fail closed at the server boundary and never make
host-agent tracing a hard dependency.

## Collector unavailable

`APIExporter` records the HTTP failure and the SDK can fall back to
`JSONLExporter`. The local demo uses JSONL or the in-memory server path; no
provider or network is required.

## Optional integration missing

Provider SDKs, LangChain integrations, Redis, PostgreSQL, Docker, and Grafana
are availability-probed or opt-in. Without them, manual tracing, SQLite, the
in-memory realtime publisher, and the dashboard demo fixtures remain usable.

## Database unavailable

The server reports the health/transaction failure and rolls back the request.
SQLite is the zero-configuration default, and startup repairs the additive local
columns used by sampling and roles. PostgreSQL is the durable optional path.

## Rate limit or authorization failure

The in-memory limiter returns `429` when a client exceeds its window. Protected
routes return `401` for missing/invalid required credentials and `403` when a
valid role lacks permission. Set `REDIS_URL` only when multi-worker limiter
coordination is needed.

## Realtime disconnect

WebSocket/SSE clients can reconnect and fall back to ordinary run/span reads.
The in-memory publisher is process-local; Redis is an optional multi-instance
transport. A disconnected subscriber never blocks trace persistence.

## Sampling disposition

Sampling is off by default. Head decisions are stable per trace ID. Tail mode
buffers a run, keeps terminal errors/slow spans when configured, and can
discard incomplete runs deterministically on timeout. The response includes
`sampled` and `sampling_reason` so dropped data is inspectable.

## Alert evaluation failure

Rules and events are local database records. A malformed rule is rejected at
validation time; evaluation failures roll back the transaction rather than
silently notifying an external service. External notification and scheduling
are intentionally not part of this project.

## OTLP mismatch

The supported contract is OTLP HTTP/JSON. Missing timestamps and unknown value
shapes are normalized where safe; malformed documents receive a validation
error. Protobuf/gRPC payloads are explicitly deferred.

## Dashboard backend offline

GET requests fall back to bundled, visibly labeled demo fixtures. Writes are not
faked. This keeps the dashboard explorable without hiding that the data is
synthetic.
