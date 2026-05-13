"""Integration tests for /api/v1/conversas endpoints."""
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
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
    MensagemRole,
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


async def _make_conversa(db_session: AsyncSession, *, whatsapp: str = "5511999990000") -> Conversa:
    c = Conversa(whatsapp=whatsapp)
    db_session.add(c)
    await db_session.flush()
    return c


async def _make_mensagem(
    db_session: AsyncSession,
    conversa: Conversa,
    text: str = "olá",
    role: MensagemRole = MensagemRole.CLIENTE,
) -> Mensagem:
    m = Mensagem(
        conversa_id=conversa.id,
        external_id=None,
        role=role,
        content_encrypted=encrypt_pii(text),
        created_at=datetime.now(tz=UTC),
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
async def app_and_token(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    admin = await _make_admin(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        yield c, token, admin, db_session


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_paginated(app_and_token: Any) -> None:
    client, token, _admin, db_session = app_and_token
    await _make_conversa(db_session, whatsapp="5511000000001")
    await _make_conversa(db_session, whatsapp="5511000000002")

    r = await client.get("/api/v1/conversas?limit=1", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert len(body["items"]) == 1
    # next_cursor should be set since we have more than 1
    assert "next_cursor" in body


@pytest.mark.asyncio
async def test_list_no_auth_401(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    app = _make_app(db_session, redis_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/conversas")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_by_id_returns_conversa_with_messages(app_and_token: Any) -> None:
    client, token, _admin, db_session = app_and_token
    c = await _make_conversa(db_session)
    await _make_mensagem(db_session, c, text="hello world")

    r = await client.get(f"/api/v1/conversas/{c.id}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(c.id)
    assert len(body["mensagens"]) == 1
    # decrypted content should appear
    assert body["mensagens"][0]["content"] == "hello world"


@pytest.mark.asyncio
async def test_get_by_id_404(app_and_token: Any) -> None:
    client, token, _admin, _db = app_and_token
    r = await client.get(f"/api/v1/conversas/{uuid4()}", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_atender_sets_status_humano(app_and_token: Any) -> None:
    client, token, admin, db_session = app_and_token
    c = await _make_conversa(db_session)

    r = await client.post(f"/api/v1/conversas/{c.id}/atender", headers=_auth(token))
    assert r.status_code == 204

    await db_session.refresh(c)
    assert c.status == ConversaStatus.HUMANO
    assert c.atendente_id == admin["id"]


@pytest.mark.asyncio
async def test_atender_404(app_and_token: Any) -> None:
    client, token, _admin, _db = app_and_token
    r = await client.post(f"/api/v1/conversas/{uuid4()}/atender", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_responder_enqueues_outbound(
    app_and_token: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token, _admin, db_session = app_and_token
    c = await _make_conversa(db_session)

    captured: list[tuple[str, str, Any]] = []
    monkeypatch.setattr(
        "ondeline_api.api.v1.conversas.CeleryOutboundEnqueuer",
        lambda: type(
            "FakeEnq",
            (),
            {"enqueue_send_outbound": lambda self, jid, text, cid: captured.append((jid, text, cid))},
        )(),
    )

    r = await client.post(
        f"/api/v1/conversas/{c.id}/responder",
        json={"text": "Olá, posso ajudar?"},
        headers=_auth(token),
    )
    assert r.status_code == 204
    assert len(captured) == 1
    assert captured[0][0] == c.whatsapp
    assert captured[0][1] == "Olá, posso ajudar?"


@pytest.mark.asyncio
async def test_responder_empty_text_rejected(app_and_token: Any) -> None:
    client, token, _admin, db_session = app_and_token
    c = await _make_conversa(db_session)

    r = await client.post(
        f"/api/v1/conversas/{c.id}/responder",
        json={"text": ""},
        headers=_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_encerrar_sets_status_encerrada(app_and_token: Any) -> None:
    client, token, _admin, db_session = app_and_token
    c = await _make_conversa(db_session)

    r = await client.post(f"/api/v1/conversas/{c.id}/encerrar", headers=_auth(token))
    assert r.status_code == 204

    await db_session.refresh(c)
    assert c.status == ConversaStatus.ENCERRADA
    assert c.estado == ConversaEstado.ENCERRADA


@pytest.mark.asyncio
async def test_delete_soft_deletes(app_and_token: Any) -> None:
    client, token, _admin, db_session = app_and_token
    c = await _make_conversa(db_session)

    r = await client.delete(f"/api/v1/conversas/{c.id}", headers=_auth(token))
    assert r.status_code == 204

    await db_session.refresh(c)
    assert c.deleted_at is not None
    assert c.retention_until is not None
    # retention_until should be ~30d from now
    diff = c.retention_until - datetime.now(tz=UTC)
    assert timedelta(days=29) < diff < timedelta(days=31)


@pytest.mark.asyncio
async def test_mensagens_pagination(app_and_token: Any) -> None:
    client, token, _admin, db_session = app_and_token
    c = await _make_conversa(db_session)
    for i in range(3):
        await _make_mensagem(db_session, c, text=f"msg {i}")

    r = await client.get(f"/api/v1/conversas/{c.id}/mensagens?limit=2", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None
