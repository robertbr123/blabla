# Cliente Mobile App — Design

**Data:** 2026-05-21
**Status:** Aprovado, pronto pra planejamento
**Escopo:** Novo app Flutter para o **cliente final** da Ondeline Telecom — consulta de plano, 2ª via de faturas, abertura de OS e chat in-app integrado ao sistema de conversas.

---

## 1. Objetivo

Dar ao cliente final um canal nativo, autônomo e bonito pra resolver o que hoje só rola via WhatsApp/atendente: ver plano, puxar fatura (PIX/boleto), abrir chamado e conversar com o suporte. App é a "cara da empresa" pro cliente — identidade visual fintech-style (Nubank/Inter), separado do app do técnico.

## 2. Arquitetura geral

- **Novo app Flutter** em `apps/cliente-mobile/`, separado de `tecnico-mobile`. Stack base igual (Riverpod, go_router, Dio, FCM, secure_storage), mas SEM GPS/câmera/Drift pesado.
- **Backend** no mesmo `apps/api/`: novo router `/api/v1/cliente-app/*` com **JWT próprio** (`audience=cliente`). Middleware distingue tokens staff vs cliente — endpoints staff **nunca** aceitam token de cliente e vice-versa.
- **Reaproveita:** SGP adapter (planos, títulos, boletos), Evolution (OTP WhatsApp), sistema de conversas (chat como `channel=app`), FCM.
- **App separado e não tab no técnico** porque: publicação distinta nas stores, identidade visual diferente e dependências divergem.

## 3. Autenticação

- **CPF + senha** com OTP via WhatsApp no primeiro acesso.
- Fluxo de cadastro: CPF → validação no SGP → OTP no telefone cadastrado no SGP → cria senha → biometria opcional → home.
- JWT TTL 30 dias com refresh, audience=`cliente`.
- Rate-limit Redis em `/auth/*`: 5 OTPs/hora por CPF, 10 logins/hora por IP.
- CPF nunca em logs — só `cpf_hash` (SHA-256) e `cpf_last4` pra UI.

## 4. Telas (4 tabs)

### Tab 1 — Home
Hero card com nome + plano vigente em destaque + status conexão + próximo vencimento (CTA "Pagar agora"). Quick actions em carrossel: 2ª via, falar conosco, sem internet, mudança de endereço. Card de uso/velocidade. Avisos administrativos.

### Tab 2 — Faturas
Lista de títulos (abertos primeiro, depois 12 meses pagos). Tap → bottom sheet com **PIX copia-e-cola**, **código de barras**, **boleto PDF**, **compartilhar**. Filtro por ano.

### Tab 3 — Suporte
Sub-tabs **Chat** e **Meus chamados**.
- **Chat:** bubbles estilo iMessage, anexo foto/áudio, bot LLM responde primeiro e escala humano na mesma thread.
- **Meus chamados:** lista de OS com status (aberto/agendado/em andamento/concluído), FAB "+ Novo chamado" abre wizard 3 steps (tipo → detalhes → confirma). Tipos: **sem internet/lenta**, **mudança de endereço**, **troca/upgrade de plano**. (Cancelamento fica fora do app — segue via humano.)

### Tab 4 — Perfil
Avatar, nome, plano resumido, editar tel/email (não CPF/endereço), notificações push por tipo, biometria, tema (claro/escuro/auto), mudar senha, sair.

### Onboarding (1º acesso)
Splash → CPF → OTP WhatsApp → criar senha → biometria opcional → home.

## 5. Modelo de dados (novas tabelas)

### `cliente_app_users`
```
id                uuid PK
cpf_hash          str UNIQUE          (SHA-256)
cpf_last4         str
sgp_id            str INDEX           (nullable até validar)
nome              str
telefone          str
email             str NULL
password_hash     str                 (bcrypt)
push_token        str NULL            (FCM)
biometric_enabled bool
last_login_at     timestamp
created_at        timestamp
status            enum(active|blocked|pending_otp)
```

### `cliente_app_otp` (curta vida, expira 10min)
```
cpf_hash, code_hash, expires_at, attempts, purpose (register|reset_pwd)
```

### `cliente_app_os`
```
id, cliente_app_user_id FK, tipo (suporte|mudanca|troca_plano),
descricao, payload_json,
status (aberto|agendado|em_andamento|concluido|cancelado),
sgp_protocolo_id NULL, atendente_user_id NULL,
created_at, updated_at
```

### Chat
Reaproveita `conversations` — `channel` ganha valor `app`. Novo campo `cliente_app_user_id` na conversa. Mensagens passam pelos workers atuais (bot LLM tool context entende canal).

### Migrations
- `0026_cliente_app_users.py` (Fase 1)
- `0027_cliente_app_os.py` (Fase 5)
- Ajuste em `conversations` pra `channel=app` (Fase 6)

## 6. Endpoints `/api/v1/cliente-app/*`

| Método | Path | Descrição |
|---|---|---|
| POST | `/auth/register/start` | CPF → busca SGP → manda OTP WhatsApp |
| POST | `/auth/register/verify` | CPF + OTP → cria user pending_pwd |
| POST | `/auth/register/password` | Define senha (token da etapa anterior) |
| POST | `/auth/login` | CPF + senha → JWT cliente |
| POST | `/auth/forgot` | Inicia reset de senha via OTP |
| GET | `/me` | Dados do user + plano resumido |
| GET | `/plano` | Plano completo SGP (cache Redis 15min) |
| GET | `/faturas?status=` | Lista títulos do SGP |
| GET | `/faturas/{titulo_id}/boleto` | Stream PDF (proxy SGP) |
| GET | `/faturas/{titulo_id}/pix` | Payload PIX copia-e-cola |
| GET | `/os` | Lista OS do cliente |
| POST | `/os` | Abre OS (body com tipo + dados específicos) |
| GET | `/chat/messages?cursor=` | Histórico paginado |
| POST | `/chat/send` | Envia mensagem (texto/foto/áudio) |
| POST | `/devices/fcm` | Registra/atualiza push token |
| GET | `/avisos` | Comunicados ativos |
| DELETE | `/me` | LGPD — soft delete + anonimização |

## 7. Segurança e LGPD

- JWT `audience=cliente` separado do staff. Middleware `require_cliente_user` distinto de `require_staff_user`.
- Endpoints staff **nunca** aceitam token cliente e vice-versa (testes de isolamento na Fase 1).
- CPF não trafega em logs — só hash + last4.
- Rate-limit Redis agressivo em `/auth/*`.
- `DELETE /me` obrigatório (LGPD) — anonimização: zera nome/tel/email/push_token, mantém `cpf_hash` placeholder e histórico de OS.
- Termos de uso + política de privacidade linkados na tela de criar senha.

## 8. Identidade visual

Estilo **fintech premium** (referências: Nubank, Inter, PicPay):
- Hero card grande com gradiente sutil, cantos arredondados 24px.
- Sombras suaves, microinterações em CTAs.
- Tipografia hierárquica forte (números grandes para valor da fatura).
- Dark mode bem feito (não só Material auto — paleta própria).
- Design tokens em `apps/cliente-mobile/lib/core/branding/`.
- Bottom nav com pill indicator, labels só nas tabs ativas.
- Haptic feedback em ações importantes (copiar PIX, abrir chamado).

## 9. Faseamento

Cada fase commitável e demonstrável. Push direto pra main. Sem feature flags eternas.

**Fase 1 — Fundação backend + auth cliente**
Migration `0026`, router `/auth/*`, JWT cliente, middleware, rate-limit, OTP via Evolution. Testes de isolamento de audience.

**Fase 2 — Scaffold app Flutter + onboarding**
`apps/cliente-mobile/` criado, tema fintech, design tokens, splash + onboarding 5 telas, login, biometria. Auth_service + secure_storage + Dio interceptor.
*Entregável:* APK instalável, cadastro completo até home placeholder.

**Fase 3 — Home + Plano + Perfil**
Endpoints `/me`, `/plano`, `/avisos`. Tab Home (hero + quick actions + avisos), Tab Perfil (editar, mudar senha, biometria, tema, sair). Cache curto (in-memory + SharedPreferences last-known).
*Entregável:* cliente vê plano e edita perfil.

**Fase 4 — Faturas**
Endpoints `/faturas`, `/faturas/{id}/boleto`, `/faturas/{id}/pix`. Tab Faturas: lista, filtros, bottom sheet PIX/boleto/share. Pull-to-refresh.
*Entregável:* cliente puxa 2ª via sozinho — já justifica o app.

**Fase 5 — Suporte: OS pelo cliente**
Migration `0027`, endpoints `/os` (lista + criar). Tab Suporte → sub-tab "Meus chamados" + wizard 3 steps. Webhook interno: nova OS gera conversa + opcional protocolo SGP. Push em mudança de status.
*Entregável:* cliente abre chamado, vê status, recebe push.

**Fase 6 — Chat in-app integrado**
Coluna `channel='app'` em conversations, workers entendem canal app. Endpoints `/chat/messages` + `/chat/send`. Realtime via polling 5s no MVP (SSE/WS depois). Sub-tab "Chat": bubbles, anexo, "atendente digitando". Push por nova mensagem. Dashboard: filtro canal `app` na caixa unificada.
*Entregável:* cliente conversa in-app, mensagem cai no dashboard.

**Fase 7 — Polimento + LGPD + stores**
`DELETE /me`, termos/privacidade, animações, haptics, ícones adaptivos, screenshots. Build release Android (.aab) + iOS (.ipa), checklist stores.

## 10. Decisões fora do escopo (registradas pra futuro)

- **Cancelamento** não está no app — segue via atendente humano (decisão deliberada).
- **Indique e ganhe** é placeholder no Perfil — implementação fica pra após Fase 7.
- **WebSocket/SSE** real fica pra após MVP — polling 5s no chat na Fase 6.
- **Atualização de endereço/CPF** não editáveis pelo cliente — exige fluxo de OS de mudança ou contato humano.
