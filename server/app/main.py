"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.diff import router as diff_router
from app.api.health import router as health_router
from app.api.replay import router as replay_router
from app.api.runs import router as runs_router
from app.api.stats import router as stats_router
from app.api.stream import router as stream_router
from app.api.traces import router as traces_router
from app.config import settings
from app.core.logging import setup_logging
from app.db.session import init_db


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events.

    Initializes the database on startup.

    Args:
        application: The FastAPI application instance.
    """
    setup_logging()
    await init_db()
    yield


app = FastAPI(
    title="AgentTrace Server",
    description="Observability and replay layer for agentic AI workflows",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts_router, prefix="/api", tags=["alerts"])
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(diff_router, prefix="/api", tags=["diff"])
app.include_router(health_router, tags=["health"])
app.include_router(replay_router, prefix="/api", tags=["replay"])
app.include_router(stats_router, prefix="/api", tags=["stats"])
app.include_router(stream_router, prefix="/api", tags=["stream"])
app.include_router(traces_router, prefix="/api", tags=["traces"])
app.include_router(runs_router, prefix="/api", tags=["runs"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors.

    Args:
        request: The incoming HTTP request.
        exc: The exception that was raised.

    Returns:
        A JSON error response with status 500.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc) if app.debug else "An unexpected error occurred",
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning server information.

    Returns:
        Dictionary with server name and version.
    """
    return {"name": "AgentTrace Server", "version": "0.1.0"}
