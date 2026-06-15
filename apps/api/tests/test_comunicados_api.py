# apps/api/tests/test_comunicados_api.py
"""Integration tests for /api/v1/admin/comunicados endpoints."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Canal, Cliente
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


# ─── Fixtures ────────────────────────────────────────────────────────────────


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


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_criar_preview_e_disparar(app_and_admin: Any, monkeypatch: Any) -> None:
    client, token, _admin, db_session = app_and_admin

    # Cidade única: o banco de teste do CI é compartilhado entre testes que
    # commitam (ex: test_broadcast_task semeia clientes em "Manaus"), então uso
    # uma cidade exclusiva pra o preview contar só o cliente deste teste.
    cidade = f"Manaus-{uuid4().hex[:8]}"

    # Seed: canal Cloud e cliente na cidade exclusiva
    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}",
        nome="Comercial",
        provider="cloud",
        cloud_phone_id="1",
        cloud_waba_id="2",
    )
    db_session.add(canal)

    db_session.add(
        Cliente(
            cpf_cnpj_encrypted=encrypt_pii("0"),
            cpf_hash=hash_pii(uuid4().hex),
            nome_encrypted=encrypt_pii("João"),
            whatsapp="5592111",
            cidade=cidade,
        )
    )

    # Os templates (comunicado_geral, lancamento_app) já vêm do seed da migration
    # 0049 — o banco de teste do CI roda as migrations, então inseri-los aqui
    # colidiria no unique de broadcast_templates.name.
    await db_session.commit()

    # GET /templates deve retornar ao menos o template semeado
    r = await client.get("/api/v1/admin/comunicados/templates", headers=_auth(token))
    assert r.status_code == 200
    assert any(t["name"] == "comunicado_geral" for t in r.json())

    # POST /comunicados cria campanha no canal Cloud
    r = await client.post(
        "/api/v1/admin/comunicados",
        json={
            "titulo": "Lançamento",
            "canal_id": str(canal.id),
            "template_name": "lancamento_app",
            "body_params": ["https://app"],
            "segmentacao": {"cidade": cidade},
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    camp_id = r.json()["id"]

    # POST /preview retorna contagem do segmento
    r = await client.post(
        "/api/v1/admin/comunicados/preview",
        json={"cidade": cidade},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # POST /{id}/send enfileira a task (monkeypatch para não precisar de Celery)
    calls: dict[str, str] = {}
    monkeypatch.setattr(
        "ondeline_api.api.v1.comunicados.send_campanha_task.delay",
        lambda cid: calls.setdefault("id", cid),
    )
    r = await client.post(
        f"/api/v1/admin/comunicados/{camp_id}/send",
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert calls["id"] == camp_id


@pytest.mark.asyncio
async def test_rejeita_canal_nao_cloud(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin

    canal = Canal(
        slug=f"ev-{uuid4().hex[:8]}",
        nome="Evo",
        provider="evolution",
        evolution_instance=f"i-{uuid4().hex[:8]}",
    )
    db_session.add(canal)
    await db_session.commit()

    r = await client.post(
        "/api/v1/admin/comunicados",
        json={
            "titulo": "x",
            "canal_id": str(canal.id),
            "template_name": "comunicado_geral",
            "body_params": ["oi"],
            "segmentacao": {},
        },
        headers=_auth(token),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_editar_campanha_rascunho(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin
    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
        cloud_phone_id="1", cloud_waba_id="2",
    )
    db_session.add(canal)
    await db_session.commit()

    r = await client.post(
        "/api/v1/admin/comunicados",
        json={
            "titulo": "Errado", "canal_id": str(canal.id),
            "template_name": "comunicado_geral", "body_params": [],
            "segmentacao": {},
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    camp_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/admin/comunicados/{camp_id}",
        json={"titulo": "Corrigido", "body_params": ["https://novo"]},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["titulo"] == "Corrigido"
    assert r.json()["body_params"] == ["https://novo"]


@pytest.mark.asyncio
async def test_editar_campanha_concluida_409(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin
    from ondeline_api.db.models.business import Campanha

    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
        cloud_phone_id="1", cloud_waba_id="2",
    )
    db_session.add(canal)
    await db_session.flush()
    camp = Campanha(
        titulo="Feita", canal_id=canal.id, template_name="comunicado_geral",
        status="concluida",
    )
    db_session.add(camp)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/admin/comunicados/{camp.id}",
        json={"titulo": "Nope"},
        headers=_auth(token),
    )
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_editar_campanha_inexistente_404(app_and_admin: Any) -> None:
    client, token, _admin, _db = app_and_admin
    r = await client.patch(
        f"/api/v1/admin/comunicados/{uuid4()}",
        json={"titulo": "X"},
        headers=_auth(token),
    )
    assert r.status_code == 404, r.text
