"""Configuration module for the AgentTrace server."""

from __future__ import annotations

from pydantic import field_validator
from shared_core.config import BaseAppConfig


class Settings(BaseAppConfig):
    """Application settings, extending the shared_core base configuration.

    Inherits infrastructure fields (REDIS_URL, LOG_LEVEL, DB_POOL_*, ...) from
    ``shared_core.config.BaseAppConfig`` and adds AgentTrace's domain fields.
    """

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/agenttrace.db"
    DATABASE_TYPE: str = "sqlite"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    MAX_TRACE_RETENTION_DAYS: int = 30
    BUFFER_SIZE: int = 100
    CORS_ORIGINS: list[str] = ["*"]
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENVIRONMENT: str = "development"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()
