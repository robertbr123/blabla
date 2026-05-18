# Comandos de Técnico via WhatsApp — Design

**Data:** 2026-05-18
**Status:** Aprovado (aguardando plano de implementação)
**Autor:** Roberio + Claude

## Problema

Hoje o bot identifica técnico cadastrado **apenas** para o comando `CONCLUIR OS-XXXX`. Qualquer outra mensagem de um técnico cai no fluxo de cliente: a LLM responde como se ele fosse um assinante (oferece 2ª via de boleto, agendamento, etc.) — comportamento errado e que polui a conversa.

O técnico precisa de um canal próprio no bot: comandos curtos que retornam dados operacionais (lista de OS, resumo do dia/mês, ajuda) e que **nunca** caem no fluxo de atendimento ao cliente.

## Escopo

Comandos suportados no MVP (case-insensitive, mensagem exata após `.strip()`):

- `OS` — lista até 10 OS ativas do técnico (status pendente ou em_andamento), em blocos detalhados.
- `RESUMO` — visão geral: contagens de pendentes, em andamento, concluídas no mês corrente, e a próxima OS agendada.
- `AJUDA` / `MENU` / `HELP` / `?` — lista os comandos disponíveis.
- `CONCLUIR OS-XXXX` — finaliza uma OS via checklist de 3 passos. **Já existe**, mas migra do `inbound.py` para o novo módulo (sem mudança de comportamento).

Mensagens de técnico que **não casam** com nenhum comando são **ignoradas silenciosamente** (zero outbound, conversa segue persistida).

Fora de escopo: detalhar OS específica via número, criar/cancelar OS, comandos com argumentos livres, comandos de áudio/imagem.

## Arquitetura

### Novo módulo: `apps/api/src/ondeline_api/services/tecnico_inbound.py`

Responsabilidades:

- `get_tecnico_by_jid(session, jid) -> Tecnico | None` — lookup com normalização de telefone BR (`_br_local_digits`). Retorna `None` se sem match ou se `tecnico.ativo=False`.
- `handle_tecnico_message(evt, tecnico, conversa, deps) -> bool` — dispatcher. Retorna `True` se a mensagem foi consumida (comando reconhecido ou CONCLUIR).
- Handlers internos: `_cmd_os`, `_cmd_resumo`, `_cmd_ajuda`, `_cmd_concluir`.
- Formatadores: `_format_os_block(os, cliente)`, `_format_resumo(counts, proxima)`.

### Mudança em `apps/api/src/ondeline_api/services/inbound.py`

Substitui o bloco atual de detecção CONCLUIR por um dispatcher único de técnico, posicionado **após** o bloco CHECKLIST_OS:

```python
# CHECKLIST_OS continua interceptado primeiro (estado da conversa do técnico)
if conversa.estado is ConversaEstado.CHECKLIST_OS and deps.session is not None:
    # ... código existente, sem mudanças ...
    return ...

# NOVO: dispatcher de técnico — substitui o bloco CONCLUIR atual
if deps.session is not None and evt.kind is InboundKind.TEXT and evt.text:
    tecnico = await get_tecnico_by_jid(deps.session, evt.jid)
    if tecnico is not None:
        consumed = await handle_tecnico_message(evt, tecnico, conversa, deps)
        if consumed:
            return InboundResult(conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False)
        # texto livre não reconhecido — ignora silenciosamente
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False,
            skipped_reason="tecnico_no_command",
        )

# Bot inativo / mídia / FSM / LLM — só para clientes (técnico já retornou acima)
if deps.session is not None:
    bot_ativo = await ConfigRepo(deps.session).get("bot.ativo")
    if bot_ativo is False:
        ...
```

**Ordem final do `inbound.py`:** parsing/dedup/persist → CHECKLIST_OS → **dispatcher técnico** → bot.ativo → mídia → FSM/LLM.

Justificativas:

- CHECKLIST_OS roda primeiro porque é continuação de um CONCLUIR já iniciado: se o técnico digitou "OS" como descrição do serviço no passo 1, queremos avançar o checklist, não listar OS.
- Dispatcher de técnico roda antes do gate `bot.ativo` para que técnico sempre consiga operar mesmo com bot desligado.

### Novos métodos em repositórios

`apps/api/src/ondeline_api/repositories/tecnico.py`:

- `get_by_jid(jid: str) -> Tecnico | None` — encapsula o lookup atualmente inline no `inbound.py`. Filtra `ativo=True`. Múltiplos matches: pega o primeiro e loga warning.

`apps/api/src/ondeline_api/repositories/ordem_servico.py`:

- `list_ativas_by_tecnico(tecnico_id: UUID, limit: int = 11) -> list[OrdemServico]` — `status IN (pendente, em_andamento)`, ordenado por `agendamento_at` (NULLS LAST). Limit 11 detecta "tem mais que 10" sem query extra.
- `count_by_status_for_tecnico(tecnico_id: UUID) -> dict[str, int]` — retorna `{"pendente": N, "em_andamento": N, "concluida_mes": N}`. `concluida_mes` filtra `status=CONCLUIDA AND concluida_em >= first_day_of_current_month` em timezone America/Manaus.
- `proxima_agendada(tecnico_id: UUID) -> OrdemServico | None` — primeira OS com `agendamento_at >= now()` e status pendente/em_andamento.

Cliente é carregado via `joinedload` no mesmo query (sem N+1).

### Função utilitária movida

`_br_local_digits` migra de `services/inbound.py` para um módulo compartilhado (`services/phone.py` ou inline em `tecnico_inbound.py`). Decisão final na implementação — não bloqueante para o spec.

## Comandos e regex

Aplicados sobre `text.strip().upper()`:

| Comando | Pattern | Notas |
|---|---|---|
| `CONCLUIR` | `^CONCLU[IÍ]R\s+OS-[\w-]+$` | já existente |
| `OS` | `^OS$` | exato — não conflita com "OS-1234" do CONCLUIR |
| `RESUMO` | `^RESUMOS?$` | aceita plural |
| `AJUDA` | `^(AJUDA\|MENU\|HELP\|\?)$` | atalhos comuns |

Ordem de avaliação: `CONCLUIR` → `OS` → `RESUMO` → `AJUDA` → nenhum match (return `False`).

## Formato de saída

### `AJUDA`

```
*Comandos disponíveis:*

📋 *OS* — lista suas OS ativas
📊 *RESUMO* — visão geral (pendentes, andamento, concluídas no mês)
✅ *CONCLUIR OS-1234* — finaliza uma OS (inicia checklist)

_Ajuda a qualquer momento: envie AJUDA._
```

### `OS` (sem OS ativa)

```
Você não tem OS ativas no momento. 🎉
```

### `OS` (com OS, ordenado por agendamento NULLS LAST)

```
*Suas OS ativas (2):*

*OS-1234* 🟡 pendente
👤 João Silva — 📞 (97) 9 8410-9856
📍 Av. Brasil 100
🔧 Sem sinal de internet
📅 hoje 14h

*OS-1235* 🟠 em andamento
👤 Maria Lima — 📞 (97) 9 8765-4321
📍 R. Sete 22
🔧 Trocar roteador
📅 sem agenda
```

Quando há mais que 10 OS: lista as 10 primeiras + linha final:

```
_... mostrando 10 de 14. Acesse o painel para ver todas._
```

### `RESUMO`

```
*Seu resumo*

🟡 Pendentes: 5
🟠 Em andamento: 2
✅ Concluídas (mês): 28

📅 Próxima agendada: OS-1234 — hoje 14h
```

- Se `proxima_agendada` retorna `None`: omite a linha "Próxima agendada".
- Se todos os contadores são 0 e sem concluídas no mês: `Você ainda não tem OS atribuídas.`

### Convenções de formatação

- **Status emojis:** pendente `🟡`, em_andamento `🟠`, concluida `✅`.
- **Telefone:** usa `cliente.whatsapp` formatado como `(DD) X XXXX-XXXX`. Ausente → omite `— 📞 ...`.
- **Agendamento:** `"hoje HHh"`, `"amanhã HHh"`, `"DD/MM HHh"`, ou `"sem agenda"` se NULL. Timezone America/Manaus.
- **Problema:** trunca em 60 chars com sufixo `…` se maior.
- **Endereço:** `os.endereco` direto (já é texto livre).
- **Nome cliente ausente:** "Cliente sem nome".

## Edge cases e error handling

| Cenário | Comportamento |
|---|---|
| `tecnico.ativo=False` | `get_tecnico_by_jid` retorna `None` → fluxo cliente (provavelmente bloqueado por bot inativo de qualquer forma) |
| JID cadastrado em `cliente.whatsapp` E `tecnico.whatsapp` | Técnico vence — cliente nunca é atendido como cliente se também é técnico |
| Cliente da OS sem nome | "Cliente sem nome" |
| Cliente da OS sem whatsapp | Omite linha `— 📞 ...` |
| OS sem `agendamento_at` | "📅 sem agenda" |
| Comando com argumentos inesperados (ex: "OS pendente") | Não casa nenhum regex → ignora silenciosamente |
| DB indisponível durante handler | Exceção sobe → 500 no webhook → Evolution retenta. Sem outbound. |
| Múltiplos técnicos com mesmo `_br_local_digits` | Pega primeiro `ativo=True`, loga warning `tecnico.duplicate_phone` |
| Bot desativado (`bot.ativo=False`) | Técnico passa normalmente — gate fica para clientes |

## Logging (structlog)

Eventos novos:

- `tecnico.cmd.identified` — `tecnico_id`, `comando`
- `tecnico.cmd.executed` — `comando`, `duracao_ms`
- `tecnico.cmd.no_match` — `text_len` (sem PII do texto)
- `tecnico.cmd.silenced` — quando técnico identificado mas comando não reconhecido
- `tecnico.duplicate_phone` (warning) — múltiplos técnicos com mesmo número normalizado

Eventos existentes em `inbound.py` (`concluir.cmd_check`, `concluir.tecnico_lookup`) migram junto com o handler CONCLUIR.

## Testes

### Unitários — `tests/test_tecnico_inbound.py`

Usa `_FakeTecnicoRepo` / `_FakeOsRepo` in-memory seguindo o padrão Protocol existente.

| Teste | Cenário | Esperado |
|---|---|---|
| `test_dispatch_os_lists_active` | técnico tem 2 OS ativas | texto formatado, 1 chamada `enqueue_send_outbound`, `consumed=True` |
| `test_dispatch_os_empty` | técnico sem OS | mensagem "Você não tem OS ativas..." |
| `test_dispatch_os_truncates_at_10` | 14 OS | texto contém "_... mostrando 10 de 14_" + 10 blocos |
| `test_dispatch_resumo` | 5 pendentes / 2 andamento / 28 mês | bate com formato |
| `test_dispatch_resumo_sem_proxima` | sem agendamento futuro | omite linha "Próxima agendada" |
| `test_dispatch_resumo_zerado` | técnico sem nenhuma OS | "Você ainda não tem OS atribuídas." |
| `test_dispatch_ajuda` | comandos AJUDA / MENU / HELP / ? | mesma mensagem |
| `test_dispatch_concluir_inicia_checklist` | regressão do CONCLUIR migrado | atualiza `checklist_metadata`, envia passo 1 |
| `test_dispatch_no_match_silent` | texto "valeu cara" | `consumed=False`, zero outbound |
| `test_dispatch_tecnico_inativo` | `tecnico.ativo=False` | `get_tecnico_by_jid` retorna `None` |
| `test_format_telefone_omitido_se_null` | cliente sem whatsapp | bloco OS sem linha de telefone |
| `test_format_problema_truncado_60_chars` | problema longo | sufixo "…" |

### Integração — `tests/test_inbound_tecnico_routing.py`

| Teste | Cenário | Esperado |
|---|---|---|
| `test_tecnico_msg_bypassa_bot_inativo` | bot.ativo=False, técnico manda OS | recebe lista |
| `test_cliente_msg_quando_bot_inativo_silenciado` | bot.ativo=False, cliente | `skipped_reason="bot_desativado"` (regressão) |
| `test_tecnico_em_checklist_responde_passo_nao_comando` | conversa CHECKLIST_OS step=1, técnico manda "OS" | trata como descrição do passo 1 |
| `test_dual_tecnico_e_cliente_prioriza_tecnico` | JID cadastrado em ambos | recebe comando, não fluxo cliente |

### Regressão garantida

- Testes existentes de CONCLUIR (`test_concluir_*`) continuam passando — comportamento e regex preservados.
- Testes de FSM/LLM_TURN não mudam — técnicos retornam antes.

## Não muda

- Modelo de dados (`Tecnico`, `OrdemServico`, `Conversa`).
- Migrations.
- FSM.
- Webhook parser.
- Frontend (dashboard/PWA).
- Worker Celery (apenas o handler `_cmd_concluir` continua enfileirando `followup_os` igual hoje).

## Plano de validação em produção

Após deploy:

1. Cadastrar 1 número de teste como técnico ativo (já existe — Roberio).
2. Enviar `AJUDA` → conferir resposta.
3. Enviar `OS` → conferir lista.
4. Enviar `RESUMO` → conferir contagens.
5. Enviar `oi` → conferir **silêncio** (zero resposta).
6. Enviar `CONCLUIR OS-XXXX` (OS de teste) → conferir checklist (regressão).
7. Validar log SSH: eventos `tecnico.cmd.*` aparecem.
