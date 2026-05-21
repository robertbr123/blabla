# Cliente App — Fase 6: Chat in-app

> subagent-driven. Checkbox `- [ ]`.

**Goal:** Cliente abre tab Suporte → sub-tab Chat → conversa com bot. Bot responde em ~3s. Mensagens persistem entre aberturas do app. Cliente vê histórico paginado.

**Architecture (MVP):** Nova tabela `cliente_app_messages` separada do `conversas/mensagens` (WhatsApp) — evita refactor do fluxo de conversas existente. Backend tem 2 endpoints (lista paginada por cursor, enviar). `POST /chat/send` grava mensagem do user → chama LLM com system prompt simples (sem tool calling por ora) → grava resposta. Flutter substitui o stub por chat real com polling 5s.

**Decisões:**
- **Sem integração com `conversas` agora.** Cross-table integration vira fase futura quando admin precisar ver mensagens app+wa juntos. MVP é "bot fala com cliente in-app".
- **LLM sem tool calling.** Prompt curto, resposta texto puro. Quando precisar consultar plano/fatura, cliente clica nos botões da Home/Faturas — não pede ao bot. Tools no chat virá depois.
- **Polling 5s.** WebSocket fica pra Fase 7.
- **Sem escalonamento humano nessa fase.** Só bot. Atendimento humano segue via OS aberta na Fase 5.

**Spec:** seção 4 tab 3 sub-tab Chat + seção 6.

**Migration:** `0028_cliente_app_messages`.

## Schema

```sql
CREATE TABLE cliente_app_messages (
  id uuid PRIMARY KEY,
  cliente_app_user_id uuid NOT NULL REFERENCES cliente_app_users(id) ON DELETE CASCADE,
  role varchar(16) NOT NULL,  -- user | bot
  content_encrypted text NOT NULL,
  llm_tokens_used int,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_cliente_app_messages_user_at
  ON cliente_app_messages(cliente_app_user_id, created_at DESC);
```

## Endpoints

| Método | Path | Descrição |
|---|---|---|
| GET | `/api/v1/cliente-app/chat/messages?cursor=<iso>&limit=50` | Lista paginada DESC por created_at; cursor é `created_at` da última msg da página anterior |
| POST | `/api/v1/cliente-app/chat/send` | Body `{text}` → grava user msg, chama LLM, grava response, retorna ambas |

## Flutter

- Replace `_ChatStub` em suporte_screen.dart pelo `ChatTab`
- Bubbles estilo iMessage (verde-menta direita pra user, cinza claro esquerda pra bot)
- Input fixo bottom com botão de enviar
- Polling 5s — `StreamProvider` baseado em `Stream.periodic`
- Loading state mientras bot responde ("digitando…")
- Initial empty state: mensagem de boas-vindas do bot
