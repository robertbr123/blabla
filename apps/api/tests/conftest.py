"""Pytest fixtures for the API."""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class FakeRedis:
    """Minimal Redis stub for health tests."""

    def __init__(self, *, alive: bool = True) -> None:
        self._alive = alive

    async def ping(self) -> bool:
        if not self._alive:
            raise ConnectionError("redis down")
        return True

    async def aclose(self) -> None:
        return None


class FakeDB:
    """Minimal async-session stub for /healthz tests."""

    def __init__(self, *, alive: bool = True) -> None:
        self._alive = alive

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        if not self._alive:
            raise ConnectionError("db down")
        return None


@pytest.fixture
def app() -> Iterator[FastAPI]:
    from ondeline_api.main import create_app

    instance = create_app()
    yield instance
    instance.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def healthy_deps() -> dict[str, Any]:
    return {"db": FakeDB(alive=True), "redis": FakeRedis(alive=True)}


@pytest.fixture
def broken_db_deps() -> dict[str, Any]:
    return {"db": FakeDB(alive=False), "redis": FakeRedis(alive=True)}
