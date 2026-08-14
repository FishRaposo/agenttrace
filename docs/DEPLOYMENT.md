# AgentTrace Deployment Guide

## Quick start — Docker Compose (optional integration)

```bash
cp .env.example .env
docker compose up --build
```

This starts:
- **Postgres 16** (database)
- **AgentTrace Server** (FastAPI on port 8000)
- **AgentTrace Dashboard** (Next.js on port 3000)

The server creates or migrates the database on first boot and seeds demo data if
the database is empty. Docker/PostgreSQL are optional; `make install` plus
SQLite is the canonical offline path.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/agenttrace.db` | SQLAlchemy database URL |
| `DATABASE_TYPE` | `sqlite` | `sqlite` or `postgres` |
| `SERVER_HOST` | `0.0.0.0` | API bind address |
| `SERVER_PORT` | `8000` | API port |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `OPENAI_API_KEY` | — | Required only for `AGENTTRACE_LLM_MODE=real` |
| `ANTHROPIC_API_KEY` | — | Required only for `AGENTTRACE_LLM_MODE=real` |
| `AGENTTRACE_LLM_MODE` | `sim` | `sim` (mock) or `real` (live API calls) |
| `AGENTTRACE_LLM_SEED` | `42` | Deterministic seed for simulated responses |
| `AUTH_REQUIRED` | `false` | Require JWT for protected writes/admin routes |
| `REALTIME_BACKEND` | `memory` | `memory` or optional `redis` |
| `TRACE_SAMPLING_MODE` | `off` | `off`, `head`, or `tail` |
| `TRACE_SAMPLE_RATE` | `1.0` | Stable SHA-256 retention rate |
| `TRACE_TAIL_SLOW_MS` | unset | Tail-sampling slow-span override |
| `TRACE_TAIL_KEEP_ERRORS` | `true` | Retain terminal errors in tail mode |

## Production Checklist

1. **Database**: Switch from SQLite to Postgres when durable multi-process storage is needed. Set `DATABASE_TYPE=postgres` and `DATABASE_URL=postgresql+asyncpg://...`.
2. **Secrets**: Use a secrets manager (e.g. AWS Secrets Manager, 1Password) for `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. Never commit them.
3. **Auth/SSL**: Set `AUTH_REQUIRED=true`, replace the seeded password, and put the server behind a reverse proxy (Nginx, Traefik, Caddy) with TLS termination.
4. **Backup**: Schedule daily `pg_dump` backups for Postgres.
5. **Monitoring**: The server exposes a `/health` endpoint for load-balancer health checks.

## Manual Deploy (No Docker)

### Prerequisites
- Python 3.12+
- Node.js 20+
- Postgres 14+ (optional, SQLite works for local use)

### Server

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -c "import asyncio; from app.db import init_db; asyncio.run(init_db())"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Dashboard

```bash
cd dashboard
npm ci
npm run build
npm start
```

## Seed Demo Data

```bash
python scripts/seed_demo.py
```

## Upgrade

```bash
docker compose pull
docker compose up --build -d
```

Database migrations run automatically on startup.
