# Engineering roadmap

This file is the repository-local companion to [`../ROADMAP.md`](../ROADMAP.md).
The local engineering deferrals from the migration pass are now delivered or
explicitly bounded:

| Area | Status | Evidence |
| --- | --- | --- |
| Server compatibility core | Delivered | `server/app/internal/vendor_core/`, `docs/COMPATIBILITY.md` |
| SDK/server pricing boundary | Delivered | `docs/COMPATIBILITY.md`, pricing fixtures |
| Canonical span and cost adapters | Delivered | `server/app/internal/contracts.py`, adapter tests |
| OTLP JSON metadata | Delivered | `docs/OTLP.md`, `server/tests/test_otlp.py` |
| Deterministic head/tail sampling | Delivered | `docs/SAMPLING.md`, sampling fixtures |
| Realtime transport | Delivered locally | `docs/REALTIME.md`, in-memory tests; Redis optional |
| Stateful local alerting | Delivered locally | `docs/ALERTING.md`, alert state tests |
| RBAC and redacted audit | Delivered locally | `docs/RBAC_AUDIT.md`, role-matrix tests |
| Grafana artifact | Delivered locally | `monitoring/grafana/agenttrace-overview.json` |
| Reproducible evidence | Delivered | `docs/EVIDENCE.md`, `make evidence` |
| Hosted/team workflows | Deferred | Product scope, no hosted service |
| External notification/scheduling | Deferred | Local memory/log sinks only |
| OTLP protobuf/gRPC | Deferred | JSON-only contract |

The SDK remains independently installable. No sibling checkout, external core
package, credential, or network service is required by default.
