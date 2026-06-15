# Lista de OS (cliente + busca) + paginação (OS e Conversas)

**Data:** 2026-06-15
**Status:** Aprovado (pendente implementação)

## Problema

Três melhorias nas telas admin de listagem:

1. **Conversas** — a lista mostra só o primeiro lote e "acaba", mesmo havendo mais. A API já pagina (cursor), mas a UI usa `useQuery` (página 1 só).
2. **Ordens de Serviço** — a lista mostra código/status/técnico/problema/endereço/criada, mas **não o nome do cliente**. A API **já retorna** `nome_cliente` (`OsListItem.nome_cliente`, populado em `list_os`); a UI só não exibe.
3. **OS — busca** — não há campo de busca. Hoje só filtra por status. Quer buscar por nome do cliente, técnico e código.

## Decisões (do brainstorming)

- **Busca de OS:** uma caixa de texto só, server-side, que casa **código + nome do cliente + nome do técnico**.
- **Paginação:** botão **"Carregar mais"** (não scroll infinito), em conversas e OS.
- **Escopo:** as três juntas, um spec só. Sem migration.

## Restrições que moldam o design

- **Nome do cliente é criptografado** (`clientes.nome_encrypted`) → não dá pra `ILIKE` no SQL. Mas `OrdemServico.nome_sgp` (coluna `Text`, plaintext, snapshot do nome na criação da OS) é buscável. A busca por cliente usa `nome_sgp`.
- **`useOsList` tem 3 consumidores** (`os-list.tsx`, `cliente-resumo-sgp.tsx`, `conversa-chat.tsx` — os 2 últimos embedados por `cliente_id`). NÃO mudar a forma desse hook. Criar `useOsListInfinite` separado pra tela da lista.
- **`useConversas` tem 1 consumidor** (`conversa-list.tsx`); `useTemConversaAguardando` faz fetch próprio. Pode converter `useConversas` pra infinite direto.

## Backend (1 mudança)

### `GET /api/v1/ordens_servico` — novo param `q`
`api/v1/ordens_servico.py::list_os` ganha `q: Annotated[str | None, Query()] = None`, repassado a `OrdemServicoRepo.list_paginated`.

### `OrdemServicoRepo.list_paginated` — filtro `q`
Adiciona `q: str | None = None`. Quando preenchido (após `strip`), aplica um `LEFT JOIN` em `Tecnico` (por `tecnico_id`) e um filtro:
```
WHERE (
  OrdemServico.codigo ILIKE :pat
  OR OrdemServico.nome_sgp ILIKE :pat
  OR Tecnico.nome ILIKE :pat
)
```
com `pat = f"%{q.strip()}%"`. Mantém os filtros existentes (status, tecnico_id, cliente_id) e a ordenação/cursor atuais. O `LEFT JOIN` (não inner) garante que OS sem técnico ainda apareçam (casando por código/cliente).

**Sem mudança em:** endpoint de conversas (já tem `q` + cursor), `nome_cliente` da OS (já retornado em `list_os`).

## Frontend

### `lib/api/types.ts`
`OsListFilters` ganha `q?: string`.

### `lib/api/queries.ts`
- **Novo** `useOsListInfinite({ status?, q? })` — `useInfiniteQuery`, monta querystring com `status`/`q`/`cursor`, `initialPageParam: undefined`, `getNextPageParam: (last) => last.next_cursor ?? undefined`. queryKey `['os-list-infinite', { status, q }]`.
- **Converte** `useConversas` pra `useInfiniteQuery` (mantém `status`/`q`/`canal_id`, `getNextPageParam` por `next_cursor`, mantém `refetchInterval: 15_000`). queryKey segue `['conversas', filters]`.
- `useOsList` antigo: **intacto**.

### `components/os-list.tsx`
- Coluna nova **Cliente** (`o.nome_cliente ?? '—'`), logo após a coluna **Código**.
- **Caixa de busca** (`Input`) com debounce de 300ms → estado `q` → passado a `useOsListInfinite`.
- Troca `useOsList` por `useOsListInfinite`; achata `data.pages.flatMap(p => p.items)`.
- Botão **"Carregar mais"** no fim: visível quando `hasNextPage`; `onClick={() => fetchNextPage()}`, `disabled={isFetchingNextPage}`.

### `components/conversa-list.tsx`
- Achata as páginas do infinite (`data.pages.flatMap(p => p.items)`).
- Botão **"Carregar mais"** (mesmo padrão). A busca `q` e os filtros já estão ligados — só adaptar o consumo de `data`.

## Comportamento

- Busca de OS: uma caixa; digita nome do cliente / técnico / código → filtra no servidor. Limpar → volta à lista paginada normal.
- "Carregar mais": cada clique anexa o próximo lote; some quando não há mais (`!hasNextPage`).
- OS com `nome_sgp` nulo não casam na busca por nome do cliente (filtro por status/código/técnico ainda pega). Aceitável.

## Testes

**Backend** (`tests/test_ordens_servico_api.py` ou equivalente existente):
- `q` por código → retorna a OS certa.
- `q` por nome do cliente (`nome_sgp`) → retorna.
- `q` por nome do técnico → retorna (valida o JOIN).
- `q` sem match → lista vazia.
- `q` + paginação: `next_cursor` continua funcionando com o filtro aplicado.

**Frontend:** sem testes automatizados (padrão do repo); validação por `tsc`/`lint` + CI.

## Fora de escopo

- Scroll infinito (escolhido "Carregar mais").
- Busca em nomes criptografados (usa `nome_sgp`).
- Paginação nas listas embedadas de OS por cliente (`cliente-resumo-sgp`, `conversa-chat`) — continuam página única.
- Migration (nenhuma).
