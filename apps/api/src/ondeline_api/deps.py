"""Dependency providers for DB and Redis pools.

Em M1 retornamos pools placeholder. Em M2 trocamos por SQLAlchemy
async engine e redis.asyncio.from_url().
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, Protocol

import asyncpg
from redis.asyncio import Redis

from ondeline_api.config import Settings, get_settings


class DBLike(Protocol):
    async def fetchval(self, query: str) -> Any: ...


class RedisLike(Protocol):
    async def ping(self) -> bool: ...


class _BrokenDB:
    """DBLike sentinel returned when the real pool cannot be obtained.

    Allows /healthz to handle infrastructure failures gracefully via the
    route handler's try/except, instead of propagating an exception out
    of the dependency and causing a 500.
    """

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def fetchval(self, query: str) -> Any:
        raise self._exc


class _BrokenRedis:
    """RedisLike sentinel; symmetric to _BrokenDB."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def ping(self) -> bool:
        raise self._exc


@lru_cache(maxsize=1)
def _settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def _redis_client() -> Redis:  # type: ignore[type-arg]
    return Redis.from_url(str(_settings().redis_url), decode_responses=True)


async def _make_db_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        dsn=_settings().database_url.replace("+asyncpg", ""),
        min_size=1,
        max_size=5,
    )


_db_pool: asyncpg.Pool | None = None


async def get_db() -> AsyncIterator[DBLike]:
    """Yield a connection from the pool; sentinel if pool unavailable."""
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = await _make_db_pool()
        except Exception as exc:
            yield _BrokenDB(exc)
            return
    try:
        async with _db_pool.acquire() as conn:
            yield conn
    except Exception as exc:
        yield _BrokenDB(exc)


async def get_redis() -> RedisLike:
    """Return Redis client; sentinel if URL invalid or client cannot be built."""
    try:
        return _redis_client()
    except Exception as exc:
        return _BrokenRedis(exc)
