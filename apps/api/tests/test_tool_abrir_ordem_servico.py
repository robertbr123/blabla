"""Tool abrir_ordem_servico — cria OS + notifica tecnico."""
from __future__ import annotations

from uuid import uuid4

import pytest
import respx
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Tecnico,
    TecnicoArea,
)
from ondeline_api.tools.abrir_ordem_servico import abrir_ordem_servico
from ondeline_api.tools.context import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_cria_os_com_codigo_e_notifica_tecnico(db_session: AsyncSession) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Joao"),
        whatsapp="5511@s",
        cidade="Sao Paulo",
    )
    tec = Tecnico(nome="Pedro", ativo=True, whatsapp="5511777@s")
    db_session.add_all([cliente, tec])
    await db_session.flush()
    db_session.add(TecnicoArea(tecnico_id=tec.id, cidade="Sao Paulo", rua="Rua A", prioridade=1))
    conv = Conversa(
        id=uuid4(),
        whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    BASE = "http://evo.test"
    INST = "hermes-wa"
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OK"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session,
            conversa=conv,
            cliente=cliente,
            evolution=adapter,
            sgp_router=None,  # type: ignore[arg-type]
            sgp_cache=None,  # type: ignore[arg-type]
        )
        out = await abrir_ordem_servico(
            ctx,
            problema="sem internet desde ontem",
            endereco="Rua A, 100, Centro, Sao Paulo, SP",
        )
        await adapter.aclose()

    assert out["ok"] is True
    assert out["codigo"].startswith("OS-")
    assert out["tecnico_nome"] == "Pedro"


async def test_sem_tecnico_disponivel_cria_os_sem_routing(db_session: AsyncSession) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("99988877766"),
        cpf_hash=hash_pii("99988877766"),
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5519@s",
    )
    db_session.add(cliente)
    conv = Conversa(
        id=uuid4(), whatsapp="5519@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=cliente,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await abrir_ordem_servico(ctx, problema="x", endereco="Rua Inexistente, Cidade Inexistente")
    assert out["ok"] is True
    assert out["tecnico_nome"] is None
