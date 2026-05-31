#!/bin/sh
set -e

# Wait for database to be ready (handled by depends_on condition)

# Auto-migrate on startup
python -c "
import asyncio
from app.db import init_db
asyncio.run(init_db())
"

# Auto-seed if the database is empty (no runs)
python -c "
import asyncio
from sqlalchemy import select, func
from app.db import async_session_factory
from app.models.run import Run

async def seed_if_empty():
    async with async_session_factory() as session:
        result = await session.execute(select(func.count()).select_from(Run))
        count = result.scalar()
        if count == 0:
            import subprocess
            import sys
            print('Database empty — seeding demo data...')
            subprocess.run([sys.executable, '../scripts/seed_demo.py'], check=False)

asyncio.run(seed_if_empty())
"

# Start the server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
