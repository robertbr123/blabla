"""Async engine and session factory.

The engine is created lazily on first use so tests can override the URL
via env vars before import-time wiring runs.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ondeline_api.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, closes on request end."""
    sm = get_sessionmaker()
    async with sm() as session:
        yield session


def reset_engine_cache() -> None:
    """Test helper: drop cached engine/sessionmaker so reload picks up new URL."""
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
