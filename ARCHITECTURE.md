# AgentTrace Architecture

## Overview

AgentTrace provides OpenTelemetry-compatible tracing with FinOps capabilities for AI agent systems.

## Components

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Python SDK  │────▶│  FastAPI     │────▶│  SQLite/PG   │
│  (agenttrace)│     │  Server      │     │  (trace db)  │
└──────────────┘     └──────────────┘     └──────────────┘
        │                   │
        ▼                   ▼
┌──────────────┐     ┌──────────────┐
│  OTLP Export │     │  Next.js     │
│  (optional)  │     │  Dashboard   │
└──────────────┘     └──────────────┘
```

## Span Model

- **run_id** — UUID for a complete agent run
- **span_id** — UUID for an operation within a run
- **parent_span_id** — Hierarchical relationship
- **span_type** — `llm_call`, `tool_call`, `decision`, `retrieval`, `custom`
- **metadata** — Key-value metadata including model, provider, feature
- **cost_usd** — Cost attribution per span
- **token_usage** — Prompt/completion/total tokens

## Observability

- Health check at `/health`
- Cost analytics API at `/api/costs/*`
- Budget tracking at `/api/budgets`
- Live SSE tail at `/api/stream`
- Trace diffing for regression detection
