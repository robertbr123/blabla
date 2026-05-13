"""Unit tests for the Celery queue-depth helper."""
from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis
from ondeline_api.observability.celery_queue import CELERY_QUEUES, queue_depths


@pytest.mark.asyncio
async def test_queue_depths_returns_zero_for_empty_queues() -> None:
    redis = FakeRedis()
    depths = await queue_depths(redis)
    assert set(depths.keys()) == set(CELERY_QUEUES)
    assert all(v == 0 for v in depths.values())


@pytest.mark.asyncio
async def test_queue_depths_counts_pushed_messages() -> None:
    redis = FakeRedis()
    await redis.rpush("llm", b"task1", b"task2", b"task3")
    await redis.rpush("default", b"task1")
    depths = await queue_depths(redis)
    assert depths["llm"] == 3
    assert depths["default"] == 1
    assert depths["sgp"] == 0
    assert depths["notifications"] == 0
