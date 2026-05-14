# Gestão de Planos CRUD — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o editor JSON raw por endpoints dedicados e uma página de cards com modal para criar, editar e excluir planos de internet — incluindo campos novos: `ativo`, `destaque`, `descricao`.

**Architecture:** Os planos continuam armazenados como JSONB na tabela `config` (chave `"planos"`). Novos endpoints em `/api/v1/planos` envolvem o `ConfigRepo` existente com CRUD indexado. O frontend ganha uma página `/planos` com cards por plano e modal de edição.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, Next.js 14, TanStack Query, shadcn/ui

---

## File Map

| Ação | Arquivo |
|------|---------|
| Create | `apps/api/src/ondeline_api/api/schemas/plano.py` |
| Create | `apps/api/src/ondeline_api/api/v1/planos.py` |
| Modify | `apps/api/src/ondeline_api/main.py` |
| Modify | `apps/api/src/ondeline_api/tools/consultar_planos.py` |
| Create | `apps/api/tests/test_planos.py` |
| Modify | `apps/dashboard/lib/api/types.ts` |
| Modify | `apps/dashboard/lib/api/queries.ts` |
| Create | `apps/dashboard/app/(admin)/planos/page.tsx` |
| Create | `apps/dashboard/components/planos-manager.tsx` |
| Create | `apps/dashboard/components/plano-modal.tsx` |
| Modify | `apps/dashboard/components/nav-sidebar.tsx` |

---

### Task 1: Schema Pydantic para Plano

**Files:**
- Create: `apps/api/src/ondeline_api/api/schemas/plano.py`

- [ ] **Step 1: Criar arquivo de schema**

```python
# apps/api/src/ondeline_api/api/schemas/plano.py
"""DTOs para planos de internet."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    preco: float = Field(gt=0)
    velocidade: str = Field(min_length=1, max_length=20)
    extras: list[str] = []
    descricao: str = ""
    ativo: bool = True
    destaque: bool = False


class PlanoOut(PlanoIn):
    index: int
```

- [ ] **Step 2: Verificar que o arquivo está correto**

```bash
cd apps/api && python -c "from ondeline_api.api.schemas.plano import PlanoIn, PlanoOut; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/plano.py
git commit -m "feat(planos): add PlanoIn/PlanoOut Pydantic schemas"
```

---

### Task 2: Router `/api/v1/planos` + Testes

**Files:**
- Create: `apps/api/src/ondeline_api/api/v1/planos.py`
- Create: `apps/api/tests/test_planos.py`

- [ ] **Step 1: Escrever os testes primeiro (TDD)**

```python
# apps/api/tests/test_planos.py
"""Testes de integração para /api/v1/planos."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.config import get_settings
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:  # type: ignore[type-arg]
    r: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield r
    await r.aclose()  # type: ignore[attr-defined]


@pytest.fixture
def app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    application = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _redis() -> Any:
        return redis_client

    application.dependency_overrides[get_db] = _db
    application.dependency_overrides[get_redis] = _redis
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _admin_token(client: AsyncClient, created_user: dict[str, Any]) -> str:
    r = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


@pytest.mark.asyncio
async def test_list_planos_public(client: AsyncClient) -> None:
    r = await client.get("/api/v1/planos")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "nome" in first
    assert "preco" in first
    assert "index" in first
    assert "ativo" in first
    assert "destaque" in first


@pytest.mark.asyncio
async def test_create_plano_requires_auth(client: AsyncClient) -> None:
    body = {"nome": "Teste", "preco": 99.0, "velocidade": "100MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.post("/api/v1/planos", json=body)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_plano(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "nome": "Fibra Max",
        "preco": 199.0,
        "velocidade": "200MB",
        "extras": ["IP fixo"],
        "descricao": "Para empresas",
        "ativo": True,
        "destaque": False,
    }
    r = await client.post("/api/v1/planos", json=body, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["nome"] == "Fibra Max"
    assert data["preco"] == 199.0
    assert isinstance(data["index"], int)

    r2 = await client.get("/api/v1/planos")
    names = [p["nome"] for p in r2.json()]
    assert "Fibra Max" in names


@pytest.mark.asyncio
async def test_update_plano(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"nome": "Para Editar", "preco": 100.0, "velocidade": "50MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.post("/api/v1/planos", json=body, headers=headers)
    idx = r.json()["index"]

    updated = {**body, "preco": 120.0, "destaque": True}
    r2 = await client.patch(f"/api/v1/planos/{idx}", json=updated, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["preco"] == 120.0
    assert r2.json()["destaque"] is True


@pytest.mark.asyncio
async def test_update_plano_not_found(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    body = {"nome": "X", "preco": 1.0, "velocidade": "1MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.patch("/api/v1/planos/9999", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_plano(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"nome": "Para Deletar", "preco": 50.0, "velocidade": "10MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.post("/api/v1/planos", json=body, headers=headers)
    idx = r.json()["index"]

    r2 = await client.delete(f"/api/v1/planos/{idx}", headers=headers)
    assert r2.status_code == 204

    r3 = await client.get("/api/v1/planos")
    names = [p["nome"] for p in r3.json()]
    assert "Para Deletar" not in names


@pytest.mark.asyncio
async def test_delete_plano_not_found(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    r = await client.delete("/api/v1/planos/9999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
```

- [ ] **Step 2: Rodar os testes e confirmar que falham (rota não existe)**

```bash
cd apps/api && pytest tests/test_planos.py -v 2>&1 | head -30
```

Expected: FAILED com `404 Not Found` ou `Connection refused` — confirma que as rotas ainda não existem.

- [ ] **Step 3: Implementar o router**

```python
# apps/api/src/ondeline_api/api/v1/planos.py
"""CRUD /api/v1/planos — leitura/escrita sobre config['planos']."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.plano import PlanoIn, PlanoOut
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.config import ConfigRepo

router = APIRouter(prefix="/api/v1/planos", tags=["planos"])
_admin_dep = Depends(require_role(Role.ADMIN))

_DEFAULT_PLANOS: list[dict] = [
    {
        "nome": "Essencial",
        "preco": 110.0,
        "velocidade": "35MB",
        "extras": [],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
    {
        "nome": "Plus",
        "preco": 130.0,
        "velocidade": "55MB",
        "extras": ["IPTV gratis"],
        "descricao": "",
        "ativo": True,
        "destaque": True,
    },
    {
        "nome": "Premium",
        "preco": 150.0,
        "velocidade": "55MB",
        "extras": ["IPTV", "camera comodato"],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
]


async def _load(repo: ConfigRepo) -> list[dict]:
    raw = await repo.get("planos")
    return raw if isinstance(raw, list) else _DEFAULT_PLANOS


@router.get("", response_model=list[PlanoOut])
async def list_planos(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlanoOut]:
    planos = await _load(ConfigRepo(session))
    return [PlanoOut(index=i, **p) for i, p in enumerate(planos)]


@router.post(
    "",
    response_model=PlanoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def create_plano(
    body: PlanoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlanoOut:
    repo = ConfigRepo(session)
    planos = await _load(repo)
    data = body.model_dump()
    planos.append(data)
    await repo.set("planos", planos)
    return PlanoOut(index=len(planos) - 1, **data)


@router.patch("/{index}", response_model=PlanoOut, dependencies=[_admin_dep])
async def update_plano(
    index: int,
    body: PlanoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlanoOut:
    repo = ConfigRepo(session)
    planos = await _load(repo)
    if index < 0 or index >= len(planos):
        raise HTTPException(status_code=404, detail="Plano not found")
    data = body.model_dump()
    planos[index] = data
    await repo.set("planos", planos)
    return PlanoOut(index=index, **data)


@router.delete("/{index}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_admin_dep])
async def delete_plano(
    index: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ConfigRepo(session)
    planos = await _load(repo)
    if index < 0 or index >= len(planos):
        raise HTTPException(status_code=404, detail="Plano not found")
    planos.pop(index)
    await repo.set("planos", planos)
```

- [ ] **Step 4: Registrar o router em `main.py`**

Adicionar após a linha `from ondeline_api.api.v1 import metricas as v1_metricas` em `apps/api/src/ondeline_api/main.py`:

```python
from ondeline_api.api.v1 import planos as v1_planos
```

Adicionar após `app.include_router(v1_metricas.router)`:

```python
app.include_router(v1_planos.router)
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

```bash
cd apps/api && pytest tests/test_planos.py -v
```

Expected: todos PASSED

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/planos.py \
        apps/api/src/ondeline_api/main.py \
        apps/api/tests/test_planos.py
git commit -m "feat(planos): CRUD endpoints GET/POST/PATCH/DELETE /api/v1/planos"
```

---

### Task 3: Atualizar tool `consultar_planos` para filtrar `ativo=True`

**Files:**
- Modify: `apps/api/src/ondeline_api/tools/consultar_planos.py`

- [ ] **Step 1: Atualizar `_DEFAULT_PLANOS` e adicionar filtro**

Substituir o conteúdo completo de `apps/api/src/ondeline_api/tools/consultar_planos.py`:

```python
"""Tool: consultar planos disponiveis (lidos do Config['planos'])."""
from __future__ import annotations

from typing import Any

from ondeline_api.repositories.config import ConfigRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

_DEFAULT_PLANOS = [
    {
        "nome": "Essencial",
        "preco": 110.0,
        "velocidade": "35MB",
        "extras": [],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
    {
        "nome": "Plus",
        "preco": 130.0,
        "velocidade": "55MB",
        "extras": ["IPTV gratis"],
        "descricao": "",
        "ativo": True,
        "destaque": True,
    },
    {
        "nome": "Premium",
        "preco": 150.0,
        "velocidade": "55MB",
        "extras": ["IPTV", "camera comodato"],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
]


@tool(
    name="consultar_planos",
    description="Retorna a lista de planos de internet disponiveis com preco e velocidade.",
    parameters=SCHEMA,
)
async def consultar_planos(ctx: ToolContext) -> dict[str, Any]:
    repo = ConfigRepo(ctx.session)
    raw = await repo.get("planos")
    planos = raw if isinstance(raw, list) else _DEFAULT_PLANOS
    planos_ativos = [p for p in planos if p.get("ativo", True)]
    return {"planos": planos_ativos, "pagamento": ["PIX", "Boleto"]}
```

- [ ] **Step 2: Rodar testes existentes do tool**

```bash
cd apps/api && pytest tests/test_tool_consultar_planos.py -v
```

Expected: PASSED (ou adaptar se os testes verificarem campos novos)

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/tools/consultar_planos.py
git commit -m "feat(planos): filtrar ativo=True na tool consultar_planos"
```

---

### Task 4: Tipos e Queries no Frontend

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: Adicionar tipos em `types.ts`**

Adicionar ao final de `apps/dashboard/lib/api/types.ts`:

```typescript
export interface PlanoIn {
  nome: string
  preco: number
  velocidade: string
  extras: string[]
  descricao: string
  ativo: boolean
  destaque: boolean
}

export interface PlanoOut extends PlanoIn {
  index: number
}
```

- [ ] **Step 2: Adicionar imports no topo de `queries.ts`**

Na seção de imports em `apps/dashboard/lib/api/queries.ts`, adicionar `PlanoIn` e `PlanoOut` à linha de import de types existente:

```typescript
import type {
  // ... tipos existentes ...
  PlanoIn,
  PlanoOut,
} from './types'
```

- [ ] **Step 3: Adicionar queries de planos ao final de `queries.ts`**

```typescript
// ── Planos ──────────────────────────────────────────────────────────

export function usePlanos() {
  return useQuery<PlanoOut[]>({
    queryKey: ['planos'],
    queryFn: () => apiFetch('/api/v1/planos'),
  })
}

export function useCreatePlano() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PlanoIn) =>
      apiFetch<PlanoOut>('/api/v1/planos', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planos'] }),
  })
}

export function useUpdatePlano(index: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PlanoIn) =>
      apiFetch<PlanoOut>(`/api/v1/planos/${index}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planos'] }),
  })
}

export function useDeletePlano() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (index: number) =>
      apiFetch<void>(`/api/v1/planos/${index}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planos'] }),
  })
}
```

- [ ] **Step 4: Verificar sem erros de TypeScript**

```bash
cd apps/dashboard && pnpm tsc --noEmit 2>&1 | head -20
```

Expected: sem erros novos

- [ ] **Step 5: Commit**

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(planos): tipos e queries TanStack para CRUD de planos"
```

---

### Task 5: Componente `PlanoModal`

**Files:**
- Create: `apps/dashboard/components/plano-modal.tsx`

- [ ] **Step 1: Criar o componente modal**

```typescript
// apps/dashboard/components/plano-modal.tsx
'use client'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCreatePlano, useUpdatePlano } from '@/lib/api/queries'
import type { PlanoIn, PlanoOut } from '@/lib/api/types'

interface PlanoModalProps {
  plano?: PlanoOut | null
  onClose: () => void
}

const EMPTY: PlanoIn = {
  nome: '',
  preco: 0,
  velocidade: '',
  extras: [],
  descricao: '',
  ativo: true,
  destaque: false,
}

export function PlanoModal({ plano, onClose }: PlanoModalProps) {
  const [form, setForm] = useState<PlanoIn>(plano ? { ...plano } : EMPTY)
  const [extrasInput, setExtrasInput] = useState('')
  const createPlano = useCreatePlano()
  const updatePlano = useUpdatePlano(plano?.index ?? -1)

  useEffect(() => {
    setForm(plano ? { ...plano } : EMPTY)
    setExtrasInput('')
  }, [plano])

  const isEditing = plano !== null && plano !== undefined
  const mutation = isEditing ? updatePlano : createPlano
  const isPending = mutation.isPending

  function setField<K extends keyof PlanoIn>(key: K, value: PlanoIn[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function addExtra() {
    const trimmed = extrasInput.trim()
    if (!trimmed) return
    setField('extras', [...form.extras, trimmed])
    setExtrasInput('')
  }

  function removeExtra(i: number) {
    setField('extras', form.extras.filter((_, idx) => idx !== i))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await mutation.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">
          {isEditing ? 'Editar Plano' : 'Novo Plano'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="nome">Nome</Label>
              <Input
                id="nome"
                value={form.nome}
                onChange={(e) => setField('nome', e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="preco">Preço (R$)</Label>
              <Input
                id="preco"
                type="number"
                min={0.01}
                step={0.01}
                value={form.preco}
                onChange={(e) => setField('preco', Number(e.target.value))}
                required
              />
            </div>
          </div>
          <div>
            <Label htmlFor="velocidade">Velocidade</Label>
            <Input
              id="velocidade"
              placeholder="ex: 55MB"
              value={form.velocidade}
              onChange={(e) => setField('velocidade', e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="descricao">Descrição (usada pelo bot)</Label>
            <Textarea
              id="descricao"
              rows={2}
              value={form.descricao}
              onChange={(e) => setField('descricao', e.target.value)}
            />
          </div>
          <div>
            <Label>Extras</Label>
            <div className="mt-1 flex gap-2">
              <Input
                placeholder="ex: IPTV gratis"
                value={extrasInput}
                onChange={(e) => setExtrasInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addExtra() } }}
              />
              <Button type="button" variant="outline" onClick={addExtra}>
                +
              </Button>
            </div>
            {form.extras.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {form.extras.map((ex, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800"
                  >
                    {ex}
                    <button
                      type="button"
                      onClick={() => removeExtra(i)}
                      className="ml-0.5 text-blue-600 hover:text-blue-900"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.ativo}
                onChange={(e) => setField('ativo', e.target.checked)}
              />
              Ativo
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.destaque}
                onChange={(e) => setField('destaque', e.target.checked)}
              />
              Destaque (recomendado pelo bot)
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Salvando…' : isEditing ? 'Salvar' : 'Criar'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd apps/dashboard && pnpm tsc --noEmit 2>&1 | grep "plano-modal" | head -10
```

Expected: sem erros

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/components/plano-modal.tsx
git commit -m "feat(planos): componente PlanoModal com form completo"
```

---

### Task 6: Página `/planos` com PlanosManager

**Files:**
- Create: `apps/dashboard/components/planos-manager.tsx`
- Create: `apps/dashboard/app/(admin)/planos/page.tsx`

- [ ] **Step 1: Criar componente `PlanosManager`**

```typescript
// apps/dashboard/components/planos-manager.tsx
'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { usePlanos, useDeletePlano } from '@/lib/api/queries'
import { PlanoModal } from '@/components/plano-modal'
import type { PlanoOut } from '@/lib/api/types'

export function PlanosManager() {
  const { data: planos, isLoading, error } = usePlanos()
  const deletePlano = useDeletePlano()
  const [editingPlano, setEditingPlano] = useState<PlanoOut | null | undefined>(undefined)

  // undefined = modal fechado, null = modal aberto para criação, PlanoOut = edição
  const modalOpen = editingPlano !== undefined

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando planos…</p>
  if (error) return <p className="text-sm text-destructive">Erro ao carregar planos</p>

  async function handleDelete(plano: PlanoOut) {
    if (!confirm(`Excluir o plano "${plano.nome}"?`)) return
    await deletePlano.mutateAsync(plano.index)
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Planos de Internet</h2>
        <Button onClick={() => setEditingPlano(null)}>+ Novo Plano</Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(planos ?? []).map((plano) => (
          <div
            key={plano.index}
            className={`rounded-lg border p-4 ${plano.destaque ? 'border-yellow-400 bg-yellow-50' : 'border-border bg-card'}`}
          >
            <div className="mb-1 flex items-start justify-between">
              <span className="font-semibold">{plano.nome}</span>
              <div className="flex gap-1">
                {plano.destaque && (
                  <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">
                    ⭐ destaque
                  </span>
                )}
                {!plano.ativo && (
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                    inativo
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              {plano.velocidade} · R$ {plano.preco.toFixed(2)}
            </p>
            {plano.descricao && (
              <p className="mt-1 text-xs text-muted-foreground">{plano.descricao}</p>
            )}
            {plano.extras.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {plano.extras.map((ex, i) => (
                  <span
                    key={i}
                    className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700"
                  >
                    {ex}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setEditingPlano(plano)}
              >
                Editar
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={deletePlano.isPending}
                onClick={() => handleDelete(plano)}
              >
                Excluir
              </Button>
            </div>
          </div>
        ))}
      </div>

      {modalOpen && (
        <PlanoModal
          plano={editingPlano}
          onClose={() => setEditingPlano(undefined)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Criar a página**

```typescript
// apps/dashboard/app/(admin)/planos/page.tsx
import { PlanosManager } from '@/components/planos-manager'

export default function PlanosPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Planos de Internet</h1>
        <p className="text-sm text-muted-foreground">
          Gerencie os planos apresentados pelo bot aos clientes
        </p>
      </div>
      <PlanosManager />
    </div>
  )
}
```

- [ ] **Step 3: Verificar TypeScript**

```bash
cd apps/dashboard && pnpm tsc --noEmit 2>&1 | grep -E "planos-manager|plano-modal|planos/page" | head -10
```

Expected: sem erros

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/components/planos-manager.tsx \
        apps/dashboard/app/(admin)/planos/page.tsx
git commit -m "feat(planos): página /planos com cards, modal e CRUD"
```

---

### Task 7: Link no menu lateral

**Files:**
- Modify: `apps/dashboard/components/nav-sidebar.tsx`

- [ ] **Step 1: Adicionar import do ícone e link no menu**

Em `apps/dashboard/components/nav-sidebar.tsx`, localizar a linha com os imports de ícones do Lucide e adicionar `Package`:

```typescript
import { BarChart3, CalendarClock, ClipboardList, MessageSquare, Package, Settings, UserPlus, Users, Wrench } from 'lucide-react'
```

No array `ITEMS`, adicionar o item de planos antes do item de configurações:

```typescript
  { href: '/planos', label: 'Planos', icon: Package, roles: ['admin'] },
  { href: '/config', label: 'Configurações', icon: Settings, roles: ['admin'] },
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd apps/dashboard && pnpm tsc --noEmit 2>&1 | grep "nav-sidebar" | head -5
```

Expected: sem erros

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/components/nav-sidebar.tsx
git commit -m "feat(planos): adicionar link /planos no menu lateral"
```

---

### Task 8: Smoke test visual

- [ ] **Step 1: Subir o servidor de desenvolvimento**

```bash
cd apps/dashboard && pnpm dev
```

- [ ] **Step 2: Verificar no browser**

1. Navegar para `http://localhost:3000/planos`
2. Confirmar que os 3 planos padrão aparecem como cards
3. Clicar "Editar" em um plano — modal deve abrir com campos preenchidos
4. Mudar o preço e salvar — card deve atualizar
5. Clicar "+ Novo Plano" — modal abre vazio
6. Criar um plano de teste — aparece na lista
7. Excluir o plano de teste — desaparece da lista

- [ ] **Step 3: Commit final**

```bash
git add -A
git commit -m "feat(planos): gestão completa de planos com CRUD visual"
```
