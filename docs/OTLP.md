# OTLP HTTP/JSON

AgentTrace exposes a deliberate JSON subset of the OTLP traces HTTP contract:

- `POST /api/otlp/v1/traces` accepts `resourceSpans`, resource attributes,
  instrumentation scope, span attributes, events, links, trace state, status,
  and nanosecond timestamps;
- `GET /api/otlp/v1/traces` exports the stored spans with the same metadata;
- malformed attribute values are rejected or normalized with a clear HTTP
  validation response;
- `partialSuccess.acceptedSpans` and the existing response keys are preserved.

AgentTrace adds its cost, model, provider, usage, and sampling values as
namespaced attributes. Resource and scope values are retained in trace metadata
so round trips remain inspectable. Protobuf and gRPC are explicitly deferred;
JSON is the supported offline and CI contract.

For a minimal request, send an OTLP `ExportTraceServiceRequest` with one
`resourceSpans` entry and a `scopeSpans.spans` list. The integration tests in
`server/tests/test_otlp.py` are the executable contract.
