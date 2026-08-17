# Compatibility contracts

AgentTrace has two intentionally separate Python packages. The SDK is
dependency-light and independently installable. The FastAPI server owns its
compatibility layer under `server/app/internal/` and its vendored infrastructure
subset under `server/app/internal/vendor_core/`.

`agenttrace.issue_pr` is additive inside the SDK. Importing `agenttrace` keeps the
existing top-level exports and behavior unchanged; callers opt in with
`agenttrace.issue_pr`. No server route, ingestion key, span vocabulary, cost
calculation, exporter, or default behavior changed with the absorption.

## Canonical payloads

`CanonicalSpan` and `CanonicalCostRecord` accept dictionaries, Pydantic models,
and compatible objects. `normalize_span()` and `normalize_cost_record()` map
camelCase and snake_case keys, preserve the existing enum vocabulary, and map
unknown span/status values to the server's safe fallback values. Existing
`SharedSpanIngest` and `CostRecordIngest` imports remain aliases for callers that
already use those names.

Adapters do not recompute an inbound cost. The value supplied by a producer is
stored verbatim, while the server's reporting registry is used for native
server-side metrics. The SDK's `CostTracker.PRICING` table is SDK-local and is
golden-tested independently; changing it is a separate compatibility decision.

## Golden parity

The server tests cover canonical span/cost round trips, existing run and trace
response keys, OTLP response shape, alert decisions, mocked auth/database flows,
and dashboard demo data. Add a fixture before changing score- or cost-sensitive
behavior. A clean wheel install must import `app.main`, configuration, database,
tracing, and pricing without any external package beyond declared extras.

The checked-in contract set is under
`server/tests/fixtures/golden/`: `sdk-costs.json`, `replay-payload.json`,
`run-trace-responses.json`, `canonical-round-trips.json`,
`alert-decisions.json`, `auth-database.json`, `otlp-response.json`, and
`dashboard-demo.json`. `test_golden_fixtures.py` keeps the set parseable and
ensures the public response sections remain present.

The SDK issue/PR tests pin deterministic issue/plan serialization, sandbox and
symlink refusal, protected branches, bounded `shell=False` tests, approval and
draft-only behavior, audit ordering/redaction, provider-absent offline behavior,
and replay. The portfolio evidence fixture adds a normalized end-to-end scenario.

## Provenance

The small server infrastructure subset is copied into the repository with
attribution and a source commit in `THIRD_PARTY_NOTICES.md`. The runtime imports
point only at the EvalForge-owned namespace. This keeps the default build
reproducible and makes future upgrades reviewable.
