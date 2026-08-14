"""Rate limiting with a Redis sliding window and an in-memory fallback.

Promotes the in-memory per-IP limiter found in several services to a multi-worker
safe Redis sliding window (``shared_core.redis.RedisManager``), degrading gracefully
to a per-process in-memory window when no Redis is configured or reachable.
"""

import time
import uuid
from collections import defaultdict, deque
from typing import Any, Callable, Deque, Optional

from app.internal.vendor_core.redis import RedisManager

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    _HAS_STARLETTE = True
except ImportError:  # pragma: no cover - starlette ships with fastapi consumers
    BaseHTTPMiddleware = object  # type: ignore[assignment,misc]
    JSONResponse = object  # type: ignore[assignment,misc]
    _HAS_STARLETTE = False


def sliding_window_allow(
    timestamps: Deque[float], now: float, limit: int, window_seconds: int
) -> bool:
    """Evict timestamps outside the window, append ``now``, and check the limit."""
    window_start = now - window_seconds
    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()
    timestamps.append(now)
    return len(timestamps) <= limit


def client_ip_key(request: Any) -> str:
    """Derive a rate-limit key from the client IP (Starlette ``Request``)."""
    client = getattr(request, "client", None)
    return client.host if client else "anonymous"


class RateLimiter:
    """Sliding-window rate limiter backed by Redis with an in-memory fallback."""

    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        *,
        limit: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self.redis_manager = redis_manager
        self.limit = limit
        self.window_seconds = window_seconds
        self._memory: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        """Return True if a request for ``key`` is within the limit."""
        now = time.time()
        if self.redis_manager is not None:
            try:
                return self._redis_allow(key, now)
            except Exception:
                # Fall back to in-memory on any Redis error.
                pass
        return sliding_window_allow(
            self._memory[key], now, self.limit, self.window_seconds
        )

    def reset(self) -> None:
        """Clear the in-memory window for an isolated test application."""
        self._memory.clear()

    def _redis_allow(self, key: str, now: float) -> bool:
        client = self.redis_manager.client  # type: ignore[union-attr]
        redis_key = f"ratelimit:{key}"
        window_start = now - self.window_seconds
        pipe = client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zadd(redis_key, {f"{now}:{uuid.uuid4().hex}": now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, self.window_seconds)
        results = pipe.execute()
        count = results[2]
        return count <= self.limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware returning 429 when the limiter is exceeded."""

    def __init__(
        self,
        app: object,
        limiter: RateLimiter,
        *,
        key_func: Callable[[Any], str] = client_ip_key,
    ) -> None:
        if not _HAS_STARLETTE:
            raise ImportError(
                "starlette/fastapi is required for RateLimitMiddleware. "
                "Install it via 'pip install fastapi'."
            )
        super().__init__(app)
        self.limiter = limiter
        self.key_func = key_func

    async def dispatch(self, request, call_next):  # type: ignore[override]
        key = self.key_func(request)
        if not self.limiter.allow(key):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMITED",
                    "message": "Too many requests",
                    "status": 429,
                },
            )
        return await call_next(request)
