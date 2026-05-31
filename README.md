# AgentTrace

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]() [![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)]() [![Python](https://img.shields.io/badge/python-3.11-blue)]() [![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)]() [![Next.js](https://img.shields.io/badge/Next.js-000?logo=next.js)]()

**OpenTelemetry-compatible observability for AI agents.**

Trace LLM calls, tool executions, and multi-step workflows with cost tracking, token usage, and replay capabilities.

[Quick Demo](#quick-demo) • [Architecture](#architecture) • [SDK Guide](#quickstart-local-development)

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

AgentTrace consists of three components:

1. **SDK** (`sdk/`): Python library for instrumenting agent code
2. **Server** (`server/`): FastAPI application for ingesting, storing, and serving trace data
3. **Dashboard** (`dashboard/`): Next.js UI for visualizing runs, spans, costs, and tokens

### Data Flow

```
Agent Code → SDK → Exporter (JSONL/HTTP/OTLP) → Server (FastAPI, SQLAlchemy, SQLite/PostgreSQL) → Dashboard (Next.js)
```

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

```python
from agenttrace import Tracer, SpanType
from agenttrace.exporters import APIExporter, JSONLExporter
from agenttrace.wrappers import trace_tool, trace_llm

# Initialize tracer with exporter
tracer = Tracer()
tracer.set_exporter(JSONLExporter(path="./traces.jsonl"))

# Decorate tools
@trace_tool(tracer)
def web_search(query: str) -> dict:
    # Simulate search
    return {"results": [...]}

# Decorate LLM calls
@trace_llm(tracer, model="gpt-4", cost_per_prompt_token=0.00003, cost_per_completion_token=0.00006)
def synthesize_findings(context: str) -> str:
    # Call LLM
    return "Summary of findings..."

# Run with tracing (with optional correlation ID for multi-agent workflows)
with tracer.run("research_agent", correlation_id="workflow-123"):
    results = web_search("AI agent debugging")
    summary = synthesize_findings(str(results))

# Flush to ensure data is written
tracer.flush()
```

To send the same trace data to the server, configure the exporter like this:

```python
tracer.set_exporter(APIExporter(endpoint="http://localhost:8000/api"))
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

## Deployment Notes

### Production Database

For production, use PostgreSQL instead of SQLite:

```bash
# Set environment variable
export DATABASE_URL="postgresql+asyncpg://user:password@host:5432/agenttrace"
```

Or use Docker Compose:

```bash
docker-compose up -d
```

### Environment Variables

Configure the server with environment variables:

- `DATABASE_URL`: SQLAlchemy connection string
- `DATABASE_TYPE`: Database backend (sqlite or postgres)
- `SERVER_HOST`: Host address (default: 0.0.0.0)
- `SERVER_PORT`: Port number (default: 8000)
- `MAX_TRACE_RETENTION_DAYS`: Maximum days to retain traces
- `BUFFER_SIZE`: Buffer size for trace ingestion
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins
- `SECRET_KEY`: Secret key for JWT authentication
- `ENVIRONMENT`: Environment type (development or production)

### Authentication

The server includes JWT-based authentication. To enable:

1. Set `SECRET_KEY` to a strong random value
2. Use the `/api/auth/register` endpoint to create users
3. Use the `/api/auth/token` endpoint to get access tokens
4. Include the token in the `Authorization` header: `Bearer <token>`

### CORS Configuration

In production, restrict CORS origins to specific domains:

```bash
export CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

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
- **Database design**: SQLAlchemy ORM, migrations, indexing
- **Testing**: pytest, pytest-asyncio, Playwright E2E
- **Docker**: Multi-container deployment with PostgreSQL
- **Observability**: Span-based tracing, cost tracking, token usage
- **Multi-agent correlation**: Correlation IDs for distributed workflows
- **Trace diffing**: Compare runs for regression testing
- **Prompt replay**: Step-by-step replay for debugging
- **Authentication**: JWT-based API authentication
- **Developer experience**: Decorators, context managers, API docs
- **CI/CD**: GitHub Actions with automated testing and deployment.
