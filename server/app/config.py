"""Configuration module for the AgentTrace server."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL: SQLAlchemy connection string.
        DATABASE_TYPE: Database backend type (sqlite or postgres).
        SERVER_HOST: Host address to bind the server to.
        SERVER_PORT: Port number for the server.
        MAX_TRACE_RETENTION_DAYS: Maximum days to retain traces.
        BUFFER_SIZE: Buffer size for trace ingestion.
        CORS_ORIGINS: Comma-separated list of allowed CORS origins.
        SECRET_KEY: Secret key for the application.
        ENVIRONMENT: Environment type (development or production).
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
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
