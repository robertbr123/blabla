from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Manutencao,
)
from ondeline_api.tools.consultar_manutencoes import consultar_manutencoes
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


async def test_lista_filtra_por_cidade(db_session: AsyncSession) -> None:
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            Manutencao(
                titulo="SP",
                inicio_at=now - timedelta(hours=1),
                fim_at=now + timedelta(hours=2),
                cidades=["Sao Paulo"],
            ),
            Manutencao(
                titulo="RJ",
                inicio_at=now - timedelta(hours=1),
                fim_at=now + timedelta(hours=2),
                cidades=["Rio de Janeiro"],
            ),
            Manutencao(
                titulo="PASSADA",
                inicio_at=now - timedelta(days=2),
                fim_at=now - timedelta(days=1),
                cidades=["Sao Paulo"],
            ),
        ]
    )
    await db_session.flush()
    out = await consultar_manutencoes(_ctx(db_session), cidade="sao paulo")
    titulos = sorted(m["titulo"] for m in out["manutencoes"])
    assert titulos == ["SP"]
