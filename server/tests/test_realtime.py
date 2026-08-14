"""Realtime publisher contract tests."""

import asyncio

import pytest
from app.internal.realtime import InMemoryPublisher


@pytest.mark.asyncio
async def test_in_memory_publisher_delivers_events_by_channel() -> None:
    publisher = InMemoryPublisher()
    stream = publisher.subscribe("traces")
    next_event = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)

    await publisher.publish("traces", {"span_id": "span-1"})

    assert await asyncio.wait_for(next_event, timeout=1.0) == {"span_id": "span-1"}
    await stream.aclose()
    await publisher.close()


@pytest.mark.asyncio
async def test_channels_are_isolated() -> None:
    publisher = InMemoryPublisher()
    stream = publisher.subscribe("metrics")
    next_event = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)

    await publisher.publish("traces", {"span_id": "span-2"})
    await publisher.publish("metrics", {"qps": 1})

    assert await asyncio.wait_for(next_event, timeout=1.0) == {"qps": 1}
    await stream.aclose()
    await publisher.close()
