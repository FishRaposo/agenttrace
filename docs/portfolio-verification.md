# AgentTrace local verification — 2026-10-23

AT-01–AT-07 are implemented and verified on `feat/agenttrace-portfolio`, from
`c721c3f07cb5f61b358dfe25fbc77d2e147aec92`. This is the **0.2.0 local release
candidate**. The SDK, HTTP delivery, persistence, workload concurrency and browser
interactions are real. Bundled provider responses, usage and prices are synthetic.
No hosted CI or publication of these changes is claimed.

## Observed gates

All passing commands below returned exit 0. Logs and disposable databases are
retained locally under ignored `.tmp` directories; committed observations below
remain inspectable without that machine-specific test environment.

| Gate | Final observed result |
| --- | --- |
| SDK-only, FastAPI absent | 169 passed, 2 optional-integration skips; 80.59% statement coverage |
| Complete SDK with optional integration dependencies | 171 passed, including 8 actual ASGI lifecycle tests |
| Collector suite | 124 passed; 68.57% statement coverage, reported without inventing an 80% floor |
| Ruff / formatting / Pyright | All checks pass; 149 Python files format-clean; 0 type errors or warnings |
| Original evidence and dependency boundary | Golden generation/verification and forbidden-dependency scan pass |
| Packages | SDK/server source and wheel builds; required wheel modules verified |
| Fresh installs outside checkout | SDK alone without FastAPI; collector alone without SDK; collector plus installed SDK; pip check for both environments; installed CLI to real HTTP collector |
| Frontend | 41 unit tests across 10 files; ESLint and connected production build pass |
| Production connected browser | 3 complete journeys pass against real FastAPI/SQLite/Next processes, no successful API mocks |
| Independent offline browser | 3 complete journeys pass with zero backend/provider/external requests |
| Browser layouts | All routes at 390×844, 768×1024 and 1440×900; keyboard/focus, reduced motion, contrast and clipping checked |
| Actual HTTP integrity | Concurrent root creation, duplicate delivery, conflict 409, redaction, late-event cursor resume and real SDK OTLP JSON pass |
| Restart | Accepted unfinished execution becomes interrupted, identical request deduplicates, no automatic redispatch; earlier completed cohorts remain intact |
| Benchmark | 18 condition/repeat records; 1,800 measured requests and 360 warm-up requests; delivery counters checked |
| Independent review | Six material findings reproduced, repaired and rechecked; no outstanding finding in the bounded review |

The final production build was repeated after the documentation and wording
changes. Thirteen screenshots were then recaptured from that build against a
fresh review database; real connected detail/comparison, sample isolation and
served evidence files passed again. The capture helper initially assumed the
sample error wording and a textbox role for a datalist input. Correcting those
harness assumptions required no application change. CI now includes the actual
ASGI command and committed-evidence verifier; their local executions pass, while
hosted execution of that workflow remains unobserved.

The baseline was 132 SDK tests/75% and 98 collector tests/68%, plus 29 frontend
units. Original browser verification was bounded after compilation/navigation
timeouts at 8/12; it did not pass. The final suites replace that incomplete result.
See [baseline](portfolio-baseline.md) for environment failures and RED evidence.

## Reproducible connected observations

- [Scenario report](evidence/connected/report.json) and [checksum](evidence/connected/report.sha256):
  real dashboard-compatible launches produce 20 distinct runs per cohort,
  56 incident / 58 repaired spans, 2,720 / 2,880 synthetic tokens and
  $0.0034 / $0.0036 illustrative totals. Incident is 17 completed, 2 failed,
  1 cancelled; repaired is 18 completed, 1 failed, 1 cancelled. Retrieval alone
  is repaired. Delivery is 96/98 events with zero drops, failures or unfinished work.
- [Integrity probe](evidence/connected/integrity.json): twenty simultaneous root
  requests, identical span retries with unchanged aggregates, conflicting reuse
  rejected with 409, redaction before persistence/presentation, a late application
  timestamp delivered through the newer durable ingestion cursor, and an actual
  cancelled SDK OTLP root with provider/model and 7 input / 3 output tokens.
- [Process-restart observation](evidence/connected/restart.json): an accepted job
  was interrupted before any run reached storage. That observation does not claim
  partial spans in this particular run. Separate collector tests establish
  preservation of partial records. Restart never relaunches an uncertain job.
- [Screenshots](screenshots/README.md): actual rendered failure, comparison and
  request-cohort views, with desktop/tablet/mobile coverage. Screenshots illustrate
  behavior; the real-process assertions and stored records establish it.

The first HTTP inspection exposed double-counted root aggregates. Benchmark
traffic then exposed a concurrent run-creation race; actual OTLP exposed mutable
root-ID reuse and batch atomicity. Those observations were preserved before fixes.
Final measurements below use the repaired collector/SDK, not the earlier output.

## Benchmark observations

Raw [measurements](evidence/tracing-benchmark.json) and
[checksum](evidence/tracing-benchmark.sha256) were recorded on Windows 11,
Python 3.12.14. Each condition has 20 warm-up requests and 100 measured requests,
repeated three times. Values below are medians of the three repetition summaries;
p95 is a per-repetition nearest-rank percentile, not a pooled percentile.

| Concurrency | Tracing condition | p50 ms | p95 ms | Throughput requests/s |
| --- | --- | --- | --- | --- |
| 1 | disabled | 46.422 | 47.553 | 22.74 |
| 1 | local | 46.242 | 47.691 | 22.99 |
| 1 | http | 46.332 | 47.802 | 8.92 |
| 20 | disabled | 15.147 | 15.821 | 1289.19 |
| 20 | local | 21.981 | 35.623 | 593.84 |
| 20 | http | 27.505 | 44.382 | 7.06 |

“local” performs bounded JSON serialization without disk/network I/O; “http”
uses the actual collector. The queue is 256 events, 64 KiB/event, batches up to
16, one worker, drop-newest, HTTP timeout 2 seconds and at most 2 attempts.
The dedicated collector limit was 100,000 requests/60 seconds so its normal
100/60 limiter did not dominate this local measurement. Sampling was off.
Every measured repetition records 85 completed, 10 failed and 5 cancelled
application requests from the fixed incident workload. All delivery checks are
complete, with zero dropped, failed or unfinished exports; raw counters include
retries. Latency excludes final exporter shutdown; throughput includes cohort
drain. No build/browser workload was run concurrently by this task, but other
owner services and normal OS activity remained present. These short synthetic
tasks are not a production-capacity benchmark or a universal overhead percentage.

## Reproduce the gates

Follow [actual setup](portfolio-connected.md). Use separate SDK-only and equipped
environments; install only `sdk[dev]` in the former. From the corresponding package
directory run `python -m pytest -q --cov=agenttrace` or `--cov=app` (collector).
Run the equipped SDK suite too, so optional ASGI checks are not merely skipped.
From the repository root:

```bash
python -m ruff check server/app sdk/agenttrace examples server/tests sdk/tests scripts
python -m ruff format --check server/app sdk/agenttrace examples server/tests sdk/tests scripts
python -m pyright server/app sdk/agenttrace
python scripts/portfolio_demo.py
python scripts/verify_portfolio_evidence.py
python scripts/check_forbidden_dependencies.py
python -m build sdk
python -m build server
python scripts/check_wheel_contents.py
python scripts/verify_connected_portfolio.py --endpoint http://127.0.0.1:8300
python scripts/verify_connected_integrity.py --endpoint http://127.0.0.1:8300
python scripts/benchmark_portfolio_tracing.py --collector-rate-limit 100000
python scripts/verify_connected_evidence.py
# Independently verify the committed observations instead of newly generated ones:
python scripts/verify_connected_evidence.py --connected docs/evidence/connected/report.json --benchmark docs/evidence/tracing-benchmark.json
```

Fresh wheel checks used new virtual environments and an outside-checkout working
directory, not editable imports. An initial server smoke harness assumed every
FastAPI route object had `.path`; switching that assertion to public OpenAPI paths
repaired the harness. The unchanged installed server then passed independently.

From `dashboard`, run `npm ci`, `npm test`, `npm run lint`, `npm run build`.
Finish the build before starting the production server and browser suites.
Use `PLAYWRIGHT_EXTERNAL_SERVER=1`, `PLAYWRIGHT_PORT=3404`, and
`AGENTTRACE_API_URL=http://127.0.0.1:8300`. The live suite additionally requires
`AGENTTRACE_LEGACY_RUN_ID`, the UUID of an intentionally seeded legacy-shaped
record, and accepts `AGENTTRACE_SCREENSHOTS` for output. The sample suite sets its
own source preference and rejects external requests. Chromium must be installed;
`PLAYWRIGHT_EXECUTABLE_PATH` can select the installed binary.

```bash
npm run test:e2e -- --project=chromium
npm run test:e2e:live -- --project=chromium
```

Run browser suites separately from each other, builds and timing benchmarks.
For restart verification stop only the dedicated collector you launched, retain
its disposable SQLite file and start it with the same settings. Do not reuse an
owner database. Recorded playback never re-executes the workload.

## Review and limits

Independent bounded review found two SDK lifecycle bugs (late child cleanup
masking the application error, modern ASGI disconnect status), two collector
bugs (historical diff redaction and malformed ordinal handling) and two UI bugs
(uncertain launch retry identity and overlapping sample stage clocks). All six
have regression coverage and fresh rechecks. Parent verification additionally
checked all ten cost JSON/CSV presentation paths for historical redaction,
collision-preserving totals and unchanged stored records.

Runtime npm audit reports zero findings. Five high findings remain in the ESLint
development dependency chain; no forced major downgrade was applied. Official
advisories and dependency changes are dated in the baseline. The remaining chain
is `eslint-config-next` → `@next/eslint-plugin-next` → `fast-glob` → `micromatch`
→ `braces`; the audit counts the direct advisory and its four dependents.
Capture redaction
is not comprehensive PII detection; unknown custom metadata remains the caller's
responsibility. An arbitrary blocked custom exporter may outlive `close` and is
reported unfinished. The GenAI mapping is a [pinned JSON subset](GENAI_CONVENTIONS.md),
not protobuf/gRPC or universal compatibility.

Local checks used Python 3.12.14 and Node 24.21.0 on Windows; system Python 3.14
was not replaced. Fresh hosted CI/Python 3.11/Linux, other optional provider
instrumentors against real services, PostgreSQL/Redis deployment, native/model
quality, formal accessibility certification, arbitrary power loss, paid providers,
public hosting/publication and hosted multi-user authentication remain unverified
or outside scope. Root overview guard passes. The broader operation validator
cannot decode existing nested files, and its copy-all unit harness was not rerun;
these are not passing project gates. See [handoff](portfolio-handoff.md).

## 2026-10-24 — audit refresh (this section extends, not supersedes)

An in-place audit of `feat/agenttrace-portfolio` re-verified every gate above:
SDK 171 passed/81%, server 124 passed/69%, ASGI lifecycle 8, ruff check+format
149 files, pyright 0, portfolio-demo + evidence + connected-evidence verifiers,
forbidden-dependency scan, 0.2.0 wheel build/contents/isolated import outside
the checkout; dashboard 41 units, eslint 0 warnings, production build 8 routes,
npm audit **zero** findings (dev `zod` advisory cleared in range), 3/3 offline
and 3/3 real-process connected browser journeys.

Repairs/additions: hash-pinned evidence fixtures were CRLF-based on Windows
and would have failed the hosted evidence verifier on LF checkouts —
`.gitattributes` now pins them to LF and all four `.sha256` digests were
re-pinned (verified locally on LF bytes). A new `connected-live` CI job runs a
disposable loopback collector + production dashboard through the HTTP
integrity/persistence verifiers and the connected Playwright suite on Linux.
A new axe-core suite (8 scans, WCAG 2.1 A/AA) found and repaired two real
`label-content-name-mismatch` defects — run-lane links whose accessible name
omitted a visible-text separator, and the theme toggle whose label excluded
its visible state; Open Graph/Twitter metadata added. Bounded review of the
new launch/dedup/lease, ingestion fingerprint dedup, endpoint bounds (all
paginated `le=100..500`), draft-only issue-PR boundary and loopback-only
collector URL found no additional defects.

Limits unchanged: no native/model/human claims, no Docker/PostgreSQL
verification locally (the docker-build job is exercised by hosted CI only),
no formal accessibility certification. **Hosted status:** pending — this audit
commits ahead of the first push; PR and hosted-run identifiers are recorded
in the project handoff and parent index after merge.
