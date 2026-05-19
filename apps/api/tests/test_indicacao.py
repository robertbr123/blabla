"""F10 — Indicação 'Indicou, ganhou'."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import Cliente
from ondeline_api.repositories.indicacao import IndicacaoRepo

pytestmark = pytest.mark.asyncio


async def _cliente(db_session, suffix: str) -> Cliente:
    from ondeline_api.db.crypto import encrypt_pii, hash_pii

    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(f"99988877{suffix}"),
        cpf_hash=hash_pii(f"99988877{suffix}"),
        nome_encrypted=encrypt_pii(f"Cliente {suffix}"),
        whatsapp=f"5511ind{suffix}@s.whatsapp.net",
    )
    db_session.add(c)
    await db_session.flush()
    return c


async def test_gera_codigo_unico_alfanumerico(db_session) -> None:
    cli = await _cliente(db_session, "01")
    repo = IndicacaoRepo(db_session)
    ind = await repo.get_or_create_para_cliente(cli.id)
    assert ind.codigo is not None
    assert 5 <= len(ind.codigo) <= 8
    assert ind.codigo == ind.codigo.upper()
    # Sem caracteres confusos
    assert "0" not in ind.codigo
    assert "O" not in ind.codigo
    assert "1" not in ind.codigo
    assert "I" not in ind.codigo


async def test_get_or_create_idempotente_por_cliente(db_session) -> None:
    cli = await _cliente(db_session, "02")
    repo = IndicacaoRepo(db_session)
    a = await repo.get_or_create_para_cliente(cli.id)
    b = await repo.get_or_create_para_cliente(cli.id)
    assert a.id == b.id
    assert a.codigo == b.codigo


async def test_get_by_codigo_case_insensitive(db_session) -> None:
    cli = await _cliente(db_session, "03")
    repo = IndicacaoRepo(db_session)
    ind = await repo.get_or_create_para_cliente(cli.id)
    found = await repo.get_by_codigo(ind.codigo.lower())
    assert found is not None
    assert found.id == ind.id


async def test_registrar_uso_incrementa_contador(db_session) -> None:
    cli = await _cliente(db_session, "04")
    repo = IndicacaoRepo(db_session)
    ind = await repo.get_or_create_para_cliente(cli.id)
    assert ind.usos == 0
    await repo.registrar_uso(ind.id)
    await repo.registrar_uso(ind.id)
    await db_session.refresh(ind)
    assert ind.usos == 2

    usos = await repo.list_usos(ind.id)
    assert len(usos) == 2


async def test_ranking_indicadores(db_session) -> None:
    cli_a = await _cliente(db_session, "05")
    cli_b = await _cliente(db_session, "06")
    repo = IndicacaoRepo(db_session)
    ind_a = await repo.get_or_create_para_cliente(cli_a.id)
    ind_b = await repo.get_or_create_para_cliente(cli_b.id)
    # A teve 3 usos (2 convertidos), B teve 1 (0 convertidos)
    u1 = await repo.registrar_uso(ind_a.id)
    u2 = await repo.registrar_uso(ind_a.id)
    await repo.registrar_uso(ind_a.id)
    await repo.registrar_uso(ind_b.id)
    # Marca 2 como convertidos
    from datetime import UTC, datetime

    u1.convertido_em = datetime.now(tz=UTC)
    u2.convertido_em = datetime.now(tz=UTC)
    await db_session.flush()

    ranking = await repo.ranking_indicadores(limit=10)
    # Cliente A deve aparecer primeiro
    nomes_em_ordem = [c.id for c, _, _ in ranking]
    assert cli_a.id in nomes_em_ordem
    assert cli_b.id in nomes_em_ordem
    # Verifica que A tem mais usos
    a_row = next(r for r in ranking if r[0].id == cli_a.id)
    b_row = next(r for r in ranking if r[0].id == cli_b.id)
    assert a_row[1] == 3
    assert a_row[2] == 2
    assert b_row[1] == 1
    assert b_row[2] == 0


def test_regex_indicado_por() -> None:
    """Pattern reconhece 'Indicado por XXXXXX' e variações."""
    from ondeline_api.services.inbound import _CMD_INDICADO_RE

    for text in [
        "Indicado por ABC123",
        "indicado por XYZWQ9",
        "INDICADO POR JK4LM6",
        "Indicada por NOPQR8",
        "Indicado por ABC123 — quero contratar",
    ]:
        m = _CMD_INDICADO_RE.match(text)
        assert m is not None, f"falhou em: {text!r}"
        assert len(m.group(1)) >= 4

    # Sem código → não casa
    assert _CMD_INDICADO_RE.match("Indicado por") is None
    assert _CMD_INDICADO_RE.match("Olá") is None
