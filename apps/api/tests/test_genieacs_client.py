"""GenieAcsClient contra o NBI (mockado com respx)."""
from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.adapters.genieacs.client import GenieAcsClient

pytestmark = pytest.mark.asyncio

BASE = "http://genieacs.test:7557"


def _device_raw(device_id: str = "30E1F1-AX1800-ITBSF1") -> dict[str, Any]:
    return {
        "_id": device_id,
        "_lastInform": "2026-06-10T12:00:00.000Z",
        "_deviceId": {
            "_SerialNumber": "ITBSF1",
            "_ProductClass": "AX1800",
            "_OUI": "30E1F1",
            "_Manufacturer": "INTELBRAS",
        },
        "InternetGatewayDevice": {
            "LANDevice": {
                "1": {
                    "WLANConfiguration": {
                        "1": {"SSID": {"_value": "CASA_5G"}, "Enable": {"_value": True}},
                        "6": {"SSID": {"_value": "CASA"}, "Enable": {"_value": True}},
                        "2": {"SSID": {"_value": "OFF"}, "Enable": {"_value": False}},
                    }
                }
            }
        },
    }


async def test_get_device_parseia_dto() -> None:
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[_device_raw()])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("30E1F1-AX1800-ITBSF1")
        assert dev is not None
        assert dev.modelo == "AX1800"
        assert dev.fabricante == "INTELBRAS"
        assert dev.serial == "ITBSF1"
        assert dev.last_inform is not None
        ativas = {r.instancia for r in dev.redes if r.enabled}
        assert ativas == {1, 6}
        await c.aclose()


async def test_find_by_pppoe_nao_encontrado_retorna_none() -> None:
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[])
        c = GenieAcsClient(base_url=BASE)
        assert await c.find_device_by_pppoe("ppp_inexistente") is None
        await c.aclose()


async def test_set_parameter_values_posta_task() -> None:
    async with respx.mock(base_url=BASE) as mock:
        route = mock.post("/devices/d1/tasks").respond(200, json={"_id": "t1"})
        c = GenieAcsClient(base_url=BASE)
        await c.set_parameter_values("d1", [("path.A", "senha", "xsd:string")])
        assert route.called
        sent = route.calls.last.request
        body = sent.content.decode()
        assert "setParameterValues" in body and "path.A" in body
        await c.aclose()


async def test_reboot_posta_task() -> None:
    async with respx.mock(base_url=BASE) as mock:
        route = mock.post("/devices/d1/tasks").respond(200, json={"_id": "t2"})
        c = GenieAcsClient(base_url=BASE)
        await c.reboot("d1")
        assert "reboot" in route.calls.last.request.content.decode()
        await c.aclose()


async def test_erro_de_rede_levanta_unavailable() -> None:
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").mock(side_effect=httpx.ConnectError("boom"))
        c = GenieAcsClient(base_url=BASE)
        with pytest.raises(GenieAcsUnavailableError):
            await c.get_device("d1")
        await c.aclose()


async def test_http_500_levanta_unavailable() -> None:
    async with respx.mock(base_url=BASE) as mock:
        mock.post("/devices/d1/tasks").respond(500, text="erro")
        c = GenieAcsClient(base_url=BASE)
        with pytest.raises(GenieAcsUnavailableError):
            await c.reboot("d1")
        await c.aclose()


async def test_online_por_inform_recente_e_offline_por_antigo() -> None:
    from datetime import UTC, datetime, timedelta

    recente = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
    antigo = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    async with respx.mock(base_url=BASE) as mock:
        raw = _device_raw()
        raw["_lastInform"] = recente
        mock.get("/devices/").respond(200, json=[raw])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None and dev.online is True
        await c.aclose()
    async with respx.mock(base_url=BASE) as mock:
        raw = _device_raw()
        raw["_lastInform"] = antigo
        mock.get("/devices/").respond(200, json=[raw])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None and dev.online is False
        await c.aclose()


async def test_last_inform_naive_nao_quebra() -> None:
    # _lastInform sem timezone: nao pode levantar TypeError aware-vs-naive.
    async with respx.mock(base_url=BASE) as mock:
        raw = _device_raw()
        raw["_lastInform"] = "2026-06-10T12:00:00"  # naive, sem Z/offset
        mock.get("/devices/").respond(200, json=[raw])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None
        assert dev.last_inform is not None and dev.last_inform.tzinfo is not None
        await c.aclose()
