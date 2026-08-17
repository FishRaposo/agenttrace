# Changelog

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
