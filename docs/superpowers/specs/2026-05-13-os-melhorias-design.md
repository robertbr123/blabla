# Design: Melhorias de Ordens de Serviço (itens 1–8)

**Data:** 2026-05-13  
**Escopo:** 8 melhorias operacionais em OS, técnicos, conversas e follow-up de bot  
**Abordagem:** Migração única + trabalho em 3 grupos sequenciais

---

## 1. Banco de dados

### Migração `0005_os_followup_reatribuicao.py`

Adiciona à tabela `ordens_servico`:

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `reatribuido_em` | `TIMESTAMPTZ NULL` | Momento da última reatribuição |
| `reatribuido_por` | `UUID NULL → FK users.id SET NULL` | ID do usuário que reatribuiu |
| `historico_reatribuicoes` | `JSONB NULL DEFAULT '[]'` | Array de entradas `{de, para, em, por}` |
| `follow_up_resposta` | `TEXT NULL` | Texto literal do cliente no follow-up |
| `follow_up_respondido_em` | `TIMESTAMPTZ NULL` | Quando o cliente respondeu |
| `follow_up_resultado` | `VARCHAR(20) NULL` | `'ok'` ou `'nao_ok'` |

Adiciona à tabela `conversas`:

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `followup_os_id` | `UUID NULL → FK ordens_servico.id SET NULL` | OS aguardando confirmação de follow-up |

Adiciona à enum `conversa_estado`:
- `'aguarda_followup_os'`

### Modelo `OrdemServico` (business.py)

Adiciona os 6 novos `Mapped[...]` correspondentes.

### Enum `ConversaEstado` (business.py)

Adiciona `AGUARDA_FOLLOWUP_OS = "aguarda_followup_os"`.

---

## 2. API

### Novos endpoints

#### `POST /api/v1/os/{id}/reatribuir` (item 1)

**Body:** `{ tecnico_id: UUID }`  
**Autorização:** ATENDENTE, ADMIN  

Lógica:
1. Busca OS — 404 se não encontrar
2. Bloqueia se `status == 'concluida'` — 422 `"OS concluída não pode ser reatribuída"`
3. Busca técnico novo — 404 se não encontrar; 422 se `ativo == False`
4. Registra em `historico_reatribuicoes`: `{de: old_tecnico_id, para: new_tecnico_id, em: now(), por: current_user.id}`
5. Atualiza `tecnico_id`, `reatribuido_em = now()`, `reatribuido_por = current_user.id`
6. Envia WhatsApp de cancelamento ao técnico anterior (se tiver `whatsapp`)
7. Envia WhatsApp da OS ao novo técnico (mesmo formato de `abrir_ordem_servico`)
8. Retorna `OsOut`

**Resposta:** `OsOut` (200)

---

#### `DELETE /api/v1/os/{id}` (item 7)

**Autorização:** ADMIN  

Lógica:
1. Busca OS — 404 se não encontrar
2. Busca técnico atual para obter `whatsapp`
3. Se `tecnico.whatsapp` não for null: envia mensagem de cancelamento via WhatsApp
4. Hard-delete da OS
5. Retorna `{notif_tecnico: true/false}` (200)

---

### Filtro adicional em `GET /api/v1/os` (item 4)

Adiciona query param `cliente_id: UUID | None`.  
`OrdemServicoRepo.list_paginated` passa a aceitar `cliente_id` como filtro.

---

### Alterações em endpoints existentes

#### `POST /api/v1/os` — criar OS (item 2)

`OsCreate` passa a exigir `tecnico_id: UUID`.  
Lógica após criar: busca técnico e envia WhatsApp (mesmo formato do bot).

#### `GET /api/v1/conversas/{id}` (item 3)

`ConversaOut` ganha campo `cliente: ClienteEmbutido | None`.

```python
class ClienteEmbutido(BaseModel):
    id: UUID
    nome: str           # descriptografado
    cpf_cnpj: str       # descriptografado
    whatsapp: str
    plano: str | None
    cidade: str | None
    endereco: str | None  # descriptografado
```

O endpoint preenche esse campo quando `conversa.cliente_id` não for null.

#### `POST /api/v1/os/{id}/concluir` (item 8)

Após concluir OS:
1. Busca a conversa mais recente não-encerrada do cliente (`cliente_id` da OS, `deleted_at IS NULL`, `status != 'encerrada'`) — se não encontrar, segue sem enviar follow-up
2. Envia mensagem de follow-up via WhatsApp ao cliente
3. Muda `conversa.estado = AGUARDA_FOLLOWUP_OS`
4. Persiste `conversa.followup_os_id = os_.id`

---

## 3. Dashboard

### Componentes novos

#### `components/dialog-reatribuir-tecnico.tsx` (item 1)

Dialog com:
- `<Select>` de técnicos ativos (`useTecnicos({ativo: true})`)
- Botão Confirmar → `useReatribuirOs(osId)`
- Aparece apenas para OS não concluídas/canceladas

#### `components/dialog-abrir-os-from-conversa.tsx` (item 3)

Dialog pré-preenchido com dados do `ConversaOut.cliente`:
- Campos: nome, CPF, WhatsApp, plano, cidade, bairro, rua, número, endereço, UF
- Técnico responsável obrigatório (dropdown ativo)
- Reutiliza `useCreateOs`

### Componentes alterados

#### `form-os-create.tsx` (item 2)

- Adiciona campo `Técnico responsável *` com `<Select>` via `useTecnicos({ativo: true})`
- Zod schema: `tecnico_id: z.string().uuid('Selecione o técnico responsável')`

#### `os-list.tsx` (itens 1 e 7)

- Coluna "Ações" no final da tabela
- Botão "Reatribuir" (visível se `status !== 'concluida'`) → abre `dialog-reatribuir-tecnico`
- Botão "Excluir" → confirm dialog → `useDeleteOs`

#### `conversa-chat.tsx` (itens 3 e 4)

No header da conversa:
- Botão `🔧 Abrir OS` → abre `dialog-abrir-os-from-conversa`
- Se existir OS aberta para o cliente: alerta amarelo listando: código, status, técnico, descrição

A verificação de OS aberta usa `useOsList({ cliente_id: data.cliente?.id })` filtrado por status não-concluído.

#### `conversa-list.tsx` (item 3)

- Coluna extra "Ações" com botão `Abrir OS` → abre `dialog-abrir-os-from-conversa` passando o `conversaId`

### Queries e mutations novas (`queries.ts`)

```typescript
useReatribuirOs(id: string)         // POST /api/v1/os/{id}/reatribuir
useDeleteOs(id: string)             // DELETE /api/v1/os/{id}
```

### Types novos/atualizados (`types.ts`)

```typescript
// OsCreate: adicionar tecnico_id: string (required)
// OsOut: adicionar reatribuido_em, reatribuido_por, historico_reatribuicoes, follow_up_*
// ConversaDetail: adicionar cliente: ClienteEmbutido | null
interface ClienteEmbutido { id, nome, cpf_cnpj, whatsapp, plano, cidade, endereco }
interface OsReatribuirIn { tecnico_id: string }
```

---

## 4. Bot / FSM (item 8)

### `domain/fsm.py`

Novo `ActionKind`:
- `FOLLOWUP_OS_CONFIRMAR = "followup_os_confirmar"` — cliente confirmou que ficou ok
- `FOLLOWUP_OS_ESCALAR = "followup_os_escalar"` — cliente reportou que ainda há problema

No `Fsm.transition`, case `AGUARDA_FOLLOWUP_OS`:

```python
PALAVRAS_OK = {"sim", "ok", "obrigado", "certo", "tudo bem", "já está", "resolveu", "funcionou"}
PALAVRAS_NOK = {"não", "nao", "ainda não", "continua", "sem sinal", "sem internet", "mesmo problema"}

# substring match: qualquer palavra-chave aparece no texto normalizado
text_norm = text.lower().strip()
if any(p in text_norm for p in PALAVRAS_OK):
    return FsmDecision(ENCERRADA, BOT, [Action(FOLLOWUP_OS_CONFIRMAR)])
elif any(p in text_norm for p in PALAVRAS_NOK):
    return FsmDecision(AGUARDA_ATENDENTE, AGUARDANDO, [Action(FOLLOWUP_OS_ESCALAR)])
else:
    return FsmDecision(AGUARDA_FOLLOWUP_OS, BOT, [Action(LLM_TURN)])
```

### `workers/llm_turn.py`

Traduz as novas actions:
- `FOLLOWUP_OS_CONFIRMAR`: envia "Fico feliz que tenha resolvido! 😊 Qualquer dúvida estamos aqui." + persiste `follow_up_resultado='ok'`, `follow_up_respondido_em=now()`, `follow_up_resposta=texto_cliente` na OS vinculada por `conversa.followup_os_id`
- `FOLLOWUP_OS_ESCALAR`: escalate para humano + persiste `follow_up_resultado='nao_ok'` + mesmos campos de resposta

---

## 5. Grupos de execução

| Grupo | Conteúdo | Depende de |
|-------|----------|------------|
| G1 | Migração 0005 + modelos + schemas API + todos os endpoints | — |
| G2 | Dashboard OS: form-os-create, os-list, queries/mutations, types | G1 |
| G3 | Dashboard Conversas: conversa-chat, conversa-list, dialogs + FSM/worker | G1 |

G2 e G3 podem ser executados em paralelo após G1.

---

## 6. Itens já implementados (sem trabalho adicional)

- **Item 5 (`api/api/tecnicos`):** `apiFetch` já usa paths completos, bug não existe neste código
- **Item 6 (técnicos ativo/inativo):** `Tecnico.ativo` já existe no modelo, API já filtra, dashboard já mostra status e tem toggle ativar/desativar
