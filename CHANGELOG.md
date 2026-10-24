# Changelog

## 2026-10-24 — in-place portfolio audit and publish preparation

- normalized hash-pinned evidence fixtures to LF bytes via `.gitattributes` and
  re-pinned `docs/evidence/**` and `dashboard/public/evidence/**` digests so the
  connected-evidence verifier passes on LF checkouts (Linux/macOS CI);
- added the `connected-live` hosted CI job: a disposable loopback collector
  plus production dashboard running the HTTP integrity/persistence verifiers
  and the connected Playwright suite on Linux;
- added an axe-core WCAG 2.1 A/AA Playwright suite (8 scans) and repaired two
  real `label-content-name-mismatch` defects: run-lane links whose accessible
  name omitted visible text, and the theme toggle whose label did not contain
  its visible state;
- added Open Graph/Twitter metadata alongside the existing app icon; cleared
  the last dev-chain `zod` advisory in range (npm audit now reports zero).

## 2026-08-16 — issue-to-draft-PR safety absorption

- added the dependency-free `agenttrace.issue_pr` SDK package with deterministic
  providers, sandbox/Git/test guards, explicit approval, draft-only intent,
  ordered audit/trace events, redaction, and replay;
- extended the offline evidence bundle and verifier with the absorbed workflow,
  normalized golden output, exact file/checksum coverage, and corruption tests;
- recorded the `github-issue-pr-agent@01a2404` lineage and source mapping while
  keeping live providers, server routes, and hosted automation deferred.

## 2026-08-14 — browser gate stabilization

- serialized the Playwright workers because the offline demo fixtures and Next
  development compiler share one process; parallel workers could render the
  navigated page before its URL state settled.

## 2026-08-14 — comprehensive portfolio finalization

- made the FastAPI server self-contained with an attributed internal vendor/core
  subset and aligned SDK/server/wheel/Docker/CI install paths;
- added canonical span/cost compatibility contracts, richer OTLP HTTP/JSON,
  deterministic head/tail sampling, and optional Redis realtime transport;
- added persisted local alert state, single-tenant RBAC, redacted audit logs,
  Grafana dashboard JSON, and an offline evidence bundle with golden checksums;
- reconciled setup, security, replay, architecture, roadmap, provenance, and
  contribution documentation.

Hosted/team workflows, external notification/scheduling, OTLP protobuf/gRPC,
and mandatory infrastructure services remain deferred by design.
