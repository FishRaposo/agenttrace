# Design decisions

This file records the current architectural boundaries. Historical migration
notes retain their original provenance under `docs/migrations/`.

## Keep the SDK independent

The SDK is a standalone install with its own schemas and pricing table. It never
imports server code, a sibling checkout, or the server's vendored compatibility
subset. This keeps instrumentation safe to embed in an agent process.

## Own the server compatibility layer

The server uses `CanonicalSpan`, `CanonicalCostRecord`, and normalization helpers
under `server/app/internal/`. The exact infrastructure subset needed by the
server is vendored under `vendor_core`, attributed and pinned in
`THIRD_PARTY_NOTICES.md`. This was chosen over restoring an external runtime
dependency so wheels, Docker, and offline CI are self-contained.

## Preserve cost semantics

Native SDK costs use the SDK-local pricing table. Inbound canonical costs are
stored verbatim. Server reports use the vendored registry for server-native
metrics. Any future numeric change requires a captured golden fixture first.

## JSON-only OTLP boundary

The collector supports OTLP HTTP/JSON resource and span metadata, events, links,
status, timestamps, export, and ingest. Protobuf/gRPC are deferred to keep the
portfolio slice small, inspectable, and credential-free.

## Local operational primitives

Sampling, realtime publication, alert state, RBAC, and audit logging are local
interfaces with optional integrations. SQLite, in-memory realtime, optional
Redis, and local/log alert sinks are enough for the default demo. Hosted/team
tenancy, hosted scheduling, and external notification delivery remain product
boundaries rather than hidden dependencies.

## Evidence before expansion

The offline evidence bundle and golden fixture are the regression gate for
portfolio-facing changes. It records canonical trace/cost behavior, OTLP
metadata, sampling, realtime, alert, RBAC, audit, and replay-shaped output.

## Absorb issue-to-PR safety into the SDK

The reusable safety core from `github-issue-pr-agent` belongs in the standalone
SDK, not in a second server product. The port keeps provider protocols,
deterministic mocks, sandbox/Git/test guards, approval, draft-only intent, audit,
and replay, while rejecting the source server and external `shared_core`
dependency. The full source mapping and rejected alternatives are recorded in
the dated decision record.
