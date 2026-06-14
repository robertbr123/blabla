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
                    },
                    "Hosts": {
                        "Host": {
                            "1": {
                                "HostName": {"_value": "Celular-Joao"},
                                "IPAddress": {"_value": "192.168.1.20"},
                                "MACAddress": {"_value": "AA:BB:CC:DD:EE:01"},
                                "Active": {"_value": True},
                                "InterfaceType": {"_value": "802.11"},
                            },
                            "2": {
                                "HostName": {"_value": "TV"},
                                "IPAddress": {"_value": "192.168.1.21"},
                                "MACAddress": {"_value": "AA:BB:CC:DD:EE:02"},
                                "Active": {"_value": False},
                            },
                            "3": {  # linha-fantasma sem MAC -> deve ser ignorada
                                "HostName": {"_value": "ghost"},
                                "IPAddress": {"_value": "0.0.0.0"},
                            },
                        }
                    },
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


async def test_parse_aparelhos_lista_hosts_com_mac() -> None:
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[_device_raw()])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None
        macs = {a.mac for a in dev.aparelhos}
        assert macs == {"AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"}  # ghost sem MAC fora
        joao = next(a for a in dev.aparelhos if a.mac == "AA:BB:CC:DD:EE:01")
        assert joao.nome == "Celular-Joao"
        assert joao.ip == "192.168.1.20"
        assert joao.ativo is True
        assert joao.interface == "802.11"
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


def _wan_raw(prefixo_gpon: str = "X_GponInterafceConfig") -> dict[str, Any]:
    """Subarvore WANDevice com GPON (prefixo varia por modelo) + PPPoE diag."""
    return {
        "WANDevice": {
            "1": {
                prefixo_gpon: {
                    "RXPower": {"_value": -26.5},
                    "TXPower": {"_value": 2.1},
                    "Status": {"_value": "Up"},
                },
                "WANConnectionDevice": {
                    "1": {
                        "WANPPPConnection": {
                            "1": {
                                "ConnectionStatus": {"_value": "Connected"},
                                "ExternalIPAddress": {"_value": "100.64.0.5"},
                                "Uptime": {"_value": 3600},
                                "LastConnectionError": {"_value": "ERROR_NONE"},
                            }
                        }
                    }
                },
            }
        }
    }


async def test_parse_sinal_le_gpon_e_pppoe() -> None:
    raw = _device_raw()
    raw["InternetGatewayDevice"].update(_wan_raw())
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[raw])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None and dev.sinal is not None
        assert dev.sinal.rx_power == -26.5
        assert dev.sinal.tx_power == 2.1
        assert dev.sinal.status_gpon == "Up"
        assert dev.sinal.conexao_pppoe == "Connected"
        assert dev.sinal.ip_externo == "100.64.0.5"
        assert dev.sinal.uptime_s == 3600
        assert dev.sinal.ultimo_erro == "ERROR_NONE"
        await c.aclose()


async def test_parse_sinal_prefixo_gpon_alternativo() -> None:
    raw = _device_raw()
    raw["InternetGatewayDevice"].update(_wan_raw(prefixo_gpon="X_GponInterfaceConfig"))
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[raw])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None and dev.sinal is not None
        assert dev.sinal.rx_power == -26.5
        await c.aclose()


async def test_parse_sinal_prefixo_gpon_fiberhome() -> None:
    # HG6145D (FiberHome, maioria do parque) usa o container
    # "X_FH_GponInterfaceConfig" com os MESMOS leaves RXPower/TXPower/Status.
    # Confirmado ao vivo 2026-06-11 (RX -13.6 dBm). Trava o suporte ao parque
    # FiberHome contra um refactor futuro do GPON_CFG_PATHS.
    raw = _device_raw()
    raw["InternetGatewayDevice"].update(
        _wan_raw(prefixo_gpon="X_FH_GponInterfaceConfig")
    )
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[raw])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None and dev.sinal is not None
        assert dev.sinal.rx_power == -26.5
        assert dev.sinal.tx_power == 2.1
        assert dev.sinal.status_gpon == "Up"
        await c.aclose()


async def test_parse_sinal_ausente_retorna_none() -> None:
    # _device_raw() sem subarvore WAN -> nenhum campo de sinal -> sinal None
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[_device_raw()])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None
        assert dev.sinal is None
        await c.aclose()


async def test_refresh_wan_posta_refresh_object() -> None:
    async with respx.mock(base_url=BASE) as mock:
        route = mock.post("/devices/d1/tasks").respond(200, json={"_id": "t1"})
        c = GenieAcsClient(base_url=BASE)
        await c.refresh_wan("d1")
        body = route.calls.last.request.content.decode()
        assert "refreshObject" in body
        assert "InternetGatewayDevice.WANDevice" in body
        await c.aclose()


async def test_refresh_wan_engole_erro_tecnico() -> None:
    # best-effort: falha do NBI nao pode propagar (a leitura nao depende disso).
    async with respx.mock(base_url=BASE) as mock:
        mock.post("/devices/d1/tasks").respond(500, text="erro")
        c = GenieAcsClient(base_url=BASE)
        await c.refresh_wan("d1")  # nao levanta
        await c.aclose()
