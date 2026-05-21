# Cliente App — Fase 5: Abertura de OS pelo cliente

> subagent-driven. Checkbox `- [ ]`.

**Goal:** Cliente abre chamado (sem internet / mudança endereço / troca plano) e acompanha status. Não escala automaticamente — admin no dashboard trata.

**Architecture:** Nova tabela `cliente_app_os` (separada da `ordens_servico` que é do técnico). Endpoints GET (lista) + POST (criar) + GET por id. Flutter ganha sub-tab "Meus chamados" + FAB → wizard 3 steps. Sem integração com sistema de conversas ou SGP nessa fase — admin trata pelo dashboard via endpoint admin separado (fica pra fase futura).

**Migration:** `0027_cliente_app_os`.

**Tipos suportados:**
- `sem_internet` — payload: `descricao` (text), `desde_quando` (datetime opcional)
- `mudanca_endereco` — payload: `cep`, `logradouro`, `numero`, `bairro`, `cidade`, `uf`, `data_prevista`
- `troca_plano` — payload: `plano_desejado` (text), `motivo` (text)

**Status:** `aberto` (default) → `em_atendimento` → `concluido` | `cancelado`. Admin muda via dashboard (não nessa fase).

**Spec:** seção 4 tab 3 + seção 5 + seção 6.
