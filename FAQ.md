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
**A:** Yes, through the supported OTLP HTTP/JSON subset. The SDK can export OTLP-shaped spans, and the server accepts or exports `ResourceSpans` at `/api/otlp/v1/traces`:
```python
from agenttrace.exporters.otlp import OTLPExporter

tracer.set_exporter(OTLPExporter(endpoint="http://localhost:4318/v1/traces"))
```
Protobuf/gRPC ingestion remains deliberately deferred. See [`docs/OTLP.md`](docs/OTLP.md).
