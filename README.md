# AgentTrace

[![CI](https://github.com/FishRaposo/agenttrace/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/FishRaposo/agenttrace/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)]()
[![Next.js](https://img.shields.io/badge/Next.js-000?logo=next.js)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)]()

**OpenTelemetry-compatible observability + FinOps for AI agents.**

Trace LLM calls, tool executions, and multi-step workflows with **automatic cost tracking**, **budget alerts**, **live tail**, and **waterfall replay**.

[Quick Demo](#quick-demo) • [Architecture](#architecture) • [SDK Guide](#quickstart-local-development) • [Deploy](#deployment)

---

## Quick Demo

```bash
make demo
```

Starts the trace server, dashboard, and runs a sample agent with full observability at http://localhost:3000

---

## 1. What This Is

A lightweight observability and replay layer for debugging agentic AI workflows. AgentTrace records tool calls, model invocations, intermediate decisions, input/output, latency, cost, and final results, enabling step-by-step replay and analysis of agent behavior.

## Problem It Solves

Agentic AI workflows are complex, multi-step processes that involve:
- Multiple LLM calls with different prompts
- Tool invocations (search, code execution, API calls)
- Decision points and branching logic
- State management across steps

Debugging these workflows is challenging because:
- You can't see what happened during execution
- It's hard to understand why an agent made a particular decision
- Cost and token usage are opaque
- Reproducing issues is difficult

AgentTrace solves this by providing a complete execution trace with rich metadata, cost tracking, and replay capabilities.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Agent Code     │────▶│  SDK         │────▶│  APIExporter     │
│  (Your App)     │     │  Tracer      │     │  (HTTP / Batch)  │
└─────────────────┘     └──────────────┘     └──────────────────┘
                              │                        │
                              │ trace_openai()         │
                              │ trace_anthropic()      │
                              │ trace_llm()            ▼
                              │                 ┌──────────────┐
                              │                 │  Server      │
                              │                 │  FastAPI     │
                              │                 │  SQLAlchemy  │
                              │                 │  SQLite/PG   │
                              │                 └──────────────┘
                              │                        │
                              │                        ▼
                              │                 ┌──────────────┐
                              │                 │  Dashboard   │
                              │                 │  Next.js     │
                              │                 │  Recharts    │
                              │                 └──────────────┘
                              │
                              ▼
                     ┌──────────────┐
                     │  HybridLLM   │
                     │  Client      │
                     │  (sim / real)│
                     └──────────────┘
```

AgentTrace consists of three components:

1. **SDK** (`sdk/`): Python library with decorators (`trace_openai`, `trace_anthropic`, `trace_llm`), hybrid client, and distributed tracing
2. **Server** (`server/`): FastAPI with cost analytics API, budget tracking, batch ingestion, WebSocket live tail
3. **Dashboard** (`dashboard/`): Next.js with runs list, cost breakdown, live tail, budget status, waterfall replay

### Feature Matrix

| Feature | AgentTrace | LangSmith | Langfuse | Phoenix |
|---------|-----------|-----------|----------|---------|
| Open-source | ✅ | ❌ | ✅ | ✅ |
| Self-hostable | ✅ | ❌ | ✅ | ✅ |
| Cost tracking per span | ✅ | Partial | Partial | ❌ |
| Budget alerts | ✅ | ❌ | ✅ | ❌ |
| Live tail (SSE/WS) | ✅ | ❌ | ❌ | Partial |
| Multi-agent correlation | ✅ | Partial | ❌ | ❌ |
| Waterfall timeline | ✅ | Partial | Partial | Partial |
| Prompt replay | ✅ | ❌ | ❌ | ❌ |
| Run diffing | ✅ | ❌ | ❌ | ❌ |
| Batch ingestion API | ✅ | ❌ | ❌ | ❌ |
| Provider wrappers (OpenAI/Anthropic) | ✅ | ❌ | ❌ | ❌ |
| Hybrid client (sim/real) | ✅ | ❌ | ❌ | ❌ |

## Quickstart (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for PostgreSQL)

### 1. Install the SDK

```bash
cd sdk
pip install -e .
```

### 2. Start the Trace Server

```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will:
- Initialize an SQLite database at `./data/agenttrace.db`
- Expose API at `http://localhost:8000`
- Serve API docs at `http://localhost:8000/docs`

### 3. Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

### 4. Run an Example Agent

```bash
cd examples
python research_agent.py
```

This will:
- Create a run named "research_agent"
- Record tool calls (`web_search`, `parse_content`)
- Record LLM calls (`synthesize_findings`, `generate_followup_questions`)
- Export traces to `./data/research_traces.jsonl`

Use `APIExporter` instead of `JSONLExporter` when you want the example to ingest directly into the running server and appear in the dashboard.

## Example Workflow

### Provider-Aware Wrappers (Recommended)

```python
from agenttrace import Tracer, trace_openai, trace_anthropic
from agenttrace.exporters import APIExporter

# Or use the Hybrid Client for zero-config demos
from agenttrace import HybridLLMClient

tracer = Tracer()
tracer.set_exporter(APIExporter(endpoint="http://localhost:8000/api"))

client = HybridLLMClient(mode="sim", tracer=tracer)

# Run with tracing
with tracer.run("research_agent", workflow_id="research-pipeline"):
    research = client.chat("openai", "gpt-4", messages=[
        {"role": "user", "content": "Research AI observability trends"}
    ])
    summary = client.chat("anthropic", "claude-3-sonnet", messages=[
        {"role": "user", "content": f"Summarize: {research.content}"}
    ])

tracer.flush()
```

### Manual Decorators

```python
from agenttrace import Tracer
from agenttrace.wrappers import trace_tool, trace_llm

tracer = Tracer()

@trace_tool(tracer)
def web_search(query: str) -> dict:
    return {"results": [...]}

@trace_llm(tracer, model="gpt-4", feature="summarization")
def synthesize(context: str) -> str:
    return "Summary..."

with tracer.run("agent", correlation_id="workflow-123"):
    results = web_search("AI debugging")
    summary = synthesize(str(results))
```

### Multi-Agent with Correlation ID

```python
from agenttrace import Tracer, HybridLLMClient

tracer = Tracer()
correlation_id = tracer.generate_id()

# Agent A (researcher)
with tracer.start_run("researcher", metadata={"correlation_id": correlation_id}):
    client = HybridLLMClient(tracer=tracer)
    research = client.chat("openai", "gpt-4", messages=[{"role": "user", "content": "Research"}])

# Agent B (summarizer) — same correlation_id links them in dashboard
with tracer.start_run("summarizer", metadata={"correlation_id": correlation_id}):
    summary = client.chat("anthropic", "claude-3", messages=[{"role": "user", "content": "Summarize"}])
```

## Key Design Decisions

### Span-Based Tracing

AgentTrace uses a span-based tracing model inspired by OpenTelemetry. Each operation (LLM call, tool call, decision) is a span with:
- Unique ID and parent span ID for nesting
- Type (LLM_CALL, TOOL_CALL, DECISION, RETRIEVAL, CUSTOM)
- Input/output data
- Start/end times and duration
- Cost and token usage
- Status (STARTED, COMPLETED, ERROR)

This enables composable, nestable tracing that mirrors the structure of agent workflows.

### Context Variables

The SDK uses Python's `contextvars` for thread-safe and asyncio-safe state management. The current run ID and active span are stored in context variables, allowing instrumentation to access the current trace context without explicit passing.

### Multi-Agent Trace Correlation

AgentTrace supports correlating traces across multiple agent instances using a `correlation_id`. This is useful for:
- Distributed agent workflows
- Multi-agent systems
- Tracking related executions across different services

Use the `correlation_id` parameter when starting a run:

```python
with tracer.run("agent_task", correlation_id="workflow-123"):
    # Agent execution
```

### Trace Diffing

AgentTrace provides a diff API to compare two runs side-by-side, showing:
- Cost differences
- Token usage differences
- Span count differences
- Duration differences
- Span-level differences (added, removed, changed)

Use the diff API endpoint: `/api/diff/runs?run_id_1=<id>&run_id_2=<id>`

### Prompt Replay

AgentTrace captures all inputs and outputs for each span, enabling step-by-step replay of agent execution. The replay endpoint returns all steps in chronological order with full input/output data.

Use the replay API endpoint: `/api/replay/runs/<run_id>`

### JSONL Export

JSONL (JSON Lines) is used for local development because:
- Human-readable and grep-able
- Easy to parse and analyze
- Supports streaming writes
- No external dependencies

For production, the SDK supports HTTP export to the AgentTrace server and OTLP export to OpenTelemetry-compatible systems.

### Separate Server

The server is a separate FastAPI application because:
- Decouples tracing from agent execution
- Enables real-time dashboard updates
- Supports multiple agents sharing a trace store
- Provides a REST API for custom integrations

### Pydantic Schemas

Both the SDK and server use Pydantic for type-safe validation at boundaries:
- SDK: Validates data before export
- Server: Validates incoming API requests
- Ensures consistency across components

## Failure Handling

The SDK is designed to be non-blocking:
- Export failures are logged but don't raise exceptions
- Context variables are cleared on run completion
- The tracer can be used without an exporter (no-op mode)

The server includes:
- Global exception handler for unhandled errors
- Database transaction rollback on failure
- Graceful degradation when optional features are missing

## Testing Strategy

- **SDK**: Unit tests for Tracer, Span, exporters, and wrappers
- **Server**: Integration tests for API endpoints and end-to-end workflows
- **Dashboard**: E2E tests with Playwright

Run tests with:

```bash
# SDK
cd sdk && pytest tests/ -v

# Server
cd server && pytest tests/ -v

# Dashboard
cd dashboard && npm run test:e2e
```

## Deployment

### Docker Compose (Recommended)

```bash
cp .env.example .env
docker compose up --build
```

The server auto-migrates on first boot and seeds demo data if empty. Full guide: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

### Benchmarks

Run on a local laptop (SQLite, single worker):

```bash
$ python scripts/benchmark.py
AgentTrace Ingestion Benchmark
==================================================
[Single Trace] 100 sequential requests...
  Throughput: 45 traces/sec
  Avg latency: 18ms

[Concurrent] 10 workers x 50 traces = 500 traces...
  Throughput: 280 traces/sec
  Avg latency: 22ms

[Batch] 10 batches x 50 traces = 500 traces...
  Throughput: 520 traces/sec
  Avg batch latency: 95ms
```

### Production Database

For production, use PostgreSQL instead of SQLite:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@host:5432/agenttrace"
export DATABASE_TYPE=postgres
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite | SQLAlchemy connection string |
| `DATABASE_TYPE` | `sqlite` | `sqlite` or `postgres` |
| `SERVER_HOST` | `0.0.0.0` | API bind address |
| `SERVER_PORT` | `8000` | API port |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed origins |
| `AGENTTRACE_LLM_MODE` | `sim` | `sim` (mock) or `real` |
| `OPENAI_API_KEY` | — | Required for real mode |
| `ANTHROPIC_API_KEY` | — | Required for real mode |

## CI/CD Pipeline

AgentTrace includes a GitHub Actions CI/CD pipeline that:

- Runs SDK tests with pytest
- Runs server tests with pytest
- Builds the dashboard (Next.js production build)
- Builds Docker images for server and dashboard (without pushing to a registry)

The pipeline is configured in `.github/workflows/ci.yml`.

## What This Project Demonstrates

This project demonstrates:
- **Three-tier architecture**: SDK → Server → Dashboard
- **Async/await patterns**: Python async for server, React hooks for dashboard
- **Type safety**: Python type hints, TypeScript, Pydantic validation
- **Modern web stack**: FastAPI, Next.js 14, Tailwind CSS, Recharts
- **Database design**: SQLAlchemy ORM, migrations, indexing, cost attribution columns
- **Testing**: pytest, pytest-asyncio, 85% coverage gate
- **Docker**: Multi-container deployment with healthchecks, auto-migrate, auto-seed
- **Observability**: Span-based tracing, cost tracking, token usage, waterfall timeline
- **FinOps**: Cost analytics API, budget tracking, burn-rate projection, per-model breakdown
- **Multi-agent correlation**: Correlation IDs for distributed workflows
- **Trace diffing**: Compare runs for regression testing
- **Prompt replay**: Step-by-step replay for debugging
- **Provider wrappers**: `trace_openai()`, `trace_anthropic()` with automatic token/cost extraction
- **Hybrid client**: Deterministic mock mode (`sim`) or live API mode (`real`) via env var
- **Batch ingestion**: `/api/traces/batch` for high-throughput export
- **Live tail**: SSE streaming of incoming spans in real time
- **Authentication**: JWT-based API authentication
- **Developer experience**: Decorators, context managers, API docs
- **CI/CD**: GitHub Actions with automated testing and deployment
