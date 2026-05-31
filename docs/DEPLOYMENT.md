# AgentTrace Deployment Guide

## Quick Start — Docker Compose (Recommended)

```bash
cp .env.example .env
docker compose up --build
```

This starts:
- **Postgres 16** (database)
- **AgentTrace Server** (FastAPI on port 8000)
- **AgentTrace Dashboard** (Next.js on port 3000)

The server auto-migrates the database on first boot and seeds demo data if the database is empty.

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

## Production Checklist

1. **Database**: Switch from SQLite to Postgres. Set `DATABASE_TYPE=postgres` and `DATABASE_URL=postgresql+asyncpg://...`.
2. **Secrets**: Use a secrets manager (e.g. AWS Secrets Manager, 1Password) for `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. Never commit them.
3. **SSL**: Put the server behind a reverse proxy (Nginx, Traefik, Caddy) with TLS termination.
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
pip install -r requirements.txt
python -c "import asyncio; from app.db import init_db; asyncio.run(init_db())"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Dashboard

```bash
cd dashboard
npm install
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
