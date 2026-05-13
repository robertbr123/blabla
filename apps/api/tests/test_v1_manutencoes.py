"""Integration tests for /api/v1/manutencoes endpoints."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Manutencao
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


async def _make_manutencao(
    db_session: AsyncSession,
    *,
    titulo: str = "Manutenção Teste",
    descricao: str | None = None,
    offset_hours: int = 0,
    duration_hours: int = 2,
    cidades: list[str] | None = None,
    notificar: bool = True,
) -> Manutencao:
    now = datetime.now(tz=UTC)
    inicio = now + timedelta(hours=offset_hours)
    fim = inicio + timedelta(hours=duration_hours)
    m = Manutencao(
        titulo=titulo,
        descricao=descricao,
        inicio_at=inicio,
        fim_at=fim,
        cidades=cidades,
        notificar=notificar,
    )
    db_session.add(m)
    await db_session.flush()
    return m


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
async def test_create_manutencao_returns_201(app_and_admin: Any) -> None:
    """POST /api/v1/manutencoes creates a manutencao and returns 201."""
    client, token, _admin, _db = app_and_admin
    now = datetime.now(tz=UTC)

    r = await client.post(
        "/api/v1/manutencoes",
        json={
            "titulo": "Fibra Zona Norte",
            "descricao": "Troca de cabos na Zona Norte",
            "inicio_at": (now + timedelta(hours=1)).isoformat(),
            "fim_at": (now + timedelta(hours=3)).isoformat(),
            "cidades": ["Manaus"],
            "notificar": True,
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["titulo"] == "Fibra Zona Norte"
    assert body["descricao"] == "Troca de cabos na Zona Norte"
    assert body["cidades"] == ["Manaus"]
    assert body["notificar"] is True
    assert "id" in body
    assert "criada_em" in body


@pytest.mark.asyncio
async def test_list_manutencoes_returns_all(app_and_admin: Any) -> None:
    """GET /api/v1/manutencoes returns paginated list of all manutencoes."""
    client, token, _admin, db_session = app_and_admin
    await _make_manutencao(db_session, titulo="M1", offset_hours=1)
    await _make_manutencao(db_session, titulo="M2", offset_hours=2)

    r = await client.get("/api/v1/manutencoes", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert len(body["items"]) >= 2


@pytest.mark.asyncio
async def test_list_manutencoes_ativas_filter(app_and_admin: Any) -> None:
    """GET /api/v1/manutencoes?ativas=true returns only active manutencoes."""
    client, token, _admin, db_session = app_and_admin
    # Active: started 1h ago, ends in 1h
    await _make_manutencao(db_session, titulo="Ativa", offset_hours=-1, duration_hours=2)
    # Future: starts in 5h
    await _make_manutencao(db_session, titulo="Futura", offset_hours=5, duration_hours=2)

    r = await client.get("/api/v1/manutencoes?ativas=true", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    titulos = {item["titulo"] for item in body["items"]}
    assert "Ativa" in titulos
    assert "Futura" not in titulos


@pytest.mark.asyncio
async def test_get_manutencao_detail(app_and_admin: Any) -> None:
    """GET /api/v1/manutencoes/{id} returns the manutencao detail."""
    client, token, _admin, db_session = app_and_admin
    m = await _make_manutencao(
        db_session, titulo="Detalhe Test", cidades=["Parintins", "Manaus"]
    )

    r = await client.get(f"/api/v1/manutencoes/{m.id}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(m.id)
    assert body["titulo"] == "Detalhe Test"
    assert set(body["cidades"]) == {"Parintins", "Manaus"}


@pytest.mark.asyncio
async def test_patch_manutencao_cidades(app_and_admin: Any) -> None:
    """PATCH /api/v1/manutencoes/{id} updates cidades field."""
    client, token, _admin, db_session = app_and_admin
    m = await _make_manutencao(db_session, titulo="Patch Test", cidades=["Manaus"])

    r = await client.patch(
        f"/api/v1/manutencoes/{m.id}",
        json={"cidades": ["Manaus", "Itacoatiara"]},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["cidades"]) == {"Manaus", "Itacoatiara"}

    await db_session.refresh(m)
    assert m.cidades is not None
    assert set(m.cidades) == {"Manaus", "Itacoatiara"}


@pytest.mark.asyncio
async def test_delete_manutencao_returns_204(app_and_admin: Any) -> None:
    """DELETE /api/v1/manutencoes/{id} removes the manutencao and returns 204."""
    client, token, _admin, db_session = app_and_admin
    m = await _make_manutencao(db_session, titulo="Delete Test")
    m_id = str(m.id)

    r = await client.delete(f"/api/v1/manutencoes/{m_id}", headers=_auth(token))
    assert r.status_code == 204, r.text

    r2 = await client.get(f"/api/v1/manutencoes/{m_id}", headers=_auth(token))
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_get_manutencao_404_when_not_found(app_and_admin: Any) -> None:
    """GET /api/v1/manutencoes/{unknown_id} returns 404."""
    client, token, _admin, _db = app_and_admin
    r = await client.get(f"/api/v1/manutencoes/{uuid4()}", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_atendente_gets_403(app_and_atendente: Any) -> None:
    """Atendente role gets 403 on all /api/v1/manutencoes endpoints (admin only)."""
    client, token, _atendente, _db = app_and_atendente
    now = datetime.now(tz=UTC)

    r = await client.get("/api/v1/manutencoes", headers=_auth(token))
    assert r.status_code == 403

    r = await client.post(
        "/api/v1/manutencoes",
        json={
            "titulo": "Should Fail",
            "inicio_at": now.isoformat(),
            "fim_at": (now + timedelta(hours=1)).isoformat(),
        },
        headers=_auth(token),
    )
    assert r.status_code == 403

    fake_id = uuid4()
    r = await client.get(f"/api/v1/manutencoes/{fake_id}", headers=_auth(token))
    assert r.status_code == 403

    r = await client.patch(
        f"/api/v1/manutencoes/{fake_id}",
        json={"titulo": "Nope"},
        headers=_auth(token),
    )
    assert r.status_code == 403

    r = await client.delete(f"/api/v1/manutencoes/{fake_id}", headers=_auth(token))
    assert r.status_code == 403
