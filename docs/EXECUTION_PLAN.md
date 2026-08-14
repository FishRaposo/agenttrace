# Execution record

This document records the comprehensive AgentTrace finalization pass. The
baseline SDK suite had 88 passing tests; server collection was blocked by an
external runtime package. Work was performed in independently verifiable slices
with golden fixtures before behavior-sensitive refactors.

## Delivered slices

1. **Baseline and provenance** — captured the clean baseline, pinned the
   archived source commit, and recorded the internal-core decision.
2. **Self-contained packaging** — vendored only the server-used compatibility
   subset, rewrote imports, aligned SDK/server extras and Docker/CI installs,
   and added MIT/attribution notices.
3. **Compatibility contracts** — normalized canonical span/cost objects while
   preserving keys, enum fallbacks, cost values, and existing route behavior.
4. **OTLP and sampling** — added JSON resource/scope/event/link support plus
   deterministic head/tail decisions and buffered-run tests.
5. **Realtime, alerts, RBAC, audit** — added a pluggable in-memory/Redis
   publisher, persisted alert state, local role checks, and recursive redaction.
6. **Evidence and portfolio surface** — added the offline golden fixture,
   checksum verifier, Grafana artifact, CI gates, docs, public catalog updates,
   and a machine-readable receipt.

## Verification contract

Every slice must keep the SDK/server tests, Ruff, Pyright, package install, and
offline evidence green. Frontend CI runs `npm ci`, Vitest, lint, production
build, and a Chromium Playwright smoke test. No real provider credentials or
network-backed evaluation is a required gate.

## Boundaries retained

Hosted/team workflows, hosted scheduling, external notification delivery, OTLP
protobuf/gRPC, mandatory infrastructure services, and cross-repository agent
changes remain explicitly deferred.
