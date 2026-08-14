"""Database module.

Async SQLAlchemy engine and session factory backed by the internal compatibility layer.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.internal.vendor_core.database import AsyncDatabaseManager

_db = AsyncDatabaseManager(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)
engine = _db.engine
async_session_factory = _db.AsyncSessionLocal


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all models."""


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize the database by creating all tables and seeding demo data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "sqlite":
            await conn.run_sync(_repair_sqlite_schema)

    # Seed demo user if users table is empty
    async with async_session_factory() as session:
        from app.auth import get_password_hash
        from app.models.user import User

        result = await session.execute(select(User))
        if result.scalar_one_or_none() is None:
            demo = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
            )
            session.add(demo)
            await session.commit()


def _repair_sqlite_schema(sync_conn) -> None:
    """Apply tiny idempotent repairs for local SQLite databases."""
    inspector = inspect(sync_conn)
    run_columns = {column["name"] for column in inspector.get_columns("runs")}
    if "correlation_id" not in run_columns:
        sync_conn.execute(
            text("ALTER TABLE runs ADD COLUMN correlation_id VARCHAR(36)")
        )
        sync_conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_runs_correlation_id "
                "ON runs (correlation_id)"
            )
        )
    trace_columns = {column["name"] for column in inspector.get_columns("traces")}
    if "sampled" not in trace_columns:
        sync_conn.execute(
            text("ALTER TABLE traces ADD COLUMN sampled BOOLEAN NOT NULL DEFAULT 1")
        )
    if "sampling_reason" not in trace_columns:
        sync_conn.execute(
            text("ALTER TABLE traces ADD COLUMN sampling_reason VARCHAR(50)")
        )
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "role" not in user_columns:
        sync_conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL "
                "DEFAULT 'viewer'"
            )
        )
