"""Tool abrir_ordem_servico — usa endereco do SGP por default + override."""
from __future__ import annotations

from uuid import uuid4

import pytest
import respx
from fakeredis.aioredis import FakeRedis
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Tecnico,
    TecnicoArea,
)
from ondeline_api.db.models.business import (
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools.abrir_ordem_servico import abrir_ordem_servico
from ondeline_api.tools.context import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _cli_sgp_em(cidade: str, rua: str) -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="1",
        nome="Joao",
        cpf_cnpj="11122233344",
        contratos=[
            Contrato(
                id="100",
                plano="P",
                status="ativo",
                cidade=cidade,
                endereco=EnderecoSgp(
                    logradouro=rua, numero="100", bairro="Centro",
                    cidade=cidade, uf="SP",
                ),
            )
        ],
        endereco=EnderecoSgp(logradouro=rua, numero="100", bairro="Centro", cidade=cidade, uf="SP"),
    )


async def _make_cache(db_session: AsyncSession, cli_sgp: ClienteSgp) -> SgpCacheService:
    return SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"11122233344": cli_sgp}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )


async def test_endereco_default_vem_do_cadastro_sgp(db_session: AsyncSession) -> None:
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
        id=uuid4(), whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    cli_sgp = _cli_sgp_em("Sao Paulo", "Rua A")
    cache = await _make_cache(db_session, cli_sgp)

    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=True) as router:
        m = router.post(f"{BASE}/message/sendText/{INST}").respond(200, json={"key": {"id": "OK"}})
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await abrir_ordem_servico(ctx, problema="sem internet")
        await adapter.aclose()

    assert out["ok"] is True
    assert out["codigo"].startswith("OS-")
    assert out["tecnico_nome"] == "Pedro"
    assert out["tecnico_atribuido"] is True
    assert "Rua A" in out["endereco_usado"]
    assert "Sao Paulo" in out["endereco_usado"]
    # Mensagem ao tecnico foi enviada
    assert m.call_count == 1


async def test_endereco_override_pelo_llm(db_session: AsyncSession) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Joao"),
        whatsapp="5511@s",
        cidade="Sao Paulo",
    )
    db_session.add(cliente)
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    cli_sgp = _cli_sgp_em("Sao Paulo", "Rua Cadastrada")
    cache = await _make_cache(db_session, cli_sgp)

    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=cliente,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await abrir_ordem_servico(
        ctx, problema="x", endereco="Rua Outra, 200, Bairro Z, Campinas",
    )
    assert out["ok"] is True
    assert out["endereco_usado"] == "Rua Outra, 200, Bairro Z, Campinas"


async def test_sem_endereco_no_cadastro_e_sem_override_falha(db_session: AsyncSession) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("99988877766"),
        cpf_hash=hash_pii("99988877766"),
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5519@s",
    )
    db_session.add(cliente)
    conv = Conversa(
        id=uuid4(), whatsapp="5519@s",
        estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    # SGP cache sem este cliente
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(primary=FakeSgpProvider(), secondary=FakeSgpProvider()),
        ttl_cliente=3600, ttl_negativo=300,
    )
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=cliente,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await abrir_ordem_servico(ctx, problema="x")
    assert out["ok"] is False
    assert "endereco" in out["motivo"]


async def test_sem_tecnico_disponivel_cria_os_sem_routing(db_session: AsyncSession) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5519@s",
        cidade="Cidade Sem Tecnico",
    )
    db_session.add(cliente)
    conv = Conversa(
        id=uuid4(), whatsapp="5519@s",
        estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    cli_sgp = _cli_sgp_em("Cidade Sem Tecnico", "Rua Z")
    cache = await _make_cache(db_session, cli_sgp)
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=cliente,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await abrir_ordem_servico(ctx, problema="x")
    assert out["ok"] is True
    assert out["tecnico_nome"] is None
    assert out["tecnico_atribuido"] is False


async def test_notificacao_tecnico_falha_mas_os_persiste(db_session: AsyncSession) -> None:
    """Regressao: Evolution sendText pro tecnico falhando (HTTP 400 exists:false)
    NAO pode quebrar a tool. A OS ja esta criada e o cliente precisa de confirmacao.
    """
    from ondeline_api.db.models.business import OrdemServico
    from sqlalchemy import select

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
        id=uuid4(), whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    cli_sgp = _cli_sgp_em("Sao Paulo", "Rua A")
    cache = await _make_cache(db_session, cli_sgp)

    BASE, INST = "http://evo.test", "ONDELINE"
    with respx.mock(assert_all_called=True) as router:
        # Evolution retorna 400 exists:false — comum quando tecnico nao tem WA
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            400,
            json={"status": 400, "response": {"message": [{"exists": False}]}},
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=cliente,
            evolution=adapter, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
        )
        out = await abrir_ordem_servico(ctx, problema="sem internet")
        await adapter.aclose()

    assert out["ok"] is True
    assert out["tecnico_atribuido"] is True
    assert out["tecnico_notificado"] is False  # falhou no send
    # OS de fato existe no DB
    os_row = (
        await db_session.execute(
            select(OrdemServico).where(OrdemServico.codigo == out["codigo"])
        )
    ).scalar_one_or_none()
    assert os_row is not None


async def test_sem_cliente_falha_grace(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5519@s",
        estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=None,
        evolution=None, sgp_router=None, sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await abrir_ordem_servico(ctx, problema="x")
    assert out["ok"] is False
