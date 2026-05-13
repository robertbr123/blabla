"""Verify /auth/login does not short-circuit when user is missing/inactive (timing oracle fix)."""
from __future__ import annotations

import collections.abc
import os
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.api import auth as auth_mod
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/0")


@pytest_asyncio.fixture
async def redis_client() -> collections.abc.AsyncIterator[Redis]:  # type: ignore[type-arg]
    """Fresh Redis client per test — avoids event-loop mismatch from cached singleton."""
    client: Redis = Redis.from_url(REDIS_URL, decode_responses=True)  # type: ignore[type-arg]
    try:
        yield client
    finally:
        await client.aclose()  # type: ignore[attr-defined]


@pytest.fixture
def app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    instance = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    instance.dependency_overrides[get_db] = _override_db
    instance.dependency_overrides[get_redis] = _override_redis
    return instance


@pytest_asyncio.fixture
async def client(app: FastAPI) -> collections.abc.AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_login_calls_verify_password_for_unknown_email(client: AsyncClient) -> None:
    """Even when no user matches the email, verify_password must be invoked once
    against the dummy hash — otherwise an attacker can enumerate emails by timing.
    """
    auth_mod._DUMMY_PASSWORD_HASH = None  # force lazy init in case prior test cached it
    with patch.object(
        auth_mod, "verify_password", wraps=auth_mod.verify_password  # type: ignore[attr-defined]
    ) as spy:
        r = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "wrong-password"},
        )
    assert r.status_code == 401
    assert spy.call_count == 1, (
        "verify_password must be called even when user is missing — "
        "calling it conditionally creates a timing oracle"
    )


@pytest.mark.asyncio
async def test_dummy_hash_is_cached_after_first_call(client: AsyncClient) -> None:
    """The dummy hash is expensive to compute; cache it module-level after first use."""
    auth_mod._DUMMY_PASSWORD_HASH = None
    await client.post("/auth/login", json={"email": "a@x.com", "password": "p"})
    first = auth_mod._DUMMY_PASSWORD_HASH
    assert first is not None
    await client.post("/auth/login", json={"email": "b@y.com", "password": "p"})
    assert auth_mod._DUMMY_PASSWORD_HASH is first  # exact same object
