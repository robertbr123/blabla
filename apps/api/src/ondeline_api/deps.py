"""Dependency providers for DB and Redis used across the API."""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, Protocol

from redis.asyncio import Redis

from ondeline_api.config import get_settings
from ondeline_api.db.engine import get_db_session


class DBSessionLike(Protocol):
    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any: ...


class RedisLike(Protocol):
    async def ping(self) -> bool: ...


class _BrokenDB:
    """DBSessionLike sentinel: raises the stored exception on execute.

    Kept for test compatibility — test_health.py imports this directly.
    """

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        raise self._exc


@lru_cache(maxsize=1)
def _redis_client() -> Redis:  # type: ignore[type-arg]
    return Redis.from_url(str(get_settings().redis_url), decode_responses=True)


async def get_db() -> AsyncIterator[DBSessionLike]:
    async for session in get_db_session():
        yield session


async def get_redis() -> RedisLike:
    return _redis_client()


def reset_redis_cache() -> None:
    """Test helper."""
    _redis_client.cache_clear()
