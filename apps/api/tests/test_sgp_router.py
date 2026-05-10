"""SgpRouter — tenta primario, fallback secundario."""
from __future__ import annotations

import pytest
from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum

pytestmark = pytest.mark.asyncio


def _cli(provider: SgpProviderEnum, sgp_id: str = "1") -> ClienteSgp:
    return ClienteSgp(provider=provider, sgp_id=sgp_id, nome="X", cpf_cnpj="11122233344")


async def test_primario_encontrado_nao_consulta_secundario() -> None:
    primary = FakeSgpProvider(clientes={"11122233344": _cli(SgpProviderEnum.ONDELINE)})
    secondary = FakeSgpProvider()
    router = SgpRouter(primary=primary, secondary=secondary)
    cli = await router.buscar_por_cpf("111.222.333-44")
    assert cli is not None
    assert cli.provider is SgpProviderEnum.ONDELINE


async def test_primario_nao_encontrado_consulta_secundario() -> None:
    primary = FakeSgpProvider(clientes={})
    secondary = FakeSgpProvider(
        clientes={"11122233344": _cli(SgpProviderEnum.LINKNETAM, sgp_id="9")}
    )
    router = SgpRouter(primary=primary, secondary=secondary)
    cli = await router.buscar_por_cpf("11122233344")
    assert cli is not None
    assert cli.provider is SgpProviderEnum.LINKNETAM


async def test_primario_levanta_consulta_secundario() -> None:
    primary = FakeSgpProvider(raise_on={"11122233344"})
    secondary = FakeSgpProvider(
        clientes={"11122233344": _cli(SgpProviderEnum.LINKNETAM)}
    )
    router = SgpRouter(primary=primary, secondary=secondary)
    cli = await router.buscar_por_cpf("11122233344")
    assert cli is not None
    assert cli.provider is SgpProviderEnum.LINKNETAM


async def test_ambos_falham_retorna_none() -> None:
    primary = FakeSgpProvider(clientes={})
    secondary = FakeSgpProvider(clientes={})
    router = SgpRouter(primary=primary, secondary=secondary)
    assert await router.buscar_por_cpf("11122233344") is None
