# Security guide

AgentTrace stores prompts, tool I/O, model metadata, and cost data. Treat the
trace database and exported evidence as sensitive application data.

## Trust boundaries

The SDK runs inside the agent process. The collector applies request logging,
rate limiting, optional JWT authentication, role checks, and database
transactions. The dashboard is a browser client and must not be treated as a
trusted actor. Local SQLite and the optional PostgreSQL database are storage
boundaries, not secret stores.

The `agenttrace.issue_pr` SDK package treats issue text and plans as untrusted.
Its editor resolves paths before authorization, rejects traversal and symlink
escapes, applies allow/block policies, and protects secret/configuration paths.
Git mutations reject `main`/`master`, invalid refs/remotes, and all merges. Test
commands are exact argv allowlist entries executed with `shell=False` and a
finite timeout. A passing run stops at `awaiting_approval`; approval is required
before a draft-only sink can be invoked. The bundled sink records intent in
memory and performs no network request.

## Authentication and roles

Passwords are bcrypt-hashed and JWT bearer tokens expire according to
`ACCESS_TOKEN_EXPIRE_MINUTES`. The first local startup seeds `admin` / `admin123`
for the offline demo; replace or remove it before deployment.

Set `AUTH_REQUIRED=true` in a deployed environment. `viewer` can read
observability data, `ingestor` can additionally write runs/traces/OTLP, and
`admin` can delete runs, manage alert rules, and read audit logs. When auth is
optional, only a request with no token receives the synthetic offline identity;
invalid tokens still fail with `401`.

## Secrets and redaction

Keep `SECRET_KEY`, database credentials, and provider keys in environment
variables. Never commit `.env` files. Audit metadata recursively removes
passwords, bearer tokens, API keys, authorization headers, and password hashes.
The0.2.0 release candidate defaults SDK capture to summaries. Raw content is an
explicit opt-in. Supported credential keys/patterns are redacted before export
and new persistence; historical values are redacted on presentation. Bounded
depth and event sizes limit capture. This is not comprehensive PII detection:
exclude sensitive data upstream. Inspect capture provenance instead of assuming
historical records were collected under the current policy.

## Local bundled launcher

`PORTFOLIO_LAUNCH_ENABLED=true` explicitly enables two packaged, credential-free
scenarios when the SDK is installed. Ingestor/admin roles can launch; viewers can
inspect. Requests cannot supply Python, shell commands, paths, plugins or export
destinations. The server configuration owns the collector destination. Bind to
loopback and configure exact frontend origins. Restart interrupts unfinished
executions without automatic relaunch. No hosted multi-user authentication or
arbitrary workload execution is implied.

Identical sanitized span deliveries are idempotent; conflicting span-ID reuse
returns409. Run completion and export completion are separate. Queue saturation,
timeout and an unfinished custom exporter are visible delivery states, not
successful telemetry. See [actual setup and capture policy](portfolio-connected.md).

## Ingestion and exports

Native, canonical-adapter, and OTLP/JSON ingestion routes are rate-limited and
role-gated when auth is required. Inbound cost values are data, not executable
code, and are stored without re-evaluating producer prompts. Replay is read-only
and never re-executes a tool. OTLP export exposes stored metadata and must be
protected by the same network/auth controls as the rest of the API.

## Deployment checklist

- Override `SECRET_KEY` with a strong random value.
- Remove or change the seeded demo password.
- Set `AUTH_REQUIRED=true` and restrict `CORS_ORIGINS`.
- Terminate TLS at a reverse proxy and keep the database private.
- Prefer PostgreSQL for durable multi-process deployments.
- Use Redis only when multi-worker realtime/rate-limit coordination is needed.
- Redact sensitive payloads before exporting traces or publishing evidence.
- Keep Grafana and evidence artifacts behind the same access controls as traces.
- Keep issue/PR GitHub and planner providers opt-in; review their credentials,
  repository permissions, and approval integration before enabling them.

Hosted tenancy, external notification delivery, and hosted scheduling are not
implemented in this repository and are not implied by local RBAC. Live GitHub
PR creation, LLM planning, distributed workers, and server issue/PR routes are
not offline capabilities.
