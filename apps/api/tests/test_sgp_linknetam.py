"""SgpLinkNetAMProvider herda Ondeline; valida apenas o nome do provider."""
from __future__ import annotations

import pytest
import respx
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum

pytestmark = pytest.mark.asyncio


async def test_provider_name() -> None:
    p = SgpLinkNetAMProvider(base_url="http://x", token="t")
    assert p.name is SgpProviderEnum.LINKNETAM
    await p.aclose()


async def test_busca_funciona_e_marca_provider_certo() -> None:
    BASE = "http://link.test"
    payload = {
        "clientes": [
            {"id": "9", "nome": "X", "cpfcnpj": "11122233344", "contratos": [], "titulos": []}
        ]
    }
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(200, json=payload)
        p = SgpLinkNetAMProvider(base_url=BASE, token="t")
        cli = await p.buscar_por_cpf("11122233344")
        assert cli is not None
        assert cli.provider is SgpProviderEnum.LINKNETAM
        await p.aclose()
