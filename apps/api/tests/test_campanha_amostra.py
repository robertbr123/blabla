# apps/api/tests/test_campanha_amostra.py
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.models.business import Campanha, CampanhaDestinatario, Canal
from ondeline_api.repositories.campanha import CampanhaRepo


async def _camp(session, n_manaus, n_outras):
    canal = Canal(slug=f"a-{uuid4().hex[:8]}", nome="A", provider="cloud",
                  cloud_phone_id="1", cloud_waba_id="2")
    session.add(canal)
    await session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="x",
                    body_params=[], segmentacao={}, origem="importado", status="rascunho")
    session.add(camp)
    await session.flush()
    for i in range(n_manaus):
        session.add(CampanhaDestinatario(
            campanha_id=camp.id, cliente_id=None, whatsapp=f"55920{i:05d}",
            status="pendente", csv_cidade="Manaus", csv_status="Ativo"))
    for i in range(n_outras):
        session.add(CampanhaDestinatario(
            campanha_id=camp.id, cliente_id=None, whatsapp=f"55921{i:05d}",
            status="pendente", csv_cidade="Outra", csv_status="Ativo"))
    await session.flush()
    return camp


@pytest.mark.asyncio
async def test_amostra_respeita_filtro_e_limite(db_session):
    camp = await _camp(db_session, n_manaus=40, n_outras=5)
    repo = CampanhaRepo(db_session)
    amostra = await repo.amostra_selecionados(camp.id, {"cidade": "Manaus"}, limite=30)
    assert len(amostra) == 30
    assert all(d.csv_cidade == "Manaus" for d in amostra)


@pytest.mark.asyncio
async def test_amostra_sem_filtro_pega_todos_ate_limite(db_session):
    camp = await _camp(db_session, n_manaus=3, n_outras=2)
    repo = CampanhaRepo(db_session)
    amostra = await repo.amostra_selecionados(camp.id, {}, limite=30)
    assert len(amostra) == 5
