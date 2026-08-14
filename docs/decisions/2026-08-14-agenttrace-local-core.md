# AgentTrace local core decision

**Date:** 2026-08-14

## Decision

AgentTrace keeps its standalone SDK and owns the server compatibility layer. The
server vendors only the modules it actually uses from
`operator-shared-core@dbf276a7708da65b55e1f10b35af634b300d1f07` under
`server/app/internal/vendor_core/`. Runtime imports use the `app.internal`
namespace, and canonical ingestion models live in AgentTrace-owned modules.

## Why

The server previously depended on a sibling checkout and a public Git URL, which
made a clean install impossible. A narrow vendor preserves the current wire
contracts and database behavior without making the archived package a new
runtime dependency.

The SDK's pricing table stays local because the SDK is deliberately standalone.
Server pricing uses the vendored registry and is protected by numeric golden
fixtures.

## Deferred boundaries

Hosted/team tenancy, external alert delivery and scheduling, OTLP protobuf/gRPC,
and changes to `aria-agent` remain out of scope. Redis, PostgreSQL, and Grafana
are optional integrations; SQLite and in-memory realtime are the portfolio path.
