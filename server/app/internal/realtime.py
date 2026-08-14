"""Pluggable realtime publication with an offline in-memory default."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any, Protocol


class RealtimePublisher(Protocol):
    async def publish(self, channel: str, event: dict[str, Any]) -> None: ...

    def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]: ...

    async def close(self) -> None: ...


class InMemoryPublisher:
    """Async fan-out publisher used by tests and the offline demo."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(
            set
        )

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers.get(channel, ())):
            await queue.put(dict(event))

    async def _stream(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers[channel].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[channel].discard(queue)
            if not self._subscribers[channel]:
                self._subscribers.pop(channel, None)

    def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        return self._stream(channel)

    async def close(self) -> None:
        self._subscribers.clear()


class RedisPublisher:
    """Optional Redis pub/sub adapter loaded only when explicitly configured."""

    def __init__(self, redis_url: str) -> None:
        try:
            import redis.asyncio as redis_async  # type: ignore[reportMissingImports]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Redis realtime support requires the server[redis] extra"
            ) from exc
        self._redis = redis_async.from_url(redis_url, decode_responses=True)

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(event, default=str))

    async def _stream(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message.get("data"):
                    yield json.loads(message["data"])
                else:
                    await asyncio.sleep(0.05)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        return self._stream(channel)

    async def close(self) -> None:
        await self._redis.aclose()


def create_publisher(backend: str, redis_url: str) -> RealtimePublisher:
    """Build the explicitly selected backend; memory is the only implicit default."""
    if backend == "memory":
        return InMemoryPublisher()
    if backend == "redis":
        return RedisPublisher(redis_url)
    raise ValueError("realtime backend must be memory or redis")
