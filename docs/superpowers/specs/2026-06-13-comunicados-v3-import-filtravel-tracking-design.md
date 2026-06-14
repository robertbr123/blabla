# Comunicados v3 — Import filtrável + acompanhamento de entrega

**Data:** 2026-06-13
**Status:** Aprovado (seguindo direto pro plano)
**Base:** evolui Comunicados v2 (`2026-06-13-comunicados-v2-sync-import-botoes-design.md`).

## Contexto e problema

No v2, o import de CSV criava a lista final e disparava num clique. O provedor quer:
1. **CSV como base filtrável:** o arquivo traz `cidade/status/plano`; depois de importar, ele escolhe um recorte com filtros (igual ao segmento da base) e dispara só pra esse recorte.
2. **Acompanhamento por contato:** ver quem foi enviado/entregue/lido/falhou, filtrar por status, **reenviar as falhas** e **exportar o resultado**.

## Decisões aprovadas

1. Fluxo import → filtrar → disparar **tudo na tela de nova campanha** (botão **Importar**, depois filtros, depois **Disparar**).
2. Acompanhamento: lista com status + filtro por status + reenviar falhas + exportar resultado (os 4).
3. Colunas do CSV: `telefone` (obrigatória) + `cidade`/`status`/`plano` (opcionais) + colunas de variável (`nome`, `link`, ...) + `botao`.
4. Reenviar falhas é livre (sem limite de tentativas) — decisão do operador.

---

## Bloco 1 — CSV como base filtrável

### Dados (migration 0051)
`campanha_destinatarios` ganha 3 colunas (snapshot do CSV, separadas do campo `status` que já significa o status de envio):
- `csv_cidade` String(80) nullable
- `csv_status` String(40) nullable
- `csv_plano` String(80) nullable

Novo valor de `status` de destinatário: **`excluido`** (não recebe; filtrado fora). Sem mudança de schema (é string).

### Parser
`parse_csv_destinatarios` passa a capturar as colunas `cidade`/`status`/`plano` (header case/acento-insensível) em cada row, além de telefone/variáveis/botão já existentes.

### Fluxo e endpoints
1. **Importar** — `POST /{id}/destinatarios/importar` (estende o do v2): cria os destinatários com `csv_cidade/csv_status/csv_plano` + `body_params`/`button_param`, `status="pendente"`. Marca `campanha.origem="importado"`. Retorna `{importados, invalidos, amostra_invalidos, valores: {cidades, status, planos}}` (valores = distintos do que veio no CSV).
   - Obs: a campanha precisa existir antes do import → o form cria a campanha (rascunho) e então importa. (já é o padrão: `create_campanha` retorna o id.)
2. **Contagem ao vivo** — `POST /{id}/destinatarios/contagem` body `{cidade?, status?, plano?}` → `{total}` (conta destinatários `pendente` cujo `csv_*` casa o filtro). Alimenta o "X de Y vão receber".
3. **Selecionar + disparar** — no clique em **Disparar**: `POST /{id}/destinatarios/selecionar` body `{cidade?, status?, plano?}` marca os `pendente` que **não** casam como `status="excluido"`, recalcula `total_destinatarios` = selecionados, retorna `{selecionados}`. Em seguida o form chama o `POST /{id}/send` já existente (que enfileira a task; a task envia só os `pendente`).

> Sem filtro = todos os importados recebem (nenhum excluído). Campanhas de **segmento** (origem=segmento) seguem inalteradas (não passam por selecionar).

### Form (nova campanha)
- Origem "Importar CSV": botão **Importar** (sobe o arquivo, cria rascunho, guarda `campanhaId` + `valores` no estado).
- Depois do import: dropdowns de cidade/status/plano populados pelos `valores`; contador ao vivo (`/contagem`); botão **Disparar** (chama `selecionar` → `send`, com confirmação do total).

---

## Bloco 2 — Acompanhamento de entrega

Tudo na tela `/comunicados/{id}` (que já mostra métricas agregadas).

### Endpoints
- `GET /{id}/destinatarios?status=&limit=&cursor=` — lista destinatários: `{whatsapp, status, erro, enviada_em}`, filtro opcional por `status` (pendente/enviada/entregue/lida/falha), exclui `excluido` por padrão. Paginado (cursor por `id`/`enviada_em`, limit default 50).
- `POST /{id}/reenviar-falhas` — reseta os `status="falha"` para `pendente` (limpa `erro`/`wamid`), ajusta o contador `falhas`, põe `campanha.status="enviando"` e enfileira `send_campanha_task`. Retorna `{reenfileirados}`.
- `GET /{id}/resultado/export?format=csv` — StreamingResponse CSV com colunas `telefone,status,erro` de todos os destinatários (menos `excluido`). Admin only.

### Detalhe (frontend)
- Métricas (já existem) + **lista de contatos** com status e erro, com **filtro por status** (chips: Todos / Enviadas / Entregues / Lidas / Falhas). Polling enquanto `status="enviando"`.
- Botão **Reenviar falhas** (aparece se houver falhas).
- Botão **Exportar resultado** (CSV).

---

## API (resumo)

| Método | Rota | Função |
|---|---|---|
| POST | `/{id}/destinatarios/importar` | importa CSV (com csv_*), retorna valores |
| POST | `/{id}/destinatarios/contagem` | conta pendentes que casam o filtro |
| POST | `/{id}/destinatarios/selecionar` | marca não-selecionados como `excluido` |
| GET | `/{id}/destinatarios` | lista por status (paginado) |
| POST | `/{id}/reenviar-falhas` | re-enfileira as falhas |
| GET | `/{id}/resultado/export` | CSV telefone,status,erro |

Schemas novos: `ImportResult` (ganha `valores: SegmentoValores`), `ContagemOut {total}`, `SelecionarOut {selecionados}`, `DestinatarioOut {whatsapp, status, erro, enviada_em}`, `ReenviarResult {reenfileirados}`. Reusa `SegmentoFiltros`/`SegmentoValores`.

## Mudança no worker
`_send_campanha` já envia só `status="pendente"` em lotes — **nenhuma mudança necessária** (os `excluido` não entram; o reenviar-falhas volta as falhas pra `pendente`). Confirmar que o guard de materialização (pula resolução de segmento quando já há destinatários) cobre campanha importada.

## Testes (CI/deploy)
- Parser captura cidade/status/plano.
- `selecionar` marca corretamente os não-casantes como `excluido` e mantém os que casam como `pendente`; sem filtro não exclui ninguém.
- `contagem` conta certo.
- `reenviar-falhas` volta `falha`→`pendente`, limpa erro/wamid, ajusta contador.
- listagem filtra por status e exclui `excluido`.
- export gera CSV correto.

## Fora de escopo (futuro)
- Salvar/reaproveitar listas importadas entre campanhas.
- Dedup de telefones repetidos no CSV (hoje: cada linha vira um destinatário).
- Limite de tentativas de reenvio.
