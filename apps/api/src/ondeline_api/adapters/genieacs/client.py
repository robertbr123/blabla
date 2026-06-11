"""GenieAcsClient - fala com o NBI do GenieACS (REST).

Server-to-server pela rede docker (genieacs-nbi:7557). Otimista: enfileira
tasks sem connection_request (aplicam no inform da ONU). Erro tecnico ->
GenieAcsUnavailableError (o endpoint traduz em 503).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
import structlog

from ondeline_api.adapters.genieacs.base import (
    Aparelho,
    GenieAcsDevice,
    GenieAcsUnavailableError,
    RedeWlan,
    SinalFibra,
)

log = structlog.get_logger(__name__)

# Online se informou nos ultimos 10 min (2x o inform de 5 min do MVP).
INFORM_ONLINE_SECONDS = 600

# Paths candidatos do PPPoE Username (o indice da instancia varia por modelo).
PPPOE_USERNAME_PATHS = [
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.2.WANPPPConnection.1.Username",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.3.WANPPPConnection.1.Username",
]

# GPON e vendor-specific: o nome do container varia por modelo (AX1800 tem o
# typo de fabrica "X_GponInterafceConfig"). Tenta os candidatos, usa o 1o.
GPON_CFG_PATHS = [
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig",
    "InternetGatewayDevice.WANDevice.1.X_GponInterfaceConfig",
    "InternetGatewayDevice.WANDevice.1.X_FH_GponInterfaceConfig",
]
# O indice do WANConnectionDevice varia por modelo (igual ao PPPoE Username).
PPPOE_CONN_PATHS = [
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.2.WANPPPConnection.1",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.3.WANPPPConnection.1",
]

_WLAN_PATH = ("InternetGatewayDevice", "LANDevice", "1", "WLANConfiguration")
_HOSTS_PATH = ("InternetGatewayDevice", "LANDevice", "1", "Hosts", "Host")


def _leaf(node: Any, key: str) -> Any:
    v = node.get(key) if isinstance(node, dict) else None
    return v.get("_value") if isinstance(v, dict) else None


def _parse_last_inform(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Defensivo: se vier naive (sem timezone), assume UTC pra a subtracao
    # com datetime.now(UTC) nao levantar TypeError aware-vs-naive.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _dig(raw: dict[str, Any], dotted: str) -> Any:
    node: Any = raw
    for k in dotted.split("."):
        node = node.get(k) if isinstance(node, dict) else None
        if node is None:
            return None
    return node


def _as_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _parse_sinal(raw: dict[str, Any]) -> SinalFibra | None:
    rx = tx = None
    status: str | None = None
    for p in GPON_CFG_PATHS:
        node = _dig(raw, p)
        if not isinstance(node, dict):
            continue
        rx = _as_float(_leaf(node, "RXPower"))
        tx = _as_float(_leaf(node, "TXPower"))
        st = _leaf(node, "Status")
        if rx is not None or tx is not None or st is not None:
            status = str(st) if st is not None else None
            break

    conexao = ip_ext = ultimo = None
    uptime: int | None = None
    for p in PPPOE_CONN_PATHS:
        node = _dig(raw, p)
        if not isinstance(node, dict):
            continue
        cs = _leaf(node, "ConnectionStatus")
        if cs is not None:
            conexao = str(cs)
            ipv = _leaf(node, "ExternalIPAddress")
            ip_ext = str(ipv) if ipv is not None else None
            uptime = _as_int(_leaf(node, "Uptime"))
            err = _leaf(node, "LastConnectionError")
            ultimo = str(err) if err is not None else None
            break

    if all(v is None for v in (rx, tx, status, conexao, ip_ext, uptime, ultimo)):
        return None
    return SinalFibra(
        rx_power=rx,
        tx_power=tx,
        status_gpon=status,
        conexao_pppoe=conexao,
        ip_externo=ip_ext,
        uptime_s=uptime,
        ultimo_erro=ultimo,
    )


def _parse_aparelhos(raw: dict[str, Any]) -> list[Aparelho]:
    node: Any = raw
    for k in _HOSTS_PATH:
        node = node.get(k) if isinstance(node, dict) else None
        if node is None:
            return []
    out: list[Aparelho] = []
    for inst, h in node.items():
        if not inst.isdigit() or not isinstance(h, dict):
            continue
        mac = _leaf(h, "MACAddress")
        if not mac:
            continue  # linha-fantasma sem MAC: nao e um aparelho util
        out.append(
            Aparelho(
                nome=str(_leaf(h, "HostName") or ""),
                ip=str(_leaf(h, "IPAddress") or ""),
                mac=str(mac),
                ativo=bool(_leaf(h, "Active")),
                interface=str(
                    _leaf(h, "InterfaceType") or _leaf(h, "Layer1Interface") or ""
                ),
            )
        )
    return out


def _parse_redes(raw: dict[str, Any]) -> list[RedeWlan]:
    node: Any = raw
    for k in _WLAN_PATH:
        node = node.get(k) if isinstance(node, dict) else None
        if node is None:
            return []
    redes: list[RedeWlan] = []
    for inst, cfg in node.items():
        if not inst.isdigit() or not isinstance(cfg, dict):
            continue
        ssid = _leaf(cfg, "SSID")
        enabled = _leaf(cfg, "Enable")
        if ssid is None:
            continue
        redes.append(
            RedeWlan(instancia=int(inst), ssid=str(ssid), enabled=bool(enabled))
        )
    return redes


def _parse_device(raw: dict[str, Any]) -> GenieAcsDevice:
    dev_id = str(raw.get("_id", ""))
    did = raw.get("_deviceId") or {}
    last = _parse_last_inform(raw.get("_lastInform"))
    online = bool(
        last and (datetime.now(UTC) - last).total_seconds() <= INFORM_ONLINE_SECONDS
    )
    return GenieAcsDevice(
        device_id=dev_id,
        fabricante=str(did.get("_Manufacturer", "") or ""),
        modelo=str(did.get("_ProductClass", "") or ""),
        serial=str(did.get("_SerialNumber", "") or ""),
        last_inform=last,
        online=online,
        redes=_parse_redes(raw),
        aparelhos=_parse_aparelhos(raw),
        sinal=_parse_sinal(raw),
    )


class GenieAcsClient:
    def __init__(self, *, base_url: str, timeout: float = 15.0) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _query_devices(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        q = quote(json.dumps(query))
        try:
            r = await self._client.get(f"{self._base}/devices/?query={q}")
        except httpx.HTTPError as e:
            log.warning("genieacs.network_error", error=str(e))
            raise GenieAcsUnavailableError(f"network error: {e}") from e
        if r.status_code != 200:
            log.warning("genieacs.http_error", status=r.status_code)
            raise GenieAcsUnavailableError(f"http {r.status_code}")
        try:
            data = r.json()
        except Exception as e:
            raise GenieAcsUnavailableError("invalid json body") from e
        return data if isinstance(data, list) else []

    async def get_device(self, device_id: str) -> GenieAcsDevice | None:
        rows = await self._query_devices({"_id": device_id})
        return _parse_device(rows[0]) if rows else None

    async def find_device_by_serial(self, serial: str) -> GenieAcsDevice | None:
        rows = await self._query_devices(
            {"InternetGatewayDevice.DeviceInfo.SerialNumber._value": serial}
        )
        return _parse_device(rows[0]) if rows else None

    async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None:
        # O indice da WANPPPConnection varia por modelo: tenta os candidatos.
        for path in PPPOE_USERNAME_PATHS:
            rows = await self._query_devices({f"{path}._value": login})
            if rows:
                return _parse_device(rows[0])
        return None

    async def _post_task(self, device_id: str, task: dict[str, Any]) -> None:
        try:
            r = await self._client.post(
                f"{self._base}/devices/{quote(device_id, safe='')}/tasks",
                json=task,
            )
        except httpx.HTTPError as e:
            log.warning("genieacs.network_error", error=str(e))
            raise GenieAcsUnavailableError(f"network error: {e}") from e
        if r.status_code >= 300:
            log.warning("genieacs.http_error", status=r.status_code)
            raise GenieAcsUnavailableError(f"http {r.status_code}")

    async def set_parameter_values(
        self, device_id: str, params: list[tuple[str, str, str]]
    ) -> None:
        if not params:
            return  # nada a setar; evita task no-op na fila do GenieACS
        await self._post_task(
            device_id,
            {"name": "setParameterValues", "parameterValues": [list(p) for p in params]},
        )

    async def reboot(self, device_id: str) -> None:
        await self._post_task(device_id, {"name": "reboot"})
