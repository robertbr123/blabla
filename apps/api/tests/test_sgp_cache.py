"""SgpCache — Redis primario + DB fallback + write-through + negativo."""
from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum
from ondeline_api.services.sgp_cache import SgpCacheService

pytestmark = pytest.mark.asyncio


def _cli() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Maria",
        cpf_cnpj="11122233344",
        endereco=EnderecoSgp(cidade="SP"),
        contratos=[Contrato(id="100", plano="Premium", status="ativo", cidade="SP")],
        titulos=[Fatura(id="T1", valor=110, vencimento="2026-05-15", status="aberto")],
    )


async def test_miss_chama_router_e_grava_em_redis(db_session) -> None:
    router = SgpRouter(
        primary=FakeSgpProvider(clientes={"11122233344": _cli()}),
        secondary=FakeSgpProvider(),
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=router,
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cli = await cache.get_cliente("11122233344")
    assert cli is not None
    assert cli.sgp_id == "42"

    # 2a chamada: hit (router so foi chamado uma vez por inspecao indireta — segunda call retorna sem o fake levantar excecao mesmo se vazio)
    router2 = SgpRouter(primary=FakeSgpProvider(clientes={}), secondary=FakeSgpProvider())
    cache2 = SgpCacheService(
        redis=cache._redis,  # mesmo redis
        session=db_session,
        router=router2,
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cli2 = await cache2.get_cliente("11122233344")
    assert cli2 is not None and cli2.sgp_id == "42"  # serviu do Redis


async def test_negativo_evita_marteladas(db_session) -> None:
    router = SgpRouter(
        primary=FakeSgpProvider(clientes={}), secondary=FakeSgpProvider(clientes={})
    )
    redis = FakeRedis(decode_responses=False)
    cache = SgpCacheService(
        redis=redis,
        session=db_session,
        router=router,
        ttl_cliente=3600,
        ttl_negativo=300,
        cpf_hasher=lambda s: s,  # usar CPF direto para assertions simples
    )
    a = await cache.get_cliente("00000000000")
    b = await cache.get_cliente("00000000000")
    assert a is None and b is None
    # negativo gravado
    val = await redis.get("sgp:not_found:00000000000")
    assert val is not None


async def test_db_fallback_quando_redis_morto(db_session) -> None:
    """Se Redis raise, cai no `sgp_cache` table."""
    from ondeline_api.db.models.business import SgpCache

    # popula a tabela manualmente (cpf_hash simplificado para teste)
    db_session.add(
        SgpCache(
            cpf_hash="11122233344",
            provider=SgpProviderEnum.ONDELINE,
            payload={
                "provider": "ondeline",
                "sgp_id": "42",
                "nome": "Maria",
                "cpf_cnpj": "11122233344",
                "contratos": [],
                "titulos": [],
                "endereco": {},
                "whatsapp": "",
            },
            ttl=3600,
        )
    )
    await db_session.flush()

    class _DeadRedis:
        async def get(self, k):
            raise RuntimeError("redis down")

        async def set(self, *a, **kw):
            raise RuntimeError("redis down")

        async def delete(self, *a):
            raise RuntimeError("redis down")

    cache = SgpCacheService(
        redis=_DeadRedis(),
        session=db_session,
        router=SgpRouter(primary=FakeSgpProvider(), secondary=FakeSgpProvider()),
        ttl_cliente=3600,
        ttl_negativo=300,
        cpf_hasher=lambda s: s,  # injetavel para teste
    )
    cli = await cache.get_cliente("11122233344")
    assert cli is not None
    assert cli.nome == "Maria"


async def test_invalidate_remove_redis_e_negativo(db_session) -> None:
    redis = FakeRedis(decode_responses=False)
    router = SgpRouter(
        primary=FakeSgpProvider(clientes={"11122233344": _cli()}),
        secondary=FakeSgpProvider(),
    )
    cache = SgpCacheService(
        redis=redis,
        session=db_session,
        router=router,
        ttl_cliente=3600,
        ttl_negativo=300,
        cpf_hasher=lambda s: s,  # usar CPF direto para assertions simples
    )
    await cache.get_cliente("11122233344")  # popula
    assert await redis.get("sgp:cliente:11122233344") is not None
    await cache.invalidate("11122233344")
    assert await redis.get("sgp:cliente:11122233344") is None


def test_deserialize_round_trip_preserva_enderecos_tipados() -> None:
    """Bug #11: serializer.asdict() vira dict, mas deserializer precisa
    reconstruir EnderecoSgp dentro de Contrato e no topo do cliente.
    Sem isso, a tool abrir_ordem_servico recebe um dict e quebra com
    AttributeError em prod (FakeRedis nao pega porque nao faz JSON roundtrip).
    """
    import json

    from ondeline_api.adapters.sgp.base import EnderecoSgp
    from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum
    from ondeline_api.services.sgp_cache import (
        _deserialize_cliente,
        _serialize_cliente,
    )

    original = _cli()
    # round-trip pelo JSON, como acontece no Redis real
    payload = json.loads(json.dumps(_serialize_cliente(original)))
    restored = _deserialize_cliente(payload)

    assert restored.provider == SgpProviderEnum.ONDELINE
    assert isinstance(restored.endereco, EnderecoSgp)
    assert restored.endereco.cidade == "SP"
    assert restored.contratos[0].endereco.__class__.__name__ == "EnderecoSgp"
