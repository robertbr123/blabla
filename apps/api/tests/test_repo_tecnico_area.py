"""TecnicoRepo.find_by_area — match exato e fallback."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import Tecnico, TecnicoArea
from ondeline_api.repositories.tecnico import TecnicoRepo
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_match_exato_cidade_rua(db_session: AsyncSession) -> None:
    t1 = Tecnico(nome="Pedro", ativo=True)
    t2 = Tecnico(nome="Joana", ativo=True)
    db_session.add_all([t1, t2])
    await db_session.flush()
    db_session.add_all(
        [
            TecnicoArea(tecnico_id=t1.id, cidade="Sao Paulo", rua="Rua A", prioridade=1),
            TecnicoArea(tecnico_id=t2.id, cidade="Sao Paulo", rua="Rua B", prioridade=1),
        ]
    )
    await db_session.flush()
    repo = TecnicoRepo(db_session)
    chosen = await repo.find_by_area(cidade="Sao Paulo", rua="Rua A")
    assert chosen is not None and chosen.id == t1.id


async def test_fallback_cidade_quando_rua_nao_bate(db_session: AsyncSession) -> None:
    t = Tecnico(nome="Solo", ativo=True)
    db_session.add(t)
    await db_session.flush()
    db_session.add(
        TecnicoArea(tecnico_id=t.id, cidade="Campinas", rua="Rua X", prioridade=1)
    )
    await db_session.flush()
    repo = TecnicoRepo(db_session)
    chosen = await repo.find_by_area(cidade="Campinas", rua="Rua nao cadastrada")
    assert chosen is not None and chosen.id == t.id


async def test_sem_match_retorna_none(db_session: AsyncSession) -> None:
    repo = TecnicoRepo(db_session)
    assert await repo.find_by_area(cidade="Lugar Algum", rua="Y") is None
