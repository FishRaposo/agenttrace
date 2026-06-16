# Roadmap

Product roadmap: [../ROADMAP.md](../ROADMAP.md). This file tracks engineering follow-ups
from the migration onto `shared_core`.

## Now
- ✅ Server adopts `shared_core` (config/logging/errors/DB/rate-limit).
- ✅ SDK kept standalone (`shared_core`-free, pip-installable); import cycle fixed.
- ✅ Standard spine (Makefile, ruff, pyright, CI installing shared-core, offline demo).
- ✅ Fixed a `shared_core` `to_async_url` sqlite double-rewrite bug (regression-tested).
- ✅ **Cross-service ingestion:** the collector accepts canonical `shared_core.tracing.Span`
  objects (`POST /api/traces/spans`) so `hermes-agent-framework` can emit natively, and
  LCM-style `CostRecord`s (`POST /api/traces/costs`). Thin adapters; cost taken verbatim.
- ✅ **Threshold alerting:** cost (`GET /api/alerts`) and latency (`GET /api/alerts/latency`)
  rules, stateless and polled.
- ✅ **Best-effort OTLP interop:** `GET`/`POST /api/otlp/v1/traces` (JSON subset) export and
  ingest with AgentTrace cost/token attributes preserved.
- ✅ **Dashboard demo-mode:** offline fixtures + visible banner so the UI works with no
  backend; vitest component tests + a Playwright demo smoke spec.

## Next
- Converge the **server's** cost computation on `shared_core.pricing` (the SDK's table
  stays local — the SDK cannot import `shared_core`). *Deferred: would change pinned numeric
  cost outputs; requires a golden-output gate first (see EXECUTION_PLAN.md).*
- Promote OTLP interop from the JSON subset toward fuller spec coverage (resource attributes,
  span events/links).
- Stateful alert routing (dedup, notification sinks) on top of the polled rules.

## Later
- Optional Postgres + Redis-backed rate limiting in production (compose already provides both).
- Server Docker packaging for `shared_core` (currently installed via git in the image).
- Protobuf + gRPC OTLP (currently an explicit non-goal; JSON-only by design).

## Intentionally not building (now)
- Coupling the SDK to `shared_core` (it must remain a standalone install).
- Renaming `server/` to `services/api/` (the three-part SDK/server/dashboard layout is the
  project's identity and is documented in AGENTS.md).
