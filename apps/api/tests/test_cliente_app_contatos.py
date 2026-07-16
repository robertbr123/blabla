"""E2E /api/v1/cliente-app/contatos (GET publico, sem auth).

Contatos da operadora sao informacao publica (telefone/WhatsApp/redes) usada
no fluxo pre-login do app do cliente, entao o GET nao deve exigir token.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_listar_contatos_sem_auth_retorna_200(app: FastAPI, db_session: AsyncSession) -> None:
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/cliente-app/contatos")

    assert resp.status_code == 200
    assert "items" in resp.json()
