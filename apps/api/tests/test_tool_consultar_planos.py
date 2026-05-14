"""Tool consultar_planos — usa Config['planos'] ou default."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.models.business import Conversa, ConversaEstado, ConversaStatus
from ondeline_api.repositories.config import ConfigRepo
from ondeline_api.tools.consultar_planos import consultar_planos
from ondeline_api.tools.context import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _ctx(db_session: AsyncSession) -> ToolContext:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    return ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )


async def test_default_quando_config_vazio(db_session) -> None:
    out = await consultar_planos(_ctx(db_session))
    assert "planos" in out
    assert any(p["nome"] == "Essencial" for p in out["planos"])


async def test_le_do_config_quando_presente(db_session) -> None:
    await ConfigRepo(db_session).set(
        "planos", [{"nome": "X", "preco": 1.0, "velocidade": "1MB", "ativo": True}]
    )
    await db_session.flush()
    out = await consultar_planos(_ctx(db_session))
    assert out["planos"] == [{"nome": "X", "preco": 1.0, "velocidade": "1MB", "ativo": True}]


async def test_filtra_planos_inativos(db_session) -> None:
    await ConfigRepo(db_session).set(
        "planos",
        [
            {"nome": "Ativo", "preco": 100.0, "velocidade": "50MB", "ativo": True},
            {"nome": "Inativo", "preco": 200.0, "velocidade": "100MB", "ativo": False},
        ],
    )
    await db_session.flush()
    out = await consultar_planos(_ctx(db_session))
    assert len(out["planos"]) == 1
    assert out["planos"][0]["nome"] == "Ativo"
