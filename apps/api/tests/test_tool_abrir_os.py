"""abrir_ordem_servico: grava snapshot de sinal + linha na notificacao."""
from __future__ import annotations

from typing import Any

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente, Conversa, OrdemServico
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

CPF = "04099889289"


class _FakeWpp:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, to: str, text: str) -> None:
        self.sent.append((to, text))


async def test_abrir_os_grava_sinal(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ondeline_api.tools.abrir_ordem_servico as mod

    async def fake_cap(ctx: Any) -> dict[str, Any]:
        return {"rx_power": -29.0, "tx_power": 2.0, "status_gpon": "Up", "qualidade": "critico"}
    monkeypatch.setattr(mod, "_capturar_sinal", fake_cap)

    async def fake_end(ctx: Any) -> tuple[str, str, str]:
        return ("Rua X, 1 — Centro — Manaus/AM", "Rua X", "Manaus")
    monkeypatch.setattr(mod, "_resolve_endereco_do_cadastro", fake_end)

    cli = Cliente(cpf_cnpj_encrypted=encrypt_pii(CPF), cpf_hash=hash_pii(CPF),
                  nome_encrypted=encrypt_pii("Fulano"), whatsapp="5599@c.us")
    db_session.add(cli)
    await db_session.flush()
    conv = Conversa(whatsapp="5599@c.us", cliente_id=cli.id)
    db_session.add(conv)
    await db_session.flush()

    wpp = _FakeWpp()

    class _Ctx:
        session = db_session
        conversa = conv
        cliente = cli
        evolution = wpp
        sgp_router = None
        sgp_cache = None
        redis = None

    out = await mod.abrir_ordem_servico(_Ctx(), problema="internet lenta")
    assert out["ok"] is True
    os_ = (await db_session.execute(select(OrdemServico))).scalars().first()
    assert os_ is not None
    assert os_.sinal is not None
    assert os_.sinal["qualidade"] == "critico"
