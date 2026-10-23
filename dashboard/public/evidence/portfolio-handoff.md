# Project 04 AgentTrace handoff — 2026-10-23

Implemented and locally verified AT-01–AT-07 on `feat/agenttrace-portfolio`,
base `c721c3f07cb5f61b358dfe25fbc77d2e147aec92`. The local commit containing
this record is the delivery; no push or public release is authorized by it.
SDK, collector and dashboard versions are 0.2.0, documented as a release candidate
because capture defaults change to summaries. Original golden evidence remains
unchanged. No mandatory sibling-project dependency was added.

## Read in this order

1. [README](../README.md) and [three-minute walkthrough](portfolio-walkthrough.md).
2. [Actual workflow/setup](portfolio-connected.md), [baseline](portfolio-baseline.md)
   and [case study](portfolio-case-study.md).
3. [Verification and limitations](portfolio-verification.md), committed
   [connected observations](evidence/connected/report.json),
   [integrity proof](evidence/connected/integrity.json),
   [restart record](evidence/connected/restart.json),
   [raw benchmark](evidence/tracing-benchmark.json) and [screenshots](screenshots/README.md).
4. [Architecture](ARCHITECTURE.md), [security/capture](SECURITY.md),
   [SDK](SDK.md), [playback](REPLAY.md) and [pinned GenAI mapping](GENAI_CONVENTIONS.md).
5. External [project plan](../../plans/agenttrace.md) and
   [portfolio index](../../PORTFOLIO_PLAN.md) before choosing another project.

## Delivered and checked

Context-local tracing, child/thread ownership, terminal cancellation and actual
ASGI streaming; bounded sanitized export with deadline/counter truth; idempotent
durable ingestion/aggregates/cursors; fixed-scenario dashboard/CLI launch with
durable deduplication and restart interruption; coherent connected investigation
and independent offline guided/free preview. A retrieval repair does not repair
the independent timeout or cancellation. Recorded playback is inspection.

Final observed results: SDK-only 169 pass/2 optional skips (80.59%); equipped SDK
171 pass; collector 124 pass (68.57%); Ruff/149 format-clean/Pyright zero; original
and new evidence, forbidden scan, source/wheels and fresh outside-checkout installs
pass. Frontend 41 units/lint/build; real production browser 3/3 and offline 3/3
across all three required viewports pass. Six independent-review findings were
fixed and rechecked. Benchmark contains 18 repetition records, 1,800 measured
requests and 360 warm-ups. Exact contracts, commands and raw observations are in
the verification record; this paragraph does not claim hosted CI.

Ignored local command logs, RED/GREEN records and reviewer reports are under
`C:/Projects/operation-fan-the-hammer/.tmp/agenttrace-20261023`; disposable
acceptance data/logs are under this clone's `.tmp/connected-acceptance-20261023`.
They include pre-repair failures and must not be confused with final passing
observations. Committed JSON/checksums are the portable evidence package.

## Review runtime and next owner

Separate local review endpoints: dashboard `http://localhost:3404`, collector
`http://127.0.0.1:8300`. Review data is a new disposable
`.tmp/connected-review-20261023/agenttrace.db`, distinct from acceptance data.
Launcher is explicitly enabled, credentials are cleared, sampling is off,
loopback binding and exact 3404 origins are configured. The local collector rate
limit is raised to 100,000/60 seconds for this disposable review instance only.
Do not carry auth-off/benchmark settings into a hosted deployment.

Owner's next action: investigate Incident, compare the retrieval repair, inspect
timeout/cancellation and then launch a fresh cohort explicitly. Agent's next
action after review: consult the portfolio index; no other application upgrade
is part of this milestone. GroundTruth/Gateway integration remains optional.

Sources checked on 2026-10-23: source/tests, actual Python/CLI/HTTP/SQLite/production
browser behavior, installed framework documentation, official pinned GenAI files
and maintainer advisories, built distributions and isolated installs. All provider
answers/usage/pricing in the workload are labeled synthetic/illustrative; real
services, native/model/human evaluation, hosted CI and publication are unverified.
Five high dev-ESLint advisories remain; runtime audit is clear. Broader root
validator decoding and copy-all harness limitations are recorded separately.

IDs: AT-01–AT-07, supporting existing FTH-016. No new opportunity/experiment,
proposal/message, cash ledger change or observed receipt. Cash status unknown.
