"""Tests for POST /auth/refresh and POST /auth/logout."""
from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Session as DBSession
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


@pytest.fixture
def app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    app = create_app()

    async def _override_db() -> Any:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI):  # type: ignore[no-untyped-def]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, user: dict[str, object]) -> dict[str, str]:
    r = await client.post(
        "/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert r.status_code == 200, r.text
    return {
        "access_token": r.json()["access_token"],
        "refresh_token": r.cookies["refresh_token"],
    }


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    tokens = await _login(client, created_user)
    client.cookies.set("refresh_token", tokens["refresh_token"], path="/auth")

    resp = await client.post("/auth/refresh")

    assert resp.status_code == 200, resp.text
    new_access = resp.json()["access_token"]
    assert new_access != tokens["access_token"]


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient) -> None:
    client.cookies.set("refresh_token", "garbage", path="/auth")
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(
    client: AsyncClient,
    created_user: dict[str, object],
    db_session: AsyncSession,
) -> None:
    tokens = await _login(client, created_user)
    client.cookies.set("refresh_token", tokens["refresh_token"], path="/auth")

    resp = await client.post("/auth/logout")
    assert resp.status_code == 204

    # refresh apos logout deve falhar
    resp2 = await client.post("/auth/refresh")
    assert resp2.status_code == 401

    # sessao no DB deve ter revoked_at preenchido
    th = jwt_mod.hash_refresh_token(tokens["refresh_token"])
    res = await db_session.execute(
        select(DBSession).where(DBSession.token_hash == th)
    )
    db_sess = res.scalar_one()
    assert db_sess.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_without_cookie_idempotent(client: AsyncClient) -> None:
    resp = await client.post("/auth/logout")
    assert resp.status_code == 204
