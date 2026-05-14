"""Test GET /api/v1/conversas/{id} returns embedded cliente."""
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
from ondeline_api.db.models.business import Conversa, ConversaEstado, ConversaStatus, Cliente
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


def _make_app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    app = create_app()

    async def _override_db() -> Any:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


async def test_get_conversa_inclui_cliente_embutido(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    email = f"adm-{uuid4().hex[:6]}@test.com"
    user = User(
        email=email, password_hash=hash_password("Admin1234!"),
        role=Role.ADMIN, name="A", is_active=True,
    )
    db_session.add(user)
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Maria"),
        whatsapp="5511999@s",
        plano="Fibra 200",
        cidade="Manaus",
    )
    db_session.add(cliente)
    await db_session.flush()

    conv = Conversa(
        whatsapp="5511999@s",
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
        cliente_id=cliente.id,
    )
    db_session.add(conv)
    await db_session.flush()

    app = _make_app(db_session, redis_client)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/auth/login", json={"email": email, "password": "Admin1234!"})
        assert r.status_code == 200
        token = r.json()["access_token"]
        r2 = await c.get(
            f"/api/v1/conversas/{conv.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["cliente"] is not None
    assert data["cliente"]["nome"] == "Maria"
    assert data["cliente"]["plano"] == "Fibra 200"
