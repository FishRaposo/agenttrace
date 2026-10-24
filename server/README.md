# AgentTrace server

Self-contained FastAPI collector for the AgentTrace SDK. The default SQLite
configuration, in-memory realtime publisher, and offline demo require no
external compatibility package.

```bash
pip install -e "server[dev]"
uvicorn app.main:app --reload
```


## Local 0.2.0 release candidate

The collector remains independently installable: SDK imports occur only when
inspecting or launching bundled scenarios. Enable the launcher deliberately and
bind it to loopback. From the repository root in PowerShell:

```powershell
$env:DATABASE_URL = 'sqlite+aiosqlite:///./.tmp/local-review.db'
$env:PORTFOLIO_LAUNCH_ENABLED = 'true'
$env:PORTFOLIO_COLLECTOR_URL = 'http://127.0.0.1:8300'
$env:CORS_ORIGINS = '["http://localhost:3404","http://127.0.0.1:3404"]'
python -m uvicorn app.main:app --app-dir server --host 127.0.0.1 --port 8300
```

Create the chosen database parent directory first. Existing SQLite databases gain
additive cursor and execution tables at startup. Alembic users can apply the
`add_delivery_executions` migration. Historical trace bodies remain unchanged;
API presentation redacts supported credential patterns and reports absent
provenance as unknown. Credential redaction is not comprehensive PII detection.

- `GET /api/portfolio/scenarios` reports readiness and fixed scenario definitions.
- `POST /api/portfolio/executions` accepts only `scenario` and a UUID `request_id`.
- `GET /api/portfolio/executions/{id}` reports durable progress and delivery.

Use one collector process for this local application. Distributed workers and
leases are outside this milestone.

One active execution is reserved by a database unique constraint. Repeated
request IDs return the same execution; conflicting or competing launches return
409. Restart marks abandoned work interrupted, retains partial traces and never
runs it again automatically. Expected retrieval/timeout/cancellation outcomes are
separate from collector delivery failure. Completion checks all twenty recorded
cases, their expected stages, terminal outcomes and aggregates.

Run, statistics, cost and SSE APIs accept `cohort_id` without changing their
unfiltered behavior. SSE uses a monotonic durable ingestion cursor; resume with
`cursor` or `Last-Event-ID`. Legacy trace-ID and timestamp inputs remain accepted.
Playback endpoints read recorded data and never re-execute tools. Comparisons
align logical stages and repeated occurrences; unknown historical scenario
revisions are explicitly unknown.

The launcher reuses existing viewer/ingestor/admin authorization. If enabling
`AUTH_REQUIRED`, configure `PORTFOLIO_AUTH_TOKEN` with an internal ingestor token;
it is never returned to the browser. Local credential-free review uses the
existing offline admin identity, with no hosted multi-user authentication claim.
The default limiter remains 100 requests per 60 seconds. Dedicated benchmarks may
set `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`; record those settings.
