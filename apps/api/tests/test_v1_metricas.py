"""Integration tests for /api/v1/metricas endpoint."""
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
from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaStatus,
    Lead,
    LeadStatus,
    OrdemServico,
    OsStatus,
)
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


async def _make_cliente(db_session: AsyncSession) -> Cliente:
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("000.000.000-00"),
        cpf_hash="test-cpf-hash-" + uuid4().hex[:8],
        nome_encrypted=encrypt_pii("Test Cliente"),
        whatsapp="5511" + str(uuid4().int)[:8],
    )
    db_session.add(c)
    await db_session.flush()
    return c


async def _make_conversa(
    db_session: AsyncSession,
    status: ConversaStatus = ConversaStatus.AGUARDANDO,
) -> Conversa:
    c = Conversa(
        whatsapp="5511" + str(uuid4().int)[:8],
        status=status,
    )
    db_session.add(c)
    await db_session.flush()
    return c


async def _make_os(
    db_session: AsyncSession,
    cliente: Cliente,
    status: OsStatus = OsStatus.PENDENTE,
    concluida_em: datetime | None = None,
    csat: int | None = None,
) -> OrdemServico:
    os_ = OrdemServico(
        codigo=f"OS-{uuid4().hex[:8]}",
        cliente_id=cliente.id,
        problema="Internet caindo",
        endereco="Rua Teste, 123",
        status=status,
        concluida_em=concluida_em,
        csat=csat,
    )
    db_session.add(os_)
    await db_session.flush()
    return os_


async def _make_lead(
    db_session: AsyncSession,
    status: LeadStatus = LeadStatus.NOVO,
) -> Lead:
    lead = Lead(
        nome=f"Lead {uuid4().hex[:6]}",
        whatsapp="5511" + str(uuid4().int)[:8],
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
    admin = await _make_user(db_session, role=Role.ADMIN, name="Test Admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        yield c, token, admin, db_session


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metricas_returns_all_7_fields(app_and_token: Any) -> None:
    """GET /api/v1/metricas returns a JSON object with all 7 required fields."""
    client, token, _admin, _db = app_and_token

    r = await client.get("/api/v1/metricas", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    expected_keys = {
        "conversas_aguardando",
        "conversas_humano",
        "msgs_24h",
        "os_abertas",
        "os_concluidas_24h",
        "csat_avg_30d",
        "leads_novos_7d",
    }
    assert expected_keys == set(body.keys())


@pytest.mark.asyncio
async def test_metricas_conversas_aguardando_count(app_and_token: Any) -> None:
    """conversas_aguardando reflects seeded AGUARDANDO conversas."""
    client, token, _admin, db_session = app_and_token

    # seed 2 AGUARDANDO + 1 HUMANO — only AGUARDANDO should be counted
    await _make_conversa(db_session, status=ConversaStatus.AGUARDANDO)
    await _make_conversa(db_session, status=ConversaStatus.AGUARDANDO)
    await _make_conversa(db_session, status=ConversaStatus.HUMANO)

    r = await client.get("/api/v1/metricas", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    # We seeded at least 2 AGUARDANDO; exact count depends on DB state so use >=
    assert body["conversas_aguardando"] >= 2
    assert body["conversas_humano"] >= 1


@pytest.mark.asyncio
async def test_metricas_os_abertas_count(app_and_token: Any) -> None:
    """os_abertas includes PENDENTE and EM_ANDAMENTO orders."""
    client, token, _admin, db_session = app_and_token

    cliente = await _make_cliente(db_session)
    await _make_os(db_session, cliente, status=OsStatus.PENDENTE)
    await _make_os(db_session, cliente, status=OsStatus.EM_ANDAMENTO)
    await _make_os(db_session, cliente, status=OsStatus.CONCLUIDA)

    r = await client.get("/api/v1/metricas", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["os_abertas"] >= 2


@pytest.mark.asyncio
async def test_metricas_os_concluidas_24h(app_and_token: Any) -> None:
    """os_concluidas_24h counts only OS concluded in the last 24 hours."""
    client, token, _admin, db_session = app_and_token

    cliente = await _make_cliente(db_session)
    now = datetime.now(tz=UTC)
    # recent concluded OS (within 24h)
    await _make_os(
        db_session,
        cliente,
        status=OsStatus.CONCLUIDA,
        concluida_em=now - timedelta(hours=1),
    )
    # old concluded OS (outside 24h)
    await _make_os(
        db_session,
        cliente,
        status=OsStatus.CONCLUIDA,
        concluida_em=now - timedelta(hours=48),
    )

    r = await client.get("/api/v1/metricas", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["os_concluidas_24h"] >= 1


@pytest.mark.asyncio
async def test_metricas_leads_novos_7d(app_and_token: Any) -> None:
    """leads_novos_7d counts NOVO leads created in last 7 days."""
    client, token, _admin, db_session = app_and_token

    await _make_lead(db_session, status=LeadStatus.NOVO)

    r = await client.get("/api/v1/metricas", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["leads_novos_7d"] >= 1


@pytest.mark.asyncio
async def test_metricas_csat_avg_none_when_no_data(app_and_token: Any) -> None:
    """csat_avg_30d can be null when no rated OS exist in the last 30 days."""
    client, token, _admin, _db = app_and_token

    r = await client.get("/api/v1/metricas", headers=_auth(token))
    assert r.status_code == 200, r.text
    # csat_avg_30d should be float or null — just check it's not an unexpected type
    body = r.json()
    assert body["csat_avg_30d"] is None or isinstance(body["csat_avg_30d"], (int, float))


@pytest.mark.asyncio
async def test_metricas_atendente_can_read(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    """Atendente role is allowed to call GET /api/v1/metricas."""
    app = _make_app(db_session, redis_client)
    atendente = await _make_user(db_session, role=Role.ATENDENTE, name="Atendente User")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, atendente["email"], atendente["password"])
        r = await c.get("/api/v1/metricas", headers=_auth(token))
        assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_metricas_unauthenticated_returns_401(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    """GET /api/v1/metricas without auth token returns 401."""
    app = _make_app(db_session, redis_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/metricas")
    assert r.status_code == 401
