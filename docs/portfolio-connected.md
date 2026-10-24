# Run and inspect the actual workload

This local workflow executes real overlapping Python tasks and exports their
spans through HTTP into SQLite. Provider responses, token counts and prices are
synthetic. It is independently runnable; ARIA, EvalForge and other portfolio
repositories are not runtime dependencies.

## Clean setup

Python 3.11+ and the Node version supported by the locked Next.js release are
required. Create a virtual environment and install the packages from the clone:

```bash
python -m venv .venv
# Activate .venv using your shell's normal activation command.
python -m pip install -e "sdk[dev]" -e "server[dev]" build
cd dashboard
npm ci
```

The SDK alone needs only `python -m pip install ./sdk`; it has no mandatory
dependencies. The collector's optional workload launcher discovers the SDK
lazily and reports unavailable when it is not installed.

Use a **new disposable database**, outside any existing data directory. On
PowerShell, from the clone root:

```powershell
New-Item -ItemType Directory -Force .tmp/local-review | Out-Null
$env:DATABASE_URL = 'sqlite+aiosqlite:///./.tmp/local-review/agenttrace.db'
$env:AUTH_REQUIRED = 'false'
$env:PORTFOLIO_LAUNCH_ENABLED = 'true'
$env:PORTFOLIO_COLLECTOR_URL = 'http://127.0.0.1:8300'
$env:CORS_ORIGINS = '["http://localhost:3404","http://127.0.0.1:3404"]'
$env:RATE_LIMIT_REQUESTS = '100000'
$env:TRACE_SAMPLING_MODE = 'off'
.venv/Scripts/python -m uvicorn app.main:app --app-dir server --host 127.0.0.1 --port 8300
```

The raised limiter is for this disposable loopback demonstration/benchmark only.
One incident exports 96 events; the ordinary 100 requests/minute default can
otherwise throttle a launch plus dashboard inspection. It is not a recommended
hosted security setting. Provider credentials are unnecessary; clear any inherited
provider keys before verification.

In another PowerShell window, build and start the connected production frontend.
Finish the build **before** browser verification; do not replace a running
production build while tests are reading it.

```powershell
cd dashboard
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8300'
$env:NEXT_PUBLIC_DEMO_MODE = '0'
npm run build
npm run start -- --hostname 127.0.0.1 --port 3404
```

Open <http://localhost:3404>. Select the connected source, choose Incident and
explicitly run the bundled workload. An expected retrieval error, timeout and
cancellation do not mean the launcher failed. Investigate the saved cohort and
then launch Repaired: only the retrieval defect is repaired.

The same installed SDK implementation is available from the terminal:

```bash
python -m agenttrace.portfolio --scenario incident --endpoint http://127.0.0.1:8300
python -m agenttrace.portfolio --scenario repaired --endpoint http://127.0.0.1:8300
python scripts/verify_connected_portfolio.py --endpoint http://127.0.0.1:8300
```

Use `--output` on the workload CLI to save its delivery/application report. A
complete delivery exits 0; an incomplete delivery exits 2. The CLI contacts only
the explicitly selected collector. Recorded playback is a read operation and
does not run the application again.

## API boundaries

`GET /api/portfolio/scenarios` reports readiness and fixed bundled scenarios.
`POST /api/portfolio/executions` takes a scenario and UUID request ID; it never
accepts code, plugins, destinations or filesystem paths. The server permits one
active execution. Identical request-ID reuse returns the original job;
conflicting reuse or a competing launch returns 409. Inspect progress using
`GET /api/portfolio/executions/{id}`.

The existing viewer role inspects data; ingestor/admin launches. Local auth-off
mode is convenient single-user development, not hosted authentication. Bind to
loopback and configure exact browser origins. Existing unfiltered routes remain
available; optional `cohort_id` scopes runs, statistics, costs and live events.

## Durability and investigation

Executions persist in additive SQLite tables. Restart marks unfinished jobs
interrupted; it never redispatches them. Partial trace records remain inspectable.
Application completion, job completion and telemetry delivery are separate
claims. Inspect all three before describing a run as complete.

Span-ID ingestion is idempotent only for identical sanitized content. Conflicting
reuse returns 409. Duplicate delivery cannot add token/cost totals, alerts or live
events. Terminal run outcomes cannot be reopened by delayed start messages.
Recorded spans determine aggregate counts. The live stream uses a durable
ingestion cursor so late-arriving spans remain observable; span timestamps retain
their application meaning.

Comparisons align logical stages and their occurrence/attempt. Missing stages
are visible. Unknown historical revisions remain unknown; incompatible scenario
revisions cannot support an implied repair comparison.

## Capture and export policy — 0.2.0 release candidate

The capture default changes in 0.2.0. New traces retain operation identity,
status, sizes and safe diagnostics. Raw input/output requires explicit opt-in.
Credential-shaped keys and supported credential patterns are redacted before
export and before new collector persistence. Historical data is redacted when
presented, without inventing capture provenance. This is not comprehensive PII
detection; do not send sensitive content merely because a redactor exists.

The bounded exporter accepts immutable sanitized snapshots, with 256 queued events,
64 KiB/event, one worker, batches up to 16 and drop-newest saturation. HTTP delivery
uses a 2-second timeout and at most 2 attempts; permanent validation/authentication
failures are not retried. Inspect delivered/dropped/failed/retries/unfinished,
not just queue emptiness. `flush()` remains callable; deadline-aware flush/close
cannot promise a blocked custom exporter has finished. Close rejects new events.
Telemetry errors must not replace application results.

Keep original inline exporters available for controlled use. Shipped workload
and instrumentation examples use bounded delivery. See the
[pinned GenAI subset](GENAI_CONVENTIONS.md) for the JSON interoperability boundary.

## Sample preview and failure recovery

Explicit sample entry uses fixed local data, not a backend. Its label stays
visible and Reset restores scenario, filters, selections and playback. Live
collector events and sample playback use distinct wording. Network/SSE failures
stay errors, with Retry and explicit sample entry. Switching sources closes old
subscriptions and discards obsolete responses.

## Retention and limitations

Local SQLite files and ignored artifacts are retained until manually removed.
Stop only the processes you launched before deleting a specifically identified
disposable database. No automatic retention cleanup or remote export destination
is configured. Never delete an existing owner's database during setup/testing.

This milestone does not establish hosted tenancy, paid-provider correctness,
production load capacity, arbitrary-power-loss guarantees or a formal
accessibility certification. See [verification](portfolio-verification.md) for
the exact observed gates and [walkthrough](portfolio-walkthrough.md) for review.
