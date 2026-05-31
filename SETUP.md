# AgentTrace Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)

## SDK Setup

```bash
cd sdk
pip install -e .
```

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

## Quick Test

```python
from agenttrace import Tracer, start_span

tracer = Tracer()
with start_span("test_operation") as span:
    span.set_tag("model", "gpt-4")
    # ... your code ...

# Export to backend
import requests
requests.post("http://localhost:8000/api/traces", json=tracer.export())
```

## Prometheus

Metrics available at: http://localhost:8000/metrics
