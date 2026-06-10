# Rede WiFi — Etapa 3, Fatia 2: Aparelhos conectados + Sinal da fibra

**Data:** 2026-06-10
**App alvo:** técnico-mobile (read-only, sem reboot, sem write)
**Depende de:** Fatia 1 (`2026-06-10-rede-wifi-etapa3-fatia1-trocar-senha-design.md`) — reusa todo o esqueleto.

## Objetivo

Dar ao técnico em campo, na mesma tela "Rede do cliente" (`/rede/:cpf`), duas
informações de diagnóstico que hoje exigem ir até a ONU ou ligar pro NOC:

1. **Aparelhos conectados** no WiFi/LAN do cliente (nome / IP / MAC).
2. **Sinal da fibra** — potência óptica (RX/TX), status GPON e diagnóstico do
   PPPoE (conexão, IP externo, uptime, último erro).

Tudo **read-only**: nenhuma escrita, nenhum reboot. O caminho de troca de senha
da Fatia 1 (`/status`, `/wifi/senha`) fica **intacto**.

## Decisões (do brainstorming)

- **Escopo:** aparelhos **+** sinal óptico nesta fatia (não fatiar mais).
- **Freshness do óptico:** a árvore `WANDevice` não é descoberta no inform
  normal — precisa de `refreshObject`. Sem STUN, o refresh não volta na hora
  (aplica no próximo inform, ~5min). Estratégia escolhida: **refresh best-effort
  ao abrir a tela + mostrar o que já estiver na árvore**, com selo de "última
  leitura". Técnico que revisita vê dado fresco. 1ª leitura pode vir vazia
  (mensagem clara, não erro). (Alternativas descartadas: só-leitura sem refresh
  = frustrante no parque atual; refresh síncrono com espera = falha sob NAT sem
  STUN.)
- **Placement:** estende a `RedeScreen` existente com duas seções novas, em vez
  de criar tela nova (a tela já é "Rede do cliente").
- **Endpoint:** `POST /api/v1/rede/diagnostico` separado, não estende o
  `/status`. Mantém o caminho de troca de senha lean e sem o side-effect de
  refresh; risco baixo na Fatia 1.

## Sinergia de bônus

O `refreshObject` de `InternetGatewayDevice.WANDevice` refresca a subárvore
inteira recursivamente — inclui `WANPPPConnection.Username`. Logo, abrir a tela
de diagnóstico **também esquenta a resolução por PPPoE da Fatia 1** (que hoje
depende de refresh/preset manual do WANDevice).

## Arquitetura

Reusa 100% o fluxo da Fatia 1: CPF → SGP → `contrato.pppoe_login` → device no
GenieACS via `_resolver_por_cpf` (fallback serial). Camada única em `apps/api`,
consumida pelo app técnico. Nenhum frontend fala direto com o GenieACS.

```
RedeScreen (/rede/:cpf)
  ├─ redeStatusProvider      → POST /api/v1/rede/status      (Fatia 1, intacto)
  └─ redeDiagnosticoProvider → POST /api/v1/rede/diagnostico (Fatia 2, novo)
                                   │
                              RedeService.diagnostico_rede(cpf, serial)
                                   ├─ _resolver_por_cpf  (reuso)
                                   ├─ genie.refresh_wan(device_id)  (best-effort)
                                   └─ device.aparelhos + device.sinal + last_inform
```

## Backend

### `adapters/genieacs/base.py` — DTOs novos

```python
@dataclass(frozen=True, slots=True)
class Aparelho:
    nome: str            # HostName ("" quando ausente)
    ip: str              # IPAddress
    mac: str             # MACAddress
    ativo: bool          # Active
    interface: str = ""  # InterfaceType / Layer1Interface quando disponível (wifi/eth)

@dataclass(frozen=True, slots=True)
class SinalFibra:
    # Todos opcionais — o que não vier da árvore fica None e a UI omite.
    rx_power: float | None = None      # dBm (potência recebida — a mais importante)
    tx_power: float | None = None      # dBm (potência transmitida)
    status_gpon: str | None = None     # Status da interface GPON
    conexao_pppoe: str | None = None   # WANPPPConnection.ConnectionStatus
    ip_externo: str | None = None      # ExternalIPAddress
    uptime_s: int | None = None        # Uptime (segundos)
    ultimo_erro: str | None = None     # LastConnectionError
```

`GenieAcsDevice` ganha:

```python
aparelhos: list[Aparelho] = field(default_factory=list)
sinal: SinalFibra | None = None
```

### `adapters/genieacs/client.py`

- **`_parse_aparelhos(raw)`** — lê `InternetGatewayDevice.LANDevice.1.Hosts.Host.*`
  (cada instância numérica), extrai `HostName`/`IPAddress`/`MACAddress`/`Active`
  via `_leaf`. Padrão TR-098, funciona em qualquer modelo. Omite hosts sem
  MAC (linha-fantasma).
- **`_parse_sinal(raw)`** — paths candidatos por modelo (mesma estratégia do
  `PPPOE_USERNAME_PATHS`): GPON é vendor-specific.
  ```python
  GPON_RX_PATHS = [
      # AX1800 (Intelbras) — typo de fábrica preservado:
      "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower",
      # variantes prováveis (FiberHome HG6145D etc) — confirmar no parque:
      "InternetGatewayDevice.WANDevice.1.X_GponInterfaceConfig.RXPower",
      "InternetGatewayDevice.WANDevice.1.X_FH_GponInterfaceConfig.RXPower",
  ]
  # idem para TXPower / Status, derivando o prefixo do path que casou.
  ```
  Diagnóstico PPPoE: `WANConnectionDevice.{i}.WANPPPConnection.1.{ConnectionStatus,
  ExternalIPAddress,Uptime,LastConnectionError}` — varia o índice (reusa a ideia
  dos candidatos). Retorna `SinalFibra` só com os campos que vieram; se **nenhum**
  campo veio, retorna `None`.
- **`refresh_wan(device_id)`** — posta
  `{"name":"refreshObject","objectName":"InternetGatewayDevice.WANDevice"}`
  via `_post_task` (sem connection_request → fila → próximo inform). **Best-effort:**
  envolve em try/except `GenieAcsUnavailableError`, loga `genieacs.refresh_wan_falhou`
  e segue — a leitura do que já existe não pode falhar por causa do refresh.
- `_parse_device` passa a popular `aparelhos` e `sinal`.
- A query de device já retorna o doc completo (sem projection), então Hosts e
  WAN entram quando presentes — sem mudança em `_query_devices`.

### `services/rede_service.py`

- `GenieProto` ganha `async def refresh_wan(self, device_id: str) -> None: ...`.
- DTO `DiagnosticoRede`:
  ```python
  @dataclass(frozen=True, slots=True)
  class DiagnosticoRede:
      encontrada: bool
      device: GenieAcsDevice | None = None
      motivo: str | None = None  # "onu_nao_encontrada" quando encontrada=False
  ```
- Método novo:
  ```python
  async def diagnostico_rede(self, cpf, serial=None) -> DiagnosticoRede:
      cpf = _so_digitos(cpf)
      if not cpf: raise CpfInvalidoError(...)
      res = await self._resolver_por_cpf(cpf, serial)
      if res.device is None:
          return DiagnosticoRede(encontrada=False, motivo="onu_nao_encontrada")
      await self._genie.refresh_wan(res.device.device_id)  # best-effort dentro do client
      return DiagnosticoRede(encontrada=True, device=res.device)
  ```
  (O `refresh_wan` já é best-effort no client; o service não precisa try/except.)

### `api/schemas/rede.py`

```python
class AparelhoOut(BaseModel):
    nome: str; ip: str; mac: str; ativo: bool; interface: str = ""

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
    motivo: str | None = None
```

### `api/v1/rede.py`

`POST /api/v1/rede/diagnostico`, mesma `_role_dep` (TECNICO/ADMIN), mesma
tradução de erro da Fatia 1: `CpfInvalidoError`→422, `GenieAcsUnavailableError`
→503. "Não encontrada" → `encontrada=false` no corpo (não 404, igual `/status`).
Reusa `get_rede_service`.

## Frontend (`tecnico-mobile`)

### `features/rede/rede_data.dart`
- Models `Aparelho`, `SinalFibra`, `Diagnostico` (com `fromJson`).
- `redeDiagnosticoProvider = FutureProvider.autoDispose.family<Diagnostico, String>`
  → `POST /api/v1/rede/diagnostico` body `{cpf}`.

### `features/rede/rede_screen.dart`
Abaixo do bloco WiFi existente, duas seções (ambas dependem do
`redeDiagnosticoProvider`, renderizadas com seu próprio `.when`):

- **Aparelhos conectados (N)** — lista `nome • IP • MAC`; ícone wifi/eth quando
  `interface` disponível. Vazio → "Nenhum aparelho conectado no momento."
- **Sinal da fibra** — RX power com cor por faixa, TX power, status GPON,
  conexão PPPoE, uptime (formatado), último erro; rodapé "última leitura: HH:MM"
  (de `last_inform`). `sinal == null` → "Sinal ainda não disponível — puxe pra
  atualizar (~5min)."
- O `IconButton` de refresh do AppBar passa a invalidar **os dois** providers
  (`redeStatusProvider` + `redeDiagnosticoProvider`).

**Faixas de cor do RX power** (helper comentado, GPON típico em dBm):
- **Verde (bom):** `-8 >= rx >= -25`
- **Amarelo (atenção):** `-25 > rx >= -27`
- **Vermelho (crítico):** `rx < -27` **ou** `rx > -8` (sinal quente demais)
- `null` → cinza / "—"

## Edge cases

- **Sinal vazio é estado normal** (1ª leitura sem refresh prévio): mensagem
  amigável, nunca erro.
- **HG6145D (maioria do parque): path óptico ainda NÃO confirmado.** Vai mostrar
  "—" no parque real até mapearmos o path real (puxar no debug pós-deploy, igual
  fizemos com WiFi/PPPoE). **Follow-up:** confirmar `X_*GponInterfaceConfig` do
  HG6145D e adicionar à lista de candidatos. Aparelhos (Hosts) funcionam em
  qualquer modelo.
- **Multi-contrato / cache stale:** herdados do `_resolver_por_cpf` da Fatia 1
  (mesmo comportamento, mesmas pendências).
- **GenieACS indisponível:** 503, igual `/status`. Refresh best-effort não
  derruba a leitura.

## Testes (rodam na máquina de deploy)

- `test_genieacs_client.py`: parse de aparelhos (nome/ip/mac/ativo, omite sem
  MAC); parse de sinal com path candidato que casa e com ausência total (→ None);
  `refresh_wan` engole erro técnico (best-effort).
- service: `diagnostico_rede` resolve device, dispara `refresh_wan`, retorna
  aparelhos+sinal; `encontrada=False` quando sem device.

## Fora de escopo (não fazer nesta fatia)

- Dashboard/admin (Fatia 3) e app cliente (Fatia 4).
- Preset permanente do WANDevice no GenieACS (Fatia 5 — provisionamento).
- STUN / aplicar instantâneo (Fatia 5).
- Qualquer escrita: trocar senha já é Fatia 1; reboot remoto é futuro.
