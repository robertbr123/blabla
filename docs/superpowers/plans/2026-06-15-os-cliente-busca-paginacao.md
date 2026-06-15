# Lista de OS (cliente + busca) + paginação — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar nome do cliente na lista de OS, busca por texto (código/cliente/técnico) na lista de OS, e botão "Carregar mais" (paginação cursor) nas listas de OS e Conversas.

**Architecture:** Backend ganha um filtro `q` no `list_paginated` da OS (LEFT JOIN em Tecnico + ILIKE em codigo/nome_sgp/tecnico.nome) exposto no endpoint `GET /api/v1/os`. Conversas e `nome_cliente` da OS já existem no backend. No frontend: hook novo `useOsListInfinite`, conversão de `useConversas` pra infinite, e as duas telas ganham "Carregar mais" + (OS) coluna Cliente e caixa de busca.

**Tech Stack:** FastAPI + SQLAlchemy async (API); Next.js + TanStack Query `useInfiniteQuery` (dashboard).

**Spec:** `docs/superpowers/specs/2026-06-15-os-cliente-busca-paginacao-design.md`

**Nota de ambiente:** Sem stack local — não rodar pytest/pnpm aqui; CI roda no push. Trabalhar na `main`, commit local por task, **sem push**. Cada commit termina com uma linha em branco seguida de:
`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

**Backend (`apps/api`):**
- Modify: `src/ondeline_api/repositories/ordem_servico.py` — `q` em `list_paginated`.
- Modify: `src/ondeline_api/api/v1/ordens_servico.py` — param `q` em `list_os`.
- Modify: `tests/test_v1_ordens_servico.py` — testes do `q` (nível repo).

**Dashboard (`apps/dashboard`):**
- Modify: `lib/api/queries.ts` — `OsListFilters.q`, `useOsListInfinite`, `useConversas`→infinite.
- Modify: `components/os-list.tsx` — coluna Cliente + busca + "Carregar mais".
- Modify: `components/conversa-list.tsx` — flatten páginas + "Carregar mais".

---

## Task 1: Filtro `q` no backend de OS (TDD)

**Files:**
- Test: `apps/api/tests/test_v1_ordens_servico.py`
- Modify: `apps/api/src/ondeline_api/repositories/ordem_servico.py`
- Modify: `apps/api/src/ondeline_api/api/v1/ordens_servico.py`

- [ ] **Step 1: Escrever o teste que falha (nível repo)**

Adicionar ao fim de `apps/api/tests/test_v1_ordens_servico.py`. Usa os helpers já existentes `_make_cliente_repo`, `_make_tecnico_repo`, `_make_os_repo` e o padrão de `test_list_paginated_by_cliente_id`. `repo.create` não aceita `nome_sgp`, então setamos direto no objeto.

```python
@pytest.mark.asyncio
async def test_list_paginated_q_busca_codigo_cliente_tecnico(
    db_session: AsyncSession,
) -> None:
    """q casa por codigo, nome_sgp (cliente) e nome do tecnico (via join)."""
    from ondeline_api.repositories.ordem_servico import OrdemServicoRepo as _Repo

    cliente = await _make_cliente_repo(db_session)
    tec = await _make_tecnico_repo(db_session)
    tec.nome = "Hercules Magalhaes"
    os1 = await _make_os_repo(db_session, cliente, tec)
    os1.nome_sgp = "James Montefusco"
    await db_session.flush()

    repo = _Repo(db_session)

    # por código (pega um pedaço do código real)
    rows, _ = await repo.list_paginated(q=os1.codigo[-4:])
    assert any(r.id == os1.id for r in rows)

    # por nome do cliente (nome_sgp)
    rows, _ = await repo.list_paginated(q="montefusco")
    assert [r.id for r in rows] == [os1.id]

    # por nome do técnico (join)
    rows, _ = await repo.list_paginated(q="hercules")
    assert [r.id for r in rows] == [os1.id]

    # sem match
    rows, _ = await repo.list_paginated(q="zzzz-nao-existe")
    assert rows == []
```

- [ ] **Step 2: Reasoning (não dá pra rodar local)** — falharia com `TypeError: list_paginated() got an unexpected keyword argument 'q'`.

- [ ] **Step 3: Implementar o filtro no repo**

Em `apps/api/src/ondeline_api/repositories/ordem_servico.py`:

(a) No import de modelos no topo, adicionar `Tecnico`:
```python
from ondeline_api.db.models.business import OrdemServico, OsStatus, Tecnico
```

(b) Em `list_paginated`, adicionar o parâmetro `q` na assinatura (depois de `cidade`):
```python
        cidade: str | None = None,  # filter via Cliente.cidade join
        q: str | None = None,
```

(c) Trocar o import local `from sqlalchemy import desc, select` por:
```python
        from sqlalchemy import desc, or_, select
```

(d) Após o bloco do `cliente_id` (linha `stmt = stmt.where(OrdemServico.cliente_id == cliente_id)`) e ANTES do `if cursor is not None:`, adicionar:
```python
        if q and q.strip():
            pat = f"%{q.strip()}%"
            stmt = stmt.outerjoin(
                Tecnico, OrdemServico.tecnico_id == Tecnico.id
            ).where(
                or_(
                    OrdemServico.codigo.ilike(pat),
                    OrdemServico.nome_sgp.ilike(pat),
                    Tecnico.nome.ilike(pat),
                )
            )
```
O `outerjoin` (não inner) garante que OS sem técnico ainda apareçam casando por código/cliente. Como é um técnico por OS, o join não duplica linhas; `.scalars()` segue retornando `OrdemServico`.

- [ ] **Step 4: Expor `q` no endpoint**

Em `apps/api/src/ondeline_api/api/v1/ordens_servico.py`, no `list_os` (linha ~125), adicionar o parâmetro depois de `cliente_id`:
```python
    q: Annotated[str | None, Query()] = None,
```
E passar pro repo na chamada `repo.list_paginated(...)`:
```python
        cliente_id=cliente_id,
        q=q,
        cursor=parse_cursor(cursor),
```
`Query` e `Annotated` já estão importados no arquivo (usados pelos outros params).

- [ ] **Step 5: Rodar os testes (quando no CI)**

Run: `cd apps/api && uv run pytest tests/test_v1_ordens_servico.py -k "q_busca or list_paginated" -v`
Expected: PASS (o teste novo + os de list existentes).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/ordem_servico.py apps/api/src/ondeline_api/api/v1/ordens_servico.py apps/api/tests/test_v1_ordens_servico.py
git commit -m "feat(os): busca q (codigo/cliente/tecnico) na lista de OS"
```

---

## Task 2: Hooks do dashboard (`useOsListInfinite` + `useConversas` infinite)

**Files:**
- Modify: `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: Adicionar `q` ao `OsListFilters`**

Em `apps/dashboard/lib/api/queries.ts`, na interface `OsListFilters` (linha ~563), adicionar:
```typescript
  q?: string
```

- [ ] **Step 2: Criar `useOsListInfinite`**

Logo após a função `useOsList` (que termina antes de outra `export function`), adicionar. `useInfiniteQuery`, `apiFetch` e o tipo já estão disponíveis no arquivo (`useInfiniteQuery` é importado na linha 1):
```typescript
export function useOsListInfinite(filters: { status?: string; q?: string } = {}) {
  return useInfiniteQuery<CursorPage<import('./types').OsListItem>>({
    queryKey: ['os-list-infinite', filters],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams()
      if (filters.status) params.set('status', filters.status)
      if (filters.q) params.set('q', filters.q)
      if (pageParam) params.set('cursor', pageParam as string)
      const qs = params.toString()
      return apiFetch(`/api/v1/os${qs ? `?${qs}` : ''}`)
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  })
}
```

- [ ] **Step 3: Converter `useConversas` pra infinite**

Substituir a função `useConversas` inteira (linhas ~48-59, o bloco que hoje usa `useQuery<CursorPage<ConversaListItem>>`) por:
```typescript
export function useConversas(filters: ConversaListFilters = {}) {
  return useInfiniteQuery<CursorPage<ConversaListItem>>({
    queryKey: ['conversas', filters],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams()
      if (filters.status) params.set('status', filters.status)
      if (filters.q) params.set('q', filters.q)
      if (filters.canal_id) params.set('canal_id', filters.canal_id)
      if (pageParam) params.set('cursor', pageParam as string)
      const qs = params.toString()
      return apiFetch(`/api/v1/conversas${qs ? `?${qs}` : ''}`)
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    refetchInterval: 15_000,
  })
}
```
NÃO mexer em `useTemConversaAguardando` (faz fetch próprio, continua igual).

- [ ] **Step 4: Verificar typecheck**

Run: `cd apps/dashboard && pnpm tsc --noEmit` (se pnpm disponível; senão verificar por inspeção e reportar). Atenção: `useConversas` agora retorna `InfiniteData` — o `conversa-list.tsx` será adaptado na Task 4 (typecheck pode acusar o consumo antigo até lá; é esperado).

- [ ] **Step 5: Commit**

```bash
git add apps/dashboard/lib/api/queries.ts
git commit -m "feat(dashboard): useOsListInfinite + useConversas infinite (paginacao cursor)"
```

---

## Task 3: Lista de OS — coluna Cliente + busca + "Carregar mais"

**Files:**
- Modify: `apps/dashboard/components/os-list.tsx`

- [ ] **Step 1: Trocar imports e hook**

Trocar a linha de import de queries (linha 8):
```tsx
import { useDeleteOs, useOsListInfinite, useTecnicos } from '@/lib/api/queries'
```
Adicionar `Input` e `Search` aos imports (linha 4 e 7). Trocar a linha 4:
```tsx
import { ClipboardList, Plus, Search, Trash2, UserCog } from 'lucide-react'
```
E adicionar o import do Input após o import do Button (linha 6):
```tsx
import { Input } from '@/components/ui/input'
```

- [ ] **Step 2: Estado de busca + consumo do hook infinite**

Trocar o bloco (linhas 35-41):
```tsx
  const [status, setStatus] = useState('')
  const [reatribuirOsId, setReatribuirOsId] = useState<string | null>(null)
  const { data, isLoading, error } = useOsList({ status: status || undefined })
  const { data: tecnicosData } = useTecnicos({})
  const tecnicoNomePorId = new Map(
    (tecnicosData?.items ?? []).map((t) => [t.id, t.nome])
  )
```
por:
```tsx
  const [status, setStatus] = useState('')
  const [busca, setBusca] = useState('')
  const [q, setQ] = useState('')
  const [reatribuirOsId, setReatribuirOsId] = useState<string | null>(null)
  // debounce 300ms: digita em `busca`, aplica em `q` (o que vai pra API)
  useEffect(() => {
    const t = setTimeout(() => setQ(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])
  const {
    data, isLoading, error, hasNextPage, fetchNextPage, isFetchingNextPage,
  } = useOsListInfinite({ status: status || undefined, q: q || undefined })
  const oss = data?.pages.flatMap((p) => p.items) ?? []
  const { data: tecnicosData } = useTecnicos({})
  const tecnicoNomePorId = new Map(
    (tecnicosData?.items ?? []).map((t) => [t.id, t.nome])
  )
```
E adicionar `useEffect` ao import do react (linha 3):
```tsx
import { useEffect, useState } from 'react'
```

- [ ] **Step 3: Caixa de busca na toolbar**

No `<div className="flex items-center gap-3">` (linha 51), adicionar a busca ANTES do `<Select>` de status:
```tsx
        <div className="relative max-w-xs flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por código, cliente ou técnico…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="pl-8"
          />
        </div>
```

- [ ] **Step 4: Substituir `data.items` por `oss` e adicionar coluna Cliente**

(a) Trocar `data && data.items.length === 0` (linha 77) por `!isLoading && oss.length === 0`.

(b) Trocar `data && data.items.length > 0` (linha 94) por `oss.length > 0`.

(c) Trocar `data.items.map((o: OsListItem) =>` (linha 109) por `oss.map((o: OsListItem) =>`.

(d) Adicionar o header da coluna Cliente logo após o `<th>Código</th>` (linha 99):
```tsx
                <th className="px-4 py-2.5 font-semibold">Cliente</th>
```

(e) Adicionar a célula Cliente logo após a célula do código (depois do `</td>` que fecha o link do código, linha 115):
```tsx
                  <td className="px-4 py-3">{o.nome_cliente ?? '—'}</td>
```

- [ ] **Step 5: Botão "Carregar mais"**

Logo após o `</div>` que fecha o bloco `oss.length > 0` (a `<div className="rounded-md border bg-card overflow-hidden">`, linha ~152-153), adicionar antes do fechamento do componente:
```tsx
      {hasNextPage && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Carregando…' : 'Carregar mais'}
          </Button>
        </div>
      )}
```

- [ ] **Step 6: Verificar typecheck/lint**

Run: `cd apps/dashboard && pnpm tsc --noEmit && pnpm lint` (se disponível; senão por inspeção). Conferir: `Search`/`Trash2`/`UserCog`/`Plus`/`ClipboardList` são exports válidos do lucide-react; nenhuma aspas reta nova em JSX (o `…` é unicode, ok).

- [ ] **Step 7: Commit**

```bash
git add apps/dashboard/components/os-list.tsx
git commit -m "feat(os): coluna Cliente + busca + carregar mais na lista de OS"
```

---

## Task 4: Lista de Conversas — flatten + "Carregar mais"

**Files:**
- Modify: `apps/dashboard/components/conversa-list.tsx`

- [ ] **Step 1: Consumir o hook infinite + flatten**

Trocar o bloco do hook (linhas 104-108):
```tsx
  const { data, isLoading, error } = useConversas({
    status: status || undefined,
    q: q || undefined,
    canal_id: canalId || undefined,
  })
```
por:
```tsx
  const {
    data, isLoading, error, hasNextPage, fetchNextPage, isFetchingNextPage,
  } = useConversas({
    status: status || undefined,
    q: q || undefined,
    canal_id: canalId || undefined,
  })
  const conversas = data?.pages.flatMap((p) => p.items) ?? []
```

- [ ] **Step 2: Substituir `data.items` por `conversas`**

(a) `data && data.items.length === 0` (linha ~167) → `!isLoading && conversas.length === 0`.

(b) `data && data.items.length > 0` (linha ~173) → `conversas.length > 0`.

(c) `data.items.map((c) => {` (linha 184) → `conversas.map((c) => {`.

- [ ] **Step 3: Botão "Carregar mais"**

Logo após o `</div>` que fecha o bloco `conversas.length > 0` (a `<div className="rounded-md border bg-card overflow-hidden">`), antes do `</div>` final do componente (linha ~239-240), adicionar:
```tsx
      {hasNextPage && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Carregando…' : 'Carregar mais'}
          </Button>
        </div>
      )}
```
`Button` já está importado no arquivo (linha 6).

- [ ] **Step 4: Verificar typecheck/lint**

Run: `cd apps/dashboard && pnpm tsc --noEmit && pnpm lint` (se disponível; senão por inspeção). Conferir que não sobrou nenhum `data.items` no arquivo.

- [ ] **Step 5: Commit**

```bash
git add apps/dashboard/components/conversa-list.tsx
git commit -m "feat(conversas): carregar mais (paginacao cursor) na lista"
```

---

## Self-Review (preenchido)

**Spec coverage:**
- `q` no backend de OS (codigo/nome_sgp/tecnico via JOIN) → Task 1 ✅
- `q` exposto no endpoint → Task 1 ✅
- Coluna Cliente (usa `nome_cliente` já retornado) → Task 3 ✅
- Caixa de busca única (debounce) → Task 3 ✅
- "Carregar mais" OS → Task 3 ✅
- "Carregar mais" Conversas → Task 4 ✅
- `useOsList` antigo intacto (embedados não quebram) → não tocado; novo hook separado ✅
- `useConversas` infinite (1 consumidor adaptado) → Task 2 + Task 4 ✅

**Placeholder scan:** sem TODO/TBD; cada passo tem código ou comando concreto.

**Type consistency:** `useOsListInfinite`/`useConversas` retornam `InfiniteData<CursorPage<T>>`; ambos componentes achatam via `data.pages.flatMap(p => p.items)` e usam `hasNextPage`/`fetchNextPage`/`isFetchingNextPage` (API do `useInfiniteQuery`). `getNextPageParam` lê `last.next_cursor` (campo real do `CursorPage`). `OsListFilters.q` casa com o param `q` do endpoint. Repo `list_paginated(q=...)` casa com a chamada do endpoint.

**Ordem de execução:** Task 2 deixa `conversa-list.tsx` temporariamente incompatível (typecheck) até a Task 4 — esperado e anotado; a sequência fecha tudo.
