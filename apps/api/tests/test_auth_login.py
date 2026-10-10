"""Integration tests for POST /auth/login."""
from __future__ import annotations

import collections.abc
import os
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
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
    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_login_with_correct_credentials_returns_tokens(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "Bearer"
    # Refresh token vem em cookie HttpOnly
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_with_unknown_email_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "x"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(
    client: AsyncClient,
    created_user: dict[str, object],
    db_session: AsyncSession,
) -> None:
    user = created_user["user"]
    user.is_active = False  # type: ignore[attr-defined]
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_locks_after_5_failures(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    for _ in range(5):
        await client.post(
            "/auth/login",
            json={"email": created_user["email"], "password": "wrong"},
        )
    # 6a tentativa, mesmo com senha correta, deve retornar 423
    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )
    assert resp.status_code == 423


@pytest.mark.asyncio
async def test_login_manter_conectado_dura_30_dias(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    """Com `remember`, refresh e csrf viram cookies persistentes de 30 dias e o
    refresh token carrega esse prazo; sem ele, csrf continua cookie de sessao."""
    from ondeline_api.auth import jwt as jwt_mod

    cred = {"email": created_user["email"], "password": created_user["password"]}
    trinta_dias = 30 * 24 * 3600

    resp = await client.post("/auth/login", json={**cred, "remember": True})
    assert resp.status_code == 200, resp.text
    cookies = {c.split("=", 1)[0]: c for c in resp.headers.get_list("set-cookie")}
    assert f"Max-Age={trinta_dias}" in cookies["refresh_token"]
    assert f"Max-Age={trinta_dias}" in cookies["csrf_token"]
    payload = jwt_mod.decode_refresh_token(resp.cookies["refresh_token"])
    assert payload["exp"] - payload["iat"] == trinta_dias

    resp = await client.post("/auth/login", json=cred)
    assert resp.status_code == 200, resp.text
    cookies = {c.split("=", 1)[0]: c for c in resp.headers.get_list("set-cookie")}
    assert f"Max-Age={7 * 24 * 3600}" in cookies["refresh_token"]
    assert "Max-Age" not in cookies["csrf_token"]
