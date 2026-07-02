"""LeadRepo.upsert_by_whatsapp — captura idempotente de lead por whatsapp."""
from __future__ import annotations

import uuid as _uuid

import pytest
from ondeline_api.db.models.business import Lead, LeadStatus
from ondeline_api.repositories.lead import LeadRepo

pytestmark = pytest.mark.asyncio


def _jid() -> str:
    return f"55119{str(_uuid.uuid4().int)[:8]}@s.whatsapp.net"


async def test_upsert_cria_quando_nao_existe(db_session) -> None:
    repo = LeadRepo(db_session)
    jid = _jid()
    lead, created = await repo.upsert_by_whatsapp(
        whatsapp=jid, nome="Contato teste", interesse="quer fibra"
    )
    assert created is True
    assert lead.whatsapp == jid
    assert lead.status is LeadStatus.NOVO
    assert lead.interesse == "quer fibra"


async def test_upsert_reusa_lead_aberto_sem_duplicar(db_session) -> None:
    """Segundo upsert no mesmo whatsapp reusa o lead aberto (nao duplica),
    faz upgrade do nome-placeholder e preenche interesse vazio."""
    repo = LeadRepo(db_session)
    jid = _jid()
    a, c1 = await repo.upsert_by_whatsapp(whatsapp=jid, nome="Contato 5511", interesse=None)
    b, c2 = await repo.upsert_by_whatsapp(whatsapp=jid, nome="Maria Silva", interesse="plano 500")
    assert c1 is True
    assert c2 is False
    assert a.id == b.id
    assert b.nome == "Maria Silva"      # placeholder "Contato ..." vira nome real
    assert b.interesse == "plano 500"   # preenche lacuna


async def test_upsert_nao_sobrescreve_nome_real(db_session) -> None:
    repo = LeadRepo(db_session)
    jid = _jid()
    await repo.upsert_by_whatsapp(whatsapp=jid, nome="Joana Real", interesse=None)
    b, _ = await repo.upsert_by_whatsapp(whatsapp=jid, nome="Contato 5511", interesse=None)
    assert b.nome == "Joana Real"       # nome real nao e rebaixado pra placeholder


async def test_upsert_cria_novo_se_anterior_fechado(db_session) -> None:
    repo = LeadRepo(db_session)
    jid = _jid()
    a, _ = await repo.upsert_by_whatsapp(whatsapp=jid, nome="Contato X", interesse=None)
    a.status = LeadStatus.PERDIDO
    await db_session.flush()
    b, created = await repo.upsert_by_whatsapp(whatsapp=jid, nome="Contato X2", interesse=None)
    assert created is True
    assert b.id != a.id


async def test_upsert_preserva_indicacao_id(db_session) -> None:
    repo = LeadRepo(db_session)
    jid = _jid()
    ind = _uuid.uuid4()
    # cria via indicacao
    a, _ = await repo.upsert_by_whatsapp(
        whatsapp=jid, nome="Indicado", interesse="Indicado por ABC", indicacao_id=ind
    )
    assert a.indicacao_id == ind
    # upsert posterior (sem indicacao) nao apaga
    b, _ = await repo.upsert_by_whatsapp(whatsapp=jid, nome="Maria", interesse=None)
    assert b.id == a.id
    assert b.indicacao_id == ind
    _ = Lead  # import usado
