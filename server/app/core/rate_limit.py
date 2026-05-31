"""In-memory rate limiting middleware for FastAPI.

Tracks requests per IP and returns 429 when the configured limit is exceeded.
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware.

    Tracks requests per client IP within a time window.
    Configurable via RATE_LIMIT env var (format: "requests/minute").
    """

    def __init__(self, app: Callable, rate_limit: str | None = None) -> None:
        super().__init__(app)
        self._requests: dict[str, list[float]] = {}
        limit_str = rate_limit or getattr(settings, "RATE_LIMIT", "100/minute")
        parts = limit_str.split("/")
        self.max_requests = int(parts[0])
        window_str = parts[1] if len(parts) > 1 else "minute"
        self.window_seconds = self._parse_window(window_str)

    def _parse_window(self, window: str) -> int:
        windows = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        return windows.get(window, 60)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        timestamps = self._requests.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < self.window_seconds]
        self._requests[client_ip] = timestamps

        if len(timestamps) >= self.max_requests:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.window_seconds)},
            )

        timestamps.append(now)
        return await call_next(request)
