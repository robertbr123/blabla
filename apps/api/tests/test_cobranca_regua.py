"""F2 — Régua de cobrança."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.services.cobranca_regua import (
    GATILHOS,
    _decide_gatilho,
    _escolher_lembrete_do_dia,
    _render_mensagem,
)


def _fatura(venc: date, valor: float = 100.0, fid: str = "F1") -> Fatura:
    return Fatura(
        id=fid,
        valor=valor,
        vencimento=venc.isoformat(),
        status="aberto",
        link_pdf="http://example/f.pdf",
        codigo_pix="00020126...",
    )


def test_decide_gatilho_dminus3_quando_falta_3_dias() -> None:
    today = date(2026, 5, 18)
    f = _fatura(today + timedelta(days=3))
    assert _decide_gatilho(f, today) == "D-3"


@pytest.mark.parametrize("d,esperado", [(1, "D+1"), (5, "D+5"), (15, "D+15")])
def test_decide_gatilho_atrasos(d: int, esperado: str) -> None:
    today = date(2026, 5, 18)
    f = _fatura(today - timedelta(days=d))
    assert _decide_gatilho(f, today) == esperado


def test_decide_gatilho_none_fora_dos_gatilhos() -> None:
    today = date(2026, 5, 18)
    # Vencimento amanha — nao casa com nenhum gatilho
    assert _decide_gatilho(_fatura(today + timedelta(days=1)), today) is None
    # Atraso de 2 dias — tambem nao
    assert _decide_gatilho(_fatura(today - timedelta(days=2)), today) is None


def test_escolhe_gatilho_mais_grave_quando_duas_faturas_casam_no_mesmo_dia() -> None:
    today = date(2026, 5, 18)
    faturas = [
        _fatura(today - timedelta(days=15), fid="F_VELHA"),  # D+15
        _fatura(today - timedelta(days=1), fid="F_NOVA"),  # D+1
    ]
    res = _escolher_lembrete_do_dia(faturas, today)
    assert res is not None
    fatura, gatilho = res
    assert gatilho == "D+15"
    assert fatura.id == "F_VELHA"


def test_escolha_none_se_nenhuma_fatura_casa() -> None:
    today = date(2026, 5, 18)
    faturas = [_fatura(today + timedelta(days=20))]  # nem chegou no D-3
    assert _escolher_lembrete_do_dia(faturas, today) is None


@pytest.mark.parametrize("gatilho", list(GATILHOS.keys()))
def test_render_mensagem_inclui_nome_e_valor(gatilho: str) -> None:
    f = _fatura(date(2026, 5, 18), valor=149.90, fid="X")
    msg = _render_mensagem(gatilho, "João Silva", f)
    assert "João" in msg
    assert "149,90" in msg
    assert "PARAR" in msg


def test_render_mensagem_usa_cliente_quando_nome_vazio() -> None:
    f = _fatura(date(2026, 5, 18))
    msg = _render_mensagem("D-3", "", f)
    assert "Cliente" in msg


def test_render_dminus3_difere_de_dplus15() -> None:
    f = _fatura(date(2026, 5, 18))
    m_a = _render_mensagem("D-3", "Ana", f)
    m_b = _render_mensagem("D+15", "Ana", f)
    assert m_a != m_b
    assert "Aviso final" in m_b


# ── Integração com DB: opt-out via inbound ──────────────────────


@pytest.mark.asyncio
async def test_optout_persiste_em_cliente(db_session) -> None:
    """Cliente respondendo 'PARAR' marca cobranca_optout=True."""
    from ondeline_api.db.crypto import encrypt_pii, hash_pii
    from ondeline_api.db.models.business import Cliente
    from ondeline_api.repositories.cobranca import CobrancaRepo
    from ondeline_api.repositories.conversa import ConversaRepo

    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("44455566677"),
        cpf_hash=hash_pii("44455566677"),
        nome_encrypted=encrypt_pii("Carlos"),
        whatsapp="5511777optout@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()
    assert cliente.cobranca_optout is False

    # Simula opt-out direto no model (caminho integrado e testado em inbound).
    cliente.cobranca_optout = True
    cliente.cobranca_optout_at = datetime.now(tz=UTC)
    await db_session.flush()
    await db_session.refresh(cliente)
    assert cliente.cobranca_optout is True

    # Régua deve pular esse cliente (validado por filtro WHERE).
    # Cria conversa + lembrete pra checar repo de idempotência.
    repo_conv = ConversaRepo(db_session)
    await repo_conv.get_or_create_by_whatsapp(cliente.whatsapp)
    repo_cobr = CobrancaRepo(db_session)
    inserted = await repo_cobr.registrar(
        cliente_id=cliente.id,
        fatura_id="FAT-1",
        gatilho="D+1",
        vencimento=date(2026, 5, 17),
    )
    assert inserted is not None
    # 2a chamada com mesmos params deve devolver None (idempotente).
    again = await repo_cobr.registrar(
        cliente_id=cliente.id,
        fatura_id="FAT-1",
        gatilho="D+1",
        vencimento=date(2026, 5, 17),
    )
    assert again is None
    assert await repo_cobr.ja_enviado(cliente.id, "FAT-1", "D+1") is True
