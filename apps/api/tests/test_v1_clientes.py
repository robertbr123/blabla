"""Integration tests for /api/v1/clientes endpoints (incl. LGPD export/delete)."""
from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
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


async def _make_cliente(
    db_session: AsyncSession,
    *,
    nome: str = "Maria Souza",
    cpf: str = "123.456.789-00",
    whatsapp: str = "5511988887777",
    cidade: str = "Manaus",
    plano: str = "200MB",
    status: str = "ativo",
) -> Cliente:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf),
        cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii(nome),
        whatsapp=whatsapp,
        plano=plano,
        status=status,
        cidade=cidade,
    )
    db_session.add(cliente)
    await db_session.flush()
    return cliente


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
async def test_list_returns_list_items_without_pii(app_and_admin: Any) -> None:
    """GET /api/v1/clientes returns list without PII fields (no nome/cpf_cnpj)."""
    client, token, _admin, db_session = app_and_admin
    await _make_cliente(db_session, nome="Ana Lima", cpf="111.222.333-44", whatsapp="5511900000001")
    await _make_cliente(db_session, nome="Carlos Dias", cpf="555.666.777-88", whatsapp="5511900000002")

    r = await client.get("/api/v1/clientes", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert len(body["items"]) >= 2
    first = body["items"][0]
    # list item fields present
    assert "id" in first
    assert "whatsapp" in first
    assert "cidade" in first
    assert "plano" in first
    # PII fields must NOT be present
    assert "nome" not in first
    assert "cpf_cnpj" not in first
    assert "endereco" not in first


@pytest.mark.asyncio
async def test_detail_returns_decrypted_pii(app_and_admin: Any) -> None:
    """GET /api/v1/clientes/{id} returns ClienteDetail with decrypted nome and cpf."""
    client, token, _admin, db_session = app_and_admin
    cliente = await _make_cliente(
        db_session, nome="Pedro Alves", cpf="999.888.777-66", whatsapp="5511900000010"
    )

    r = await client.get(f"/api/v1/clientes/{cliente.id}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(cliente.id)
    assert body["nome"] == "Pedro Alves"
    assert body["cpf_cnpj"] == "999.888.777-66"
    assert body["whatsapp"] == "5511900000010"


@pytest.mark.asyncio
async def test_get_cliente_404(app_and_admin: Any) -> None:
    """GET /api/v1/clientes/{unknown_id} returns 404."""
    client, token, _admin, _db = app_and_admin
    r = await client.get(f"/api/v1/clientes/{uuid4()}", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_returns_zip_with_required_files(app_and_admin: Any) -> None:
    """GET /api/v1/clientes/{id}/export returns ZIP containing all three JSON files."""
    client, token, _admin, db_session = app_and_admin
    cliente = await _make_cliente(
        db_session, nome="Export Test", cpf="000.111.222-33", whatsapp="5511900000020"
    )
    # Add a conversa linked to this cliente
    conv = Conversa(
        cliente_id=cliente.id,
        whatsapp=cliente.whatsapp,
        estado=ConversaEstado.ENCERRADA,
        status=ConversaStatus.ENCERRADA,
    )
    db_session.add(conv)
    await db_session.flush()

    r = await client.get(f"/api/v1/clientes/{cliente.id}/export", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert "attachment" in r.headers.get("content-disposition", "")

    buf = io.BytesIO(r.content)
    with zipfile.ZipFile(buf) as zf:
        names = set(zf.namelist())
        assert "cliente.json" in names
        assert "conversas.json" in names
        assert "ordens_servico.json" in names
        assert "README.txt" in names

        import json
        cliente_json = json.loads(zf.read("cliente.json"))
        assert cliente_json["nome"] == "Export Test"
        assert cliente_json["cpf_cnpj"] == "000.111.222-33"

        conversas_json = json.loads(zf.read("conversas.json"))
        assert len(conversas_json) == 1
        assert conversas_json[0]["id"] == str(conv.id)


@pytest.mark.asyncio
async def test_delete_soft_deletes_and_sets_retention(app_and_admin: Any) -> None:
    """DELETE /api/v1/clientes/{id} soft-deletes and sets retention_until=now+30d."""
    client, token, _admin, db_session = app_and_admin
    cliente = await _make_cliente(
        db_session, nome="Delete Test", cpf="444.333.222-11", whatsapp="5511900000030"
    )
    cliente_id = str(cliente.id)

    before = datetime.now(tz=UTC)
    r = await client.delete(f"/api/v1/clientes/{cliente_id}", headers=_auth(token))
    assert r.status_code == 204, r.text

    # Subsequent GET should return 404 (soft-deleted)
    r2 = await client.get(f"/api/v1/clientes/{cliente_id}", headers=_auth(token))
    assert r2.status_code == 404

    # Check DB state
    await db_session.refresh(cliente)
    assert cliente.deleted_at is not None
    assert cliente.retention_until is not None
    expected_min = before + timedelta(days=29)
    expected_max = before + timedelta(days=31)
    assert expected_min <= cliente.retention_until <= expected_max


@pytest.mark.asyncio
async def test_atendente_can_read_but_not_export_or_delete(app_and_atendente: Any) -> None:
    """Atendente role can list/detail clientes but export and delete are admin-only (403)."""
    client, token, _atendente, db_session = app_and_atendente
    cliente = await _make_cliente(
        db_session, nome="Role Test", cpf="777.888.999-00", whatsapp="5511900000040"
    )

    # Atendente can list
    r = await client.get("/api/v1/clientes", headers=_auth(token))
    assert r.status_code == 200

    # Atendente can get detail
    r = await client.get(f"/api/v1/clientes/{cliente.id}", headers=_auth(token))
    assert r.status_code == 200

    # Atendente cannot export (admin only)
    r = await client.get(f"/api/v1/clientes/{cliente.id}/export", headers=_auth(token))
    assert r.status_code == 403

    # Atendente cannot delete (admin only)
    r = await client.delete(f"/api/v1/clientes/{cliente.id}", headers=_auth(token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    """Unauthenticated requests to /api/v1/clientes return 401."""
    app = _make_app(db_session, redis_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/clientes")
    assert r.status_code == 401
