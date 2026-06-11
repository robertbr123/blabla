# Rede WiFi — Fatia 6: diagnóstico de rede no bot (LLM) + na OS

**Data:** 2026-06-11
**Superfícies:** API (FastAPI: tool LLM, OS, prompt) · dashboard (painel) · app técnico (Flutter)
**Depende de:** Fatia 2/3 (`RedeService`, `diagnostico_rede`, `GenieAcsClient`, mappers).

## Objetivo

Levar o diagnóstico de rede (aparelhos conectados + sinal óptico da Fatia 2) pra
dois lugares novos, além de um ajuste no painel:

- **A — PPPoE no painel:** mostrar o login PPPoE do cliente na aba Rede da conversa.
- **B — bot triagem:** quando o cliente reclama de internet lenta/caindo, o bot
  (LLM) consulta o GenieACS e responde com quantos aparelhos estão conectados e a
  qualidade do sinal; se o sinal está ruim, **oferece abrir um chamado** (com OK
  do cliente).
- **C — sinal na OS:** ao abrir uma OS (pelo bot ou pela dashboard), capturar o
  sinal óptico e entregar pro técnico — na notificação WhatsApp e na tela de
  detalhe da OS no app técnico — com a bolinha de cor 🟢🟡🔴 + valor.

## Decisões (do brainstorming)

- **B (sinal ruim):** bot **informa + oferece** abrir OS, só abre com confirmação
  do cliente (usa o tool `abrir_ordem_servico` existente). NÃO abre sozinho.
- **C (entrega pro técnico):** bolinha + valor na **notificação WhatsApp E na tela
  da OS no app técnico** (Flutter, exige rebuild).
- **Captura do sinal na OS:** busca **server-side best-effort** no momento de criar
  (cpf → `RedeService.diagnostico_rede`), não passa snapshot pelo body. Single
  source; se GenieACS fora / sem ONU → `sinal=null`, OS criada normal.
- **`qualidade_sinal` = helper único** no backend (bot + OS + notificação usam o
  mesmo), reusando as faixas da Fatia 2/3.
- **Coluna `sinal` JSONB** na `OrdemServico` (flexível) vs colunas separadas.

## Fundação compartilhada: `qualidade_sinal`

Helper puro no backend, em `services/rede_service.py` (módulo-level, junto do
`RedeService`) — fonte de verdade da cor:

```python
def qualidade_sinal(rx_power: float | None) -> tuple[str, str]:
    """(label, emoji) do RX power GPON (dBm). Mesmas faixas da Fatia 2/3."""
    if rx_power is None:
        return ("desconhecido", "⚪")
    if rx_power > -8 or rx_power < -27:
        return ("critico", "🔴")
    if rx_power < -25:
        return ("atencao", "🟡")
    return ("bom", "🟢")
```

O app técnico (Flutter) espelha as MESMAS faixas num helper `_corSinal` (igual ao
`_corRx` da Fatia 2) ou lê o `qualidade` já gravado no snapshot.

## Parte A — PPPoE no painel

Expor `pppoe_login` no diagnóstico (hoje só o `StatusRedeOut` tem):

1. `api/schemas/rede.py` `DiagnosticoOut`: adicionar `pppoe_login: str | None = None`.
2. `services/rede_service.py` `DiagnosticoRede` dataclass: adicionar
   `pppoe_login: str | None = None`.
3. `diagnostico_rede`: retornar `DiagnosticoRede(..., pppoe_login=res.pppoe)` no
   caminho encontrado (e `pppoe_login=None`/`res.pppoe` no não-encontrado, igual
   `status_rede` faz).
4. `api/v1/rede.py` `diagnostico_out`: mapear `pppoe_login=diag.pppoe_login` nos
   dois ramos.
5. Dashboard: `RedeDiagnostico` (types.ts) ganha `pppoe_login: string | null`; o
   `conversa-rede-panel.tsx` mostra "PPPoE: {d.pppoe_login}" (perto do sinal).

O endpoint da conversa (`/conversas/{id}/rede/diagnostico`) reusa o mesmo
`diagnostico_out` → herda o campo automaticamente.

## Parte B — bot triagem de rede

### Tool nova `tools/consultar_rede.py`
Segue o padrão `@tool` (igual `tools/consultar_manutencoes.py`). Recebe
`ToolContext` (tem `session`, `cliente`, `sgp_cache`). Monta `RedeService` a partir
do ctx + um `GenieAcsClient` novo (mesma receita de `api/v1/rede.py:get_rede_service`,
mas usando `ctx.session`/`ctx.sgp_cache`). CPF de `decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)`.

- Sem parâmetros (ou um `tipo` opcional, default = resumo completo).
- Se `ctx.cliente is None` → `{"encontrada": False, "motivo": "cliente_nao_identificado"}`.
- Caso ok, chama `diagnostico_rede(cpf)` e retorna estruturado:
  ```python
  {
    "encontrada": True,
    "online": d.online,
    "aparelhos_conectados": len(d.aparelhos),
    "sinal": {
        "rx_power": d.sinal.rx_power if d.sinal else None,
        "qualidade": qualidade_sinal(d.sinal.rx_power if d.sinal else None)[0],
        "emoji": qualidade_sinal(...)[1],
    },
  }
  ```
  (`encontrada=False` quando sem ONU; erro técnico do GenieACS → retorno amigável,
  não exceção que quebra o loop do LLM — capturar `GenieAcsUnavailableError` e
  retornar `{"erro": "indisponivel"}`.)
- Import em `tools/__init__.py` (auto-discovery).

### System prompt (`services/llm_loop.py`)
Adicionar instrução (após o bloco de identificação do cliente):
*"Se o cliente reclamar de internet lenta/instável/caindo E já estiver
identificado: use a tool `consultar_rede`. Reporte de forma NATURAL quantos
aparelhos estão conectados e a qualidade do sinal. Se a qualidade for 'critico'
(🔴), explique que provavelmente é o sinal da fibra e OFEREÇA abrir um chamado
técnico — só chame `abrir_ordem_servico` se o cliente CONFIRMAR. Se muitos
aparelhos conectados, comente que pode ser congestionamento da rede do cliente.
Nunca mostre os campos crus (rx_power etc.) — traduza pra linguagem do cliente."*

(Se o canal usar `PromptVariant` no DB, a instrução entra na variante ativa; senão
no `SYSTEM_PROMPT` hardcoded. Decidir na implementação conforme o estado do prompt
em produção — o plano vai checar.)

## Parte C — sinal na OS

### Modelo + migração
`OrdemServico` (`db/models/business.py`) ganha:
```python
sinal: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```
Snapshot: `{"rx_power": float|None, "tx_power": float|None, "status_gpon": str|None, "qualidade": str}`.
Migração nova (próximo número após 0046).

### Captura na criação (best-effort, server-side)
Helper compartilhado em `services/rede_service.py` (módulo-level):
```python
async def snapshot_sinal(rede: RedeService, cpf: str) -> dict | None:
    try:
        diag = await rede.diagnostico_rede(cpf)
    except GenieAcsUnavailableError:
        return None
    if not diag.encontrada or diag.device is None or diag.device.sinal is None:
        return None
    s = diag.device.sinal
    return {
        "rx_power": s.rx_power, "tx_power": s.tx_power,
        "status_gpon": s.status_gpon, "qualidade": qualidade_sinal(s.rx_power)[0],
    }
```
- **`abrir_ordem_servico` tool:** ao criar, se `ctx.cliente` tem cpf, captura o
  snapshot e grava no `sinal`. (Best-effort: falha não impede a OS.)
- **`POST /api/v1/os` (dashboard):** ao criar, resolve o cpf do `cliente_id` da OS
  (ou do body) e captura. Best-effort.
- O `OrdemServicoRepo.create` ganha um param `sinal: dict | None = None`.

### Notificação WhatsApp ao técnico
As duas rotas já montam e enviam a mensagem da OS pro técnico. Adicionar uma linha
quando `sinal` presente:
`📶 Sinal: {emoji} {rx_power} dBm` (emoji de `qualidade_sinal`). Quando `sinal`
nulo, omite a linha (não polui).

### App técnico (Flutter, `tecnico-mobile`)
- `OsOut` (schema) ganha `sinal` (objeto opcional); o model Dart da OS idem.
- A tela de detalhe da OS mostra, quando há sinal, uma linha com **bolinha colorida
  + "{rx_power} dBm"** (helper `_corSinal` espelhando as faixas do backend, ou
  lendo `qualidade`).
- Exige rebuild/redistribuição do app técnico (Watchtower não atualiza apps).

## Edge cases
- Cliente sem ONU → tool `encontrada=false` (bot não inventa); OS sem sinal.
- Sinal `null` (dança do refresh) → bot reporta só aparelhos; snapshot grava
  `qualidade="desconhecido"` ou `sinal=null` (sem sinal útil → null).
- GenieACS fora → tool retorna `{"erro":"indisponivel"}`; OS criada sem sinal.
- Bot só abre OS com confirmação do cliente (fluxo existente do `abrir_ordem_servico`).

## Testes
**Backend:** `qualidade_sinal` (todas as faixas + null); tool `consultar_rede`
(encontrada / sem-cliente / GenieACS-fora); `snapshot_sinal` (best-effort: retorna
None quando indisponível/sem ONU); `pppoe_login` no diagnostico (4-file change);
captura de sinal no `POST /os` e no tool `abrir_ordem_servico` (grava snapshot;
falha do GenieACS não bloqueia a OS); linha de sinal na notificação; migração.
**Dashboard:** typecheck (pppoe no painel).
**Flutter:** analyze + rebuild (sinal na tela da OS).

## Fora de escopo (fatias futuras)
Lista proativa "clientes com sinal ruim"; auto-OS sem confirmação; histórico de
sinal por OS ao longo do tempo; alertas proativos de degradação.
