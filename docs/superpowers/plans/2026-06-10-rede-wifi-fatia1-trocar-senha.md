# Rede WiFi — Fatia 1: Trocar senha (app técnico) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O técnico, durante uma visita, troca a senha do WiFi do cliente pelo app — ponta a ponta (adapter GenieACS → service → endpoint → tela no app técnico).

**Architecture:** Backend novo em `apps/api` que fala com o `genieacs-nbi` (server-to-server, rede docker). Adapter HTTP (igual ao SGP) → service que resolve a ONU por PPPoE (com fallback serial) e envia Set(senha em todas as redes ativas)+Reboot → endpoints `GET/POST /api/v1/rede/{cliente_id}` com RBAC técnico/admin → tela Flutter no app técnico. Confirmação otimista (passphrase é write-only). Sem Celery.

**Tech Stack:** FastAPI, httpx, SQLAlchemy async + Alembic, Pydantic, pytest/respx; Flutter (Dio + Riverpod).

**Spec:** `docs/superpowers/specs/2026-06-10-rede-wifi-etapa3-fatia1-trocar-senha-design.md`

---

## ⚠️ Regras deste repo (sobrepõem o fluxo padrão)

1. **NÃO rodar pytest/alembic/docker/npm/flutter localmente** — não há stack local. Validação = CI no push. Onde o template TDD diz "run test", aqui significa: escrever o teste, escrever a impl, e rodar **ruff + mypy** local; o **pytest roda no CI**.
2. Lint/types (da raiz do repo):
   - `apps/api/.venv/bin/ruff check <arquivos>`
   - `cd apps/api && .venv/bin/mypy <arquivos relativos a apps/api>`
3. **Comentários e docstrings SEM acento e SEM travessão** (CI: RUF002/RUF003). Imports ordenados (I001).
4. **Commit atômico por task, SEM push.** `git add` explícito só dos arquivos da task (há arquivos não relacionados no working tree — nunca `git add -A`). Toda mensagem termina com:
   ```
   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
5. **Nada de push sem OK do Robert.** O deploy é automático no push (GHCR + Watchtower); o dashboard/app exigem passos manuais. Push só nos checkpoints marcados.

---

## Desvio consciente do spec (registrar)

- O spec fala em `/api/v1/rede/{contrato_id}`. Na prática o app técnico tem o **`cliente_id`** (UUID do `Cliente` local, da OS/cadastro), e o caminho pro PPPoE é `Cliente local → CPF → SGP → contrato → pppoe_login` (não há tabela local de contratos). Por isso os endpoints usam **`{cliente_id}`**. O `contrato_id` do SGP é guardado no registro do pedido pra rastreio.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `apps/api/src/ondeline_api/config.py` (MOD) | settings `genieacs_url/user/password` |
| `apps/api/src/ondeline_api/adapters/genieacs/__init__.py` (NEW) | pacote |
| `apps/api/src/ondeline_api/adapters/genieacs/base.py` (NEW) | `GenieAcsUnavailableError` + DTOs frozen (`GenieAcsDevice`, `RedeWlan`) |
| `apps/api/src/ondeline_api/adapters/genieacs/wifi_paths.py` (NEW) | perfis por modelo + `montar_plano` (puro) |
| `apps/api/src/ondeline_api/adapters/genieacs/client.py` (NEW) | `GenieAcsClient` (HTTP no NBI) |
| `apps/api/src/ondeline_api/db/models/rede.py` (NEW) | model `RedeWifiPedido` |
| `apps/api/src/ondeline_api/db/models/__init__.py` (MOD) | registrar `rede` |
| `apps/api/alembic/versions/0044_rede_wifi_pedido.py` (NEW) | migração |
| `apps/api/alembic/env.py` (MOD) | registrar `rede` no metadata |
| `apps/api/src/ondeline_api/services/rede_service.py` (NEW) | orquestração (resolve ONU, valida, envia, registra) |
| `apps/api/src/ondeline_api/api/schemas/rede.py` (NEW) | schemas Pydantic |
| `apps/api/src/ondeline_api/api/v1/rede.py` (NEW) | endpoints + dep `get_rede_service` |
| `apps/api/src/ondeline_api/main.py` (MOD) | `include_router` |
| `apps/api/tests/test_genieacs_wifi_paths.py` (NEW) | unit do plano |
| `apps/api/tests/test_genieacs_client.py` (NEW) | adapter (respx) |
| `apps/api/tests/test_rede_service.py` (NEW) | service (fake client) |
| `apps/api/tests/test_v1_rede.py` (NEW) | endpoint (httpx ASGI) |
| `apps/tecnico-mobile/lib/features/rede/rede_data.dart` (NEW) | providers/repo Dio |
| `apps/tecnico-mobile/lib/features/rede/rede_screen.dart` (NEW) | tela |

---

## Task 1: Config — settings do GenieACS

**Files:**
- Modify: `apps/api/src/ondeline_api/config.py` (perto do bloco SGP, ~linha 81-86)

- [ ] **Step 1: Adicionar as settings** após `sgp_ondeline_token`:

```python
    # GenieACS (TR-069) — server-to-server pela rede docker interna.
    # NBI sem auth no MVP (user/password prontos pra futuro).
    genieacs_url: str = "http://genieacs-nbi:7557"
    genieacs_user: str = ""
    genieacs_password: str = ""
```

- [ ] **Step 2: Lint**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/config.py`
Expected: All checks passed!

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/config.py
git commit -m "feat(rede): settings do GenieACS (url/user/password)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2: Adapter base — exceção + DTOs

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/genieacs/__init__.py`
- Create: `apps/api/src/ondeline_api/adapters/genieacs/base.py`

- [ ] **Step 1: Criar o pacote** — `apps/api/src/ondeline_api/adapters/genieacs/__init__.py` vazio:

```python
```

- [ ] **Step 2: Criar `base.py`** — molde `adapters/sgp/base.py` (frozen+slots, `__all__` pro mypy):

```python
"""Interface GenieACS (TR-069). DTOs e excecao tecnica.

O GenieACS expoe os dados da ONU numa arvore aninhada (cada folha vira
um objeto com `_value`/`_writable`). Aqui isolamos isso em DTOs simples
que o service e o endpoint consomem sem conhecer o shape cru do NBI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "GenieAcsDevice",
    "GenieAcsUnavailableError",
    "RedeWlan",
]


class GenieAcsUnavailableError(RuntimeError):
    """Falha tecnica ao falar com o NBI do GenieACS (rede / HTTP != 2xx).

    Distinto de "device nao encontrado" (retorno None). O endpoint traduz
    isto em 503; nunca em "ONU nao encontrada".
    """


@dataclass(frozen=True, slots=True)
class RedeWlan:
    """Uma instancia WLANConfiguration da ONU (uma rede WiFi)."""

    instancia: int
    ssid: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class GenieAcsDevice:
    device_id: str
    fabricante: str = ""
    modelo: str = ""  # ProductClass (ex: "AX1800")
    serial: str = ""
    last_inform: datetime | None = None
    online: bool = False
    redes: list[RedeWlan] = field(default_factory=list)
```

- [ ] **Step 3: Lint + types**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/adapters/genieacs/ && cd apps/api && .venv/bin/mypy src/ondeline_api/adapters/genieacs/base.py`
Expected: ruff ok + `Success: no issues found`

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/genieacs/__init__.py apps/api/src/ondeline_api/adapters/genieacs/base.py
git commit -m "feat(rede): adapter GenieACS base (DTOs + GenieAcsUnavailableError)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3: wifi_paths — perfis por modelo + montar_plano (puro, TDD)

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/genieacs/wifi_paths.py`
- Test: `apps/api/tests/test_genieacs_wifi_paths.py`

- [ ] **Step 1: Escrever o teste** `apps/api/tests/test_genieacs_wifi_paths.py`:

```python
"""Resolucao do plano de troca de senha (puro, sem rede)."""
from __future__ import annotations

from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.adapters.genieacs.wifi_paths import montar_plano, perfil_do_modelo

_BASE = "InternetGatewayDevice.LANDevice.1.WLANConfiguration"


def _device(modelo: str, redes: list[RedeWlan]) -> GenieAcsDevice:
    return GenieAcsDevice(device_id="d1", modelo=modelo, redes=redes)


def test_seta_senha_so_nas_redes_ativas() -> None:
    dev = _device(
        "AX1800",
        [
            RedeWlan(instancia=1, ssid="CASA_5G", enabled=True),
            RedeWlan(instancia=6, ssid="CASA", enabled=True),
            RedeWlan(instancia=2, ssid="DESATIVADA", enabled=False),
        ],
    )
    plano = montar_plano(dev, "NovaSenha123")
    paths = [p[0] for p in plano.params]
    assert f"{_BASE}.1.KeyPassphrase" in paths
    assert f"{_BASE}.6.KeyPassphrase" in paths
    assert f"{_BASE}.2.KeyPassphrase" not in paths  # desativada nao entra
    assert all(p[1] == "NovaSenha123" and p[2] == "xsd:string" for p in plano.params)


def test_ax1800_precisa_reboot() -> None:
    dev = _device("AX1800", [RedeWlan(instancia=1, ssid="x", enabled=True)])
    assert montar_plano(dev, "s").needs_reboot is True


def test_modelo_desconhecido_usa_default_conservador() -> None:
    # default reinicia sempre (needs_reboot=True) e usa KeyPassphrase
    perfil = perfil_do_modelo("MODELO_QUE_NAO_EXISTE")
    assert perfil.needs_reboot is True
    assert perfil.passphrase_param == "KeyPassphrase"


def test_sem_rede_ativa_plano_vazio() -> None:
    dev = _device("AX1800", [RedeWlan(instancia=1, ssid="x", enabled=False)])
    assert montar_plano(dev, "s").params == []
```

- [ ] **Step 2: Implementar** `apps/api/src/ondeline_api/adapters/genieacs/wifi_paths.py`:

```python
"""Mapa modelo -> perfil WiFi e montagem do plano de troca de senha.

Achados do spike (memoria rede_wifi_genieacs): a senha mora em
`...WLANConfiguration.{i}.KeyPassphrase`; e write-only (GET volta vazio).
O 5G so aplica apos reboot. Setamos a senha em TODAS as instancias ativas
(Enable=true) com o mesmo valor — cobre 2.4 e 5G sem classificar banda.

Mapa extensivel por modelo. Default conservador (reinicia sempre) ate o
modelo ser mapeado.
"""
from __future__ import annotations

from dataclasses import dataclass

from ondeline_api.adapters.genieacs.base import GenieAcsDevice

WLAN_BASE = "InternetGatewayDevice.LANDevice.1.WLANConfiguration"


@dataclass(frozen=True, slots=True)
class WifiPerfil:
    passphrase_param: str
    needs_reboot: bool


@dataclass(frozen=True, slots=True)
class PlanoTrocaSenha:
    params: list[tuple[str, str, str]]  # (path, valor, xsd type)
    needs_reboot: bool


# Confirmado no spike: AX1800 (Intelbras) usa KeyPassphrase e exige reboot
# pro 5G aplicar. Novos modelos: adicionar aqui (ex.: PreSharedKey.1.KeyPassphrase).
PERFIS: dict[str, WifiPerfil] = {
    "AX1800": WifiPerfil(passphrase_param="KeyPassphrase", needs_reboot=True),
}

# Modelo desconhecido: caminho mais comum (TR-098) + reboot por seguranca.
DEFAULT_PERFIL = WifiPerfil(passphrase_param="KeyPassphrase", needs_reboot=True)


def perfil_do_modelo(modelo: str) -> WifiPerfil:
    return PERFIS.get(modelo, DEFAULT_PERFIL)


def montar_plano(device: GenieAcsDevice, nova_senha: str) -> PlanoTrocaSenha:
    perfil = perfil_do_modelo(device.modelo)
    params = [
        (f"{WLAN_BASE}.{r.instancia}.{perfil.passphrase_param}", nova_senha, "xsd:string")
        for r in device.redes
        if r.enabled
    ]
    return PlanoTrocaSenha(params=params, needs_reboot=perfil.needs_reboot)
```

- [ ] **Step 3: Lint + types**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/adapters/genieacs/wifi_paths.py apps/api/tests/test_genieacs_wifi_paths.py && cd apps/api && .venv/bin/mypy src/ondeline_api/adapters/genieacs/wifi_paths.py`
Expected: ruff ok + mypy Success. (pytest roda no CI)

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/genieacs/wifi_paths.py apps/api/tests/test_genieacs_wifi_paths.py
git commit -m "feat(rede): mapa de paths WiFi por modelo + montar_plano (AX1800 + default)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4: GenieAcsClient — HTTP no NBI (TDD com respx)

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/genieacs/client.py`
- Test: `apps/api/tests/test_genieacs_client.py`

Contexto do NBI (REST do GenieACS):
- Buscar device: `GET /devices/?query=<json-url-encoded>` → array de devices crus.
- Cada device cru: `_id`, `_lastInform` (ISO), `_deviceId._SerialNumber/_ProductClass/_OUI/_Manufacturer`, e a arvore `InternetGatewayDevice...`. Cada folha = `{"_value": ..., "_writable": ...}`.
- Enfileirar task: `POST /devices/<id>/tasks` body `{"name":"setParameterValues","parameterValues":[[path,val,type]]}` ou `{"name":"reboot"}`. SEM `?connection_request` (otimista; aplica no inform).

- [ ] **Step 1: Escrever o teste** `apps/api/tests/test_genieacs_client.py`:

```python
"""GenieAcsClient contra o NBI (mockado com respx)."""
from __future__ import annotations

import httpx
import pytest
import respx
from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.adapters.genieacs.client import GenieAcsClient

pytestmark = pytest.mark.asyncio

BASE = "http://genieacs.test:7557"


def _device_raw(device_id: str = "30E1F1-AX1800-ITBSF1") -> dict:
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
        # 2 redes ativas (instancias 1 e 6), 1 desativada
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
```

- [ ] **Step 2: Implementar** `apps/api/src/ondeline_api/adapters/genieacs/client.py`:

```python
"""GenieAcsClient — fala com o NBI do GenieACS (REST).

Server-to-server pela rede docker (genieacs-nbi:7557). Otimista: enfileira
tasks sem connection_request (aplicam no inform da ONU). Erro tecnico ->
GenieAcsUnavailableError (o endpoint traduz em 503).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx
import structlog

from ondeline_api.adapters.genieacs.base import (
    GenieAcsDevice,
    GenieAcsUnavailableError,
    RedeWlan,
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

_WLAN_PATH = ("InternetGatewayDevice", "LANDevice", "1", "WLANConfiguration")


def _leaf(node: Any, key: str) -> Any:
    v = node.get(key) if isinstance(node, dict) else None
    return v.get("_value") if isinstance(v, dict) else None


def _parse_last_inform(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


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
                f"{self._base}/devices/{device_id}/tasks",
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
        await self._post_task(
            device_id,
            {"name": "setParameterValues", "parameterValues": [list(p) for p in params]},
        )

    async def reboot(self, device_id: str) -> None:
        await self._post_task(device_id, {"name": "reboot"})
```

- [ ] **Step 3: Lint + types**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/adapters/genieacs/client.py apps/api/tests/test_genieacs_client.py && cd apps/api && .venv/bin/mypy src/ondeline_api/adapters/genieacs/client.py`
Expected: ruff ok + mypy Success.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/genieacs/client.py apps/api/tests/test_genieacs_client.py
git commit -m "feat(rede): GenieAcsClient (find by pppoe/serial, set params, reboot)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5: Model + migração — `rede_wifi_pedido`

**Files:**
- Create: `apps/api/src/ondeline_api/db/models/rede.py`
- Modify: `apps/api/src/ondeline_api/db/models/__init__.py`
- Modify: `apps/api/alembic/env.py:10`
- Create: `apps/api/alembic/versions/0044_rede_wifi_pedido.py`

- [ ] **Step 1: Criar o model** `apps/api/src/ondeline_api/db/models/rede.py` (molde `cliente_app.py`):

```python
"""ORM model para auditoria de troca de senha WiFi (TR-069).

Registra o FATO da troca (quem, qual ONU, quando) — NUNCA a senha em si.
Status comeca em 'enviado'; fatias futuras (app cliente) podem evoluir
para 'confirmado'/'falhou'.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ondeline_api.db.base import Base


class RedeWifiPedido(Base):
    __tablename__ = "rede_wifi_pedido"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    contrato_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pppoe_login: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ator_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="enviado")
    reiniciou: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

- [ ] **Step 2: Registrar o model** em `apps/api/src/ondeline_api/db/models/__init__.py`:

```python
from ondeline_api.db.models import business, cliente_app, estoque, identity, promocoes, rede

__all__ = ["business", "cliente_app", "estoque", "identity", "promocoes", "rede"]
```

- [ ] **Step 3: Registrar no alembic env** — `apps/api/alembic/env.py:10`:

```python
from ondeline_api.db.models import business, identity, rede  # noqa: F401  -- register models
```

- [ ] **Step 4: Criar a migração** `apps/api/alembic/versions/0044_rede_wifi_pedido.py` (molde `0043`):

```python
"""rede_wifi_pedido: auditoria de troca de senha WiFi (TR-069).

Registra o fato da troca (cliente, ONU, ator, quando) — nunca a senha.

Revision ID: 0044_rede_wifi_pedido
Revises: 0043_whatsapp_message_status
Create Date: 2026-06-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0044_rede_wifi_pedido"
down_revision: str | None = "0043_whatsapp_message_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rede_wifi_pedido",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contrato_id", sa.String(64), nullable=True),
        sa.Column("pppoe_login", sa.String(128), nullable=True),
        sa.Column("device_id", sa.String(128), nullable=False),
        sa.Column("ator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="enviado"),
        sa.Column("reiniciou", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_rede_wifi_pedido_cliente", "rede_wifi_pedido", ["cliente_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_rede_wifi_pedido_cliente", table_name="rede_wifi_pedido")
    op.drop_table("rede_wifi_pedido")
```

- [ ] **Step 5: Lint + types**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/db/models/rede.py apps/api/src/ondeline_api/db/models/__init__.py apps/api/alembic/versions/0044_rede_wifi_pedido.py apps/api/alembic/env.py && cd apps/api && .venv/bin/mypy src/ondeline_api/db/models/rede.py`
Expected: ruff ok + mypy Success.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/db/models/rede.py apps/api/src/ondeline_api/db/models/__init__.py apps/api/alembic/versions/0044_rede_wifi_pedido.py apps/api/alembic/env.py
git commit -m "feat(rede): tabela rede_wifi_pedido (auditoria, sem a senha) + migracao 0044

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 6: RedeService — orquestração (TDD com fake client)

**Files:**
- Create: `apps/api/src/ondeline_api/services/rede_service.py`
- Test: `apps/api/tests/test_rede_service.py`

O service resolve a ONU a partir do **cliente_id local**: `Cliente.cpf` → `SgpCacheService.get_cliente(cpf)` → contrato (primeiro ativo) → `pppoe_login` → `genieacs.find_device_by_pppoe()` (fallback serial). Valida a senha (WPA 8-63), envia Set+Reboot, registra o pedido.

- [ ] **Step 1: Escrever o teste** `apps/api/tests/test_rede_service.py` (fakes locais, sem rede):

```python
"""RedeService: resolve ONU, valida senha, envia, registra pedido."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato
from ondeline_api.adapters.sgp.base import SgpProvider as SgpProviderEnum
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.db.models.rede import RedeWifiPedido
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class _FakeGenie:
    def __init__(self, *, by_pppoe=None, by_serial=None) -> None:
        self._by_pppoe = by_pppoe
        self._by_serial = by_serial
        self.set_calls: list[tuple[str, list]] = []
        self.reboots: list[str] = []

    async def find_device_by_pppoe(self, login: str):
        return self._by_pppoe

    async def find_device_by_serial(self, serial: str):
        return self._by_serial

    async def set_parameter_values(self, device_id, params):
        self.set_calls.append((device_id, params))

    async def reboot(self, device_id):
        self.reboots.append(device_id)


class _FakeSgpCache:
    def __init__(self, cliente: ClienteSgp | None) -> None:
        self._cliente = cliente

    async def get_cliente(self, cpf: str):
        return self._cliente


def _dev() -> GenieAcsDevice:
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X",
        modelo="AX1800",
        online=True,
        redes=[RedeWlan(instancia=1, ssid="CASA_5G", enabled=True),
               RedeWlan(instancia=6, ssid="CASA", enabled=True)],
    )


def _cli_sgp() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE, sgp_id="42", nome="Maria", cpf_cnpj="11122233344",
        contratos=[Contrato(id="C1", plano="100MB", status="ativo", pppoe_login="ppp5")],
    )


async def _make_cliente(db_session: AsyncSession) -> Cliente:
    cpf = uuid4().hex[:11]
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf), cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii("Maria"), whatsapp=f"55{uuid4().hex[:9]}@s.whatsapp.net",
    )
    db_session.add(c)
    await db_session.flush()
    return c


async def test_troca_seta_as_redes_e_reinicia_e_registra(db_session: AsyncSession) -> None:
    cli = await _make_cliente(db_session)
    genie = _FakeGenie(by_pppoe=_dev())
    svc = RedeService(session=db_session, genieacs=genie, sgp_cache=_FakeSgpCache(_cli_sgp()))
    ator = uuid4()

    res = await svc.trocar_senha_wifi(
        cliente_id=cli.id, nova_senha="NovaSenha123", serial=None, ator_user_id=ator
    )

    assert res.device_id == "30E1F1-AX1800-X"
    assert res.reiniciando is True
    assert len(genie.set_calls) == 1
    paths = [p[0] for p in genie.set_calls[0][1]]
    assert any(".1.KeyPassphrase" in p for p in paths)
    assert any(".6.KeyPassphrase" in p for p in paths)
    assert genie.reboots == ["30E1F1-AX1800-X"]
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.device_id == "30E1F1-AX1800-X"
    assert pedido.ator_user_id == ator
    assert pedido.status == "enviado"


async def test_senha_curta_rejeitada(db_session: AsyncSession) -> None:
    cli = await _make_cliente(db_session)
    svc = RedeService(session=db_session, genieacs=_FakeGenie(by_pppoe=_dev()),
                      sgp_cache=_FakeSgpCache(_cli_sgp()))
    with pytest.raises(SenhaInvalidaError):
        await svc.trocar_senha_wifi(cliente_id=cli.id, nova_senha="curta", serial=None,
                                    ator_user_id=uuid4())


async def test_fallback_serial_quando_pppoe_nao_acha(db_session: AsyncSession) -> None:
    cli = await _make_cliente(db_session)
    genie = _FakeGenie(by_pppoe=None, by_serial=_dev())
    svc = RedeService(session=db_session, genieacs=genie, sgp_cache=_FakeSgpCache(_cli_sgp()))
    res = await svc.trocar_senha_wifi(cliente_id=cli.id, nova_senha="NovaSenha123",
                                      serial="ITBSF1", ator_user_id=uuid4())
    assert res.device_id == "30E1F1-AX1800-X"


async def test_sem_pppoe_e_sem_serial_levanta(db_session: AsyncSession) -> None:
    cli = await _make_cliente(db_session)
    genie = _FakeGenie(by_pppoe=None, by_serial=None)
    svc = RedeService(session=db_session, genieacs=genie, sgp_cache=_FakeSgpCache(_cli_sgp()))
    with pytest.raises(OnuNaoEncontradaError):
        await svc.trocar_senha_wifi(cliente_id=cli.id, nova_senha="NovaSenha123",
                                    serial=None, ator_user_id=uuid4())
```

- [ ] **Step 2: Implementar** `apps/api/src/ondeline_api/services/rede_service.py`:

```python
"""RedeService — orquestra a troca de senha WiFi via GenieACS.

Resolve a ONU a partir do cliente local: Cliente.cpf -> SGP -> contrato ->
pppoe_login -> device no GenieACS (fallback serial). Valida a senha (WPA),
envia Set(senha nas redes ativas)+Reboot, registra o pedido. Otimista:
a senha e write-only, nao da pra confirmar por read-back.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsDevice
from ondeline_api.adapters.genieacs.wifi_paths import montar_plano
from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.db.models.rede import RedeWifiPedido

log = structlog.get_logger(__name__)

SENHA_MIN = 8
SENHA_MAX = 63


class SenhaInvalidaError(ValueError):
    """Senha fora do range WPA-PSK (8-63 chars ASCII)."""


class OnuNaoEncontradaError(Exception):
    """Nao foi possivel resolver a ONU (sem PPPoE no GenieACS e sem serial)."""


class _GenieProto(Protocol):
    async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None: ...
    async def find_device_by_serial(self, serial: str) -> GenieAcsDevice | None: ...
    async def set_parameter_values(
        self, device_id: str, params: list[tuple[str, str, str]]
    ) -> None: ...
    async def reboot(self, device_id: str) -> None: ...


class _SgpCacheProto(Protocol):
    async def get_cliente(self, cpf: str) -> ClienteSgp | None: ...


@dataclass(frozen=True, slots=True)
class StatusRede:
    encontrada: bool
    device: GenieAcsDevice | None = None
    pppoe_login: str | None = None
    motivo: str | None = None  # "onu_nao_encontrada" | "cliente_sem_contrato"


@dataclass(frozen=True, slots=True)
class ResultadoTroca:
    device_id: str
    reiniciando: bool


def _primeiro_contrato(contratos: list[Contrato]) -> Contrato | None:
    for c in contratos:
        if c.status and "ativ" in c.status.lower():
            return c
    return contratos[0] if contratos else None


def _validar_senha(senha: str) -> None:
    if not (SENHA_MIN <= len(senha) <= SENHA_MAX) or not senha.isascii():
        raise SenhaInvalidaError("senha WiFi deve ter 8 a 63 caracteres ASCII")


class RedeService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        genieacs: _GenieProto,
        sgp_cache: _SgpCacheProto,
    ) -> None:
        self._session = session
        self._genie = genieacs
        self._sgp = sgp_cache

    async def _contrato_do_cliente(self, cliente_id: UUID) -> Contrato | None:
        cliente = (
            await self._session.execute(select(Cliente).where(Cliente.id == cliente_id))
        ).scalar_one_or_none()
        if cliente is None:
            return None
        cpf = decrypt_pii(cliente.cpf_cnpj_encrypted)
        cli_sgp = await self._sgp.get_cliente(cpf)
        if cli_sgp is None:
            return None
        return _primeiro_contrato(cli_sgp.contratos)

    async def _resolver_device(
        self, cliente_id: UUID, serial: str | None
    ) -> tuple[GenieAcsDevice | None, str | None]:
        """Retorna (device, pppoe_login). Tenta PPPoE; cai pro serial."""
        contrato = await self._contrato_do_cliente(cliente_id)
        pppoe = contrato.pppoe_login if contrato and contrato.pppoe_login else None
        device: GenieAcsDevice | None = None
        if pppoe:
            device = await self._genie.find_device_by_pppoe(pppoe)
        if device is None and serial:
            device = await self._genie.find_device_by_serial(serial)
        return device, pppoe

    async def status_rede(self, cliente_id: UUID, serial: str | None = None) -> StatusRede:
        device, pppoe = await self._resolver_device(cliente_id, serial)
        if device is None:
            return StatusRede(
                encontrada=False, pppoe_login=pppoe, motivo="onu_nao_encontrada"
            )
        return StatusRede(encontrada=True, device=device, pppoe_login=pppoe)

    async def trocar_senha_wifi(
        self,
        *,
        cliente_id: UUID,
        nova_senha: str,
        serial: str | None,
        ator_user_id: UUID,
    ) -> ResultadoTroca:
        _validar_senha(nova_senha)
        device, pppoe = await self._resolver_device(cliente_id, serial)
        if device is None:
            raise OnuNaoEncontradaError("ONU nao encontrada por PPPoE nem serial")

        plano = montar_plano(device, nova_senha)
        if plano.params:
            await self._genie.set_parameter_values(device.device_id, plano.params)
        if plano.needs_reboot:
            await self._genie.reboot(device.device_id)

        contrato = await self._contrato_do_cliente(cliente_id)
        self._session.add(
            RedeWifiPedido(
                cliente_id=cliente_id,
                contrato_id=contrato.id if contrato else None,
                pppoe_login=pppoe,
                device_id=device.device_id,
                ator_user_id=ator_user_id,
                status="enviado",
                reiniciou=plano.needs_reboot,
            )
        )
        await self._session.flush()
        log.info(
            "rede.senha_trocada",
            cliente_id=str(cliente_id),
            device_id=device.device_id,
            redes=len(plano.params),
            reboot=plano.needs_reboot,
        )
        return ResultadoTroca(device_id=device.device_id, reiniciando=plano.needs_reboot)
```

- [ ] **Step 3: Lint + types**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/services/rede_service.py apps/api/tests/test_rede_service.py && cd apps/api && .venv/bin/mypy src/ondeline_api/services/rede_service.py`
Expected: ruff ok + mypy Success.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/services/rede_service.py apps/api/tests/test_rede_service.py
git commit -m "feat(rede): RedeService (resolve ONU por PPPoE/serial, troca senha + reboot, registra)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 7: Schemas Pydantic

**Files:**
- Create: `apps/api/src/ondeline_api/api/schemas/rede.py`

- [ ] **Step 1: Criar os schemas** `apps/api/src/ondeline_api/api/schemas/rede.py`:

```python
"""Schemas para /api/v1/rede/*."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RedeWlanOut(BaseModel):
    instancia: int
    ssid: str
    enabled: bool


class StatusRedeOut(BaseModel):
    encontrada: bool
    device_id: str | None = None
    fabricante: str | None = None
    modelo: str | None = None
    online: bool = False
    last_inform: datetime | None = None
    redes: list[RedeWlanOut] = Field(default_factory=list)
    pppoe_login: str | None = None
    motivo: str | None = None  # quando encontrada=False


class TrocarSenhaIn(BaseModel):
    senha: str = Field(min_length=8, max_length=63)
    serial: str | None = None


class TrocarSenhaOut(BaseModel):
    status: str  # "enviado"
    device_id: str
    reiniciando: bool
    aviso: str
```

- [ ] **Step 2: Lint + types**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/api/schemas/rede.py && cd apps/api && .venv/bin/mypy src/ondeline_api/api/schemas/rede.py`
Expected: ruff ok + mypy Success.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/rede.py
git commit -m "feat(rede): schemas Pydantic de status e troca de senha

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 8: Endpoints + registro (TDD com httpx ASGI)

**Files:**
- Create: `apps/api/src/ondeline_api/api/v1/rede.py`
- Modify: `apps/api/src/ondeline_api/main.py` (bloco `include_router`)
- Test: `apps/api/tests/test_v1_rede.py`

O endpoint injeta o `RedeService` via dependency `get_rede_service` (sobrescrevível no teste). A dep monta o `GenieAcsClient` + `SgpCacheService` (igual `cliente_app_me`).

- [ ] **Step 1: Escrever o teste** `apps/api/tests/test_v1_rede.py` (molde `test_v1_ordens_servico.py`; sobrescreve `get_rede_service` com um fake).

> ⚠️ **Antes de colar:** abra `tests/test_v1_ordens_servico.py` e copie o jeito REAL de (a) criar um `User` (o nome do campo de hash de senha e demais campos obrigatórios do model `User` podem diferir de `senha_hash`/`hash_password` usados abaixo) e (b) obter o fixture `db_session` e montar o app. Ajuste `_make_tecnico` e `_token` aos nomes reais — o esqueleto abaixo assume nomes que você deve confirmar.

```python
"""Endpoints /api/v1/rede/* (RBAC tecnico/admin)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.db.crypto import hash_password
from ondeline_api.db.models.identity import Role, User
from ondeline_api.main import create_app
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    ResultadoTroca,
    StatusRede,
)
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class _FakeService:
    def __init__(self, *, status=None, troca=None, raise_troca=None) -> None:
        self._status = status
        self._troca = troca
        self._raise = raise_troca

    async def status_rede(self, cliente_id, serial=None):
        return self._status

    async def trocar_senha_wifi(self, *, cliente_id, nova_senha, serial, ator_user_id):
        if self._raise:
            raise self._raise
        return self._troca


async def _make_tecnico(db_session: AsyncSession) -> User:
    u = User(
        email=f"t{uuid4().hex[:6]}@x.com", senha_hash=hash_password("Senha123!"),
        nome="Tec", role=Role.TECNICO, is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


def _dev() -> GenieAcsDevice:
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X", modelo="AX1800", fabricante="INTELBRAS", online=True,
        redes=[RedeWlan(instancia=1, ssid="CASA_5G", enabled=True)],
    )


async def _app_with(db_session, fake_service):
    app = create_app()
    from ondeline_api.deps import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_rede_service] = lambda: fake_service
    return app


async def _token(app, db_session) -> str:
    tec = await _make_tecnico(db_session)
    from ondeline_api.auth import jwt as jwt_mod
    return jwt_mod.encode_access_token(tec.id, Role.TECNICO.value)


async def test_status_online(db_session: AsyncSession) -> None:
    fake = _FakeService(status=StatusRede(encontrada=True, device=_dev(), pppoe_login="ppp5"))
    app = await _app_with(db_session, fake)
    token = await _token(app, db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(f"/api/v1/rede/{uuid4()}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["encontrada"] is True
    assert body["modelo"] == "AX1800"


async def test_trocar_senha_ok(db_session: AsyncSession) -> None:
    fake = _FakeService(troca=ResultadoTroca(device_id="30E1F1-AX1800-X", reiniciando=True))
    app = await _app_with(db_session, fake)
    token = await _token(app, db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            f"/api/v1/rede/{uuid4()}/wifi/senha",
            headers={"Authorization": f"Bearer {token}"},
            json={"senha": "NovaSenha123"},
        )
    assert r.status_code == 200
    assert r.json()["reiniciando"] is True


async def test_trocar_senha_onu_nao_encontrada_404(db_session: AsyncSession) -> None:
    fake = _FakeService(raise_troca=OnuNaoEncontradaError("x"))
    app = await _app_with(db_session, fake)
    token = await _token(app, db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            f"/api/v1/rede/{uuid4()}/wifi/senha",
            headers={"Authorization": f"Bearer {token}"},
            json={"senha": "NovaSenha123"},
        )
    assert r.status_code == 404


async def test_sem_token_401(db_session: AsyncSession) -> None:
    app = await _app_with(db_session, _FakeService())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(f"/api/v1/rede/{uuid4()}")
    assert r.status_code == 401
```

- [ ] **Step 2: Implementar** `apps/api/src/ondeline_api/api/v1/rede.py`:

```python
"""GET/POST /api/v1/rede/{cliente_id} — gerencia da rede WiFi via TR-069.

cliente_id = UUID do Cliente local (o app tecnico tem da OS). O service
resolve a ONU por PPPoE (do contrato no SGP) com fallback serial.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.client import GenieAcsClient
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.api.schemas.rede import (
    RedeWlanOut,
    StatusRedeOut,
    TrocarSenhaIn,
    TrocarSenhaOut,
)
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.workers.runtime import get_redis

router = APIRouter(prefix="/api/v1/rede", tags=["rede"])

_role_dep = Depends(require_role(Role.TECNICO, Role.ADMIN))

AVISO_REBOOT = "A internet do cliente vai reiniciar e voltar em cerca de 2 minutos."


async def get_rede_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncIterator[RedeService]:
    """Monta GenieAcsClient + SgpCacheService e injeta o RedeService.

    Sobrescrita inteira nos testes (app.dependency_overrides[get_rede_service]).
    """
    s = get_settings()
    redis = await get_redis()
    genie = GenieAcsClient(base_url=s.genieacs_url)
    sgp_ond = await load_sgp_config(session, "ondeline")
    sgp_lnk = await load_sgp_config(session, "linknetam")
    router_sgp = SgpRouter(
        primary=SgpOndelineProvider(**sgp_ond),
        secondary=SgpLinkNetAMProvider(**sgp_lnk),
    )
    cache = SgpCacheService(
        redis=redis,
        session=session,
        router=router_sgp,
        ttl_cliente=s.sgp_cache_ttl_cliente,
        ttl_negativo=s.sgp_cache_ttl_negativo,
    )
    try:
        yield RedeService(session=session, genieacs=genie, sgp_cache=cache)
    finally:
        await genie.aclose()
        await router_sgp.aclose()


@router.get("/{cliente_id}", response_model=StatusRedeOut, dependencies=[_role_dep])
async def status_rede(
    cliente_id: UUID,
    service: Annotated[RedeService, Depends(get_rede_service)],
    serial: str | None = None,
) -> StatusRedeOut:
    st = await service.status_rede(cliente_id, serial)
    if not st.encontrada or st.device is None:
        return StatusRedeOut(
            encontrada=False, pppoe_login=st.pppoe_login, motivo=st.motivo
        )
    d = st.device
    return StatusRedeOut(
        encontrada=True,
        device_id=d.device_id,
        fabricante=d.fabricante,
        modelo=d.modelo,
        online=d.online,
        last_inform=d.last_inform,
        redes=[RedeWlanOut(instancia=r.instancia, ssid=r.ssid, enabled=r.enabled) for r in d.redes],
        pppoe_login=st.pppoe_login,
    )


@router.post(
    "/{cliente_id}/wifi/senha", response_model=TrocarSenhaOut, dependencies=[_role_dep]
)
async def trocar_senha(
    cliente_id: UUID,
    payload: TrocarSenhaIn,
    service: Annotated[RedeService, Depends(get_rede_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> TrocarSenhaOut:
    try:
        res = await service.trocar_senha_wifi(
            cliente_id=cliente_id,
            nova_senha=payload.senha,
            serial=payload.serial,
            ator_user_id=user.id,
        )
    except SenhaInvalidaError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    aviso = AVISO_REBOOT if res.reiniciando else "Senha enviada."
    return TrocarSenhaOut(
        status="enviado",
        device_id=res.device_id,
        reiniciando=res.reiniciando,
        aviso=aviso,
    )
```

- [ ] **Step 3: Registrar o router** em `apps/api/src/ondeline_api/main.py` — adicionar o import com os outros `v1_*` e o `include_router`. Localizar o bloco `from ondeline_api.api.v1 import ( ... )` (ou imports individuais) e a sequência de `app.include_router(...)`; adicionar:

```python
    from ondeline_api.api.v1 import rede as v1_rede
    app.include_router(v1_rede.router)
```
(seguir exatamente o estilo já usado no arquivo — se os outros usam import no topo, importar no topo; se importam dentro de `create_app`, idem.)

- [ ] **Step 4: Lint + types**

Run: `apps/api/.venv/bin/ruff check apps/api/src/ondeline_api/api/v1/rede.py apps/api/src/ondeline_api/main.py apps/api/tests/test_v1_rede.py && cd apps/api && .venv/bin/mypy src/ondeline_api/api/v1/rede.py`
Expected: ruff ok + mypy Success.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/rede.py apps/api/src/ondeline_api/main.py apps/api/tests/test_v1_rede.py
git commit -m "feat(rede): endpoints GET/POST /api/v1/rede/{cliente_id} (RBAC tecnico/admin)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

> **CHECKPOINT — backend completo.** Pedir OK do Robert pra push. CI valida (ruff+mypy+pytest). Após deploy: confirmar que `blabla-api` alcança `blabla-genieacs-nbi:7557` (dependência de rede docker — §7 do spec) e a migração 0044 rodou. Teste manual via curl com token de técnico.

---

## Task 9: App técnico — tela "Rede do cliente"

**Files:**
- Create: `apps/tecnico-mobile/lib/features/rede/rede_data.dart`
- Create: `apps/tecnico-mobile/lib/features/rede/rede_screen.dart`

Padrão do app (confirmado): Dio via `apiClientProvider`, Riverpod `FutureProvider.autoDispose.family`, telas em `features/<x>/`. A tela é aberta a partir do cliente/OS passando o `cliente_id`.

- [ ] **Step 1: Criar `rede_data.dart`** (models + providers):

```dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';

class RedeWlan {
  RedeWlan({required this.instancia, required this.ssid, required this.enabled});
  final int instancia;
  final String ssid;
  final bool enabled;

  factory RedeWlan.fromJson(Map<String, dynamic> j) => RedeWlan(
        instancia: j['instancia'] as int,
        ssid: (j['ssid'] ?? '') as String,
        enabled: (j['enabled'] ?? false) as bool,
      );
}

class StatusRede {
  StatusRede({
    required this.encontrada,
    this.modelo,
    this.fabricante,
    this.online = false,
    this.redes = const [],
    this.pppoeLogin,
    this.motivo,
  });
  final bool encontrada;
  final String? modelo;
  final String? fabricante;
  final bool online;
  final List<RedeWlan> redes;
  final String? pppoeLogin;
  final String? motivo;

  factory StatusRede.fromJson(Map<String, dynamic> j) => StatusRede(
        encontrada: (j['encontrada'] ?? false) as bool,
        modelo: j['modelo'] as String?,
        fabricante: j['fabricante'] as String?,
        online: (j['online'] ?? false) as bool,
        redes: ((j['redes'] ?? []) as List)
            .map((e) => RedeWlan.fromJson(e as Map<String, dynamic>))
            .toList(),
        pppoeLogin: j['pppoe_login'] as String?,
        motivo: j['motivo'] as String?,
      );
}

final redeStatusProvider =
    FutureProvider.autoDispose.family<StatusRede, String>((ref, clienteId) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/rede/$clienteId');
  return StatusRede.fromJson(r.data as Map<String, dynamic>);
});

/// Troca a senha. Retorna o aviso pra UI. Lanca em erro (tratado na tela).
Future<String> trocarSenhaWifi(
  Dio dio, {
  required String clienteId,
  required String senha,
  String? serial,
}) async {
  final r = await dio.post(
    '/api/v1/rede/$clienteId/wifi/senha',
    data: {'senha': senha, if (serial != null && serial.isNotEmpty) 'serial': serial},
  );
  return (r.data['aviso'] ?? 'Senha enviada.') as String;
}
```

- [ ] **Step 2: Criar `rede_screen.dart`** (tela):

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import 'rede_data.dart';

class RedeScreen extends ConsumerStatefulWidget {
  const RedeScreen({super.key, required this.clienteId});
  final String clienteId;

  @override
  ConsumerState<RedeScreen> createState() => _RedeScreenState();
}

class _RedeScreenState extends ConsumerState<RedeScreen> {
  final _senha = TextEditingController();
  final _serial = TextEditingController();
  bool _enviando = false;

  @override
  void dispose() {
    _senha.dispose();
    _serial.dispose();
    super.dispose();
  }

  Future<void> _trocar(bool precisaSerial) async {
    final senha = _senha.text.trim();
    if (senha.length < 8 || senha.length > 63) {
      _msg('A senha deve ter de 8 a 63 caracteres.');
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Trocar senha do WiFi'),
        content: const Text(
          'A internet do cliente vai reiniciar e voltar em cerca de 2 minutos. Continuar?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Trocar')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _enviando = true);
    try {
      final dio = ref.read(apiClientProvider);
      final aviso = await trocarSenhaWifi(
        dio,
        clienteId: widget.clienteId,
        senha: senha,
        serial: precisaSerial ? _serial.text.trim() : null,
      );
      if (mounted) _msg(aviso);
    } catch (e) {
      if (mounted) _msg('Falha ao trocar a senha. Tente novamente.');
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  void _msg(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  @override
  Widget build(BuildContext context) {
    final status = ref.watch(redeStatusProvider(widget.clienteId));
    return Scaffold(
      appBar: AppBar(title: const Text('Rede do cliente')),
      body: status.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Erro ao carregar a rede.')),
        data: (s) => _body(s),
      ),
    );
  }

  Widget _body(StatusRede s) {
    final precisaSerial = !s.encontrada;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (s.encontrada) ...[
          Row(children: [
            Icon(s.online ? Icons.wifi : Icons.wifi_off,
                color: s.online ? Colors.green : Colors.grey),
            const SizedBox(width: 8),
            Text(s.online ? 'Online' : 'Offline',
                style: const TextStyle(fontWeight: FontWeight.bold)),
            const Spacer(),
            Text(s.modelo ?? ''),
          ]),
          const SizedBox(height: 8),
          const Text('Redes WiFi ativas:'),
          for (final r in s.redes.where((r) => r.enabled))
            ListTile(leading: const Icon(Icons.router), title: Text(r.ssid), dense: true),
        ] else ...[
          const Text(
            'Nao localizei a ONU pelo cadastro. Informe o serial da etiqueta:',
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _serial,
            decoration: const InputDecoration(labelText: 'Serial da ONU', border: OutlineInputBorder()),
          ),
        ],
        const Divider(height: 32),
        TextField(
          controller: _senha,
          decoration: const InputDecoration(
            labelText: 'Nova senha do WiFi (8 a 63 caracteres)',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: (s.encontrada && !s.online) || _enviando
              ? null
              : () => _trocar(precisaSerial),
          icon: _enviando
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.lock_reset),
          label: const Text('Trocar senha do WiFi'),
        ),
        if (s.encontrada && !s.online)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text('Aparelho offline. Tente quando voltar.',
                style: TextStyle(color: Colors.grey)),
          ),
      ],
    );
  }
}
```

- [ ] **Step 3: Conferir lint** (sem rodar flutter — CI valida). Revisar visualmente: imports usados, sem `late` não inicializado, `mounted` checado após await. (CI roda `flutter analyze`.)

- [ ] **Step 4: Commit**

```bash
git add apps/tecnico-mobile/lib/features/rede/rede_data.dart apps/tecnico-mobile/lib/features/rede/rede_screen.dart
git commit -m "feat(rede): tela Rede do cliente no app tecnico (status + trocar senha)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

> **Nota de integração (fora desta fatia, mencionar ao Robert):** falta um ponto de entrada pra `RedeScreen` (ex.: botão "Rede do cliente" na tela de detalhe do cliente/OS, passando `clienteId`). É um link de 1 linha; decidir onde encaixa ao revisar o app — não bloqueia a fatia.

---

## Verificação final (após deploy)
1. Migração 0044 aplicada (tabela `rede_wifi_pedido` existe).
2. `blabla-api` alcança `blabla-genieacs-nbi:7557` (mesma rede docker — §7 do spec).
3. Confirmar o path real do PPPoE Username no AX1800 (um `GET /devices/?query=...` no NBI); se divergir dos candidatos em `PPPOE_USERNAME_PATHS`, ajustar a constante.
4. Token de técnico → `GET /api/v1/rede/{cliente_id}` retorna status; `POST .../wifi/senha` troca + reinicia; confirmar conectando no WiFi com a senha nova.
```
