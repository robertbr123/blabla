"""Integration tests for /api/v1/config endpoints (admin-only)."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    app = create_app()

    async def _override_db() -> Any:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_user(
    db_session: AsyncSession,
    role: Role = Role.ADMIN,
    name: str = "Test User",
) -> dict[str, Any]:
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        name=name,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"email": email, "password": password, "id": user.id}


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def app_and_token(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    admin = await _make_user(db_session, role=Role.ADMIN, name="Test Admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        yield c, token, admin, db_session


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_config_creates_new_key(app_and_token: Any) -> None:
    """PUT /api/v1/config/{key} creates a new config entry and returns it."""
    client, token, _admin, _db = app_and_token
    key = f"test_key_{uuid4().hex[:6]}"

    r = await client.put(
        f"/api/v1/config/{key}",
        json={"value": {"enabled": True, "limit": 100}},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["key"] == key
    assert body["value"] == {"enabled": True, "limit": 100}
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_get_config_returns_stored_value(app_and_token: Any) -> None:
    """GET /api/v1/config/{key} returns the previously set value."""
    client, token, _admin, _db = app_and_token
    key = f"test_key_{uuid4().hex[:6]}"

    # create it first
    put_r = await client.put(
        f"/api/v1/config/{key}",
        json={"value": "hello"},
        headers=_auth(token),
    )
    assert put_r.status_code == 200, put_r.text

    r = await client.get(f"/api/v1/config/{key}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["key"] == key
    assert body["value"] == "hello"


@pytest.mark.asyncio
async def test_get_config_404_for_unknown_key(app_and_token: Any) -> None:
    """GET /api/v1/config/{key} returns 404 for a key that does not exist."""
    client, token, _admin, _db = app_and_token

    r = await client.get(f"/api/v1/config/nonexistent_key_{uuid4().hex}", headers=_auth(token))
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


@pytest.mark.asyncio
async def test_put_config_overwrites_existing(app_and_token: Any) -> None:
    """PUT /api/v1/config/{key} on an existing key replaces the value."""
    client, token, _admin, _db = app_and_token
    key = f"test_key_{uuid4().hex[:6]}"

    r1 = await client.put(
        f"/api/v1/config/{key}",
        json={"value": 42},
        headers=_auth(token),
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["value"] == 42

    r2 = await client.put(
        f"/api/v1/config/{key}",
        json={"value": 99},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["value"] == 99

    # confirm GET reflects new value
    r3 = await client.get(f"/api/v1/config/{key}", headers=_auth(token))
    assert r3.status_code == 200, r3.text
    assert r3.json()["value"] == 99


@pytest.mark.asyncio
async def test_atendente_gets_403_on_config(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    """Atendente role cannot access /api/v1/config — should get 403."""
    app = _make_app(db_session, redis_client)
    atendente = await _make_user(db_session, role=Role.ATENDENTE, name="Atendente User")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, atendente["email"], atendente["password"])

        r = await c.get("/api/v1/config/some_key", headers=_auth(token))
        assert r.status_code == 403

        r2 = await c.put(
            "/api/v1/config/some_key",
            json={"value": "x"},
            headers=_auth(token),
        )
        assert r2.status_code == 403
