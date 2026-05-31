# AgentTrace Architecture

## Overview

AgentTrace provides OpenTelemetry-compatible tracing for AI agent systems.

## Components

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Python SDK  │────▶│  FastAPI     │────▶│  PostgreSQL  │
│  (agenttrace)│     │  Backend     │     │  (trace db)  │
└──────────────┘     └──────────────┘     └──────────────┘
        │                   │
        ▼                   ▼
┌──────────────┐     ┌──────────────┐
│  Prometheus  │     │  Next.js     │
│  /metrics    │     │  Dashboard   │
└──────────────┘     └──────────────┘
```

## Span Model

- **trace_id** — UUID for a complete request
- **span_id** — UUID for an operation within a trace
- **parent_id** — Hierarchical relationship
- **tags** — Key-value metadata
- **events** — Timed log entries

## Observability

- Prometheus metrics at `/metrics`
- Grafana dashboard JSON for trace volume and latency
- Trace diffing for regression detection
