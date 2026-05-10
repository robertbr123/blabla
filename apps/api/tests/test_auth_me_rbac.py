"""Tests for /auth/me and require_role dependency."""
from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.auth.rbac import require_role
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
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

    test = APIRouter()

    @test.get("/admin-only")
    async def admin_only(
        user: User = Depends(require_role(Role.ADMIN)),  # noqa: B008
    ) -> dict[str, str]:
        return {"ok": user.email}

    @test.get("/atendente-or-admin")
    async def both(
        user: User = Depends(require_role(Role.ADMIN, Role.ATENDENTE)),  # noqa: B008
    ) -> dict[str, str]:
        return {"ok": user.email}

    app.include_router(test)
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


@pytest.mark.asyncio
async def test_me_returns_user(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    token = await _login(client, created_user["email"], created_user["password"])  # type: ignore[arg-type]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200
    body = r.json()
    assert body["email"] == created_user["email"]
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_me_without_token_401(client: AsyncClient) -> None:
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_only_allows_admin(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    token = await _login(client, created_user["email"], created_user["password"])  # type: ignore[arg-type]
    r = await client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_only_blocks_tecnico(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = User(
        email="tec@example.com",
        password_hash=hash_password("Pa$$w0rd"),
        role=Role.TECNICO,
        name="Tec",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = await _login(client, "tec@example.com", "Pa$$w0rd")
    r = await client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_combined_role_allows_atendente(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    atendente = User(
        email="at@example.com",
        password_hash=hash_password("Pa$$w0rd"),
        role=Role.ATENDENTE,
        name="At",
        is_active=True,
    )
    db_session.add(atendente)
    await db_session.flush()

    token = await _login(client, "at@example.com", "Pa$$w0rd")
    r = await client.get(
        "/atendente-or-admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
