# AgentTrace setup guide

## Prerequisites

- Python 3.11+
- Node.js 20+ for the dashboard
- Docker only for optional PostgreSQL/Redis integration

## Canonical install

```bash
python -m pip install -e "sdk[dev]"
python -m pip install -e "server[dev]"
cd dashboard && npm ci
```

The server wheel contains its internal compatibility subset. No sibling
checkout, external core package, credential, or network service is required.

## Start locally

```bash
cd server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# in a second terminal
cd dashboard
npm run dev
```

The server creates SQLite data under `server/data/` and exposes `/docs`; the
dashboard runs at `http://localhost:3000`.

## Offline proof

```bash
make demo
make evidence
make test
make lint
make typecheck
```

`make evidence` needs no credentials or network and verifies the normalized
golden fixture. See [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

## SDK smoke example

```python
from agenttrace import Tracer
from agenttrace.exporters.api_exporter import APIExporter

tracer = Tracer()
tracer.set_exporter(APIExporter(endpoint="http://localhost:8000/api"))
with tracer.run("setup-smoke"):
    span = tracer.start_span("llm_call")
    span.input_data = {"prompt": "Hello"}
    span.output_data = {"response": "Hi!"}
    span.end()
    tracer.end_span(span)
tracer.flush()
```

## Optional Docker services

```bash
docker compose up --build
```

Docker, PostgreSQL, Redis, and Grafana are integration surfaces, not default
requirements. Review [`docs/SECURITY.md`](docs/SECURITY.md) before deployment.
