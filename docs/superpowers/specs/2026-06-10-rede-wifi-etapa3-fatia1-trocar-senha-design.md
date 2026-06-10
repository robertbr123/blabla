# Rede WiFi — Etapa 3, Fatia 1: Trocar senha do WiFi (app técnico)

**Data:** 2026-06-10
**Status:** Design aprovado — aguardando spec review → plano
**Autor:** Robert + Claude
**Contexto macro:** `docs/superpowers/specs/2026-06-07-autoatendimento-rede-wifi-spike-genieacs-design.md` (arquitetura 1 backend → 3 frontends) + spike concluído (GenieACS no ar, write provado nas 2 bandas).

---

## 1. O que esta fatia entrega

Primeira fatia vertical do backend TR-069: **o técnico, durante uma instalação/visita, troca a senha do WiFi do cliente pelo app** — ponta a ponta (adapter GenieACS → service → endpoint → tela no app técnico). É a superfície de menor risco (uso interno, técnico fisicamente na frente da ONU).

Não é "o backend inteiro": é a fatia mais fina que entrega valor real e valida o fluxo do reboot no mundo real. As demais features e superfícies vêm em fatias seguintes (§9).

## 2. Decisões (tomadas no brainstorming 2026-06-10)

| Decisão | Escolha | Por quê |
|---|---|---|
| Escopo do 1º PR | Fatia vertical: trocar senha, app técnico | Testável de verdade rápido; menor risco |
| Reboot/bandas | **Senha única 2.4+5G + reboot automático** | É o que o cliente entende por "senha do WiFi"; no técnico o reboot é indolor (cliente ainda não usa a net) |
| Confirmação | **Otimista + registro do pedido** | A passphrase é **write-only** (GET volta vazio) → impossível confirmar a senha por read-back; o técnico confirma conectando |
| Chave cliente→ONU | **PPPoE + fallback serial** | PPPoE é a chave do §3.7 (serve as 3 superfícies); serial garante que o técnico nunca trava na instalação |

### Achados do spike que moldam o design (memória `rede_wifi_genieacs`)
- **2.4GHz aplica a senha direto** via `SetParameterValues`; **5GHz só aplica após reboot** da ONU (confirmado no AX1800). → trocar senha = Set(2.4) + Set(5G) + **Reboot**.
- **"Sem fault" ≠ "aplicou"**: o GenieACS aceita o Set sem fault, mas o rádio pode não propagar. Combinado com passphrase write-only → não há confirmação programática da senha. Decisão: otimista.
- **Mapa de paths é por modelo+banda**: o AX1800 usa `...WLANConfiguration.{i}.KeyPassphrase`; fallback `...PreSharedKey.1.KeyPassphrase`. Parque é misto (vários modelos/marcas) → mapa extensível.

## 3. Fluxo de ponta a ponta

```
App técnico (dentro de uma OS) → tela "Rede do cliente"
  GET  /api/v1/rede/{contrato_id}              → status da ONU (online?, modelo, redes ativas)
  POST /api/v1/rede/{contrato_id}/wifi/senha   → { senha, serial? }
        │
   RedeService.trocar_senha_wifi():
        ├─ resolve ONU:  pppoe_login (SGP cache do contrato) → GenieAcsClient.find_device_by_pppoe()
        │                 └ não achou e veio serial → GenieAcsClient.find_device_by_serial()
        │                 └ não achou e sem serial → 404 { motivo: "onu_nao_encontrada" }
        ├─ valida senha: WPA-PSK 8–63 chars ASCII → senão 422
        ├─ monta plano:  instâncias WLAN com Enable=true + path de senha do modelo
        ├─ envia (NBI):  SetParameterValues(senha em cada instância ativa) + Reboot
        └─ registra:     RedeWifiPedido (contrato, pppoe, device, ator, status=enviado)
  → 200 { status:"enviado", device_id, reiniciando:true, aviso:"A ONU vai reiniciar e voltar em ~2 min" }
```

Tudo **síncrono** no request — os POSTs no NBI são rápidos (a aplicação real acontece depois, no inform/reboot da ONU). **Sem worker Celery** nesta fatia (coerente com "otimista, sem polling").

**Por que setar a senha em todas as instâncias `Enable=true`** em vez de classificar banda: cobre 2.4+5G (e qualquer rede ativa) com a mesma senha de forma robusta, sem depender de detectar perfeitamente qual instância é 2.4 vs 5G. As instâncias desativadas (no AX1800 do teste: CTC-*, AP-*) são ignoradas.

## 4. Componentes novos (seguindo padrões existentes do `apps/api`)

### 4.1 Adapter — `adapters/genieacs/`
Molde: `adapters/sgp/base.py` + `ondeline.py` (classe HTTP long-lived, exceção própria, DTOs frozen).
- **`base.py`**: `GenieAcsUnavailableError(RuntimeError)`; DTOs frozen `GenieAcsDevice` (device_id, fabricante, modelo, serial, `last_inform: datetime|None`, `online: bool`, `redes: list[RedeWlan]`) e `RedeWlan` (instancia: int, ssid, enabled).
- **`client.py`**: `GenieAcsClient(base_url, timeout, ...)` com `httpx.AsyncClient`:
  - `find_device_by_pppoe(login) -> GenieAcsDevice | None` — query no NBI pelo parâmetro Username do WANPPPConnection.
  - `find_device_by_serial(serial) -> GenieAcsDevice | None`.
  - `get_device(device_id) -> GenieAcsDevice | None`.
  - `set_parameter_values(device_id, params: list[tuple[str,str,str]]) -> None` (POST `/devices/{id}/tasks`).
  - `reboot(device_id) -> None` (POST task `{"name":"reboot"}`).
  - `aclose()`.
  - Erros: `httpx.HTTPError`/status≠2xx → `GenieAcsUnavailableError`.
- **`wifi_paths.py`**: mapa **modelo → perfil WiFi**:
  - `AX1800`: `passphrase_param="KeyPassphrase"`, `passphrase_fallback="PreSharedKey.1.KeyPassphrase"`, `needs_reboot=True`.
  - `__default__` (TR-098): igual ao AX1800 (KeyPassphrase + fallback), `needs_reboot=True` (conservador).
  - `resolve_plano(device, nova_senha) -> PlanoTrocaSenha` (lista de `(path, valor, tipo)` por instância ativa + `needs_reboot`).
  - `online`: `last_inform` dentro de ~2× o intervalo de inform (ex.: últimos 10 min).

### 4.2 Service — `services/rede_service.py`
Molde: `services/sgp_cache.py` (injeção de deps). `RedeService(session, genieacs_client, sgp_cache)`:
- `status_rede(contrato_id) -> StatusRede` (resolve ONU + monta status).
- `trocar_senha_wifi(*, contrato_id, nova_senha, serial=None, ator_user_id) -> ResultadoTroca`.
- Resolve `pppoe_login` do contrato via SGP cache (por CPF/contrato) → `find_device_by_pppoe`; fallback serial.
- Valida senha (8–63 ASCII). Monta plano (wifi_paths). Envia Set+Reboot. Registra `RedeWifiPedido`.

### 4.3 Modelo — `db/models/` + migração alembic
Tabela **`rede_wifi_pedido`** (auditoria + base pro app cliente depois):
- `id` UUID PK, `contrato_id` str, `pppoe_login` str|null, `device_id` str, `ator_user_id` UUID FK users,
- `status` str (`enviado` por ora; futuro: `confirmado`/`falhou`), `reiniciou` bool, `created_at` timestamptz default now.
- **NÃO armazena a senha** (nem hash) — auditoria é "quem trocou a senha de qual ONU e quando", não o segredo.

### 4.4 Endpoints — `api/v1/rede.py` + `api/schemas/rede.py`
Molde: `api/v1/ordens_servico.py`. `router = APIRouter(prefix="/api/v1/rede", tags=["rede"])`, registrado em `main.py`.
- `GET /api/v1/rede/{contrato_id}` — `dependencies=[require_role(TECNICO, ADMIN)]`. Resposta: status da ONU (online, modelo, redes ativas) ou `{ onu: null, motivo, pppoe_login }` quando não resolveu por PPPoE.
- `POST /api/v1/rede/{contrato_id}/wifi/senha` — idem role. Body `{ senha: str, serial: str|None }`. Resposta `{ status, device_id, reiniciando, aviso }`. Erros: 404 (ONU não encontrada), 422 (senha inválida), 503 (`GenieAcsUnavailableError`).

### 4.5 Config — `config.py`
- `genieacs_url: str = "http://genieacs-nbi:7557"` (rede docker interna), `genieacs_user: str = ""`, `genieacs_password: str = ""` (NBI sem auth no MVP; campos prontos pra futuro).

## 5. App técnico (`apps/tecnico-mobile`)
Tela **"Rede do cliente"**, acessível a partir da OS/cliente (segue padrões de tela/estado do app — ver memória `flutter_app_state`):
- Card de status: 🟢 online / ⚫ offline, modelo da ONU, redes WiFi ativas (SSIDs).
- Campo "nova senha" + confirmar senha; validação local (8–63).
- Botão **Trocar senha do WiFi** com aviso: *"A internet do cliente vai reiniciar e voltar em ~2 min."*
- Estado de envio → sucesso ("Senha enviada. A ONU está reiniciando."), com instrução pro técnico testar conectando.
- Se a ONU não foi achada por PPPoE (`onu: null`): campo/scan do **serial** da etiqueta e reenvio.
- Offline: ações desabilitadas + "Aparelho offline, tente quando voltar."

## 6. Escopo

**Dentro:** trocar senha (2.4+5G, mesma senha) + reboot; status online/offline + modelo + redes ativas; resolução PPPoE com fallback serial; registro do pedido; tela no app técnico; testes.

**Fora (próximas fatias — §9):** ver aparelhos conectados; trocar nome do SSID; dashboard; app cliente; STUN/TLS/auth-por-ONU; confirmação automática; mapa de paths para outros modelos além do AX1800/default.

## 7. Dependências operacionais (fora do código — Robert, na VPS)
1. **Rede docker**: `blabla-api` precisa alcançar `blabla-genieacs-nbi:7557` (mesma rede docker do compose). Confirmar/ajustar no `docker-compose.prod.yml`.
2. **Firewall na 7547** (cwmp público): restringir às faixas de IP das ONUs antes da base real (`iptables -I DOCKER-USER`); scanner já se registrou no ACS. Apagar device fake `DISCOVERYSERVICE-*`.
3. **Provisionamento** (só quando for além da ONU de teste): garantir Periodic Inform ativo nas ONUs e que o PPPoE Username seja lido pelo GenieACS.

## 8. Riscos / itens a confirmar na implementação
- **Path do PPPoE Username no AX1800**: confirmar o caminho TR-069 exato do `WANPPPConnection.*.Username` (Robert tem o device; um GET no NBI resolve). Fallback serial cobre enquanto não confirmado.
- **Formato da query do NBI** por parâmetro aninhado (`...Username._value`) e índice da instância WANPPPConnection variável por modelo.
- **`__default__` com `needs_reboot=True`** é conservador (reinicia sempre). Quando outros modelos forem mapeados, ajustar quais aplicam sem reboot.

## 9. ROADMAP das próximas fatias (LEMBRETE — não esquecer)

Ordem por menor risco (§3.6 do design macro: técnico → dashboard → cliente):

- **Fatia 1 (ESTA):** Trocar senha WiFi — **app técnico**. Backend (adapter+service+endpoint+tabela) + tela técnico.
- **Fatia 2:** **Ver aparelhos conectados** — app técnico. Reusa o `GenieAcsClient` (refreshObject da tabela Hosts + leitura nome/IP/MAC/ativo) + tela de lista. Baixo risco, sem reboot.
- **Fatia 3:** Levar **senha + aparelhos pro Dashboard** (admin/atendente). Reusa os mesmos endpoints; nova UI no dashboard Next.js; permissão de staff.
- **Fatia 4:** Levar pro **App cliente** (tela "Minha Rede" na feature `conexao`). Aqui a UX do reboot precisa de cuidado (cliente está usando a internet) — confirmação explícita + a base de "registro do pedido" da Fatia 1 ajuda. Por ser exposto ao público, caprichar (rate limit, só a própria ONU).
- **Fatia 5 (hardening pré-base real):** firewall 7547 + TLS no cwmp + auth por ONU + STUN (aplicar instantâneo, dispensa reboot-espera) + provisionamento da base apontar pro ACS + mapa de paths pra mais modelos do parque misto. Avaliar confirmação automática (detectar volta do reboot) se necessária no fluxo do cliente.

**Features futuras destravadas pela ponte** (não planejadas como fatias ainda): trocar nome do SSID, reboot remoto exposto, diagnóstico de sinal óptico, gestão de firmware.

## 10. Testes
- **Adapter**: `respx` mockando o NBI (find_by_pppoe, set_parameter_values, reboot, erro→`GenieAcsUnavailableError`). Molde: `tests/test_sgp_ondeline.py`.
- **wifi_paths**: unit puro (resolução de instâncias ativas + plano + fallback de path).
- **Service**: client fake (sem rede) — resolve PPPoE→serial, valida senha, registra pedido.
- **Endpoint**: httpx ASGI + role TECNICO/ADMIN (200, 404 sem ONU, 422 senha inválida, 503 GenieACS down). Molde: `tests/test_v1_ordens_servico.py`.
- **Flutter**: conforme padrão do app técnico.
