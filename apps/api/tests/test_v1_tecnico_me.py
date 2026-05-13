"""Integration tests for /api/v1/tecnico/me/* endpoints."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Cliente, OrdemServico, OsStatus, Tecnico
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


async def _make_tecnico_user(
    db_session: AsyncSession,
) -> tuple[User, Tecnico, str]:
    pw = "test-pwd-123!"
    email = f"tec_{uuid4().hex[:6]}@test.example"
    user = User(
        email=email,
        password_hash=hash_password(pw),
        role=Role.TECNICO,
        name="Tec Test",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    tec = Tecnico(nome="Tec Test", user_id=user.id, ativo=True)
    db_session.add(tec)
    await db_session.flush()
    return user, tec, pw


async def _make_cliente(db_session: AsyncSession) -> Cliente:
    import hashlib
    import hmac as hmac_mod

    from cryptography.fernet import Fernet
    from ondeline_api.config import get_settings

    settings = get_settings()
    key = settings.pii_encryption_key.get_secret_value().encode()
    f = Fernet(key)
    cpf = "12345678901"
    pepper = settings.pii_hash_pepper.get_secret_value().encode()
    cpf_hash = hmac_mod.new(pepper, cpf.encode(), hashlib.sha256).hexdigest()
    cliente = Cliente(
        cpf_cnpj_encrypted=f.encrypt(cpf.encode()).decode(),
        cpf_hash=cpf_hash,
        nome_encrypted=f.encrypt(b"Cliente Test").decode(),
        whatsapp="5592999990000",
    )
    db_session.add(cliente)
    await db_session.flush()
    return cliente


async def _make_os(
    db_session: AsyncSession,
    cliente_id: Any,
    tecnico_id: Any,
    *,
    status: OsStatus = OsStatus.PENDENTE,
) -> OrdemServico:
    os_ = OrdemServico(
        codigo=f"OS-{uuid4().hex[:6]}",
        cliente_id=cliente_id,
        tecnico_id=tecnico_id,
        problema="Sem sinal",
        endereco="Rua Teste 123",
        status=status,
    )
    db_session.add(os_)
    await db_session.flush()
    return os_


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def app_and_tecnico(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    user, tec, pw = await _make_tecnico_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user.email, pw)
        yield c, token, user, tec, db_session


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_os_returns_only_my_os(app_and_tecnico: Any) -> None:
    """GET /os returns only OS assigned to the current tecnico."""
    client, token, _user, tec, db_session = app_and_tecnico
    cliente = await _make_cliente(db_session)
    # my OS
    await _make_os(db_session, cliente.id, tec.id, status=OsStatus.PENDENTE)
    # another tecnico's OS
    other_tec = Tecnico(nome="Other Tec", ativo=True)
    db_session.add(other_tec)
    await db_session.flush()
    await _make_os(db_session, cliente.id, other_tec.id, status=OsStatus.PENDENTE)

    r = await client.get("/api/v1/tecnico/me/os", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["tecnico_id"] == str(tec.id)


@pytest.mark.asyncio
async def test_list_os_status_filter(app_and_tecnico: Any) -> None:
    """GET /os?status=concluida returns concluida OS (normally excluded)."""
    client, token, _user, tec, db_session = app_and_tecnico
    cliente = await _make_cliente(db_session)
    await _make_os(db_session, cliente.id, tec.id, status=OsStatus.CONCLUIDA)

    # default filter excludes concluida
    r = await client.get("/api/v1/tecnico/me/os", headers=_auth(token))
    assert r.status_code == 200
    assert len(r.json()) == 0

    # explicit filter returns it
    r2 = await client.get("/api/v1/tecnico/me/os?status=concluida", headers=_auth(token))
    assert r2.status_code == 200
    assert len(r2.json()) == 1


@pytest.mark.asyncio
async def test_detail_os_404_not_mine(app_and_tecnico: Any) -> None:
    """GET /os/{id} returns 404 when OS belongs to another tecnico."""
    client, token, _user, _tec, db_session = app_and_tecnico
    cliente = await _make_cliente(db_session)
    other_tec = Tecnico(nome="Other Tec 2", ativo=True)
    db_session.add(other_tec)
    await db_session.flush()
    os_ = await _make_os(db_session, cliente.id, other_tec.id)

    r = await client.get(f"/api/v1/tecnico/me/os/{os_.id}", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_gps_update_sets_coords(app_and_tecnico: Any) -> None:
    """POST /gps updates gps_lat/gps_lng on the Tecnico row."""
    client, token, _user, tec, db_session = app_and_tecnico

    r = await client.post(
        "/api/v1/tecnico/me/gps",
        json={"lat": -3.1190, "lng": -60.0217},
        headers=_auth(token),
    )
    assert r.status_code == 204, r.text

    await db_session.refresh(tec)
    assert tec.gps_lat == pytest.approx(-3.1190)
    assert tec.gps_lng == pytest.approx(-60.0217)
    assert tec.gps_ts is not None


@pytest.mark.asyncio
async def test_iniciar_sets_em_andamento_and_gps(app_and_tecnico: Any) -> None:
    """POST /os/{id}/iniciar sets status=em_andamento and gps_inicio_lat/lng."""
    client, token, _user, tec, db_session = app_and_tecnico
    cliente = await _make_cliente(db_session)
    os_ = await _make_os(db_session, cliente.id, tec.id, status=OsStatus.PENDENTE)

    r = await client.post(
        f"/api/v1/tecnico/me/os/{os_.id}/iniciar",
        json={"lat": -3.1190, "lng": -60.0217},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "em_andamento"

    await db_session.refresh(os_)
    assert os_.status == OsStatus.EM_ANDAMENTO
    assert os_.gps_inicio_lat == pytest.approx(-3.1190)
    assert os_.gps_inicio_lng == pytest.approx(-60.0217)


@pytest.mark.asyncio
async def test_concluir_sets_concluida_csat_gps(app_and_tecnico: Any) -> None:
    """POST /os/{id}/concluir sets status=concluida + csat + gps_fim."""
    client, token, _user, tec, db_session = app_and_tecnico
    cliente = await _make_cliente(db_session)
    os_ = await _make_os(db_session, cliente.id, tec.id, status=OsStatus.EM_ANDAMENTO)

    r = await client.post(
        f"/api/v1/tecnico/me/os/{os_.id}/concluir",
        json={"csat": 5, "comentario": "Tudo certo", "lat": -3.1200, "lng": -60.0300},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "concluida"
    assert body["csat"] == 5
    assert body["comentario_cliente"] == "Tudo certo"
    assert body["concluida_em"] is not None

    await db_session.refresh(os_)
    assert os_.gps_fim_lat == pytest.approx(-3.1200)
    assert os_.gps_fim_lng == pytest.approx(-60.0300)


@pytest.mark.asyncio
async def test_403_if_user_has_no_tecnico_row(db_session: AsyncSession, redis_client: Any) -> None:
    """Returns 403 when the authenticated user has no Tecnico row."""
    pw = "test-pwd-123!"
    email = f"tec_norow_{uuid4().hex[:6]}@test.example"
    user = User(
        email=email,
        password_hash=hash_password(pw),
        role=Role.TECNICO,
        name="No Row Tec",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    app = _make_app(db_session, redis_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, email, pw)
        r = await client.get("/api/v1/tecnico/me/os", headers=_auth(token))
        assert r.status_code == 403
        assert "tecnico" in r.json()["detail"]


@pytest.mark.asyncio
async def test_401_unauthenticated() -> None:
    """Returns 401 without a token."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/tecnico/me/os")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_atendente_gets_403(db_session: AsyncSession, redis_client: Any) -> None:
    """Atendente role gets 403 on tecnico/me endpoints."""
    pw = "test-pwd-123!"
    email = f"atendente_{uuid4().hex[:6]}@test.example"
    user = User(
        email=email,
        password_hash=hash_password(pw),
        role=Role.ATENDENTE,
        name="Atendente Test",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    app = _make_app(db_session, redis_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, email, pw)
        r = await client.get("/api/v1/tecnico/me/os", headers=_auth(token))
        assert r.status_code == 403
