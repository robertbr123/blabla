# apps/api/tests/test_campanha_repo_v3.py
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.models.business import Campanha, CampanhaDestinatario, Canal
from ondeline_api.repositories.campanha import CampanhaRepo


async def _campanha_com_destinatarios(session):
    canal = Canal(slug=f"k-{uuid4().hex[:8]}", nome="K", provider="cloud",
                  cloud_phone_id="1", cloud_waba_id="2")
    session.add(canal)
    await session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="x",
                    body_params=[], segmentacao={}, origem="importado",
                    status="rascunho")
    session.add(camp)
    await session.flush()
    dados = [
        ("5592000001", "Manaus", "Ativo"),
        ("5592000002", "Manaus", "Cancelado"),
        ("5592000003", "Itacoatiara", "Ativo"),
    ]
    for tel, cid, st in dados:
        session.add(CampanhaDestinatario(
            campanha_id=camp.id, cliente_id=None, whatsapp=tel,
            status="pendente", csv_cidade=cid, csv_status=st,
        ))
    await session.flush()
    return camp


@pytest.mark.asyncio
async def test_contar_selecionados_com_filtro(db_session):
    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    n = await repo.contar_selecionados(camp.id, {"cidade": "Manaus", "status": "Ativo"})
    assert n == 1
    n_todos = await repo.contar_selecionados(camp.id, {})
    assert n_todos == 3


@pytest.mark.asyncio
async def test_marcar_excluidos_mantem_so_o_recorte(db_session):
    from sqlalchemy import func, select

    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    selecionados = await repo.marcar_excluidos(camp.id, {"cidade": "Manaus"})
    assert selecionados == 2
    n_excl = (await db_session.execute(
        select(func.count()).select_from(CampanhaDestinatario).where(
            CampanhaDestinatario.campanha_id == camp.id,
            CampanhaDestinatario.status == "excluido",
        )
    )).scalar_one()
    assert n_excl == 1


@pytest.mark.asyncio
async def test_reenviar_falhas_reseta(db_session):
    from sqlalchemy import select

    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    dest = (await db_session.execute(
        select(CampanhaDestinatario).where(CampanhaDestinatario.campanha_id == camp.id).limit(1)
    )).scalar_one()
    dest.status = "falha"
    dest.erro = "x"
    dest.wamid = "w"
    await db_session.flush()

    n = await repo.reenviar_falhas(camp.id)
    assert n == 1
    await db_session.refresh(dest)
    assert dest.status == "pendente"
    assert dest.erro is None
    assert dest.wamid is None


@pytest.mark.asyncio
async def test_list_destinatarios_filtra_status(db_session):
    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    todos = await repo.list_destinatarios(camp.id, status=None, limit=50, offset=0)
    assert len(todos) == 3
    await repo.marcar_excluidos(camp.id, {"cidade": "Manaus"})
    visiveis = await repo.list_destinatarios(camp.id, status=None, limit=50, offset=0)
    assert all(d.status != "excluido" for d in visiveis)
