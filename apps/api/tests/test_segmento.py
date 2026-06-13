# apps/api/tests/test_segmento.py
from __future__ import annotations

import pytest

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.services.segmento import (
    amostra_segmento,
    contar_segmento,
)


async def _mk(session, *, nome, whatsapp, cidade=None, status=None, plano=None,
              deleted=False, optout=False):
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("000"),
        cpf_hash=hash_pii(whatsapp),  # hash único por teste
        nome_encrypted=encrypt_pii(nome),
        whatsapp=whatsapp,
        cidade=cidade,
        status=status,
        plano=plano,
        marketing_optout=optout,
    )
    if deleted:
        from datetime import UTC, datetime
        c.deleted_at = datetime.now(tz=UTC)
    session.add(c)
    await session.flush()
    return c


@pytest.mark.asyncio
async def test_resolver_filtra_cidade_status_plano(db_session):
    await _mk(db_session, nome="A", whatsapp="5592111", cidade="Manaus", status="Ativo", plano="100MB")
    await _mk(db_session, nome="B", whatsapp="5592222", cidade="Itacoatiara", status="Ativo", plano="100MB")
    await _mk(db_session, nome="C", whatsapp="5592333", cidade="Manaus", status="Cancelado", plano="100MB")

    total = await contar_segmento(db_session, {"cidade": "Manaus", "status": "Ativo"})
    assert total == 1


@pytest.mark.asyncio
async def test_resolver_exclui_deleted_optout_e_sem_whatsapp(db_session):
    await _mk(db_session, nome="ok", whatsapp="5592444", cidade="Manaus")
    await _mk(db_session, nome="del", whatsapp="5592555", cidade="Manaus", deleted=True)
    await _mk(db_session, nome="opt", whatsapp="5592666", cidade="Manaus", optout=True)
    await _mk(db_session, nome="vazio", whatsapp="", cidade="Manaus")

    total = await contar_segmento(db_session, {"cidade": "Manaus"})
    assert total == 1


@pytest.mark.asyncio
async def test_base_inteira_sem_filtro(db_session):
    await _mk(db_session, nome="A", whatsapp="5592777")
    await _mk(db_session, nome="B", whatsapp="5592888")
    total = await contar_segmento(db_session, {})
    assert total == 2


@pytest.mark.asyncio
async def test_amostra_decripta_nome(db_session):
    await _mk(db_session, nome="João Silva", whatsapp="5592999", cidade="Manaus")
    amostra = await amostra_segmento(db_session, {"cidade": "Manaus"}, limite=5)
    assert amostra[0]["nome"] == "João Silva"
    assert amostra[0]["whatsapp"] == "5592999"
