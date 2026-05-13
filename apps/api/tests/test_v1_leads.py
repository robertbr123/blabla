"""Integration tests for /api/v1/leads endpoints."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Lead, LeadStatus
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


async def _make_admin(db_session: AsyncSession) -> dict[str, Any]:
    email = f"admin-{uuid4().hex[:8]}@example.com"
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
    return {"email": email, "password": password, "id": user.id}


async def _make_lead(
    db_session: AsyncSession,
    *,
    nome: str = "Joao Silva",
    whatsapp: str = "5511988887777",
    status: LeadStatus = LeadStatus.NOVO,
) -> Lead:
    lead = Lead(
        nome=nome,
        whatsapp=whatsapp,
        status=status,
    )
    db_session.add(lead)
    await db_session.flush()
    return lead


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def app_and_token(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    admin = await _make_admin(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        yield c, token, admin, db_session


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_lead_returns_201_with_novo_status(app_and_token: Any) -> None:
    """POST /api/v1/leads creates a lead with status=novo by default."""
    client, token, _admin, _db = app_and_token

    r = await client.post(
        "/api/v1/leads",
        json={
            "nome": "Maria Costa",
            "whatsapp": "5511977776666",
            "interesse": "Plano 200MB",
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nome"] == "Maria Costa"
    assert body["whatsapp"] == "5511977776666"
    assert body["interesse"] == "Plano 200MB"
    assert body["status"] == "novo"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_list_leads_paginated(app_and_token: Any) -> None:
    """GET /api/v1/leads returns paginated list with cursor."""
    client, token, _admin, db_session = app_and_token
    await _make_lead(db_session, nome="Lead A", whatsapp="5511900000001")
    await _make_lead(db_session, nome="Lead B", whatsapp="5511900000002")
    await _make_lead(db_session, nome="Lead C", whatsapp="5511900000003")

    r = await client.get("/api/v1/leads?limit=2", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None


@pytest.mark.asyncio
async def test_list_leads_filter_by_status(app_and_token: Any) -> None:
    """GET /api/v1/leads?status=convertido returns only matching leads."""
    client, token, _admin, db_session = app_and_token
    await _make_lead(db_session, nome="Convertido", whatsapp="5511900000010", status=LeadStatus.CONVERTIDO)
    await _make_lead(db_session, nome="Novo Lead", whatsapp="5511900000011", status=LeadStatus.NOVO)

    r = await client.get("/api/v1/leads?status=convertido", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(item["status"] == "convertido" for item in body["items"])


@pytest.mark.asyncio
async def test_get_lead_returns_detail(app_and_token: Any) -> None:
    """GET /api/v1/leads/{id} returns the lead detail."""
    client, token, _admin, db_session = app_and_token
    lead = await _make_lead(db_session, nome="Detail Test", whatsapp="5511900000020")

    r = await client.get(f"/api/v1/leads/{lead.id}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(lead.id)
    assert body["nome"] == "Detail Test"


@pytest.mark.asyncio
async def test_get_lead_404(app_and_token: Any) -> None:
    """GET /api/v1/leads/{id} returns 404 for unknown id."""
    client, token, _admin, _db = app_and_token
    r = await client.get(f"/api/v1/leads/{uuid4()}", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_lead_updates_status_and_notas(app_and_token: Any) -> None:
    """PATCH /api/v1/leads/{id} updates status and notas fields."""
    client, token, _admin, db_session = app_and_token
    lead = await _make_lead(db_session, nome="Patch Lead", whatsapp="5511900000030")

    r = await client.patch(
        f"/api/v1/leads/{lead.id}",
        json={"status": "contato", "notas": "Ligamos, demonstrou interesse."},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "contato"
    assert body["notas"] == "Ligamos, demonstrou interesse."

    await db_session.refresh(lead)
    assert lead.status == LeadStatus.CONTATO
    assert lead.notas == "Ligamos, demonstrou interesse."


@pytest.mark.asyncio
async def test_delete_lead_removes_record(app_and_token: Any) -> None:
    """DELETE /api/v1/leads/{id} removes the lead and subsequent GET returns 404."""
    client, token, _admin, db_session = app_and_token
    lead = await _make_lead(db_session, nome="Delete Me", whatsapp="5511900000040")
    lead_id = str(lead.id)

    r = await client.delete(f"/api/v1/leads/{lead_id}", headers=_auth(token))
    assert r.status_code == 204, r.text

    r2 = await client.get(f"/api/v1/leads/{lead_id}", headers=_auth(token))
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_leads_unauthenticated_returns_401(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    """GET /api/v1/leads without auth returns 401."""
    app = _make_app(db_session, redis_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/leads")
    assert r.status_code == 401
