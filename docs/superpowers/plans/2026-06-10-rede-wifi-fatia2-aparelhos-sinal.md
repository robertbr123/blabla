# Rede WiFi — Fatia 2: Aparelhos conectados + Sinal da fibra — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar à tela "Rede do cliente" (app técnico) a lista de aparelhos conectados e o diagnóstico de sinal da fibra (RX/TX power, status GPON, conexão PPPoE), read-only, sem reboot.

**Architecture:** Reusa o esqueleto da Fatia 1 (CPF→SGP→pppoe→ONU via `_resolver_por_cpf`). Endpoint novo `POST /api/v1/rede/diagnostico` que dispara um `refreshObject` best-effort do WANDevice e devolve o que já está na árvore do device. Duas seções novas na `RedeScreen` existente. Caminho de troca de senha (`/status`, `/wifi/senha`) fica intacto.

**Tech Stack:** FastAPI + httpx + respx (testes) no backend; Flutter + Riverpod + Dio no app técnico.

**Spec:** `docs/superpowers/specs/2026-06-10-rede-wifi-etapa3-fatia2-aparelhos-sinal-design.md`

**Convenção do projeto:** testes (`pytest`), `ruff` e `mypy` rodam na **máquina de deploy depois do push**, não no ambiente local. Os passos "Run" abaixo são os comandos a executar nesse ambiente; a ordem TDD (teste falhando antes da implementação) deve ser respeitada ao escrever o código.

---

### Task 1: DTOs `Aparelho`/`SinalFibra` + parse de aparelhos (Hosts)

**Files:**
- Modify: `apps/api/src/ondeline_api/adapters/genieacs/base.py`
- Modify: `apps/api/src/ondeline_api/adapters/genieacs/client.py`
- Test: `apps/api/tests/test_genieacs_client.py`

- [ ] **Step 1: Adicionar os DTOs novos em `base.py`**

No `base.py`, adicione ao `__all__` os nomes `"Aparelho"` e `"SinalFibra"`, e acrescente os dataclasses (depois de `RedeWlan`):

```python
@dataclass(frozen=True, slots=True)
class Aparelho:
    """Um host na LAN/WiFi do cliente (tabela Hosts, TR-098 padrao)."""

    nome: str
    ip: str
    mac: str
    ativo: bool
    interface: str = ""  # InterfaceType / Layer1Interface quando disponivel


@dataclass(frozen=True, slots=True)
class SinalFibra:
    """Diagnostico optico (GPON) + PPPoE. Todos opcionais: o que nao veio da
    arvore fica None e a UI omite."""

    rx_power: float | None = None
    tx_power: float | None = None
    status_gpon: str | None = None
    conexao_pppoe: str | None = None
    ip_externo: str | None = None
    uptime_s: int | None = None
    ultimo_erro: str | None = None
```

E estenda `GenieAcsDevice` com dois campos novos (depois de `redes`):

```python
    aparelhos: list[Aparelho] = field(default_factory=list)
    sinal: "SinalFibra | None" = None
```

- [ ] **Step 2: Escrever o teste de parse de aparelhos (falhando)**

Em `test_genieacs_client.py`, estenda o `_device_raw` helper para aceitar Hosts e adicione o teste. Acrescente ao dict retornado por `_device_raw` (dentro de `InternetGatewayDevice.LANDevice.1`, ao lado de `WLANConfiguration`) uma chave `Hosts`:

```python
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
```

E o teste novo:

```python
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
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_genieacs_client.py::test_parse_aparelhos_lista_hosts_com_mac -v`
Expected: FAIL (`dev.aparelhos` vazio — parsing ainda não existe).

- [ ] **Step 4: Implementar `_parse_aparelhos` no `client.py`**

No `client.py`, importe `Aparelho` e `SinalFibra` do `base` (adicione aos imports existentes de `genieacs.base`), defina o path e a função, e chame no `_parse_device`:

```python
_HOSTS_PATH = ("InternetGatewayDevice", "LANDevice", "1", "Hosts", "Host")


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
```

No `_parse_device`, adicione ao construtor do `GenieAcsDevice`:

```python
        aparelhos=_parse_aparelhos(raw),
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `pytest tests/test_genieacs_client.py::test_parse_aparelhos_lista_hosts_com_mac -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/genieacs/base.py apps/api/src/ondeline_api/adapters/genieacs/client.py apps/api/tests/test_genieacs_client.py
git commit -m "feat(rede): parse de aparelhos conectados (Hosts) no GenieAcsClient"
```

---

### Task 2: Parse do sinal da fibra (GPON + PPPoE) com paths candidatos por modelo

**Files:**
- Modify: `apps/api/src/ondeline_api/adapters/genieacs/client.py`
- Test: `apps/api/tests/test_genieacs_client.py`

- [ ] **Step 1: Escrever os testes de parse de sinal (falhando)**

Em `test_genieacs_client.py`, adicione um helper que injeta a subárvore WAN e dois testes (path que casa e ausência total):

```python
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


async def test_parse_sinal_ausente_retorna_none() -> None:
    # _device_raw() sem subarvore WAN -> nenhum campo de sinal -> sinal None
    async with respx.mock(base_url=BASE) as mock:
        mock.get("/devices/").respond(200, json=[_device_raw()])
        c = GenieAcsClient(base_url=BASE)
        dev = await c.get_device("x")
        assert dev is not None
        assert dev.sinal is None
        await c.aclose()
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_genieacs_client.py -k parse_sinal -v`
Expected: FAIL (atributo `sinal` ainda não é populado).

- [ ] **Step 3: Implementar `_parse_sinal` + helpers no `client.py`**

Adicione as listas de candidatos (perto de `PPPOE_USERNAME_PATHS`):

```python
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
```

E os helpers + a função (perto de `_parse_redes`):

```python
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
```

No `_parse_device`, adicione ao construtor do `GenieAcsDevice`:

```python
        sinal=_parse_sinal(raw),
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_genieacs_client.py -k parse_sinal -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/genieacs/client.py apps/api/tests/test_genieacs_client.py
git commit -m "feat(rede): parse do sinal optico (GPON) + diag PPPoE com paths por modelo"
```

---

### Task 3: `refresh_wan` best-effort no client

**Files:**
- Modify: `apps/api/src/ondeline_api/adapters/genieacs/client.py`
- Test: `apps/api/tests/test_genieacs_client.py`

- [ ] **Step 1: Escrever os testes (falhando)**

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falham**

Run: `pytest tests/test_genieacs_client.py -k refresh_wan -v`
Expected: FAIL (`refresh_wan` não existe).

- [ ] **Step 3: Implementar `refresh_wan` (método da classe `GenieAcsClient`)**

Adicione na classe `GenieAcsClient`, depois de `reboot`:

```python
    async def refresh_wan(self, device_id: str) -> None:
        """Best-effort: enfileira refreshObject do WANDevice (popula o sinal
        optico + diag PPPoE no proximo inform). Falha tecnica do NBI NAO
        propaga: a leitura do que ja existe na arvore nao pode quebrar por
        causa do refresh."""
        try:
            await self._post_task(
                device_id,
                {
                    "name": "refreshObject",
                    "objectName": "InternetGatewayDevice.WANDevice",
                },
            )
        except GenieAcsUnavailableError as e:
            log.warning("genieacs.refresh_wan_falhou", device_id=device_id, error=str(e))
```

- [ ] **Step 4: Rodar e confirmar que passam**

Run: `pytest tests/test_genieacs_client.py -k refresh_wan -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/genieacs/client.py apps/api/tests/test_genieacs_client.py
git commit -m "feat(rede): refresh_wan best-effort (refreshObject do WANDevice)"
```

---

### Task 4: `diagnostico_rede` no RedeService

**Files:**
- Modify: `apps/api/src/ondeline_api/services/rede_service.py`
- Test: `apps/api/tests/test_rede_service.py`

- [ ] **Step 1: Escrever os testes (falhando)**

Em `test_rede_service.py`: o `_FakeGenie` precisa registrar chamadas a `refresh_wan`. Adicione ao `__init__` do `_FakeGenie` `self.refresh_calls: list[str] = []` e o método:

```python
    async def refresh_wan(self, device_id):
        self.refresh_calls.append(device_id)
```

Atualize `_dev()` para incluir aparelhos+sinal e adicione os testes:

```python
def _dev_diag() -> GenieAcsDevice:
    from ondeline_api.adapters.genieacs.base import Aparelho, SinalFibra
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X",
        modelo="AX1800",
        online=True,
        aparelhos=[Aparelho(nome="Cel", ip="192.168.1.2", mac="AA:01", ativo=True)],
        sinal=SinalFibra(rx_power=-26.5, conexao_pppoe="Connected"),
    )


async def test_diagnostico_resolve_dispara_refresh_e_retorna(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev_diag())
    svc = _svc(db_session, genie)
    diag = await svc.diagnostico_rede(CPF)
    assert diag.encontrada is True
    assert diag.device is not None
    assert diag.device.aparelhos[0].mac == "AA:01"
    assert diag.device.sinal is not None and diag.device.sinal.rx_power == -26.5
    assert genie.refresh_calls == ["30E1F1-AX1800-X"]  # refresh disparado


async def test_diagnostico_onu_nao_encontrada(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=None, by_serial=None)
    svc = _svc(db_session, genie)
    diag = await svc.diagnostico_rede(CPF)
    assert diag.encontrada is False
    assert diag.motivo == "onu_nao_encontrada"
    assert genie.refresh_calls == []  # sem device, sem refresh


async def test_diagnostico_cpf_vazio_rejeitado(db_session: AsyncSession) -> None:
    svc = _svc(db_session, _FakeGenie(by_pppoe=_dev_diag()))
    with pytest.raises(CpfInvalidoError):
        await svc.diagnostico_rede("---")
```

- [ ] **Step 2: Rodar e confirmar que falham**

Run: `pytest tests/test_rede_service.py -k diagnostico -v`
Expected: FAIL (`diagnostico_rede` e `refresh_wan` no Protocol não existem).

- [ ] **Step 3: Implementar no `rede_service.py`**

Adicione ao `GenieProto` (depois de `reboot`):

```python
    async def refresh_wan(self, device_id: str) -> None: ...
```

Adicione o DTO (perto de `StatusRede`):

```python
@dataclass(frozen=True, slots=True)
class DiagnosticoRede:
    encontrada: bool
    device: GenieAcsDevice | None = None
    motivo: str | None = None  # "onu_nao_encontrada" quando encontrada=False
```

Adicione o método na classe `RedeService` (depois de `status_rede`):

```python
    async def diagnostico_rede(
        self, cpf: str, serial: str | None = None
    ) -> DiagnosticoRede:
        """Read-only: aparelhos conectados + sinal da fibra. Dispara um
        refreshObject best-effort do WANDevice (popula optico/PPPoE no proximo
        inform) e retorna o que ja esta na arvore do device."""
        cpf = _so_digitos(cpf)
        if not cpf:
            raise CpfInvalidoError("CPF invalido")
        res = await self._resolver_por_cpf(cpf, serial)
        if res.device is None:
            return DiagnosticoRede(encontrada=False, motivo="onu_nao_encontrada")
        await self._genie.refresh_wan(res.device.device_id)  # best-effort no client
        return DiagnosticoRede(encontrada=True, device=res.device)
```

- [ ] **Step 4: Rodar e confirmar que passam**

Run: `pytest tests/test_rede_service.py -k diagnostico -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/rede_service.py apps/api/tests/test_rede_service.py
git commit -m "feat(rede): RedeService.diagnostico_rede (aparelhos + sinal + refresh wan)"
```

---

### Task 5: Schemas + endpoint `POST /api/v1/rede/diagnostico`

**Files:**
- Modify: `apps/api/src/ondeline_api/api/schemas/rede.py`
- Modify: `apps/api/src/ondeline_api/api/v1/rede.py`
- Test: `apps/api/tests/test_v1_rede.py`

- [ ] **Step 1: Adicionar os schemas em `schemas/rede.py`**

```python
class AparelhoOut(BaseModel):
    nome: str
    ip: str
    mac: str
    ativo: bool
    interface: str = ""


class SinalFibraOut(BaseModel):
    rx_power: float | None = None
    tx_power: float | None = None
    status_gpon: str | None = None
    conexao_pppoe: str | None = None
    ip_externo: str | None = None
    uptime_s: int | None = None
    ultimo_erro: str | None = None


class DiagnosticoIn(BaseModel):
    cpf: str = Field(min_length=11, max_length=18)
    serial: str | None = None


class DiagnosticoOut(BaseModel):
    encontrada: bool
    last_inform: datetime | None = None
    aparelhos: list[AparelhoOut] = Field(default_factory=list)
    sinal: SinalFibraOut | None = None
    motivo: str | None = None  # quando encontrada=False
```

- [ ] **Step 2: Escrever o teste de endpoint (falhando)**

Em `test_v1_rede.py`, adicione ao `_FakeService` o suporte a diagnóstico. No `__init__` acrescente o parâmetro `diag: "DiagnosticoRede | None" = None` e `self._diag = diag`, e o método:

```python
    async def diagnostico_rede(self, cpf: str, serial: str | None = None):
        assert self._diag is not None
        return self._diag
```

Importe o DTO no topo: `from ondeline_api.services.rede_service import DiagnosticoRede` (junte aos imports existentes de `rede_service`). E o teste:

```python
@pytest.mark.asyncio
async def test_diagnostico_encontrada(
    db_session: AsyncSession, redis_client: Any
) -> None:
    """POST /api/v1/rede/diagnostico retorna aparelhos + sinal quando achada."""
    from datetime import UTC, datetime
    from ondeline_api.adapters.genieacs.base import Aparelho, SinalFibra

    dev = GenieAcsDevice(
        device_id="30E1F1-AX1800-X",
        modelo="AX1800",
        online=True,
        last_inform=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
        aparelhos=[Aparelho(nome="Cel", ip="192.168.1.2", mac="AA:01", ativo=True)],
        sinal=SinalFibra(rx_power=-26.5, conexao_pppoe="Connected"),
    )
    fake = _FakeService(diag=DiagnosticoRede(encontrada=True, device=dev))
    app = _make_app_overrides(db_session, redis_client, fake)
    tec = await _make_tecnico_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, tec["email"], tec["password"])
        r = await c.post(
            "/api/v1/rede/diagnostico", json={"cpf": CPF}, headers=_auth(token)
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["encontrada"] is True
    assert body["aparelhos"][0]["mac"] == "AA:01"
    assert body["sinal"]["rx_power"] == -26.5
    assert body["sinal"]["conexao_pppoe"] == "Connected"


@pytest.mark.asyncio
async def test_diagnostico_nao_encontrada_200(
    db_session: AsyncSession, redis_client: Any
) -> None:
    """ONU nao achada -> encontrada=false no corpo (nao 404)."""
    fake = _FakeService(diag=DiagnosticoRede(encontrada=False, motivo="onu_nao_encontrada"))
    app = _make_app_overrides(db_session, redis_client, fake)
    tec = await _make_tecnico_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, tec["email"], tec["password"])
        r = await c.post(
            "/api/v1/rede/diagnostico", json={"cpf": CPF}, headers=_auth(token)
        )
    assert r.status_code == 200, r.text
    assert r.json()["encontrada"] is False
```

- [ ] **Step 3: Rodar e confirmar que falham**

Run: `pytest tests/test_v1_rede.py -k diagnostico -v`
Expected: FAIL (rota `/diagnostico` não existe → 404).

- [ ] **Step 4: Implementar o endpoint em `api/v1/rede.py`**

Adicione `DiagnosticoIn`, `DiagnosticoOut`, `AparelhoOut`, `SinalFibraOut` aos imports de `api.schemas.rede`. Adicione o endpoint depois de `status_rede`:

```python
@router.post("/diagnostico", response_model=DiagnosticoOut, dependencies=[_role_dep])
async def diagnostico_rede(
    payload: DiagnosticoIn,
    service: Annotated[RedeService, Depends(get_rede_service)],
) -> DiagnosticoOut:
    try:
        diag = await service.diagnostico_rede(payload.cpf, payload.serial)
    except CpfInvalidoError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    if not diag.encontrada or diag.device is None:
        return DiagnosticoOut(encontrada=False, motivo=diag.motivo)
    d = diag.device
    return DiagnosticoOut(
        encontrada=True,
        last_inform=d.last_inform,
        aparelhos=[
            AparelhoOut(nome=a.nome, ip=a.ip, mac=a.mac, ativo=a.ativo, interface=a.interface)
            for a in d.aparelhos
        ],
        sinal=_sinal_out(d.sinal),
    )
```

E o helper de conversão (acima do endpoint; campos explícitos porque `SinalFibra`
tem `slots=True` e não suporta `vars()`):

```python
def _sinal_out(s: SinalFibra | None) -> SinalFibraOut | None:
    if s is None:
        return None
    return SinalFibraOut(
        rx_power=s.rx_power,
        tx_power=s.tx_power,
        status_gpon=s.status_gpon,
        conexao_pppoe=s.conexao_pppoe,
        ip_externo=s.ip_externo,
        uptime_s=s.uptime_s,
        ultimo_erro=s.ultimo_erro,
    )
```

> Importe também `SinalFibra` de `ondeline_api.adapters.genieacs.base` no `rede.py`
> (junto do `GenieAcsUnavailableError` já importado).

- [ ] **Step 5: Rodar e confirmar que passam (e a suíte de rede inteira)**

Run: `pytest tests/test_v1_rede.py tests/test_rede_service.py tests/test_genieacs_client.py -v`
Expected: PASS (todos, incluindo os da Fatia 1 que não devem ter regressão).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/rede.py apps/api/src/ondeline_api/api/v1/rede.py apps/api/tests/test_v1_rede.py
git commit -m "feat(rede): endpoint POST /api/v1/rede/diagnostico (aparelhos + sinal)"
```

---

### Task 6: Flutter — models + provider de diagnóstico

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/rede/rede_data.dart`

- [ ] **Step 1: Adicionar models e provider em `rede_data.dart`**

Acrescente ao fim do arquivo:

```dart
class Aparelho {
  Aparelho({
    required this.nome,
    required this.ip,
    required this.mac,
    required this.ativo,
    this.interface = '',
  });
  final String nome;
  final String ip;
  final String mac;
  final bool ativo;
  final String interface;

  factory Aparelho.fromJson(Map<String, dynamic> j) => Aparelho(
        nome: (j['nome'] ?? '') as String,
        ip: (j['ip'] ?? '') as String,
        mac: (j['mac'] ?? '') as String,
        ativo: (j['ativo'] ?? false) as bool,
        interface: (j['interface'] ?? '') as String,
      );
}

class SinalFibra {
  SinalFibra({
    this.rxPower,
    this.txPower,
    this.statusGpon,
    this.conexaoPppoe,
    this.ipExterno,
    this.uptimeS,
    this.ultimoErro,
  });
  final double? rxPower;
  final double? txPower;
  final String? statusGpon;
  final String? conexaoPppoe;
  final String? ipExterno;
  final int? uptimeS;
  final String? ultimoErro;

  factory SinalFibra.fromJson(Map<String, dynamic> j) => SinalFibra(
        rxPower: (j['rx_power'] as num?)?.toDouble(),
        txPower: (j['tx_power'] as num?)?.toDouble(),
        statusGpon: j['status_gpon'] as String?,
        conexaoPppoe: j['conexao_pppoe'] as String?,
        ipExterno: j['ip_externo'] as String?,
        uptimeS: (j['uptime_s'] as num?)?.toInt(),
        ultimoErro: j['ultimo_erro'] as String?,
      );
}

class Diagnostico {
  Diagnostico({
    required this.encontrada,
    this.lastInform,
    this.aparelhos = const [],
    this.sinal,
    this.motivo,
  });
  final bool encontrada;
  final DateTime? lastInform;
  final List<Aparelho> aparelhos;
  final SinalFibra? sinal;
  final String? motivo;

  factory Diagnostico.fromJson(Map<String, dynamic> j) => Diagnostico(
        encontrada: (j['encontrada'] ?? false) as bool,
        lastInform: j['last_inform'] != null
            ? DateTime.tryParse(j['last_inform'] as String)?.toLocal()
            : null,
        aparelhos: ((j['aparelhos'] ?? []) as List)
            .map((e) => Aparelho.fromJson(e as Map<String, dynamic>))
            .toList(),
        sinal: j['sinal'] != null
            ? SinalFibra.fromJson(j['sinal'] as Map<String, dynamic>)
            : null,
        motivo: j['motivo'] as String?,
      );
}

/// Diagnostico read-only (aparelhos + sinal da fibra). CPF no body (POST).
final redeDiagnosticoProvider =
    FutureProvider.autoDispose.family<Diagnostico, String>((ref, cpf) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.post('/api/v1/rede/diagnostico', data: {'cpf': cpf});
  return Diagnostico.fromJson(r.data as Map<String, dynamic>);
});
```

- [ ] **Step 2: Verificar análise estática**

Run: `cd apps/tecnico-mobile && flutter analyze`
Expected: sem issues novos no `rede_data.dart`.

- [ ] **Step 3: Commit**

```bash
git add apps/tecnico-mobile/lib/features/rede/rede_data.dart
git commit -m "feat(rede/app): models Aparelho/SinalFibra/Diagnostico + provider"
```

---

### Task 7: Flutter — seções "Aparelhos conectados" e "Sinal da fibra" na RedeScreen

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/rede/rede_screen.dart`

- [ ] **Step 1: Invalidar os dois providers no refresh do AppBar**

No `build`, troque o `onPressed` do `IconButton` de refresh para invalidar os dois:

```dart
            onPressed: () {
              ref.invalidate(redeStatusProvider(widget.cpf));
              ref.invalidate(redeDiagnosticoProvider(widget.cpf));
            },
```

- [ ] **Step 2: Adicionar helper de cor do RX power**

No topo do arquivo (após os imports), adicione:

```dart
/// Cor do RX power (GPON, dBm). Verde -8..-25 (bom), amarelo -25..-27 (atencao),
/// vermelho < -27 ou > -8 (sinal quente demais / fraco demais).
Color _corRx(double? rx) {
  if (rx == null) return Colors.grey;
  if (rx > -8 || rx < -27) return Colors.red;
  if (rx < -25) return Colors.orange;
  return Colors.green;
}

String _fmtUptime(int? s) {
  if (s == null) return '—';
  final d = s ~/ 86400, h = (s % 86400) ~/ 3600, m = (s % 3600) ~/ 60;
  if (d > 0) return '${d}d ${h}h';
  if (h > 0) return '${h}h ${m}min';
  return '${m}min';
}

String _fmtHora(DateTime? t) {
  if (t == null) return '—';
  String dois(int n) => n.toString().padLeft(2, '0');
  return '${dois(t.hour)}:${dois(t.minute)}';
}
```

- [ ] **Step 3: Renderizar as duas seções no `_body`**

No método `_body`, dentro do `ListView`, **antes** do `const Divider(height: 32)` que precede o campo de senha (ou seja, ao fim do bloco de status da ONU encontrada), adicione um widget que assiste o `redeDiagnosticoProvider` e renderiza as seções. Insira, logo após o `for (final r in s.redes.where((r) => r.enabled)) ...`:

```dart
          const Divider(height: 32),
          _diagnostico(),
```

E adicione o método `_diagnostico` na classe `_RedeScreenState`:

```dart
  Widget _diagnostico() {
    final diag = ref.watch(redeDiagnosticoProvider(widget.cpf));
    return diag.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => const Text('Não foi possível carregar o diagnóstico.',
          style: TextStyle(color: Colors.grey)),
      data: (d) {
        if (!d.encontrada) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Sinal da fibra ──
            Row(children: [
              const Icon(Icons.settings_input_antenna, size: 20),
              const SizedBox(width: 8),
              const Text('Sinal da fibra',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              const Spacer(),
              Text('última leitura: ${_fmtHora(d.lastInform)}',
                  style: const TextStyle(color: Colors.grey, fontSize: 12)),
            ]),
            const SizedBox(height: 8),
            if (d.sinal == null)
              const Text('Sinal ainda não disponível — puxe pra atualizar (~5min).',
                  style: TextStyle(color: Colors.grey))
            else ...[
              Row(children: [
                Icon(Icons.circle, size: 12, color: _corRx(d.sinal!.rxPower)),
                const SizedBox(width: 8),
                Text('RX: ${d.sinal!.rxPower?.toStringAsFixed(1) ?? '—'} dBm'),
                const SizedBox(width: 16),
                Text('TX: ${d.sinal!.txPower?.toStringAsFixed(1) ?? '—'} dBm'),
              ]),
              const SizedBox(height: 4),
              Text('GPON: ${d.sinal!.statusGpon ?? '—'}   •   '
                  'PPPoE: ${d.sinal!.conexaoPppoe ?? '—'}'),
              if (d.sinal!.ipExterno != null) Text('IP: ${d.sinal!.ipExterno}'),
              Text('Uptime: ${_fmtUptime(d.sinal!.uptimeS)}'
                  '${d.sinal!.ultimoErro != null && d.sinal!.ultimoErro != 'ERROR_NONE' ? '   •   Último erro: ${d.sinal!.ultimoErro}' : ''}'),
            ],
            const Divider(height: 32),
            // ── Aparelhos conectados ──
            Text('Aparelhos conectados (${d.aparelhos.length})',
                style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            if (d.aparelhos.isEmpty)
              const Text('Nenhum aparelho conectado no momento.',
                  style: TextStyle(color: Colors.grey))
            else
              for (final a in d.aparelhos)
                ListTile(
                  dense: true,
                  leading: Icon(
                      a.interface.contains('11') || a.interface.toLowerCase().contains('wifi')
                          ? Icons.wifi
                          : Icons.lan,
                      size: 20,
                      color: a.ativo ? Colors.green : Colors.grey),
                  title: Text(a.nome.isEmpty ? a.ip : a.nome),
                  subtitle: Text('${a.ip}  •  ${a.mac}'),
                ),
          ],
        );
      },
    );
  }
```

> Nota: o `_diagnostico()` só desenha as seções quando a ONU foi encontrada (`s.encontrada`). Se a tela está no estado `!s.encontrada` (pedindo serial), o bloco onde inserimos a chamada (`if (s.encontrada) ...`) já não é renderizado — então não duplique a chamada no `else`.

- [ ] **Step 4: Verificar análise estática**

Run: `cd apps/tecnico-mobile && flutter analyze`
Expected: sem issues novos.

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/rede/rede_screen.dart
git commit -m "feat(rede/app): secoes Aparelhos conectados + Sinal da fibra na tela do tecnico"
```

---

## Notas de deploy / follow-up

- **HG6145D (FiberHome, maioria do parque):** o path óptico ainda não foi confirmado. No parque real o sinal pode vir "—" até mapearmos o container GPON real (debug pós-deploy, igual WiFi/PPPoE da Fatia 1) e adicioná-lo a `GPON_CFG_PATHS`/`PPPOE_CONN_PATHS`. Aparelhos (Hosts) funcionam desde já em qualquer modelo.
- **Preset permanente do WANDevice** (pra o sinal aparecer sem depender de o técnico abrir a tela antes) é Fatia 5 (provisionamento). Nesta fatia o refresh é on-open best-effort.
- **Push só com OK do Robert** (regra de workflow). Os commits ficam locais até liberação.
