"""Tool enviar_boleto — selecao por mes/atraso + envio via Evolution mock."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import respx
from fakeredis.aioredis import FakeRedis
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
)
from ondeline_api.db.models.business import (
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools import enviar_boleto as enviar_boleto_mod
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.enviar_boleto import enviar_boleto
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _faturas(*, atrasados: int = 0, atual_y: int, atual_m: int) -> list[Fatura]:
    """3 faturas: mes anterior (atrasada) + mes corrente + mes seguinte.

    `atrasados` (dias_atraso do SGP) NAO afeta a logica nova — a lib calcula
    atraso a partir da data de vencimento vs today (monkeypatched _today).
    Param mantido por compatibilidade com chamadas antigas.
    """
    nxt_m = (atual_m % 12) + 1
    nxt_y = atual_y + (1 if atual_m == 12 else 0)
    prev_m = 12 if atual_m == 1 else atual_m - 1
    prev_y = atual_y - 1 if atual_m == 1 else atual_y
    return [
        Fatura(
            id="T_ATRASADA",
            valor=110,
            vencimento=f"{prev_y:04d}-{prev_m:02d}-15",
            status="aberto",
            link_pdf="https://sgp/T_ATRASADA.pdf",
            codigo_pix="PIX_ATRASADA",
            dias_atraso=atrasados,
        ),
        Fatura(
            id="T_ATUAL",
            valor=110,
            vencimento=f"{atual_y:04d}-{atual_m:02d}-25",
            status="aberto",
            link_pdf="https://sgp/T_ATUAL.pdf",
            codigo_pix="PIX_ATUAL",
        ),
        Fatura(
            id="T_PROX",
            valor=110,
            vencimento=f"{nxt_y:04d}-{nxt_m:02d}-15",
            status="aberto",
            link_pdf="https://sgp/T_PROX.pdf",
            codigo_pix="PIX_PROX",
        ),
    ]


def _cli_with_titles(titulos: list[Fatura]) -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="X",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=titulos,
    )


async def _setup(db_session: AsyncSession, titulos: list[Fatura]) -> tuple[Cliente, Conversa, SgpCacheService]:
    cli_sgp = _cli_with_titles(titulos)
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"11122233344": cli_sgp}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("X"),
        whatsapp="5511@s",
    )
    conv = Conversa(
        id=uuid4(),
        whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add_all([cliente, conv])
    await db_session.flush()
    return cliente, conv, cache


async def test_default_envia_apenas_1_fatura_atrasada_quando_houver(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    titulos = _faturas(atrasados=10, atual_y=2026, atual_m=5)
    cliente, conv, cache = await _setup(db_session, titulos)

    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=False) as router:
        m = router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        t = router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "X"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await enviar_boleto(ctx)
        await adapter.aclose()

    assert out["ok"] is True
    assert out["enviados"] == 1
    assert out["vencimentos"] == [titulos[0].vencimento]  # T_ATRASADA
    assert m.call_count == 1  # so 1 PDF
    assert t.call_count == 1  # so 1 PIX


async def test_default_envia_fatura_do_mes_corrente_quando_sem_atraso(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sem atrasada (todas futuras): pega a do mes corrente."""
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    # so faturas futuras — nenhuma atrasada
    titulos = [
        Fatura(id="T_ATUAL", valor=110, vencimento="2026-05-25", status="aberto",
               link_pdf="https://sgp/T1.pdf", codigo_pix="PIX1"),
        Fatura(id="T_PROX", valor=110, vencimento="2026-06-15", status="aberto",
               link_pdf="https://sgp/T2.pdf", codigo_pix="PIX2"),
    ]
    cliente, conv, cache = await _setup(db_session, titulos)
    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=False) as router:
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "X"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await enviar_boleto(ctx)
        await adapter.aclose()
    assert out["enviados"] == 1
    assert out["vencimentos"] == ["2026-05-25"]


async def test_default_ignora_dias_atraso_inconsistente_do_sgp(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regressao: SGP retornou dias_atraso=228 pra fatura de 2026-12-30 (futura).
    Tool nao pode confiar nesse campo — deve usar a data de vencimento.
    Hoje=2026-05-16, faturas: 04, 05 (futura), 12 (futura). Atrasada = so 04.
    """
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    titulos = [
        Fatura(id="T_04", valor=110, vencimento="2026-04-30", status="aberto",
               link_pdf="https://sgp/T04.pdf", codigo_pix="PIX04",
               dias_atraso=16),  # SGP diz 16, mas e atrasada de verdade
        Fatura(id="T_05", valor=110, vencimento="2026-05-30", status="aberto",
               link_pdf="https://sgp/T05.pdf", codigo_pix="PIX05",
               dias_atraso=45),  # SGP diz 45, mas e futura
        Fatura(id="T_12", valor=110, vencimento="2026-12-30", status="aberto",
               link_pdf="https://sgp/T12.pdf", codigo_pix="PIX12",
               dias_atraso=228),  # SGP diz 228, mas e futura
    ]
    cliente, conv, cache = await _setup(db_session, titulos)
    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=False) as router:
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "X"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await enviar_boleto(ctx)
        await adapter.aclose()
    # Deve pegar T_04 (a unica realmente atrasada por data), NAO T_12
    assert out["vencimentos"] == ["2026-04-30"]


async def test_mes_proximo_seleciona_mes_seguinte(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    titulos = _faturas(atrasados=10, atual_y=2026, atual_m=5)
    cliente, conv, cache = await _setup(db_session, titulos)
    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=False) as router:
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "X"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await enviar_boleto(ctx, mes="proximo")
        await adapter.aclose()
    assert out["vencimentos"] == ["2026-06-15"]


async def test_mes_nome_pt_outubro(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    titulos = [
        Fatura(id="T_OUT", valor=99, vencimento="2026-10-10", status="aberto",
               link_pdf="https://sgp/T_OUT.pdf", codigo_pix="PIX_OUT"),
        Fatura(id="T_NOV", valor=99, vencimento="2026-11-10", status="aberto",
               link_pdf="https://sgp/T_NOV.pdf", codigo_pix="PIX_NOV"),
    ]
    cliente, conv, cache = await _setup(db_session, titulos)
    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=False) as router:
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "X"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await enviar_boleto(ctx, mes="outubro")
        await adapter.aclose()
    assert out["vencimentos"] == ["2026-10-10"]


async def test_mes_iso_yyyy_mm(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    titulos = _faturas(atrasados=10, atual_y=2026, atual_m=5)
    cliente, conv, cache = await _setup(db_session, titulos)
    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=False) as router:
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "X"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await enviar_boleto(ctx, mes="2026-04")
        await adapter.aclose()
    assert out["vencimentos"] == ["2026-04-15"]


async def test_mes_inexistente_retorna_catalogo(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    titulos = [
        Fatura(id="T1", valor=99, vencimento="2026-05-15", status="aberto",
               link_pdf="https://sgp/T1.pdf", codigo_pix="PIX1"),
    ]
    cliente, conv, cache = await _setup(db_session, titulos)
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=cliente,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await enviar_boleto(ctx, mes="janeiro")
    assert out["enviados"] == 0
    assert "meses_disponiveis" in out
    assert out["meses_disponiveis"] == ["2026-05"]


async def test_max_boletos_5_envia_todos(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quando cliente pede 'todos os boletos', LLM passa max_boletos=5."""
    monkeypatch.setattr(
        enviar_boleto_mod, "_today",
        lambda: datetime(2026, 5, 16, tzinfo=UTC).date(),
    )
    titulos = _faturas(atrasados=5, atual_y=2026, atual_m=5)
    cliente, conv, cache = await _setup(db_session, titulos)
    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=False) as router:
        m = router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "X"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await enviar_boleto(ctx, max_boletos=5)
        await adapter.aclose()
    assert out["enviados"] == 3
    assert m.call_count == 3


async def test_sem_faturas_retorna_ok_zero(db_session: AsyncSession) -> None:
    titulos: list[Fatura] = []
    cliente, conv, cache = await _setup(db_session, titulos)
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=cliente,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await enviar_boleto(ctx)
    assert out == {"ok": True, "enviados": 0, "mensagem": "Sem faturas em aberto."}


async def test_sem_cliente_falha_grace(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=None,
        evolution=None, sgp_router=None, sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await enviar_boleto(ctx)
    assert out["ok"] is False
