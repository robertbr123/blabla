# Bot Toggle — Design Spec

**Data:** 2026-05-14  
**Escopo:** Toggle on/off do bot WhatsApp via painel de configurações

---

## Contexto

O sistema precisa de uma forma operacional de desativar o bot temporariamente sem restart de container. Quando desativado, mensagens continuam sendo salvas mas o bot não processa FSM/LLM nem responde.

---

## Arquitetura

### Dados

- **Chave:** `bot.ativo` na tabela `config` (já existe)
- **Tipo:** JSON booleano (`true` / `false`)
- **Default implícito:** `true` — se a chave não existir no banco, o bot está ativo
- **Nenhum migration necessário**

### Backend — `services/inbound.py`

Interceptação logo após o guard `from_me` (~linha 113), antes de qualquer lógica FSM/LLM:

```python
if deps.session is not None:
    bot_ativo = await ConfigRepo(deps.session).get("bot.ativo")
    if bot_ativo is False:
        conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid)
        await deps.mensagens.insert_inbound_or_skip(
            conversa_id=conversa.id,
            external_id=evt.external_id,
            text=evt.text,
            media_type=evt.kind.value if evt.kind in _MEDIA_KINDS else None,
            media_url=None,
        )
        return InboundResult(
            conversa_id=conversa.id,
            persisted=True,
            duplicate=False,
            escalated=False,
            skipped_reason="bot_desativado",
        )
```

**Regra de avaliação:** `None` (chave ausente) → bot ativo. Só `False` explícito desativa.

**Sem cache Redis** — query direta na sessão já existente. A tabela `config` é tiny; latência negligenciável.

**Endpoint:** Nenhum novo endpoint necessário. `GET /api/v1/config/bot.ativo` e `PUT /api/v1/config/bot.ativo` já existem no router de config genérico.

### Dashboard — Página de Configurações

**Localização:** `/configuracoes` — nova seção "Bot WhatsApp" acima das credenciais SGP.

**Componente:** Toggle switch (`<Switch>` do shadcn/ui) com label "Bot ativo".

**Comportamento:**
- Ao montar: `GET /api/v1/config/bot.ativo` — toggle ON se valor for `true` ou `null`
- Ao clicar: `PUT /api/v1/config/bot.ativo` com `{"value": true|false}` — optimistic update + toast de confirmação
- Sem confirmação modal — a ação é reversível instantaneamente

**Layout:**

```
┌─────────────────────────────────────────────┐
│ Bot WhatsApp                                │
│                                             │
│  Bot ativo          [toggle ON/OFF]         │
│  Quando desativado, mensagens são salvas    │
│  mas o bot não responde automaticamente.    │
└─────────────────────────────────────────────┘
```

---

## O que fica fora deste spec

- Mensagem automática de "bot indisponível" ao cliente (pode ser próxima iteração)
- Agendamento de horário de funcionamento (ex: bot ativo só das 8h às 18h)
- Toggle por número/instância (hoje é global)
