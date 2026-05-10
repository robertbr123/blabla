"""SgpOndelineProvider — POST + parsing."""
from __future__ import annotations

from typing import Any

import pytest
import respx
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider

pytestmark = pytest.mark.asyncio

BASE = "http://sgp.test"


def _resp_cliente() -> dict[str, Any]:
    return {
        "clientes": [
            {
                "id": "42",
                "nome": "Maria Silva",
                "cpfcnpj": "111.222.333-44",
                "celular": "5511999999999",
                "endereco": {
                    "logradouro": "Rua A",
                    "numero": "10",
                    "bairro": "Centro",
                    "cidade": "Sao Paulo",
                    "uf": "SP",
                    "cep": "01000-000",
                },
                "contratos": [
                    {
                        "id": "100",
                        "status": "ativo",
                        "servicos": [
                            {
                                "plano": {"descricao": "Premium 100MB"},
                                "endereco": {"cidade": "Sao Paulo"},
                            }
                        ],
                    }
                ],
                "titulos": [
                    {
                        "id": "T1",
                        "valor": 110.0,
                        "valorCorrigido": 115.0,
                        "dataVencimento": "2026-05-15",
                        "status": "aberto",
                        "link": "https://sgp.test/boletos/T1.pdf",
                        "codigoPix": "PIX_T1",
                        "diasAtraso": 0,
                    }
                ],
            }
        ]
    }


async def test_buscar_por_cpf_ok() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(200, json=_resp_cliente())
        p = SgpOndelineProvider(base_url=BASE, token="t", app="mikrotik", timeout=2)
        cli = await p.buscar_por_cpf("111.222.333-44")
        assert cli is not None
        assert cli.sgp_id == "42"
        assert cli.cpf_cnpj == "11122233344"
        assert cli.contratos[0].plano == "Premium 100MB"
        assert cli.contratos[0].cidade == "Sao Paulo"
        assert cli.titulos[0].link_pdf == "https://sgp.test/boletos/T1.pdf"
        assert cli.titulos[0].valor == 115.0
        await p.aclose()


async def test_buscar_nao_encontrado_retorna_none() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(200, json={"clientes": []})
        p = SgpOndelineProvider(base_url=BASE, token="t")
        assert await p.buscar_por_cpf("00000000000") is None
        await p.aclose()


async def test_buscar_http_error_retorna_none() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(500, json={"err": "x"})
        p = SgpOndelineProvider(base_url=BASE, token="t")
        assert await p.buscar_por_cpf("11122233344") is None
        await p.aclose()


async def test_buscar_network_error_retorna_none() -> None:
    import httpx as _httpx

    async with respx.mock() as router:
        router.post(f"{BASE}/api/ura/clientes/").mock(
            side_effect=_httpx.ConnectError("boom")
        )
        p = SgpOndelineProvider(base_url=BASE, token="t")
        assert await p.buscar_por_cpf("11122233344") is None
        await p.aclose()


async def test_cpf_vazio_retorna_none() -> None:
    p = SgpOndelineProvider(base_url=BASE, token="t")
    assert await p.buscar_por_cpf("") is None
    await p.aclose()
