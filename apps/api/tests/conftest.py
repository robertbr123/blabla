"""Pytest fixtures for the API."""
from __future__ import annotations

import collections.abc
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


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


class BrokenDB:
    """DBSessionLike sentinel: raises the stored exception on execute."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        raise self._exc


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


@pytest.fixture
def broken_db() -> BrokenDB:
    return BrokenDB(ConnectionError("simulated db pool failure"))


INTEGRATION_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline",
)


@pytest.fixture(scope="session", autouse=True)
def _set_secrets() -> None:
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret-32-bytes-minimum-okk")
    os.environ.setdefault("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())
    os.environ.setdefault("PII_HASH_PEPPER", "test-pepper-not-for-prod-32-bytes-x")


@pytest.fixture(scope="session", autouse=True)
def _flush_lockout_keys() -> None:
    """Wipe lockout keys at session start so leftover state from prior runs doesn't pollute tests."""
    import os

    from redis import Redis

    url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
    try:
        r = Redis.from_url(url, decode_responses=True)
        keys = r.keys("lockout:login:*")
        if keys:
            r.delete(*keys)
        r.close()
    except Exception:
        # If Redis is unreachable, tests that need it will fail with a clearer error.
        pass


@pytest_asyncio.fixture
async def db_session() -> collections.abc.AsyncIterator[AsyncSession]:
    """Per-test session with rollback at end. Requires Postgres running."""
    engine = create_async_engine(INTEGRATION_DB_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with sm(bind=conn) as session:
            yield session
        await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def created_user(db_session: AsyncSession) -> dict[str, object]:
    """Cria um user admin com senha conhecida e retorna dict com email/senha/id."""
    from ondeline_api.auth.passwords import hash_password
    from ondeline_api.db.models.identity import Role, User

    email = f"test-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=Role.ADMIN,
        name="Test Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "email": email, "password": password, "user": user}
