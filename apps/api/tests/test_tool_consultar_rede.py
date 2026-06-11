"""Tool consultar_rede: aparelhos + sinal pro bot triar internet lenta."""
from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.asyncio


def _ctx(cliente: Any) -> Any:
    class _Ctx:
        def __init__(self) -> None:
            self.session = None
            self.conversa = None
            self.cliente = cliente
            self.evolution = None
            self.sgp_router = None
            self.sgp_cache = None
    return _Ctx()


async def test_consultar_rede_sem_cliente() -> None:
    from ondeline_api.tools.consultar_rede import consultar_rede
    out = await consultar_rede(_ctx(None))
    assert out["encontrada"] is False
    assert out["motivo"] == "cliente_nao_identificado"


async def test_payload_consulta_formata_aparelhos_e_sinal() -> None:
    from ondeline_api.adapters.genieacs.base import Aparelho, GenieAcsDevice, SinalFibra
    from ondeline_api.services.rede_service import DiagnosticoRede
    from ondeline_api.tools.consultar_rede import _payload_consulta

    class _FakeRede:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            dev = GenieAcsDevice(
                device_id="X", online=True,
                aparelhos=[Aparelho(nome="A", ip="1", mac="m1", ativo=True),
                           Aparelho(nome="B", ip="2", mac="m2", ativo=True)],
                sinal=SinalFibra(rx_power=-13.0),
            )
            return DiagnosticoRede(encontrada=True, device=dev)

    out = await _payload_consulta(_FakeRede(), "04099889289")
    assert out["encontrada"] is True
    assert out["aparelhos_conectados"] == 2
    assert out["sinal"]["qualidade"] == "bom"
    assert out["sinal"]["emoji"] == "🟢"
    assert out["sinal"]["rx_power"] == -13.0
