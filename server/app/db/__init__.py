"""Database session module — async SQLAlchemy engine and session factory."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all models."""

    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session.

    Yields:
        An async SQLAlchemy session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "sqlite":
            await conn.run_sync(_repair_sqlite_schema)


def _repair_sqlite_schema(sync_conn) -> None:
    """Apply tiny idempotent repairs for local SQLite databases."""
    inspector = inspect(sync_conn)
    run_columns = {column["name"] for column in inspector.get_columns("runs")}
    if "correlation_id" not in run_columns:
        sync_conn.execute(text("ALTER TABLE runs ADD COLUMN correlation_id VARCHAR(36)"))
        sync_conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_runs_correlation_id ON runs (correlation_id)")
        )
