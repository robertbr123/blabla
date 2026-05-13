"""Integration tests for /api/v1/tecnicos endpoints."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Tecnico, TecnicoArea
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
    *,
    role: Role = Role.ADMIN,
) -> dict[str, Any]:
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        name=f"Test {role.value.title()}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"email": email, "password": password, "id": user.id}


async def _make_tecnico(
    db_session: AsyncSession,
    *,
    nome: str = "Carlos Tech",
    whatsapp: str | None = "5592988887777",
    ativo: bool = True,
) -> Tecnico:
    tec = Tecnico(nome=nome, whatsapp=whatsapp, ativo=ativo)
    db_session.add(tec)
    await db_session.flush()
    return tec


async def _make_area(
    db_session: AsyncSession,
    tecnico_id: Any,
    *,
    cidade: str = "Manaus",
    rua: str = "Av Brasil",
    prioridade: int = 1,
) -> TecnicoArea:
    area = TecnicoArea(
        tecnico_id=tecnico_id, cidade=cidade, rua=rua, prioridade=prioridade
    )
    db_session.add(area)
    await db_session.flush()
    return area


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def app_and_admin(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    admin = await _make_user(db_session, role=Role.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        yield c, token, admin, db_session


@pytest_asyncio.fixture
async def app_and_atendente(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    atendente = await _make_user(db_session, role=Role.ATENDENTE)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, atendente["email"], atendente["password"])
        yield c, token, atendente, db_session


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_tecnico_returns_201(app_and_admin: Any) -> None:
    """POST /api/v1/tecnicos creates a tecnico and returns 201."""
    client, token, _admin, _db = app_and_admin

    r = await client.post(
        "/api/v1/tecnicos",
        json={"nome": "Joao Tecnico", "whatsapp": "5592977776666"},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nome"] == "Joao Tecnico"
    assert body["whatsapp"] == "5592977776666"
    assert body["ativo"] is True
    assert "id" in body
    assert body["areas"] == []


@pytest.mark.asyncio
async def test_list_tecnicos_paginated(app_and_admin: Any) -> None:
    """GET /api/v1/tecnicos returns paginated list with cursor."""
    client, token, _admin, db_session = app_and_admin
    await _make_tecnico(db_session, nome="Tec A", whatsapp="5592900000001")
    await _make_tecnico(db_session, nome="Tec B", whatsapp="5592900000002")
    await _make_tecnico(db_session, nome="Tec C", whatsapp="5592900000003")

    r = await client.get("/api/v1/tecnicos?limit=2", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None


@pytest.mark.asyncio
async def test_list_tecnicos_filter_by_ativo(app_and_admin: Any) -> None:
    """GET /api/v1/tecnicos?ativo=false returns only inactive tecnicos."""
    client, token, _admin, db_session = app_and_admin
    await _make_tecnico(db_session, nome="Ativo Tec", whatsapp="5592900000010", ativo=True)
    await _make_tecnico(db_session, nome="Inativo Tec", whatsapp="5592900000011", ativo=False)

    r = await client.get("/api/v1/tecnicos?ativo=false", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(item["ativo"] is False for item in body["items"])


@pytest.mark.asyncio
async def test_get_tecnico_detail_with_areas(app_and_admin: Any) -> None:
    """GET /api/v1/tecnicos/{id} returns detail including nested areas."""
    client, token, _admin, db_session = app_and_admin
    tec = await _make_tecnico(db_session, nome="Area Tec", whatsapp="5592900000020")
    await _make_area(db_session, tec.id, cidade="Manaus", rua="Av Brasil")
    await _make_area(db_session, tec.id, cidade="Manaus", rua="Rua Flores", prioridade=2)

    r = await client.get(f"/api/v1/tecnicos/{tec.id}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(tec.id)
    assert body["nome"] == "Area Tec"
    assert len(body["areas"]) == 2
    cidades = {a["cidade"] for a in body["areas"]}
    assert "Manaus" in cidades


@pytest.mark.asyncio
async def test_get_tecnico_404(app_and_admin: Any) -> None:
    """GET /api/v1/tecnicos/{unknown_id} returns 404."""
    client, token, _admin, _db = app_and_admin
    r = await client.get(f"/api/v1/tecnicos/{uuid4()}", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_tecnico_updates_ativo(app_and_admin: Any) -> None:
    """PATCH /api/v1/tecnicos/{id} updates the ativo flag."""
    client, token, _admin, db_session = app_and_admin
    tec = await _make_tecnico(db_session, nome="Patch Tec", ativo=True)

    r = await client.patch(
        f"/api/v1/tecnicos/{tec.id}",
        json={"ativo": False},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ativo"] is False

    await db_session.refresh(tec)
    assert tec.ativo is False


@pytest.mark.asyncio
async def test_add_and_list_area(app_and_admin: Any) -> None:
    """POST /api/v1/tecnicos/{id}/areas adds an area; GET /areas lists it."""
    client, token, _admin, db_session = app_and_admin
    tec = await _make_tecnico(db_session, nome="Area Add Tec")

    r = await client.post(
        f"/api/v1/tecnicos/{tec.id}/areas",
        json={"cidade": "Manaus", "rua": "Av Torquato Tapajós", "prioridade": 3},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cidade"] == "Manaus"
    assert body["rua"] == "Av Torquato Tapajós"
    assert body["prioridade"] == 3

    r2 = await client.get(f"/api/v1/tecnicos/{tec.id}/areas", headers=_auth(token))
    assert r2.status_code == 200, r2.text
    assert len(r2.json()) == 1


@pytest.mark.asyncio
async def test_delete_area_removes_it(app_and_admin: Any) -> None:
    """DELETE /api/v1/tecnicos/{id}/areas/{cidade}/{rua} removes the area."""
    client, token, _admin, db_session = app_and_admin
    tec = await _make_tecnico(db_session, nome="Area Del Tec")
    await _make_area(db_session, tec.id, cidade="Parintins", rua="Rua Paraiba")

    r = await client.delete(
        f"/api/v1/tecnicos/{tec.id}/areas/Parintins/Rua Paraiba",
        headers=_auth(token),
    )
    assert r.status_code == 204, r.text

    r2 = await client.get(f"/api/v1/tecnicos/{tec.id}/areas", headers=_auth(token))
    assert r2.status_code == 200
    assert r2.json() == []


@pytest.mark.asyncio
async def test_delete_area_404_when_missing(app_and_admin: Any) -> None:
    """DELETE /api/v1/tecnicos/{id}/areas/{cidade}/{rua} returns 404 when not found."""
    client, token, _admin, db_session = app_and_admin
    tec = await _make_tecnico(db_session, nome="No Area Tec")

    r = await client.delete(
        f"/api/v1/tecnicos/{tec.id}/areas/Manaus/Rua Inexistente",
        headers=_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_tecnico_cascades_areas(app_and_admin: Any) -> None:
    """DELETE /api/v1/tecnicos/{id} removes tecnico and cascades to TecnicoArea."""
    client, token, _admin, db_session = app_and_admin
    tec = await _make_tecnico(db_session, nome="Cascade Del Tec")
    await _make_area(db_session, tec.id, cidade="Manaus", rua="Rua Cascade")
    tec_id = str(tec.id)

    r = await client.delete(f"/api/v1/tecnicos/{tec_id}", headers=_auth(token))
    assert r.status_code == 204, r.text

    # Subsequent GET returns 404
    r2 = await client.get(f"/api/v1/tecnicos/{tec_id}", headers=_auth(token))
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_atendente_gets_403_on_all_endpoints(app_and_atendente: Any) -> None:
    """Atendente role gets 403 on all /api/v1/tecnicos endpoints (admin only)."""
    client, token, _atendente, _db = app_and_atendente

    r = await client.get("/api/v1/tecnicos", headers=_auth(token))
    assert r.status_code == 403

    r = await client.post(
        "/api/v1/tecnicos",
        json={"nome": "Should Fail"},
        headers=_auth(token),
    )
    assert r.status_code == 403

    fake_id = uuid4()
    r = await client.get(f"/api/v1/tecnicos/{fake_id}", headers=_auth(token))
    assert r.status_code == 403

    r = await client.patch(
        f"/api/v1/tecnicos/{fake_id}",
        json={"ativo": False},
        headers=_auth(token),
    )
    assert r.status_code == 403

    r = await client.delete(f"/api/v1/tecnicos/{fake_id}", headers=_auth(token))
    assert r.status_code == 403
