# AgentTrace Setup Guide

## Prerequisites

- Python 3.12+
- Node.js 20+ (for dashboard)
- Docker (optional, for PostgreSQL)

## SDK Setup

```bash
cd sdk
pip install -e ".[dev]"
```

## Server Setup

```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server auto-initializes an SQLite database at `./data/agenttrace.db`.

## Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

## Quick Test

```python
from agenttrace import Tracer
from agenttrace.exporters.api_exporter import APIExporter

tracer = Tracer()
tracer.set_exporter(APIExporter(endpoint="http://localhost:8000/api"))

with tracer.run("test_operation"):
    span = tracer.start_span("llm_call")
    span.input_data = {"prompt": "Hello"}
    span.output_data = {"response": "Hi!"}
    span.end()
    tracer.end_span(span)

tracer.flush()
```

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```
