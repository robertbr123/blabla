"""Tests for login lockout counter (Redis-backed)."""
from __future__ import annotations

import pytest
from ondeline_api.auth import lockout


class InMemoryRedis:
    """Minimal stub of redis.asyncio.Redis for lockout tests."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = seconds
        return True

    async def get(self, key: str) -> str | None:
        v = self.store.get(key)
        return str(v) if v is not None else None

    async def delete(self, key: str) -> int:
        existed = key in self.store
        self.store.pop(key, None)
        self.ttls.pop(key, None)
        return 1 if existed else 0


@pytest.fixture
def redis() -> InMemoryRedis:
    return InMemoryRedis()


@pytest.mark.asyncio
async def test_first_failure_returns_remaining(redis: InMemoryRedis) -> None:
    state = await lockout.record_failure(redis, "user@example.com")

    assert state.locked is False
    assert state.attempts == 1
    assert state.remaining == 4


@pytest.mark.asyncio
async def test_fifth_failure_locks(redis: InMemoryRedis) -> None:
    for _ in range(4):
        await lockout.record_failure(redis, "user@example.com")
    state = await lockout.record_failure(redis, "user@example.com")

    assert state.locked is True
    assert state.attempts == 5


@pytest.mark.asyncio
async def test_is_locked_after_lockout(redis: InMemoryRedis) -> None:
    for _ in range(5):
        await lockout.record_failure(redis, "user@example.com")

    assert await lockout.is_locked(redis, "user@example.com") is True


@pytest.mark.asyncio
async def test_is_locked_when_no_attempts(redis: InMemoryRedis) -> None:
    assert await lockout.is_locked(redis, "user@example.com") is False


@pytest.mark.asyncio
async def test_clear_resets_attempts(redis: InMemoryRedis) -> None:
    await lockout.record_failure(redis, "user@example.com")
    await lockout.clear(redis, "user@example.com")

    assert await lockout.is_locked(redis, "user@example.com") is False


@pytest.mark.asyncio
async def test_isolation_between_users(redis: InMemoryRedis) -> None:
    for _ in range(5):
        await lockout.record_failure(redis, "a@example.com")

    assert await lockout.is_locked(redis, "a@example.com") is True
    assert await lockout.is_locked(redis, "b@example.com") is False
