"""Configuration module for the AgentTrace server."""

from __future__ import annotations

from pydantic import Field, field_validator

from app.internal.vendor_core.config import BaseAppConfig


class Settings(BaseAppConfig):
    """Application settings, extending the pinned internal base configuration.

    Inherits infrastructure fields (REDIS_URL, LOG_LEVEL, DB_POOL_*, ...) from
    the internally vendored compatibility base and adds AgentTrace's domain fields.
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
    AUTH_REQUIRED: bool = False
    REALTIME_BACKEND: str = "memory"
    TRACE_SAMPLING_MODE: str = "off"
    TRACE_SAMPLE_RATE: float = Field(default=1.0, ge=0.0, le=1.0)
    TRACE_TAIL_SLOW_MS: float | None = Field(default=None, ge=0.0)
    TRACE_TAIL_KEEP_ERRORS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()
