# AgentTrace FAQ

## Q: How do I export traces to another system?
**A:** Use `tracer.export()` to get JSON, then POST to `/api/traces` on the backend.

## Q: Can I use this with OpenTelemetry?
**A:** Not yet. Phase 3 of the roadmap includes OTLP export for compatibility with Jaeger, Zipkin, and Datadog.
