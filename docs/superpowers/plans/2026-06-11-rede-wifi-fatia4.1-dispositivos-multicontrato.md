# Rede WiFi Fatia 4.1 — dispositivos + selo de saúde + multi-contrato — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Na tela "Minha Rede WiFi" do app cliente: mostrar dispositivos conectados + um selo de saúde do sinal, e corrigir o bug de multi-contrato (resolver a ONU do contrato selecionado; sem ONU → "em construção").

**Architecture:** `RedeService` fica contrato-aware (param `contrato_id` opcional, matching estrito). Novo endpoint cliente `GET /cliente-app/rede/aparelhos` reusa `diagnostico_rede` e traduz `sinal.rx_power` num selo. Frontend: providers passam a observar `contratoAtualProvider` + nova seção na tela.

**Tech Stack:** FastAPI + SQLAlchemy async + Pydantic. Flutter + Riverpod + Dio + go_router. Spec: `docs/superpowers/specs/2026-06-11-rede-wifi-fatia4.1-dispositivos-multicontrato-design.md`.

> **⚠️ Sem stack local:** não rodar `pytest`/`flutter`/`ruff`/`docker` nesta máquina — os passos "Run" rodam no CI após push. Commitar LOCAL na main, **não pushar** sem OK do Robert.

---

## File Structure

**Backend (modificar):**
- `apps/api/src/ondeline_api/services/rede_service.py` — resolver contrato-aware.
- `apps/api/src/ondeline_api/api/schemas/cliente_app_rede.py` — schemas de aparelhos + `contrato_id`.
- `apps/api/src/ondeline_api/api/v1/cliente_app_rede.py` — `contrato_id` no status/troca, novo `/aparelhos`, helper de saúde.
- `apps/api/tests/test_rede_service.py` — testes do resolver contrato-aware.
- `apps/api/tests/test_cliente_app_rede.py` — testes do `/aparelhos`, saúde, `contrato_id`.

**Frontend (modificar):**
- `apps/cliente-mobile/lib/core/api/rede_repository.dart` — DTOs de aparelhos, `aparelhos()`, `contratoId` em tudo, providers observam contrato.
- `apps/cliente-mobile/lib/features/rede/rede_screen.dart` — passa contrato na troca, aviso das 2 bandas, seção saúde+dispositivos.

---

## Task 1: Resolver contrato-aware no RedeService

**Files:**
- Modify: `apps/api/src/ondeline_api/services/rede_service.py`
- Test: `apps/api/tests/test_rede_service.py`

- [ ] **Step 1: Escrever os testes (TDD)**

Adicionar ao final de `apps/api/tests/test_rede_service.py` (reusa `_FakeGenie`, `_FakeSgpCache`, `_dev`, `CPF`, `select`, `RedeWifiPedido`, `uuid4` já importados no arquivo):

```python
async def test_status_contrato_id_resolve_so_aquele(db_session: AsyncSession) -> None:
    """Multi-contrato: com contrato_id, resolve SO aquele contrato. O contrato
    'A' nao tem ONU -> encontrada=False (NAO cai pro 'B' que tem)."""
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE, sgp_id="7", nome="Multi", cpf_cnpj=CPF,
        contratos=[
            Contrato(id="A", plano="X", status="ativo", pppoe_login="ppp_sem_onu"),
            Contrato(id="B", plano="Y", status="ativo", pppoe_login="ppp6"),
        ],
    )

    class _GenieMulti(_FakeGenie):
        async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None:
            return _dev() if login == "ppp6" else None

    svc = RedeService(session=db_session, genieacs=_GenieMulti(),
                      sgp_cache=_FakeSgpCache(cli))
    # Contrato A (sem ONU) -> nao encontrada, e NAO usa o B.
    st_a = await svc.status_rede(CPF, contrato_id="A")
    assert st_a.encontrada is False
    # Contrato B (com ONU) -> encontrada.
    st_b = await svc.status_rede(CPF, contrato_id="B")
    assert st_b.encontrada is True and st_b.device is not None


async def test_status_sem_contrato_id_mantem_primeiro_com_onu(db_session: AsyncSession) -> None:
    """Sem contrato_id (tecnico/dashboard): comportamento atual — acha o 1o com ONU."""
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE, sgp_id="7", nome="Multi", cpf_cnpj=CPF,
        contratos=[
            Contrato(id="A", plano="X", status="ativo", pppoe_login="ppp_sem_onu"),
            Contrato(id="B", plano="Y", status="ativo", pppoe_login="ppp6"),
        ],
    )

    class _GenieMulti(_FakeGenie):
        async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None:
            return _dev() if login == "ppp6" else None

    svc = RedeService(session=db_session, genieacs=_GenieMulti(),
                      sgp_cache=_FakeSgpCache(cli))
    st = await svc.status_rede(CPF)
    assert st.encontrada is True


async def test_troca_contrato_id_targeta_o_contrato_certo(db_session: AsyncSession) -> None:
    """Troca com contrato_id usa o pppoe daquele contrato (auditoria registra ele)."""
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE, sgp_id="7", nome="Multi", cpf_cnpj=CPF,
        contratos=[
            Contrato(id="A", plano="X", status="ativo", pppoe_login="ppp5"),
            Contrato(id="B", plano="Y", status="ativo", pppoe_login="ppp6"),
        ],
    )

    class _GenieMulti(_FakeGenie):
        async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None:
            return _dev()  # qualquer pppoe acha (pra isolar a escolha do contrato)

    svc = RedeService(session=db_session, genieacs=_GenieMulti(),
                      sgp_cache=_FakeSgpCache(cli))
    await svc.trocar_senha_wifi(cpf=CPF, nova_senha="NovaSenha123",
                                serial=None, ator_user_id=uuid4(), contrato_id="B")
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.contrato_id == "B"
    assert pedido.pppoe_login == "ppp6"
```

- [ ] **Step 2: Rodar os testes (CI) — devem FALHAR**

Run: `cd apps/api && pytest tests/test_rede_service.py -k contrato_id -v`
Expected: FAIL (`status_rede()`/`trocar_senha_wifi()` ainda não aceitam `contrato_id`).

- [ ] **Step 3: Tornar o resolver contrato-aware**

Em `apps/api/src/ondeline_api/services/rede_service.py`, trocar a assinatura e o início do `_resolver_por_cpf`. Substituir:

```python
    async def _resolver_por_cpf(self, cpf: str, serial: str | None) -> _Resolucao:
        """CPF -> SGP -> contrato -> pppoe -> device. PPPoE e a chave PRINCIPAL
        (o SGP faz o RADIUS, entao o login bate com o Username na ONU); serial
        e o fallback. Reusado pelo app do cliente (passa o CPF do login).

        Cliente pode ter VARIOS contratos (varias ONUs): tenta CADA pppoe e usa
        o primeiro que tem ONU registrada no GenieACS."""
        cli = await self._sgp.get_cliente(cpf)
        contratos = _contratos_ordenados(cli.contratos) if cli else []
```

por:

```python
    async def _resolver_por_cpf(
        self, cpf: str, serial: str | None, contrato_id: str | None = None
    ) -> _Resolucao:
        """CPF -> SGP -> contrato -> pppoe -> device. PPPoE e a chave PRINCIPAL
        (o SGP faz o RADIUS, entao o login bate com o Username na ONU); serial
        e o fallback. Reusado pelo app do cliente (passa o CPF do login).

        Cliente pode ter VARIOS contratos (varias ONUs). Sem contrato_id: tenta
        CADA pppoe e usa o primeiro com ONU (tecnico/dashboard). COM contrato_id:
        matching ESTRITO — resolve SO aquele contrato; sem ONU -> device None
        (nao cai pra outro contrato, senao volta o bug do app cliente)."""
        cli = await self._sgp.get_cliente(cpf)
        contratos = _contratos_ordenados(cli.contratos) if cli else []
        if contrato_id:
            contratos = [c for c in contratos if c.id == contrato_id]
```

- [ ] **Step 4: Repassar `contrato_id` nos 3 métodos públicos**

No mesmo arquivo, trocar as 3 assinaturas + a chamada interna ao resolver.

`status_rede`:
```python
    async def status_rede(
        self, cpf: str, serial: str | None = None, contrato_id: str | None = None
    ) -> StatusRede:
        cpf = _so_digitos(cpf)
        if not cpf:
            raise CpfInvalidoError("CPF invalido")
        res = await self._resolver_por_cpf(cpf, serial, contrato_id)
```
(o resto do método igual)

`diagnostico_rede`:
```python
    async def diagnostico_rede(
        self, cpf: str, serial: str | None = None, contrato_id: str | None = None
    ) -> DiagnosticoRede:
```
e dentro dele trocar `res = await self._resolver_por_cpf(cpf, serial)` por
`res = await self._resolver_por_cpf(cpf, serial, contrato_id)`.

`trocar_senha_wifi` — adicionar o parâmetro keyword-only e repassar:
```python
    async def trocar_senha_wifi(
        self,
        *,
        cpf: str,
        nova_senha: str,
        serial: str | None,
        ator_user_id: UUID,
        contrato_id: str | None = None,
    ) -> ResultadoTroca:
```
e trocar a linha `res = await self._resolver_por_cpf(cpf, serial)` (dentro de `trocar_senha_wifi`) por `res = await self._resolver_por_cpf(cpf, serial, contrato_id)`.

> Cuidado: `status_rede`, `diagnostico_rede` e `trocar_senha_wifi` cada um tem sua própria chamada a `_resolver_por_cpf(cpf, serial)` — atualizar as TRÊS pra passar `contrato_id`.

- [ ] **Step 5: Rodar os testes (CI) — devem PASSAR**

Run: `cd apps/api && pytest tests/test_rede_service.py -v`
Expected: PASS (novos + os antigos, incl. `test_multi_contrato_usa_o_que_tem_onu` que não passa `contrato_id`).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/services/rede_service.py apps/api/tests/test_rede_service.py
git commit -m "feat(rede): resolver contrato-aware (matching estrito por contrato_id)"
```

---

## Task 2: Schemas + endpoint /aparelhos + saúde + contrato_id nos endpoints do cliente

**Files:**
- Modify: `apps/api/src/ondeline_api/api/schemas/cliente_app_rede.py`
- Modify: `apps/api/src/ondeline_api/api/v1/cliente_app_rede.py`
- Test: `apps/api/tests/test_cliente_app_rede.py`

- [ ] **Step 1: Adicionar os schemas**

Em `apps/api/src/ondeline_api/api/schemas/cliente_app_rede.py`, adicionar `contrato_id` no input de troca e os schemas de aparelhos. Substituir a classe `TrocarSenhaClienteIn` por:

```python
class TrocarSenhaClienteIn(BaseModel):
    # SEM cpf: o cliente so pode trocar a propria rede (CPF do token).
    senha: str = Field(min_length=8, max_length=63)
    contrato_id: str | None = None  # qual contrato (multi-contrato); None = atual


class AparelhoClienteOut(BaseModel):
    nome: str
    ip: str


class AparelhosClienteOut(BaseModel):
    encontrada: bool
    total: int = 0
    aparelhos: list[AparelhoClienteOut] = Field(default_factory=list)
    # "excelente" | "boa" | "fraca" | "indisponivel"
    saude: str = "indisponivel"
```

- [ ] **Step 2: Escrever os testes (TDD)**

Em `apps/api/tests/test_cliente_app_rede.py`: (a) estender o `_FakeService` pra aceitar `contrato_id` e ter `diagnostico_rede`; (b) adicionar testes. 

Trocar a classe `_FakeService` inteira por:

```python
class _FakeService:
    def __init__(
        self,
        *,
        status: StatusRede | None = None,
        troca: ResultadoTroca | None = None,
        raise_troca: Exception | None = None,
        diag: "DiagnosticoRede | None" = None,
    ) -> None:
        self._status = status
        self._troca = troca
        self._raise = raise_troca
        self._diag = diag
        self.last_contrato_id: str | None = None

    async def status_rede(
        self, cpf: str, serial: str | None = None, contrato_id: str | None = None
    ) -> StatusRede:
        self.last_contrato_id = contrato_id
        assert self._status is not None
        return self._status

    async def diagnostico_rede(
        self, cpf: str, serial: str | None = None, contrato_id: str | None = None
    ) -> "DiagnosticoRede":
        self.last_contrato_id = contrato_id
        assert self._diag is not None
        return self._diag

    async def trocar_senha_wifi(
        self, *, cpf: str, nova_senha: str, serial: str | None, ator_user_id: UUID,
        contrato_id: str | None = None,
    ) -> ResultadoTroca:
        self.last_contrato_id = contrato_id
        if self._raise:
            raise self._raise
        assert self._troca is not None
        return self._troca
```

Adicionar o import de `DiagnosticoRede` na seção de imports do teste (junto dos outros de `rede_service`):
```python
from ondeline_api.services.rede_service import (
    DiagnosticoRede,
    OnuNaoEncontradaError,
    ResultadoTroca,
    StatusRede,
)
```

E adicionar estes testes ao final do arquivo (reusa `_dev`, `_make_app`, `_make_cliente`, `_auth`, `GenieAcsDevice`, `RedeWlan`):

```python
def _dev_com_sinal(rx: float | None):
    from ondeline_api.adapters.genieacs.base import Aparelho, SinalFibra
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X", modelo="AX1800", online=True,
        redes=[RedeWlan(instancia=1, ssid="CASA", enabled=True)],
        aparelhos=[
            Aparelho(nome="Celular", ip="192.168.1.10", mac="AA:BB", ativo=True),
            Aparelho(nome="", ip="192.168.1.11", mac="CC:DD", ativo=False),
        ],
        sinal=SinalFibra(rx_power=rx) if rx is not None else None,
    )


async def test_aparelhos_encontrada_com_saude(db_session: AsyncSession) -> None:
    fake = _FakeService(diag=DiagnosticoRede(encontrada=True, device=_dev_com_sinal(-13.6)))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/aparelhos", headers=_auth(u))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["encontrada"] is True
    assert body["total"] == 2
    assert body["saude"] == "excelente"  # -13.6 dBm
    assert body["aparelhos"][0]["nome"] == "Celular"
    assert body["aparelhos"][0]["ip"] == "192.168.1.10"


async def test_aparelhos_saude_boa_no_limite(db_session: AsyncSession) -> None:
    fake = _FakeService(diag=DiagnosticoRede(encontrada=True, device=_dev_com_sinal(-26.0)))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/aparelhos", headers=_auth(u))
    assert r.json()["saude"] == "boa"  # -26 dBm (AX1800 que funciona) nao alarma


async def test_aparelhos_sem_sinal_indisponivel(db_session: AsyncSession) -> None:
    fake = _FakeService(diag=DiagnosticoRede(encontrada=True, device=_dev_com_sinal(None)))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/aparelhos", headers=_auth(u))
    assert r.json()["saude"] == "indisponivel"


async def test_aparelhos_nao_encontrada(db_session: AsyncSession) -> None:
    fake = _FakeService(diag=DiagnosticoRede(encontrada=False, motivo="onu_nao_encontrada"))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/aparelhos", headers=_auth(u))
    assert r.status_code == 200, r.text
    assert r.json()["encontrada"] is False
    assert r.json()["total"] == 0


async def test_status_repassa_contrato_id(db_session: AsyncSession) -> None:
    fake = _FakeService(status=StatusRede(encontrada=True, device=_dev()))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.get("/api/v1/cliente-app/rede/status?contrato_id=XYZ", headers=_auth(u))
    assert fake.last_contrato_id == "XYZ"
```

- [ ] **Step 3: Rodar (CI) — FALHAR**

Run: `cd apps/api && pytest tests/test_cliente_app_rede.py -k "aparelhos or contrato_id" -v`
Expected: FAIL (endpoint `/aparelhos` e param `contrato_id` ainda não existem).

- [ ] **Step 4: Implementar no endpoint do cliente**

Em `apps/api/src/ondeline_api/api/v1/cliente_app_rede.py`:

(a) Adicionar imports — no bloco dos schemas, incluir os novos; e importar `SinalFibra`:
```python
from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError, SinalFibra
from ondeline_api.api.schemas.cliente_app_rede import (
    AparelhoClienteOut,
    AparelhosClienteOut,
    RedeClienteStatusOut,
    RedeWifiOut,
    TrocarSenhaClienteIn,
    TrocarSenhaClienteOut,
)
```
(substituindo a linha `from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError` e o bloco de import dos schemas pelos acima.)

(b) Adicionar o helper de saúde logo após `AVISO_REBOOT`:
```python
def _saude_from_sinal(sinal: SinalFibra | None) -> str:
    """Traduz o RX optico (dBm) num selo amigavel, escondendo o numero."""
    if sinal is None or sinal.rx_power is None:
        return "indisponivel"
    rx = sinal.rx_power
    if -24 <= rx <= -8:
        return "excelente"
    if -27 <= rx < -24:
        return "boa"
    return "fraca"  # rx < -27 (fraco) ou rx > -8 (forte demais)
```

(c) `GET /status` — aceitar `contrato_id` e repassar. Substituir a assinatura e a chamada:
```python
@router.get("/status", response_model=RedeClienteStatusOut)
async def status_rede_cliente(
    user: Annotated[ClienteAppUser, Depends(get_current_cliente_user)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    contrato_id: str | None = None,
) -> RedeClienteStatusOut:
    cpf = decrypt_pii(user.cpf_encrypted)
    try:
        st = await service.status_rede(cpf, contrato_id=contrato_id)
```
(o resto do corpo do `status_rede_cliente` permanece igual)

(d) Adicionar o endpoint `/aparelhos` logo após o `status_rede_cliente`:
```python
@router.get("/aparelhos", response_model=AparelhosClienteOut)
async def aparelhos_rede_cliente(
    user: Annotated[ClienteAppUser, Depends(get_current_cliente_user)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    contrato_id: str | None = None,
) -> AparelhosClienteOut:
    cpf = decrypt_pii(user.cpf_encrypted)
    try:
        diag = await service.diagnostico_rede(cpf, contrato_id=contrato_id)
    except CpfInvalidoError:
        return AparelhosClienteOut(encontrada=False)
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    if not diag.encontrada or diag.device is None:
        return AparelhosClienteOut(encontrada=False)
    d = diag.device
    return AparelhosClienteOut(
        encontrada=True,
        total=len(d.aparelhos),
        aparelhos=[AparelhoClienteOut(nome=a.nome, ip=a.ip) for a in d.aparelhos],
        saude=_saude_from_sinal(d.sinal),
    )
```

(e) `POST /wifi/senha` — repassar `contrato_id` do payload. Trocar a chamada ao service:
```python
        res = await service.trocar_senha_wifi(
            cpf=cpf,
            nova_senha=payload.senha,
            serial=None,
            ator_user_id=user.id,
            contrato_id=payload.contrato_id,
        )
```

- [ ] **Step 5: Rodar (CI) — PASSAR**

Run: `cd apps/api && pytest tests/test_cliente_app_rede.py -v`
Expected: PASS (todos, novos + antigos).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/cliente_app_rede.py apps/api/src/ondeline_api/api/v1/cliente_app_rede.py apps/api/tests/test_cliente_app_rede.py
git commit -m "feat(rede): endpoint /aparelhos (dispositivos + selo de saude) + contrato_id no cliente"
```

---

## Task 3: Repository Flutter — aparelhos + contrato-aware

**Files:**
- Modify: `apps/cliente-mobile/lib/core/api/rede_repository.dart`

- [ ] **Step 1: Reescrever o repository**

Substituir o conteúdo de `apps/cliente-mobile/lib/core/api/rede_repository.dart` por:

```dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../contrato/contrato_atual_provider.dart';
import 'api_client.dart';

class RedeWifiInfo {
  RedeWifiInfo({required this.ssid});
  factory RedeWifiInfo.fromJson(Map<String, dynamic> j) =>
      RedeWifiInfo(ssid: j['ssid'] as String);
  final String ssid;
}

class RedeStatusDto {
  RedeStatusDto({
    required this.encontrada,
    required this.online,
    this.modelo,
    required this.redes,
  });

  factory RedeStatusDto.fromJson(Map<String, dynamic> j) => RedeStatusDto(
        encontrada: j['encontrada'] as bool,
        online: (j['online'] as bool?) ?? false,
        modelo: j['modelo'] as String?,
        redes: ((j['redes'] as List?) ?? const [])
            .map((e) => RedeWifiInfo.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final bool encontrada;
  final bool online;
  final String? modelo;
  final List<RedeWifiInfo> redes;

  String get nomeRede => redes.isNotEmpty ? redes.first.ssid : 'Sua rede WiFi';
}

class RedeAparelho {
  RedeAparelho({required this.nome, required this.ip});
  factory RedeAparelho.fromJson(Map<String, dynamic> j) => RedeAparelho(
        nome: (j['nome'] as String?) ?? '',
        ip: (j['ip'] as String?) ?? '',
      );
  final String nome;
  final String ip;

  /// Nome pra exibir, com fallback quando a ONU nao reporta o hostname.
  String get nomeExibicao => nome.trim().isNotEmpty ? nome : 'Dispositivo';
}

class RedeAparelhosDto {
  RedeAparelhosDto({
    required this.encontrada,
    required this.total,
    required this.aparelhos,
    required this.saude,
  });

  factory RedeAparelhosDto.fromJson(Map<String, dynamic> j) => RedeAparelhosDto(
        encontrada: (j['encontrada'] as bool?) ?? false,
        total: (j['total'] as int?) ?? 0,
        aparelhos: ((j['aparelhos'] as List?) ?? const [])
            .map((e) => RedeAparelho.fromJson(e as Map<String, dynamic>))
            .toList(),
        saude: (j['saude'] as String?) ?? 'indisponivel',
      );

  final bool encontrada;
  final int total;
  final List<RedeAparelho> aparelhos;
  final String saude; // excelente | boa | fraca | indisponivel
}

class TrocaResultDto {
  TrocaResultDto({
    required this.status,
    required this.reiniciando,
    required this.aviso,
  });

  factory TrocaResultDto.fromJson(Map<String, dynamic> j) => TrocaResultDto(
        status: j['status'] as String,
        reiniciando: (j['reiniciando'] as bool?) ?? false,
        aviso: (j['aviso'] as String?) ?? '',
      );

  final String status;
  final bool reiniciando;
  final String aviso;
}

/// Lancada quando o backend responde 429 (cooldown anti-flood).
class CooldownException implements Exception {
  CooldownException(this.minutosRestantes);
  final int minutosRestantes;
}

class RedeRepository {
  RedeRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/rede';

  Future<RedeStatusDto> status({String? contratoId}) async {
    final r = await _dio.get(
      '$_base/status',
      queryParameters: contratoId != null ? {'contrato_id': contratoId} : null,
    );
    return RedeStatusDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<RedeAparelhosDto> aparelhos({String? contratoId}) async {
    final r = await _dio.get(
      '$_base/aparelhos',
      queryParameters: contratoId != null ? {'contrato_id': contratoId} : null,
    );
    return RedeAparelhosDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<TrocaResultDto> trocarSenha(String senha, {String? contratoId}) async {
    try {
      final r = await _dio.post('$_base/wifi/senha', data: {
        'senha': senha,
        if (contratoId != null) 'contrato_id': contratoId,
      });
      return TrocaResultDto.fromJson(r.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 429) {
        throw CooldownException(_minutosFrom(e.response?.data));
      }
      rethrow;
    }
  }

  int _minutosFrom(Object? data) {
    if (data is Map && data['detail'] is Map) {
      final m = (data['detail'] as Map)['minutos_restantes'];
      if (m is int) return m;
    }
    return 5;
  }
}

final redeRepositoryProvider = Provider<RedeRepository>(
  (ref) => RedeRepository(ref.watch(apiClientProvider)),
);

/// Status da rede do contrato SELECIONADO (observa contratoAtualProvider).
final redeStatusProvider = FutureProvider<RedeStatusDto>((ref) {
  final contratoId = ref.watch(contratoAtualProvider);
  return ref.watch(redeRepositoryProvider).status(contratoId: contratoId);
});

/// Dispositivos + saude do contrato selecionado.
final redeAparelhosProvider = FutureProvider<RedeAparelhosDto>((ref) {
  final contratoId = ref.watch(contratoAtualProvider);
  return ref.watch(redeRepositoryProvider).aparelhos(contratoId: contratoId);
});
```

> Confirmar (read): `apps/cliente-mobile/lib/core/contrato/contrato_atual_provider.dart` exporta `contratoAtualProvider` cujo valor é `String?` (o contrato_id). Se o nome/caminho diferir, ajustar o import e o uso. (O `conexao_repository.dart` usa exatamente `import '../contrato/contrato_atual_provider.dart';` + `ref.watch(contratoAtualProvider)`.)

- [ ] **Step 2: Analisar (CI)**

Run: `cd apps/cliente-mobile && flutter analyze lib/core/api/rede_repository.dart`
Expected: No issues.

- [ ] **Step 3: Commit**

```bash
git add apps/cliente-mobile/lib/core/api/rede_repository.dart
git commit -m "feat(rede/app): repository contrato-aware + DTOs de dispositivos/saude"
```

---

## Task 4: Tela — aviso das 2 bandas + seção saúde/dispositivos + troca por contrato

**Files:**
- Modify: `apps/cliente-mobile/lib/features/rede/rede_screen.dart`

- [ ] **Step 1: Passar o contrato selecionado na troca**

Em `_confirmarTroca` (dentro de `_RedeScreenState`), trocar a linha que chama o repositório:
```dart
      final res = await ref.read(redeRepositoryProvider).trocarSenha(_senha.text);
```
por:
```dart
      final contratoId = ref.read(contratoAtualProvider);
      final res = await ref
          .read(redeRepositoryProvider)
          .trocarSenha(_senha.text, contratoId: contratoId);
```

E adicionar o import do provider de contrato no topo do arquivo (junto dos outros imports):
```dart
import '../../core/contrato/contrato_atual_provider.dart';
```

- [ ] **Step 2: Aviso das 2 bandas no form**

Em `_FormTroca.build`, trocar o texto auxiliar:
```dart
              const Text(
                'De 8 a 63 caracteres. Ao trocar, sua internet reinicia por ~2 min.',
                style: TextStyle(color: BrandTokens.textSecondary, fontSize: 12),
              ),
```
por:
```dart
              const Text(
                'Esta senha vale para suas duas redes (2.4GHz e 5GHz). '
                'De 8 a 63 caracteres. Ao trocar, sua internet reinicia por ~2 min.',
                style: TextStyle(color: BrandTokens.textSecondary, fontSize: 12),
              ),
```

- [ ] **Step 3: Inserir a seção saúde+dispositivos abaixo do form**

Em `_FormTroca.build`, no `ListView(children: [...])`, depois do `Container` do card de troca (o último item antes do fechamento do `children`), adicionar:
```dart
        const SizedBox(height: BrandTokens.spaceLg),
        const _SaudeEDispositivos(),
```

- [ ] **Step 4: Adicionar os widgets da seção**

Adicionar ao final de `rede_screen.dart` (depois de `_EmConstrucao`, antes do fim do arquivo) — note que a tela já importa `flutter_riverpod` e `rede_repository.dart`:

```dart
class _SaudeEDispositivos extends ConsumerWidget {
  const _SaudeEDispositivos();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(redeAparelhosProvider);
    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(BrandTokens.spaceMd),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => const SizedBox.shrink(),
      data: (d) {
        if (!d.encontrada) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SaudeBadge(saude: d.saude),
            const SizedBox(height: BrandTokens.spaceLg),
            _DispositivosCard(aparelhos: d.aparelhos, total: d.total),
          ],
        );
      },
    );
  }
}

class _SaudeBadge extends StatelessWidget {
  const _SaudeBadge({required this.saude});
  final String saude;

  ({Color cor, IconData icon, String label, String sub}) _ui() {
    switch (saude) {
      case 'excelente':
        return (
          cor: BrandTokens.success,
          icon: Icons.signal_cellular_alt_rounded,
          label: 'Sinal excelente',
          sub: 'Sua fibra está com sinal ótimo.',
        );
      case 'boa':
        return (
          cor: BrandTokens.primary,
          icon: Icons.signal_cellular_alt_rounded,
          label: 'Sinal bom',
          sub: 'Sua conexão está saudável.',
        );
      case 'fraca':
        return (
          cor: BrandTokens.warning,
          icon: Icons.signal_cellular_alt_2_bar_rounded,
          label: 'Sinal fraco',
          sub: 'Pode valer a pena falar com o suporte.',
        );
      default:
        return (
          cor: BrandTokens.info,
          icon: Icons.wifi_tethering_rounded,
          label: 'Conexão ativa',
          sub: 'Sua rede está no ar.',
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final ui = _ui();
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: ui.cor.withOpacity(0.10),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: ui.cor.withOpacity(0.30)),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: ui.cor.withOpacity(0.16),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Icon(ui.icon, color: ui.cor, size: 22),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(ui.label,
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: ui.cor)),
                Text(ui.sub,
                    style: const TextStyle(color: BrandTokens.textSecondary, fontSize: 12)),
              ],
            ),
          ),
          if (saude == 'fraca')
            TextButton(
              onPressed: () => context.push('/suporte/novo'),
              child: const Text('Suporte'),
            ),
        ],
      ),
    );
  }
}

class _DispositivosCard extends StatelessWidget {
  const _DispositivosCard({required this.aparelhos, required this.total});
  final List<RedeAparelho> aparelhos;
  final int total;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: isDark ? Colors.white12 : BrandTokens.divider),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            child: Text(
              'Dispositivos conectados ($total)',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
          ),
          if (aparelhos.isEmpty)
            const Padding(
              padding: EdgeInsets.fromLTRB(
                  BrandTokens.spaceMd, 0, BrandTokens.spaceMd, BrandTokens.spaceMd),
              child: Text(
                'Nenhum aparelho conectado agora.',
                style: TextStyle(color: BrandTokens.textSecondary, fontSize: 13),
              ),
            )
          else
            ...aparelhos.map((a) => _DispositivoRow(aparelho: a)),
        ],
      ),
    );
  }
}

class _DispositivoRow extends StatelessWidget {
  const _DispositivoRow({required this.aparelho});
  final RedeAparelho aparelho;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceMd, vertical: BrandTokens.spaceSm),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: const Icon(Icons.devices_other_rounded,
                color: BrandTokens.primary, size: 18),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(aparelho.nomeExibicao,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                    maxLines: 1, overflow: TextOverflow.ellipsis),
                if (aparelho.ip.isNotEmpty)
                  Text(aparelho.ip,
                      style: const TextStyle(
                          color: BrandTokens.textSecondary, fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 5: Invalidar aparelhos no pull-to-refresh**

No `RefreshIndicator.onRefresh` do `build` de `_RedeScreenState`, adicionar a invalidação do provider de aparelhos. Trocar:
```dart
        onRefresh: () async {
          ref.invalidate(redeStatusProvider);
          await ref.read(redeStatusProvider.future);
        },
```
por:
```dart
        onRefresh: () async {
          ref.invalidate(redeStatusProvider);
          ref.invalidate(redeAparelhosProvider);
          await ref.read(redeStatusProvider.future);
        },
```

- [ ] **Step 6: Analisar (CI)**

Run: `cd apps/cliente-mobile && flutter analyze lib/features/rede/rede_screen.dart`
Expected: No issues.

- [ ] **Step 7: Commit**

```bash
git add apps/cliente-mobile/lib/features/rede/rede_screen.dart
git commit -m "feat(rede/app): selo de saude + dispositivos conectados + aviso 2 bandas + troca por contrato"
```

---

## Self-Review (feita ao escrever o plano)

- **Cobertura do spec:** resolver contrato-aware estrito (Task 1) ✓; selo de saúde + thresholds (Task 2 helper + Task 4 badge) ✓; lista de aparelhos nome+IP sem online/offline (Task 2 endpoint só nome/ip + Task 4 card) ✓; multi-contrato no front via providers observando `contratoAtualProvider` (Task 3) ✓; contrato sem ONU → em construção (resolver estrito → `encontrada=false` → `_EmConstrucao` já existente) ✓; aviso 2 bandas (Task 4 step 2) ✓; degradação graciosa do selo/seção (Task 4: error→SizedBox.shrink, !encontrada→shrink) ✓.
- **Consistência de tipos:** `status_rede`/`diagnostico_rede`/`trocar_senha_wifi` ganham `contrato_id` (Task 1) e o fake do teto (Task 2) casa as assinaturas; `AparelhosClienteOut`/`AparelhoClienteOut` (Task 2) ↔ `RedeAparelhosDto`/`RedeAparelho` (Task 3) ↔ usados na Task 4; `redeAparelhosProvider`/`redeStatusProvider` definidos na Task 3 e usados na Task 4; `saude` strings (`excelente|boa|fraca|indisponivel`) idênticas no helper (Task 2) e no `_SaudeBadge._ui` (Task 4).
- **Sem placeholder:** todo passo tem código real. Limiares de dBm explícitos. 
- **Verificação pendente de nome:** `contratoAtualProvider` (caminho `core/contrato/contrato_atual_provider.dart`, valor `String?`) — Task 3 manda confirmar via read; é o mesmo que `conexao_repository.dart` já usa.

## Fora de escopo
Bloquear/renomear aparelho, dBm cru na tela, captura de temperatura/bias, presets (Fatia 5).
