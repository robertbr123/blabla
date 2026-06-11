# Rede WiFi — Fatia 3: Rede do cliente dentro da conversa (dashboard / suporte)

**Data:** 2026-06-11
**App alvo:** dashboard Next.js (admin / atendente / técnico)
**Depende de:** Fatia 2 (`RedeService.diagnostico_rede`, `GenieAcsClient`, schemas) — reusa o backend inteiro.

## Objetivo

Dar ao **atendente de suporte**, dentro da conversa de WhatsApp que ele já está
atendendo, uma visão e controle da rede do cliente:

- **Ver** se a ONU está online, o sinal da fibra (RX/TX/status GPON), a conexão
  PPPoE, o IP externo, o uptime e os aparelhos conectados.
- **Agir:** trocar a senha do WiFi e reiniciar a ONU (com confirmação e aviso de
  ~2min offline).

Tudo a partir do cliente **vinculado à conversa** — o atendente nunca digita CPF.

## Decisões (do brainstorming)

- **Permissão:** atendente tem **acesso total** (ver + trocar senha + reboot), com
  confirmação na UI + aviso de ~2min + auditoria do ator. Abre a capacidade de
  rede pro papel ATENDENTE (hoje os `/api/v1/rede/*` são só TÉCNICO/ADMIN).
- **Superfície da API = endpoints escopados por conversa** (`/api/v1/conversas/{id}/rede/*`).
  O CPF é derivado server-side do `conversa.cliente_id` → `Cliente` → decrypt.
  O atendente **nunca manda CPF** (LGPD: só age no cliente daquela conversa, não
  em CPF arbitrário). Os `/api/v1/rede/*` atuais (CPF no body, TÉCNICO/ADMIN) ficam
  **intactos** — técnico-mobile não muda.
- **"Colar diagnóstico na conversa" = pré-preenche a caixa de resposta** (draft
  editável), não auto-envia — o atendente revisa antes de mandar pro cliente.
- **Auditoria de reboot:** coluna nova `tipo` em `rede_wifi_pedido`
  (`'senha'|'reboot'`, default `'senha'`). Auditoria unificada e PII-safe.
- **Sem cooldown pra staff** (diferente do app cliente da Fatia 4) — confiança +
  auditoria do ator bastam.

## Escopo desta fatia

**Inclui:** painel de rede na conversa (ver + trocar senha + reboot) + selo de
saúde no header + botão "colar diagnóstico na conversa".

**Fora de escopo (fatias próprias depois):** auto-triagem por LLM, abrir OS
automática por sinal crítico, lista proativa "clientes com sinal ruim".

## Arquitetura

```
conversa-chat.tsx
   ├─ header: selo de saúde (🟢 online + cor do sinal quando disponível)
   └─ aba "Rede" → conversa-rede-panel.tsx
        ├─ GET  /api/v1/conversas/{id}/rede/status       (selo: online, leve, sem refresh)
        ├─ GET  /api/v1/conversas/{id}/rede/diagnostico   (painel: aparelhos+sinal, dispara refresh)
        ├─ POST /api/v1/conversas/{id}/rede/wifi/senha     body {senha}
        └─ POST /api/v1/conversas/{id}/rede/reboot
                       │ cada endpoint:
                       │   conversa_id → Conversa.cliente_id → Cliente → decrypt(cpf_cnpj)
                       │   (cliente_id nulo → 409 "conversa sem cliente vinculado")
                       └─ RedeService (Fatia 2, reusado)
```

## Backend

### Novo: `api/v1/conversas_rede.py`
Sub-router `prefix="/api/v1/conversas"`, `dependencies=[require_role(Role.ADMIN, Role.ATENDENTE, Role.TECNICO)]`.

Helper de resolução (reusa o padrão de decrypt já usado pra montar o
`ClienteEmbutido` em `conversas.py`):

```python
class ConversaSemClienteError(Exception): ...

async def _cpf_da_conversa(session: AsyncSession, conversa_id: UUID) -> str:
    conv = await session.get(Conversa, conversa_id)
    if conv is None:
        raise HTTPException(404, "conversa nao encontrada")
    if conv.cliente_id is None:
        raise ConversaSemClienteError()
    cli = await session.get(Cliente, conv.cliente_id)
    if cli is None or not cli.cpf_cnpj_encrypted:
        raise ConversaSemClienteError()
    return decrypt_pii(cli.cpf_cnpj_encrypted)
```

Os endpoints injetam o `RedeService` (via `get_rede_service`, igual `rede.py`),
resolvem o CPF e chamam o service. Mapeamento de erro:
- `ConversaSemClienteError` → **409** "conversa sem cliente vinculado"
- `GenieAcsUnavailableError` → 503
- `SenhaInvalidaError` → 422
- `OnuNaoEncontradaError` (na troca/reboot) → 404
- diagnostico/status com ONU não achada → 200 com `encontrada=false` (igual Fatia 2)

Endpoints:
- `GET  /{conversa_id}/rede/status` → `StatusRedeOut` (reusa `service.status_rede(cpf)`).
- `GET  /{conversa_id}/rede/diagnostico` → `DiagnosticoOut` (reusa `service.diagnostico_rede(cpf)`).
- `POST /{conversa_id}/rede/wifi/senha` body `TrocarSenhaConversaIn {senha}` → `TrocarSenhaOut` (reusa `service.trocar_senha_wifi(cpf, senha, serial=None, ator_user_id=user.id)`).
- `POST /{conversa_id}/rede/reboot` → `RebootOut` (novo `service.reiniciar_onu(...)`).

Registrar o router novo no app (onde os outros `api/v1/*` routers são incluídos).

### `services/rede_service.py` — método novo
```python
@dataclass(frozen=True, slots=True)
class ResultadoReboot:
    device_id: str

async def reiniciar_onu(
    self, *, cpf: str, serial: str | None, ator_user_id: UUID
) -> ResultadoReboot:
    cpf = _so_digitos(cpf)
    if not cpf:
        raise CpfInvalidoError("CPF invalido")
    res = await self._resolver_por_cpf(cpf, serial)
    if res.device is None:
        raise OnuNaoEncontradaError("ONU nao encontrada por PPPoE nem serial")
    pedido = RedeWifiPedido(
        cpf_hash=hash_pii(cpf), contrato_id=res.contrato_id, pppoe_login=res.pppoe,
        device_id=res.device.device_id, ator_user_id=ator_user_id,
        status="pendente", reiniciou=True, tipo="reboot",
    )
    self._session.add(pedido)
    await self._session.flush()
    await self._genie.reboot(res.device.device_id)
    pedido.status = "enviado"
    await self._session.flush()
    return ResultadoReboot(device_id=res.device.device_id)
```
(O `GenieProto` já tem `reboot`. Mesmo padrão de auditoria-antes-do-envio da troca de senha.)

### Migração — coluna `tipo` em `rede_wifi_pedido`
Nova migração Alembic: `tipo` `String`, `nullable=False`, `server_default="senha"`.
Atualizar o model `RedeWifiPedido` com `tipo: Mapped[str] = mapped_column(server_default="senha")`.
A troca de senha existente passa a setar `tipo="senha"` explicitamente (ou herda o default).

### Schemas (`api/schemas/`)
`TrocarSenhaConversaIn {senha: str = Field(min_length=8, max_length=63)}` e
`RebootOut {status: str, device_id: str, aviso: str}`. `StatusRedeOut`/`DiagnosticoOut`/
`TrocarSenhaOut` reusados da Fatia 2.

## Frontend (dashboard)

### `lib/api/queries.ts` — hooks novos
Padrão `apiFetch` + react-query (igual `useResponder`):
- `useRedeStatus(conversaId, enabled)` — `useQuery` GET `/conversas/{id}/rede/status`. `enabled` controla quando carrega (selo: ao abrir conversa só se tem cliente).
- `useRedeDiagnostico(conversaId, enabled)` — `useQuery` GET diagnostico, `enabled` quando a aba "Rede" abre (lazy, evita bater na ONU à toa).
- `useTrocarSenhaConversa(conversaId)` — `useMutation` POST wifi/senha, `toast` + invalida diagnostico/status.
- `useReiniciarOnu(conversaId)` — `useMutation` POST reboot, `toast`.

Tipos TS espelhando `StatusRedeOut`/`DiagnosticoOut`/`TrocarSenhaOut`/`RebootOut` em `lib/api/types.ts`.

### `components/conversa-rede-panel.tsx` (conteúdo da aba "Rede")
- Estados: conversa sem cliente (409) → "Vincule o cliente pra ver a rede"; `encontrada=false` → "Cliente sem equipamento gerenciável" (sem botões); ONU ok → render completo.
- **Sinal:** cor por faixa de RX (porta os thresholds do Flutter `_corRx` pro TS — verde `-8..-25`, amarelo `-25..-27`, vermelho fora; cinza se null), TX, status GPON, conexão PPPoE, IP, uptime formatado, "última leitura". Null → "ainda não disponível, atualize em ~5min".
- **Aparelhos:** lista nome/IP/MAC (count no título).
- **Ações:** campo senha + botão "Trocar senha" + botão "Reiniciar ONU", cada um com dialog de confirmação + aviso "a internet do cliente reinicia e volta em ~2min".

### `components/conversa-chat.tsx`
- Adiciona a aba "Rede" na tab bar (visível pra staff logado — endpoints já liberam atendente).
- **Selo no header:** bolinha 🟢/⚪ online via `useRedeStatus` (carrega só se `data.cliente` existe). Ganha cor do sinal se o diagnóstico já tiver carregado.
- **"Colar diagnóstico na conversa":** botão (no painel) que gera o resumo textual e **pré-preenche o estado da caixa de resposta** (o input que o `useResponder` envia) — o atendente edita e envia. Não cria endpoint novo.

### Helper de resumo (TS)
Função pura `resumoDiagnostico(d: Diagnostico): string` que monta a frase amigável
a partir de sinal + uptime + nº de aparelhos (ex: "Sinal ótimo (-13 dBm), conexão
estável há 1d 21h, 7 aparelhos conectados.").

## Edge cases
- Conversa sem cliente vinculado → 409 → mensagem amigável; selo escondido.
- Cliente sem ONU no GenieACS → 200 `encontrada=false` → sem botões de ação.
- Sinal null (dança do refresh) → "ainda não disponível, atualize em ~5min".
- GenieACS fora → 503 → toast.
- Troca de senha / reboot → confirmação + aviso de ~2min (reusa `AVISO_REBOOT`).

## Testes
**Backend:**
- `conversas_rede`: role inclui ATENDENTE (atendente 200, não 403); resolução
  conversa→cliente→cpf; **409** quando `cliente_id` nulo; troca de senha e reboot
  chamam o service com o CPF derivado e `ator_user_id` do token; reboot grava
  `tipo='reboot'` na `rede_wifi_pedido`.
- `rede_service.reiniciar_onu`: resolve, chama `reboot`, audita (`tipo='reboot'`,
  status enviado), `OnuNaoEncontradaError` quando sem device.
- Migração aplica (CI roda `alembic upgrade head`).

**Dashboard:** typecheck + build (padrão do projeto; sem testes de componente novos).

## Fora de escopo
Auto-triagem por LLM, abertura automática de OS por sinal crítico, lista proativa
de clientes com sinal ruim — cada uma vira sua fatia depois.
