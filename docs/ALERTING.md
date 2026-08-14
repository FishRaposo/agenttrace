# Local alerting

Alert rules and events are persisted in SQLite or PostgreSQL. Supported rule
kinds are daily cost, per-run cost, and latency. Ingestion and the legacy
`/api/alerts` views evaluate rules and upsert deterministic deduplication keys.
Events move through `open`, `acknowledged`, and `resolved` states; an admin can
acknowledge an event through `/api/alerts/events/{id}/ack`.

The existing `/api/alerts` and `/api/alerts/latency` response fields remain
unchanged. New rule/event endpoints are additive. Notification delivery is
intentionally local (memory/log/database); Slack, Discord, webhooks, hosted
scheduling, and external paging services remain deferred.
