# AgentTrace FAQ

## Q: How do I export traces to the dashboard?
**A:** Configure the `APIExporter` and call `tracer.flush()`:
```python
from agenttrace import Tracer
from agenttrace.exporters.api_exporter import APIExporter

tracer = Tracer()
tracer.set_exporter(APIExporter(endpoint="http://localhost:8000/api"))
# ... run your agent ...
tracer.flush()
```

## Q: Can I use this with OpenTelemetry?
**A:** Yes. The SDK includes an OTLP exporter that converts AgentTrace spans to OpenTelemetry format and sends them to any OTLP-compatible backend (Jaeger, Zipkin, Datadog, etc.):
```python
from agenttrace.exporters.otlp import OTLPExporter

tracer.set_exporter(OTLPExporter(endpoint="http://localhost:4318/v1/traces"))
```
