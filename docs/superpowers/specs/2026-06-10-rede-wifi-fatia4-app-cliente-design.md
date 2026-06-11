# Rede WiFi — Fatia 4: app do CLIENTE trocar a própria senha

**Data:** 2026-06-10
**Status:** Design aprovado, pronto pra plano de implementação
**Relacionado:** `2026-06-10-rede-wifi-etapa3-fatia1-trocar-senha-design.md` (Fatia 1 — app técnico), memória `rede-wifi-genieacs`, `rede-wifi-roadmap`

## Objetivo

Permitir que o **cliente final** troque a senha do WiFi da própria casa pelo app, com uma
tela bonita seguindo o padrão visual do app. Quando o roteador do cliente ainda não está
gerenciado pelo GenieACS, mostrar uma tela amigável de "em construção" (funcionalidade
chegando), em vez de erro.

É a Fatia 4 do roadmap de rede WiFi. O backend (`RedeService`, GenieACS, tabela
`rede_wifi_pedido`) já existe da Fatia 1; o trabalho aqui é **expor pro cliente com segurança**
+ **a tela Flutter**.

## Contexto que torna isso possível

- `RedeService.trocar_senha_wifi(cpf, nova_senha, serial, ator_user_id)` e
  `RedeService.status_rede(cpf, serial)` já existem e estão validados em produção.
- `get_rede_service` (em `api/v1/rede.py`) monta GenieACS + SgpRouter + SgpCacheService e
  **não força role** (o `require_role(TECNICO, ADMIN)` fica nas rotas, não na dependency) →
  pode ser reusado tal qual pelo cliente.
- O CPF do cliente logado sai de `decrypt_pii(user.cpf_encrypted)` (igual `cliente_app_conexao`
  já faz), com `user = Depends(get_current_cliente_user)`.
- `rede_wifi_pedido` tem `cpf_hash` **indexado** → cooldown é uma query barata.
- `status_rede` devolve `encontrada=False` quando não acha ONU pra aquele CPF → é o gatilho
  natural da tela "em construção".

## Decisões (alinhadas com o Robert)

1. **Ponto de entrada:** card de ação rápida na **Home** + botão "Gerenciar rede WiFi" dentro
   da tela **Conexão** ("Status da conexão"). **Mantém as 4 tabs** da navbar (não vira 5ª tab).
2. **Reboot:** trocar **senha única nas 2 bandas** (igual técnico) + **avisar e pedir
   confirmação** antes (cliente fica ~2 min offline) + estado visual de "reconectando" depois.
3. **Rate limit:** **cooldown simples no backend** — 1 troca a cada 5 min por `cpf_hash`,
   usando a `rede_wifi_pedido` que já registra cada troca. App mostra "aguarde X min".
4. **Segurança/LGPD:** CPF **nunca** vai no body do cliente — derivado do token. Senha nunca
   logada nem persistida (o modelo já não guarda a senha).

## Arquitetura

Endpoints **novos e exclusivos do cliente** sob `/api/v1/cliente-app/rede/*`, autenticados com
`get_current_cliente_user`, que derivam o CPF do token e reusam `RedeService`/`get_rede_service`.
Frontend novo em `lib/features/rede/`, padrão visual do `conexao_screen` (hero gradient + cards
`BrandTokens`).

```
Home (card) ─┐
Conexão (botão) ─┴─> /rede (RedeScreen)
                         │
                         ├─ GET  /api/v1/cliente-app/rede/status        -> status_rede(cpf_do_token)
                         └─ POST /api/v1/cliente-app/rede/wifi/senha     -> cooldown + trocar_senha_wifi(...)
```

## Backend

### `api/v1/cliente_app_rede.py` (novo)

Router `prefix="/api/v1/cliente-app/rede"`, `tags=["cliente-app:rede"]`, auth de cliente.

- **`GET /status?contrato_id=`**
  - `cpf = decrypt_pii(user.cpf_encrypted)`.
  - `st = await service.status_rede(cpf)`.
  - Resposta enxuta pro cliente (sem device_id/internals): `{encontrada, online, modelo, redes:[{ssid}]}`.
  - `encontrada=False` → app mostra "em construção".
  - `contrato_id` opcional repassado pro futuro (hoje o service itera os contratos por CPF).

- **`POST /wifi/senha`** body `{senha, contrato_id?}` (**sem cpf**):
  1. **Cooldown:** contar `rede_wifi_pedido` com `cpf_hash == <hash do cpf>` e
     `created_at > now() - 5min`. Se houver, `429` com `{detail, minutos_restantes}`.
     (Usar o **mesmo helper de hash** que o `RedeService` usa pra escrever `cpf_hash`, pra a
     query bater.)
  2. `res = await service.trocar_senha_wifi(cpf=cpf, nova_senha=senha, ator_user_id=user.id)`.
  3. Retorna `{status:"enviado", reiniciando: res.reiniciando, aviso}`.
  - Erros: `SenhaInvalidaError`→422, `OnuNaoEncontradaError`→404, `GenieAcsUnavailableError`→503.

### Schemas — `api/schemas/cliente_app_rede.py` (novo)

- `RedeClienteStatusOut { encontrada: bool, online: bool, modelo: str|None, redes: list[{ssid: str}] }`
- `TrocarSenhaClienteIn { senha: str (8..63), contrato_id: str|None }`  ← **sem cpf**
- `TrocarSenhaClienteOut { status: str, reiniciando: bool, aviso: str }`

### `ator_user_id`

`rede_wifi_pedido.ator_user_id` é `UUID not null` **sem FK** (verificar na implementação). Pro
self-service, passar o `ClienteAppUser.id`. Confirmar que `ClienteAppUser.id` é UUID; se não for,
ajustar (coluna nullable + flag de origem cliente, ou coluna `ator_tipo`). Decisão de
implementação, não bloqueia o design.

### Constante

`COOLDOWN_TROCA = 5 min` (configurável depois; começa hardcoded).

## Frontend — `lib/features/rede/`

### `rede_repository.dart`
- `RedeRepository`: `Future<RedeStatusDto> status({String? contratoId})`,
  `Future<TrocaResultDto> trocarSenha(String senha, {String? contratoId})`.
- DTOs: `RedeStatusDto { encontrada, online, modelo, redes:[RedeWifi{ssid}] }`,
  `TrocaResultDto { status, reiniciando, aviso }`.
- `redeStatusProvider` (FutureProvider) observa `contratoAtualProvider` (multi-contrato), igual
  `conexaoProvider`.
- Mapear `429` num erro tipado (`CooldownError { minutosRestantes }`) pra UI mostrar a mensagem.

### `rede_screen.dart` — "Minha Rede WiFi"

`Scaffold` + `AppBar('Minha Rede WiFi')`, `RefreshIndicator`, 3 estados via `async.when`:

1. **Carregando** → `CircularProgressIndicator`.
2. **Sem ONU (`encontrada == false`)** → tela "em construção":
   - Ícone WiFi grande, título "Gerenciamento do WiFi a caminho 🛠️".
   - Texto: "Estamos preparando o controle do seu WiFi por aqui. Em breve você vai poder trocar
     a senha da sua rede direto pelo app." (copy final ajustável).
   - Botão "Voltar". Sem campo de senha.
3. **Com ONU (`encontrada == true`)**:
   - **Hero card** (gradient, padrão `_StatusHero`): ícone WiFi + nome da rede (SSID) + pill
     "online/offline".
   - **Card de troca**: campo "Nova senha" + "Confirmar senha", validação **8–63 caracteres**,
     ícone olho mostrar/ocultar, mensagens de erro inline (senhas diferentes / curta demais).
   - Botão "Trocar senha do WiFi".

### Fluxo da troca
1. Tap em "Trocar senha do WiFi" (com senha válida) → **bottom sheet de confirmação**:
   - Ícone de aviso + "Sua internet vai **reiniciar** e voltar em **cerca de 2 minutos**."
   - "Depois, reconecte seus aparelhos (celular, TV, etc.) usando a nova senha."
   - Botões "Cancelar" / "Trocar agora".
2. Confirma → chama `trocarSenha` → **estado "reconectando"**: card com contador (~2 min) +
   dica "Reconectando sua rede… seus aparelhos vão pedir a nova senha."
3. Sucesso → estado final "Senha trocada! ✅ Use a nova senha pra reconectar seus aparelhos."
4. `CooldownError` → snackbar "Você trocou a senha há pouco. Aguarde ~X min pra trocar de novo."
5. Erro genérico/503 → snackbar "Não conseguimos trocar agora. Tente mais tarde."

### Pontos de entrada
- **Home**: ação rápida / card "Minha Rede WiFi" (ícone wifi, cor própria) → `context.push('/rede')`.
- **Conexão** (`conexao_screen.dart`): botão "Gerenciar rede WiFi" quando `status == 'ativo'`
  (perto do `_DicaPanel`).
- **Router**: `GoRoute(path: '/rede', builder: (_, __) => const RedeScreen())`.

## Segurança / LGPD

- CPF derivado do token, **nunca** no body do cliente.
- Senha **nunca** logada nem persistida (modelo já não guarda).
- Cooldown corta flood de reboots (cada troca derruba a ONU).
- Só a **própria** ONU do cliente (a resolução é por CPF→SGP→pppoe do próprio token).

## Fora de escopo (Fatia 5 / futuro)

- Ver aparelhos conectados, sinal óptico (Fatia 2/3).
- Aplicar **instantâneo** (STUN) — hoje aplica no próximo inform/reboot.
- **Hardening pré-base real (Fatia 5, CRÍTICO):** TLS no cwmp + auth por ONU + firewall na
  7547 + provisionamento da base em massa + mapa de paths pra mais modelos de ONU.
- Trocar nome do SSID, banda/canal, firmware.

## Testes

- **Backend:** `/status` encontrado vs não-encontrado; `/wifi/senha` sucesso; cooldown `429`;
  exige auth de cliente (sem token → 401); CPF derivado do token (não aceita cpf no body).
- **Flutter:** smoke dos 3 estados da tela — fica pro teste no deploy (sem stack local, conforme
  fluxo do Robert).

## Dependências de infra

- `blabla-api` precisa alcançar `blabla-genieacs-nbi:7557` (mesma rede docker) — já vale da Fatia 1.
- Antes de apontar a **base real** de clientes: **Fatia 5** (hardening) é pré-requisito.
