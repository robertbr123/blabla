"""Tests for notify_sender service: render_message + send_one."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import respx
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Notificacao,
    NotificacaoStatus,
    NotificacaoTipo,
)
from ondeline_api.repositories.notificacao import NotificacaoRepo
from ondeline_api.services.notify_sender import render_message, send_one
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _notif(tipo: NotificacaoTipo, payload: dict[str, object] | None = None) -> Notificacao:
    return Notificacao(
        cliente_id=uuid4(),
        tipo=tipo,
        agendada_para=datetime.now(tz=UTC),
        payload=payload or {},
        status=NotificacaoStatus.PENDENTE,
    )


def test_render_vencimento_with_titulos() -> None:
    n = _notif(
        NotificacaoTipo.VENCIMENTO,
        {"titulos": [{"id": "T1", "valor": 110.0, "vencimento": "2026-05-15"}]},
    )
    text = render_message(n, "Joao Silva")
    assert "Joao" in text
    assert "15/05/2026" in text
    assert "110,00" in text


def test_render_atraso() -> None:
    n = _notif(NotificacaoTipo.ATRASO, {"dias_atraso": 7})
    text = render_message(n, "Maria")
    assert "Maria" in text
    assert "7 dia" in text


def test_render_pagamento() -> None:
    n = _notif(NotificacaoTipo.PAGAMENTO)
    text = render_message(n, "Pedro")
    assert "Pedro" in text
    assert "pagamento" in text.lower()


def test_render_os_concluida() -> None:
    n = _notif(
        NotificacaoTipo.OS_CONCLUIDA,
        {"codigo": "OS-20260510-001", "problema": "Troca de senha Wi-Fi"},
    )
    text = render_message(n, "Ana")
    assert "Ana" in text
    assert "OS-20260510-001" in text
    assert "Troca de senha Wi-Fi" in text
    assert "SIM" in text
    assert "NÃO" in text
    assert "nota" in text.lower()


def test_render_manutencao() -> None:
    n = _notif(
        NotificacaoTipo.MANUTENCAO,
        {
            "titulo": "Atualização de equipamento",
            "inicio_at": "2026-05-15T22:00:00+00:00",
            "fim_at": "2026-05-15T23:30:00+00:00",
        },
    )
    text = render_message(n, "Bruno")
    assert "Bruno" in text
    assert "Atualização de equipamento" in text


def test_render_no_nome_uses_default() -> None:
    n = _notif(NotificacaoTipo.PAGAMENTO)
    text = render_message(n, "")
    assert "Cliente" in text


async def test_send_one_success_marks_enviada(db_session: AsyncSession) -> None:
    cpf = uuid4().hex[:11]
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf),
        cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii("Test"),
        whatsapp=f"5511{uuid4().hex[:7]}@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()
    n = await NotificacaoRepo(db_session).schedule(
        cliente_id=cliente.id,
        tipo=NotificacaoTipo.PAGAMENTO,
        agendada_para=datetime.now(tz=UTC),
        payload={},
    )
    assert n is not None

    BASE = "http://evo.test"
    INST = "hermes-wa"
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "OK"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ok = await send_one(db_session, adapter, n, cliente)
        await adapter.aclose()
    assert ok is True
    assert n.status is NotificacaoStatus.ENVIADA
    assert n.enviada_em is not None


async def test_send_one_evolution_failure_marks_failed(db_session: AsyncSession) -> None:
    cpf = uuid4().hex[:11]
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf),
        cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii("Test"),
        whatsapp=f"5511{uuid4().hex[:7]}@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()
    n = await NotificacaoRepo(db_session).schedule(
        cliente_id=cliente.id,
        tipo=NotificacaoTipo.ATRASO,
        agendada_para=datetime.now(tz=UTC),
        payload={"dias_atraso": 1},
    )
    assert n is not None

    BASE = "http://evo.test"
    INST = "hermes-wa"
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(503, json={"err": "down"})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k", retries=0)
        ok = await send_one(db_session, adapter, n, cliente)
        await adapter.aclose()
    assert ok is False
    assert n.tentativas == 1
    assert n.status is NotificacaoStatus.PENDENTE  # not yet at 3
