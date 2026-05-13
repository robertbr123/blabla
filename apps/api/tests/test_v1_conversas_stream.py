"""SSE stream + Redis pub/sub roundtrip."""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis
from ondeline_api.services.conversa_events import publish, subscribe

pytestmark = pytest.mark.asyncio


async def test_publish_subscribe_roundtrip() -> None:
    redis = FakeRedis(decode_responses=False)
    conversa_id = uuid4()
    received: list[dict[str, Any]] = []

    async def consume() -> None:
        async for event in subscribe(redis, conversa_id):
            received.append(event)
            if len(received) >= 1:
                break

    consumer = asyncio.create_task(consume())
    # give subscriber time to subscribe
    await asyncio.sleep(0.05)
    n = await publish(redis, conversa_id, {"type": "msg", "text": "hi"})
    await asyncio.wait_for(consumer, timeout=2.0)
    assert n >= 1
    assert received[0]["type"] == "msg"
    assert received[0]["text"] == "hi"


async def test_subscribe_filters_other_conversa() -> None:
    redis = FakeRedis(decode_responses=False)
    a = uuid4()
    b = uuid4()
    received: list[dict[str, Any]] = []

    async def consume() -> None:
        async for event in subscribe(redis, a):
            received.append(event)
            break

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    # publish to B — A should NOT receive
    await publish(redis, b, {"type": "msg", "text": "for-b"})
    # publish to A — A receives
    await publish(redis, a, {"type": "msg", "text": "for-a"})
    await asyncio.wait_for(consumer, timeout=2.0)
    assert len(received) == 1
    assert received[0]["text"] == "for-a"


async def test_bad_payload_skipped() -> None:
    redis = FakeRedis(decode_responses=False)
    conversa_id = uuid4()
    received: list[dict[str, Any]] = []

    async def consume() -> None:
        async for event in subscribe(redis, conversa_id):
            received.append(event)
            break

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    # publish raw garbage directly
    await redis.publish(f"conv_events:{conversa_id}", b"not-json")
    # then publish valid one
    await publish(redis, conversa_id, {"type": "msg"})
    await asyncio.wait_for(consumer, timeout=2.0)
    assert received[0]["type"] == "msg"
