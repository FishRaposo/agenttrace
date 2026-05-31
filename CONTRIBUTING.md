# Contributing to AgentTrace

## Architecture Overview

AgentTrace follows a three-tier architecture:

```
SDK (agenttrace)  →  Server (FastAPI)  →  Dashboard (Next.js)
```

### SDK (`sdk/agenttrace/`)

Python library that provides instrumentation for agentic AI workflows. Core components:

- **Tracer** — Orchestrates runs and spans, coordinates exporters
- **Span** — Dataclass recording a unit of work (LLM call, tool call, decision, retrieval)
- **RunContext** — Context-variable based state management for nested spans
- **Exporters** — Pluggable output backends (JSONL, HTTP API, custom)
- **Wrappers** — Decorators that auto-instrument functions (`trace_llm`, `trace_tool`, etc.)

### Server (`server/app/`)

FastAPI application that ingests and serves trace data:

- **API Layer** (`api/`) — REST endpoints for traces, runs, diffs, replays, alerts, streaming
- **Service Layer** (`services/`) — Business logic for cost calculation, token aggregation
- **Data Layer** (`models/`, `db/`) — SQLAlchemy async models with SQLite/PostgreSQL
- **Config** — Environment-based settings via pydantic-settings

### Dashboard (`dashboard/`)

Next.js + Tailwind + Recharts application:

- **Run List** — Paginated table of all runs with status, cost, token count
- **Run Detail** — Timeline of spans within a run
- **Span Inspector** — Input/output payloads, metadata, timing
- **Analytics** — Cost breakdown and token usage charts

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for PostgreSQL + production mode)

### First-Time Setup

```bash
# Install all dependencies
make install

# Run database migrations
make setup

# Start the development server
make dev
```

The server will be available at `http://localhost:8000` and the dashboard at `http://localhost:3000`.

### Manual Setup

```bash
# SDK
cd sdk
pip install -e ".[dev]"

# Server
cd server
pip install -e ".[dev]"
alembic upgrade head

# Dashboard
cd dashboard
npm install
```

---

## How to Add New Span Types

1. **Define the enum value** in `sdk/agenttrace/span.py`:

   ```python
   class SpanType(str, Enum):
       LLM_CALL = "llm_call"
       TOOL_CALL = "tool_call"
       DECISION = "decision"
       RETRIEVAL = "retrieval"
       CUSTOM = "custom"
       MY_NEW_TYPE = "my_new_type"  # Add here
   ```

2. **Create a wrapper** in `sdk/agenttrace/wrappers/` if automatic instrumentation is needed. Follow the pattern in `llm_wrapper.py` or `tool_wrapper.py`.

3. **Export the wrapper** in `sdk/agenttrace/wrappers/__init__.py`.

4. **Add tests** in `sdk/tests/` covering span type, output recording, exception handling, and tracer context integration.

5. **Update server models** if the new type carries unique data. The `span_type` field on the `Trace` table accepts any string.

---

## How to Add New Exporters

1. **Create a new exporter class** in `sdk/agenttrace/exporters/` inheriting from `BaseExporter`:

   ```python
   from agenttrace.exporters.base import BaseExporter

   class MyExporter(BaseExporter):
       def export_run(self, run_data: dict) -> None: ...
       def export_span(self, span_data: dict) -> None: ...
       def flush(self) -> None: ...
   ```

2. **Export it** in `sdk/agenttrace/exporters/__init__.py`.

3. **Add tests** in `sdk/tests/test_exporters.py`.

4. **Document** the exporter in `docs/SDK.md` under "Exporter Options".

---

## How to Add Dashboard Visualizations

1. **Add a new page** in `dashboard/src/app/` following the Next.js App Router convention.

2. **Create components** in `dashboard/src/components/` for visualizations. Use Recharts for charts (bar, line, pie) matching the existing pattern.

3. **Add TypeScript types** in `dashboard/src/types/index.ts` for any new API response shapes.

4. **Add an E2E test** in `dashboard/e2e/` covering the new page's critical user flow.

5. **Run all E2E tests** after changes:

   ```bash
   make dashboard-test
   ```

---

## Testing

### SDK Unit Tests

```bash
make sdk-test
# or: cd sdk && python -m pytest tests/ -v
```

Tests are in `sdk/tests/` using standard `pytest`. Fixtures are defined in `sdk/tests/conftest.py`.

### Server Integration Tests

```bash
make server-test
# or: cd server && python -m pytest tests/ -v
```

Server tests use `pytest-asyncio` with an in-memory SQLite database and `httpx.AsyncClient`. Fixtures are defined in `server/tests/conftest.py`.

### Playwright E2E Tests

```bash
make test
# includes sdk-test and server-test only
make dashboard-test
# or: cd dashboard && npx playwright test --project=chromium
```

Dashboard E2E tests are in `dashboard/e2e/`. Install Playwright browsers first:

```bash
cd dashboard && npx playwright install --with-deps
```

### Running All Tests

```bash
make test
```

This runs SDK and server tests. Dashboard E2E tests run separately with `make dashboard-test`.

---

## PR Process

1. **Fork the repository** and create a feature branch from `master`.
2. **Make changes** following existing code conventions (see `.editorconfig`).
3. **Write tests** for new functionality.
4. **Run linting and type checking**:

   ```bash
   make lint
   ```

5. **Run formatting**:

   ```bash
   make format
   ```

6. **Run all tests**:

   ```bash
   make test
   ```

7. **Commit with a descriptive message** following conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
8. **Open a PR** against `master`. CI will run automatically via GitHub Actions.
9. **Address review feedback** and ensure CI passes before merging.

### Pre-commit Hooks

Install pre-commit to run checks automatically before each commit:

```bash
pip install pre-commit
pre-commit install
```

Hooks configured: ruff (lint + format), mypy, trailing-whitespace, end-of-file-fixer, check-yaml, check-json, eslint (dashboard only).
