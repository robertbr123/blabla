# Ondeline Bot — Operação v2: Design Spec

**Data:** 2026-05-13  
**Abordagem:** Dashboard primeiro (features visuais entregues antes das backend-only)  
**Escopo:** 6 funcionalidades cobrindo dashboard (Next.js) e backend (FastAPI + Celery)

---

## Contexto

O sistema atual (v2) já tem PostgreSQL, FSM, Celery, LLM com tool-calling e tecnico-pwa. Este spec cobre o próximo salto operacional: melhorar a tela de conversa do dashboard, a criação de OS, o atendimento humano gerenciável, a classificação de mídia, um fluxo próprio para mudança de endereço e conclusão de OS via WhatsApp.

---

## Funcionalidades

### F1 — Tela de Conversa (Dashboard)

**Layout:** Três colunas (opção B validada):
- Coluna esquerda: lista de conversas filtráveis por status (BOT / AGUARDANDO / HUMANO / ENCERRADA)
- Centro: chat com **abas** no topo
- Coluna direita: ações fixas + timer de SLA

**Abas do centro:**

| Aba | Conteúdo |
|---|---|
| Mensagens | Histórico de mensagens (CLIENTE / BOT / ATENDENTE) + input de resposta |
| Cliente SGP | Dados do cliente puxados do SGP: nome, CPF mascarado, plano, status contrato, cidade, endereço, contratos |
| + Nova OS | Formulário de OS (ver F2-A abaixo) |

**Aba Mensagens:**
- Mensagens coloridas por role: CLIENTE (azul), BOT (cinza), ATENDENTE (verde)
- Input de texto + botão Enviar — ativa endpoint `POST /api/v1/conversas/{id}/responder`
- Rolagem automática para última mensagem

**Aba Cliente SGP:**
- Dados lidos de `/api/v1/conversas/{id}` que já embute `cliente` (implementado em commit `69f7af8`)
- Se não houver cliente identificado: exibe "Cliente ainda não identificado"
- Contratos listados com status (Ativo / Suspenso) destacado visualmente

**Aba + Nova OS (F2-A):**
- Formulário embutido no centro (opção C validada)
- Campo cliente: auto-preenchido e bloqueado (vem da conversa)
- Campos editáveis: descrição do problema (textarea), endereço (pre-preenchido do SGP, editável), técnico (select com técnicos disponíveis na cidade do cliente)
- Botão "Abrir OS e Notificar Técnico" → `POST /api/v1/os`
- Após criação: aba some, chat volta para "Mensagens", mensagem de confirmação aparece no chat

**Ações fixas (coluna direita):**
- **Assumir** — atribui `atendente_id = usuário logado`, muda status para HUMANO → `PATCH /api/v1/conversas/{id}/assumir` (`transferred_at` já foi setado quando `transferir_para_humano` tool disparou)
- **Encerrar** — muda status para ENCERRADA → `PATCH /api/v1/conversas/{id}/encerrar`
- **Excluir** — soft delete (campo `deleted_at`) com confirmação modal → `DELETE /api/v1/conversas/{id}`
- **Timer SLA** — exibe tempo desde `transferred_at`; fica vermelho após 15 minutos sem `first_response_at`

**API nova necessária:**
- `PATCH /api/v1/conversas/{id}/assumir` — atribui atendente, seta timestamps
- `PATCH /api/v1/conversas/{id}/encerrar` — muda status
- `DELETE /api/v1/conversas/{id}` — soft delete

---

### F2-B — OS Standalone (Página de Ordens de Serviço)

**Layout:** Dois painéis lado a lado (opção B validada):
- Esquerda: lista de OS com filtros (status, técnico, cidade) + botão "Nova OS"
- Direita: formulário de criação sempre visível ao clicar "Nova OS"

**Formulário de criação:**
1. Campo CPF/CNPJ + botão "Buscar" → `GET /api/v1/clientes/sgp?cpf={cpf}` (endpoint novo — busca direto no SGP)
2. Após busca: exibe card do cliente (nome, plano, status, endereço) com badge "SGP ✓"
3. Campos editáveis: descrição, endereço (pre-preenchido do SGP, editável), cidade (pre-preenchida), técnico (select filtrado pela cidade)
4. Botão "Abrir OS e Notificar Técnico" → `POST /api/v1/os`
5. Após criação: formulário limpa, lista de OS atualiza, snackbar de confirmação

**API nova necessária:**
- `GET /api/v1/clientes/sgp?cpf={cpf}` — busca cliente no SGP by CPF (bypass cache ou forçar refresh)

---

### F3 — Camada Gerencial de Atendimento Humano

**Mudanças no banco (`conversas`):**

| Coluna | Tipo | Descrição |
|---|---|---|
| `atendente_id` | FK → users | Atendente que assumiu a conversa |
| `transferred_at` | timestamptz | Quando entrou na fila de humano |
| `first_response_at` | timestamptz | Quando o atendente enviou a primeira mensagem |
| `sla_minutes` | int | Default 15, configurável por conversa futuramente |

**Lógica:**
- Quando `transferir_para_humano` tool é chamado: `transferred_at = now()`, status → AGUARDANDO
- Quando atendente clica "Assumir": `atendente_id = user.id`, status → HUMANO
- Quando atendente envia primeira mensagem: `first_response_at = now()`
- SLA violado = `transferred_at` há mais de `sla_minutes` minutos e `first_response_at IS NULL`

**Dashboard:**
- Lista de conversas em AGUARDANDO ordenada por `transferred_at` ASC (mais antiga primeiro)
- Timer visível em cada card da lista: "⏱ 14min" ficando vermelho ao passar de 15min
- SSE já existente (`/api/v1/conversas/stream`) envia evento quando conversa entra em AGUARDANDO

**Migration:** `0006_atendente_sla_fields.py`

---

### F4 — Classificação de Mídia na Entrada

**Onde:** `services/inbound.py` — antes de chamar a FSM para `MSG_CLIENTE_MEDIA`

**Categorias e roteamento:**

| Categoria | Detecção | Ação |
|---|---|---|
| Comprovante de pagamento | MIME image/* ou PDF + caption contendo "comprovante", "pix", "pagamento", "paguei", "boleto" | Bot responde: "Recebi seu comprovante, encaminhando para análise." → escala com tag `comprovante` |
| Foto de equipamento/instalação | MIME image/* + caption contendo "roteador", "cabo", "sinal", "equipamento", "poste", "foto" | Bot responde: "Recebi a foto, abrindo chamado técnico." → tool `abrir_ordem_servico` com descrição gerada |
| Documento de identidade | MIME image/* ou PDF + caption contendo "rg", "cnh", "documento", "identidade", "cpf" | Bot responde: "Documento recebido, encaminhando para cadastro." → escala com tag `documento` |
| Áudio | MIME audio/* | Bot responde: "Não consigo ouvir áudios. Por favor, escreva sua mensagem." → FSM permanece no estado atual |
| Outros (vídeo, sticker, genérico) | Qualquer outro MIME | Bot responde: "Recebi seu arquivo, encaminhando para atendente." → escala sem tag específica |

**Implementação:**
- Função `classify_media(kind, caption) → MediaCategory` em `services/media_classifier.py` (arquivo novo)
- Stateless, sem LLM — classificação por regras de keywords (normalização lowercase + strip accents)
- Resultado injeta `conversa_tag` na conversa antes de escalar

**Novo campo no banco (`conversas`):** `tags` JSONB array (ex: `["comprovante", "tecnico"]`) — adicionado na migration `0006`

---

### F5 — Fluxo de Mudança de Endereço (FSM)

**Novo estado:** `MUDANCA_ENDERECO` adicionado ao enum `ConversaEstado`

**Ativação:**
- LLM detecta intenção de mudança de endereço e chama nova tool: `iniciar_mudanca_endereco()`
- Tool muda estado para `MUDANCA_ENDERECO`, envia primeira pergunta ao cliente

**Coleta sequencial (bot determinístico, sem LLM):**
1. "Qual o novo endereço? (rua e número)"
2. "Qual o bairro?"
3. "Algum ponto de referência?"

**Ao completar a coleta:**
- Verifica status financeiro do cliente no cache SGP
- **Sem pendência financeira:** chama `abrir_ordem_servico` com descrição "Mudança de endereço: {novo_endereco}" → estado volta para CLIENTE
- **Com pendência financeira:** chama `transferir_para_humano` com motivo estruturado contendo o novo endereço já coletado → estado AGUARDA_ATENDENTE

**Dados persistidos:**
- Endereço coletado salvo em `conversas.metadata` JSONB (campo `mudanca_endereco_pendente`) até OS ser aberta
- Após OS aberta, campo limpo

**Nova tool LLM:** `iniciar_mudanca_endereco()` — sem parâmetros, apenas ativa o estado

---

### F6 — Técnico Finalizar OS via WhatsApp

**Comando de ativação:** `CONCLUIDO OS-YYYYMMDD-NNN` (case-insensitive)

**Detecção:** Em `services/inbound.py`, antes da FSM, verifica se o remetente é técnico e se a mensagem casa com o padrão `r'^concluido\s+OS-\d{8}-\d{3}$'` (normalizado).

**Checklist sequencial (5 passos, determinístico — sem LLM):**

| Passo | Pergunta do bot | Campo salvo |
|---|---|---|
| 1 | "✅ OS encontrada. O que foi feito? Descreva o serviço realizado." | `checklist.servico_realizado` |
| 2 | "Houve visita presencial? Responda SIM ou NÃO." | `checklist.visita_presencial` |
| 3 | "Qual material foi utilizado? (ex: cabo, ONU, conector — ou NENHUM)" | `checklist.material_utilizado` |
| 4 | "Mande uma foto de comprovação da instalação." | `checklist.foto_url` (URL salva via Evolution media download → storage local, mesmo mecanismo de `POST /api/v1/os/{id}/foto`) |
| 5 | "Alguma observação adicional? (ou responda NENHUMA)" | `checklist.observacao` |

**Estado intermediário:** `ConversaEstado.CHECKLIST_OS` (novo estado) — técnico fica nesse estado até completar todos os passos. Passo atual salvo em `conversas.metadata` JSONB (`checklist_os_step`, `checklist_os_id`).

**Ao completar o checklist:**
- `ordens_servico.status = CONCLUIDA`
- `ordens_servico.checklist` JSONB preenchido com os 5 campos
- `ordens_servico.concluida_em = now()`
- Enfileira `followup_os_job` imediatamente para notificar o cliente
- Bot confirma: "✅ OS {codigo} concluída com sucesso! O cliente será notificado."

**Validações:**
- Passo 2: aceita apenas SIM/NÃO (case-insensitive, strip)
- Passo 4: rejeita se não for `MSG_CLIENTE_MEDIA` com MIME image/*
- Não permite pular passos; repete a pergunta se a resposta for inválida

---

## Ordem de Entrega (Dashboard Primeiro)

### Fase 1 — Dashboard: Conversa + SLA
- Migration `0006_atendente_sla_fields` (campos `atendente_id`, `transferred_at`, `first_response_at`, `tags`)
- Endpoints: `PATCH /assumir`, `PATCH /encerrar`, `DELETE /{id}` (soft delete)
- Dashboard: layout B de conversas com abas Mensagens / Cliente SGP / + Nova OS
- Dashboard: timer SLA + ações fixas à direita

### Fase 2 — Dashboard: OS Standalone
- Endpoint: `GET /api/v1/clientes/sgp?cpf={cpf}`
- Dashboard: página de OS com painel lateral de criação + busca CPF

### Fase 3 — Backend: Classificação de Mídia
- `services/media_classifier.py`
- Integração em `services/inbound.py`
- Campo `tags` na conversa (já criado na Fase 1)

### Fase 4 — Backend: Mudança de Endereço
- Novo enum estado `MUDANCA_ENDERECO`
- Nova tool LLM `iniciar_mudanca_endereco`
- Lógica de coleta sequencial em `services/inbound.py`
- Campo `metadata` em `conversas` (migration se não existir)

### Fase 5 — Backend: Técnico via WhatsApp
- Novo enum estado `CHECKLIST_OS`
- Detecção de comando `CONCLUIDO OS-*` em `services/inbound.py`
- Lógica de checklist sequencial com upload de foto

---

## Decisões Técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| Soft delete de conversa | `deleted_at` timestamptz | Preserva histórico para auditoria, filtra na listagem |
| Classificação de mídia | Keywords + MIME, sem LLM | Determinístico, sem latência, sem custo de token |
| Estado intermediário de checklist | `CHECKLIST_OS` na FSM | Evita que cliente receba resposta do bot enquanto técnico preenche checklist |
| Endereço auto-preenchido em OS | Editável (não bloqueado) | Operador pode corrigir se o cliente mora em endereço diferente do cadastro |
| SLA hardcoded em 15min | Default na config | Configurável futuramente via tabela `config` sem deploy |
| Migration `0006` | Única migration para Fase 1+2 | Menor número de migrations; campos são relacionados |

---

## O que fica fora deste spec

- Score de roteamento de técnico com peso por desempenho (complexidade alta, baixo impacto imediato)
- Reabertura automática de OS por follow-up negativo (próximo milestone)
- Analytics avançado (taxa de escalonamento, técnicos com mais reincidência)
- Cancelamento de contrato (sem trilha definida ainda)
