# Comunicados — Editar e Excluir — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir editar (status rascunho/erro) e excluir (qualquer status exceto enviando) campanhas de comunicado, via API e dashboard.

**Architecture:** Dois endpoints novos no router de comunicados (`PATCH` e `DELETE`) com guards por status. Hard delete usa o `ondelete="CASCADE"` já existente em `campanha_destinatarios`. No dashboard: botão Excluir na tela de detalhe, e uma página/form de edição focada (título, variáveis, botão, segmento — canal/template ficam read-only).

**Tech Stack:** FastAPI + SQLAlchemy async + Pydantic (API); Next.js + React Query + TanStack (dashboard). Testes API via httpx AsyncClient (pytest-asyncio).

**Spec:** `docs/superpowers/specs/2026-06-15-comunicados-editar-excluir-design.md`

**Nota de ambiente:** O Robert não roda pytest/lint localmente — os testes rodam no CI após o push. Os passos "rode o teste" descrevem o comando e o resultado esperado pra quando rodar no CI/máquina de deploy; ao executar localmente sem stack, pular a execução e seguir, confiando no CI.

---

## File Structure

**API (`apps/api`):**
- Modify: `src/ondeline_api/api/schemas/comunicado.py` — novo `CampanhaUpdate`.
- Modify: `src/ondeline_api/api/v1/comunicados.py` — endpoints `PATCH` e `DELETE`.
- Modify: `tests/test_comunicados_api.py` — testes dos 2 endpoints.

**Dashboard (`apps/dashboard`):**
- Modify: `lib/api/types.ts` — interface `CampanhaUpdate`.
- Modify: `lib/api/queries.ts` — hooks `usePatchCampanha`, `useDeleteCampanha`.
- Create: `components/comunicado-edit-form.tsx` — form de edição focado.
- Create: `app/(admin)/comunicados/[id]/editar/page.tsx` — rota de edição.
- Modify: `components/comunicado-detail.tsx` — botões Editar (link) e Excluir.

---

## Task 1: Schema `CampanhaUpdate` (API)

**Files:**
- Modify: `apps/api/src/ondeline_api/api/schemas/comunicado.py`

- [ ] **Step 1: Adicionar o schema**

No fim de `apps/api/src/ondeline_api/api/schemas/comunicado.py` (depois de `ReenviarResult`, mantendo o estilo do arquivo), adicionar:

```python
class CampanhaUpdate(BaseModel):
    """Campos editáveis de uma campanha em rascunho/erro. Todos opcionais —
    o endpoint aplica só os enviados (exclude_unset)."""
    titulo: str | None = None
    template_name: str | None = None
    template_language: str | None = None
    body_params: list[str] | None = None
    header_media_url: str | None = None
    segmentacao: SegmentoFiltros | None = None
    button_param: str | None = None
```

- [ ] **Step 2: Verificar import**

`SegmentoFiltros` e `BaseModel` já estão definidos/importados no topo do arquivo (linhas 9 e 12). Nenhum import novo necessário.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/comunicado.py
git commit -m "feat(comunicados): schema CampanhaUpdate"
```

---

## Task 2: Endpoint `PATCH /{campanha_id}` (API, TDD)

**Files:**
- Test: `apps/api/tests/test_comunicados_api.py`
- Modify: `apps/api/src/ondeline_api/api/v1/comunicados.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao fim de `apps/api/tests/test_comunicados_api.py`. Reusa os helpers `_auth` e a fixture `app_and_admin` já no arquivo. Cria uma campanha via POST, edita o título via PATCH, e valida que persistiu; e que editar uma campanha concluída dá 409.

```python
@pytest.mark.asyncio
async def test_editar_campanha_rascunho(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin
    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
        cloud_phone_id="1", cloud_waba_id="2",
    )
    db_session.add(canal)
    await db_session.commit()

    r = await client.post(
        "/api/v1/admin/comunicados",
        json={
            "titulo": "Errado", "canal_id": str(canal.id),
            "template_name": "comunicado_geral", "body_params": [],
            "segmentacao": {},
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    camp_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/admin/comunicados/{camp_id}",
        json={"titulo": "Corrigido", "body_params": ["https://novo"]},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["titulo"] == "Corrigido"
    assert r.json()["body_params"] == ["https://novo"]


@pytest.mark.asyncio
async def test_editar_campanha_concluida_409(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin
    from ondeline_api.db.models.business import Campanha

    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
        cloud_phone_id="1", cloud_waba_id="2",
    )
    db_session.add(canal)
    await db_session.flush()
    camp = Campanha(
        titulo="Feita", canal_id=canal.id, template_name="comunicado_geral",
        status="concluida",
    )
    db_session.add(camp)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/admin/comunicados/{camp.id}",
        json={"titulo": "Nope"},
        headers=_auth(token),
    )
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_editar_campanha_inexistente_404(app_and_admin: Any) -> None:
    client, token, _admin, _db = app_and_admin
    r = await client.patch(
        f"/api/v1/admin/comunicados/{uuid4()}",
        json={"titulo": "X"},
        headers=_auth(token),
    )
    assert r.status_code == 404, r.text
```

- [ ] **Step 2: Rodar o teste pra ver falhar**

Run: `cd apps/api && uv run pytest tests/test_comunicados_api.py::test_editar_campanha_rascunho -v`
Expected: FAIL com 405 Method Not Allowed (endpoint PATCH ainda não existe).

- [ ] **Step 3: Implementar o endpoint PATCH**

Em `apps/api/src/ondeline_api/api/v1/comunicados.py`, adicionar o import do schema no bloco `from ondeline_api.api.schemas.comunicado import (...)` (ordem alfabética, depois de `CampanhaListItem`):

```python
    CampanhaUpdate,
```

Depois adicionar o endpoint logo após `get_campanha` (depois da linha que fecha o `return CampanhaDetail(...)`), reusando o `CampanhaRepo` e a mesma montagem do `CampanhaDetail` do GET:

```python
@router.patch("/{campanha_id}", dependencies=[_admin_dep])
async def editar_campanha(
    campanha_id: UUID,
    body: CampanhaUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CampanhaDetail:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if c.status not in {"rascunho", "erro"}:
        raise HTTPException(status_code=409, detail=f"campanha já está '{c.status}'")
    data = body.model_dump(exclude_unset=True)
    if "segmentacao" in data and data["segmentacao"] is not None:
        data["segmentacao"] = body.segmentacao.model_dump(exclude_none=True)  # type: ignore[union-attr]
    for field, value in data.items():
        setattr(c, field, value)
    await session.commit()
    counts = await repo.status_counts(campanha_id)
    return CampanhaDetail(
        id=c.id, titulo=c.titulo, template_name=c.template_name, status=c.status,
        total_destinatarios=c.total_destinatarios, enviadas=c.enviadas, falhas=c.falhas,
        created_at=c.created_at, canal_id=c.canal_id, template_language=c.template_language,
        body_params=list(c.body_params or []), header_media_url=c.header_media_url,
        segmentacao=SegmentoFiltros.model_validate(c.segmentacao or {}),
        started_at=c.started_at, finished_at=c.finished_at, status_counts=counts,
    )
```

- [ ] **Step 4: Rodar os testes pra ver passar**

Run: `cd apps/api && uv run pytest tests/test_comunicados_api.py -k editar -v`
Expected: PASS nos 3 (`test_editar_campanha_rascunho`, `test_editar_campanha_concluida_409`, `test_editar_campanha_inexistente_404`).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/comunicados.py apps/api/tests/test_comunicados_api.py
git commit -m "feat(comunicados): PATCH /{id} edita campanha rascunho/erro"
```

---

## Task 3: Endpoint `DELETE /{campanha_id}` (API, TDD)

**Files:**
- Test: `apps/api/tests/test_comunicados_api.py`
- Modify: `apps/api/src/ondeline_api/api/v1/comunicados.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao fim de `apps/api/tests/test_comunicados_api.py`. Testa: excluir rascunho → 204 e some do banco; excluir concluída → 204 (permitido); excluir `enviando` → 409; inexistente → 404.

```python
@pytest.mark.asyncio
async def test_excluir_campanha_rascunho(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin
    from sqlalchemy import select as _select

    from ondeline_api.db.models.business import Campanha, CampanhaDestinatario

    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
        cloud_phone_id="1", cloud_waba_id="2",
    )
    db_session.add(canal)
    await db_session.flush()
    camp = Campanha(
        titulo="Lixo", canal_id=canal.id, template_name="comunicado_geral",
        status="rascunho",
    )
    db_session.add(camp)
    await db_session.flush()
    db_session.add(
        CampanhaDestinatario(campanha_id=camp.id, whatsapp="5592111", status="pendente")
    )
    await db_session.commit()
    camp_id = camp.id

    r = await client.delete(
        f"/api/v1/admin/comunicados/{camp_id}", headers=_auth(token)
    )
    assert r.status_code == 204, r.text

    # sumiu do banco (e os destinatários via cascade)
    found = (
        await db_session.execute(_select(Campanha).where(Campanha.id == camp_id))
    ).scalar_one_or_none()
    assert found is None
    dests = (
        await db_session.execute(
            _select(CampanhaDestinatario).where(
                CampanhaDestinatario.campanha_id == camp_id
            )
        )
    ).scalars().all()
    assert list(dests) == []


@pytest.mark.asyncio
async def test_excluir_campanha_concluida_ok(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin
    from ondeline_api.db.models.business import Campanha

    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
        cloud_phone_id="1", cloud_waba_id="2",
    )
    db_session.add(canal)
    await db_session.flush()
    camp = Campanha(
        titulo="Feita", canal_id=canal.id, template_name="comunicado_geral",
        status="concluida",
    )
    db_session.add(camp)
    await db_session.commit()

    r = await client.delete(
        f"/api/v1/admin/comunicados/{camp.id}", headers=_auth(token)
    )
    assert r.status_code == 204, r.text


@pytest.mark.asyncio
async def test_excluir_campanha_enviando_409(app_and_admin: Any) -> None:
    client, token, _admin, db_session = app_and_admin
    from ondeline_api.db.models.business import Campanha

    canal = Canal(
        slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
        cloud_phone_id="1", cloud_waba_id="2",
    )
    db_session.add(canal)
    await db_session.flush()
    camp = Campanha(
        titulo="Rodando", canal_id=canal.id, template_name="comunicado_geral",
        status="enviando",
    )
    db_session.add(camp)
    await db_session.commit()

    r = await client.delete(
        f"/api/v1/admin/comunicados/{camp.id}", headers=_auth(token)
    )
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_excluir_campanha_inexistente_404(app_and_admin: Any) -> None:
    client, token, _admin, _db = app_and_admin
    r = await client.delete(
        f"/api/v1/admin/comunicados/{uuid4()}", headers=_auth(token)
    )
    assert r.status_code == 404, r.text
```

- [ ] **Step 2: Rodar o teste pra ver falhar**

Run: `cd apps/api && uv run pytest tests/test_comunicados_api.py::test_excluir_campanha_rascunho -v`
Expected: FAIL com 405 Method Not Allowed (endpoint DELETE ainda não existe).

- [ ] **Step 3: Implementar o endpoint DELETE**

Em `apps/api/src/ondeline_api/api/v1/comunicados.py`, adicionar logo após o endpoint `editar_campanha` (Task 2):

```python
@router.delete("/{campanha_id}", status_code=204, dependencies=[_admin_dep])
async def excluir_campanha(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if c.status == "enviando":
        raise HTTPException(
            status_code=409, detail="cancele a campanha antes de excluir"
        )
    await session.delete(c)
    await session.commit()
```

Nota: o `ondelete="CASCADE"` em `campanha_destinatarios.campanha_id` (business.py:900) apaga os destinatários no banco. O `await session.delete(c)` do ORM dispara o cascade do banco no commit.

- [ ] **Step 4: Rodar os testes pra ver passar**

Run: `cd apps/api && uv run pytest tests/test_comunicados_api.py -k excluir -v`
Expected: PASS nos 4.

- [ ] **Step 5: Rodar a suíte de comunicados inteira (regressão)**

Run: `cd apps/api && uv run pytest tests/test_comunicados_api.py -v`
Expected: todos PASS (os antigos + 7 novos).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/comunicados.py apps/api/tests/test_comunicados_api.py
git commit -m "feat(comunicados): DELETE /{id} exclui campanha (bloqueia enviando)"
```

---

## Task 4: Types e hooks do dashboard

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: Adicionar a interface `CampanhaUpdate`**

Em `apps/dashboard/lib/api/types.ts`, logo após a interface `CampanhaCreate` (termina na linha ~996), adicionar:

```typescript
export interface CampanhaUpdate {
  titulo?: string
  template_name?: string
  template_language?: string
  body_params?: string[]
  header_media_url?: string | null
  segmentacao?: SegmentoFiltros
  button_param?: string | null
}
```

- [ ] **Step 2: Adicionar os hooks**

Em `apps/dashboard/lib/api/queries.ts`, no bloco de Comunicados (após `useReenviarFalhas`, ~linha 1905, antes de `resultadoExportUrl`), adicionar. Seguem o padrão de `usePatchCanal` (PATCH com `{id, body}`) e `useDeleteEstoqueItem` (DELETE retornando void), invalidando as queries `['campanhas']` e `['campanha', id]`. Usa o `qc` do `useQueryClient()` — confirmar que o arquivo já importa `useQueryClient` (importa; usado em vários hooks acima).

```typescript
export function usePatchCampanha() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: import('./types').CampanhaUpdate }) =>
      apiFetch<import('./types').CampanhaDetail>(`/api/v1/admin/comunicados/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['campanhas'] })
      qc.invalidateQueries({ queryKey: ['campanha', id] })
    },
  })
}

export function useDeleteCampanha() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/admin/comunicados/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campanhas'] }),
  })
}
```

- [ ] **Step 3: Verificar typecheck**

Run: `cd apps/dashboard && pnpm tsc --noEmit`
Expected: sem erros novos relacionados a `CampanhaUpdate`/`usePatchCampanha`/`useDeleteCampanha`.

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(comunicados): hooks usePatchCampanha + useDeleteCampanha"
```

---

## Task 5: Form de edição (dashboard)

**Files:**
- Create: `apps/dashboard/components/comunicado-edit-form.tsx`
- Create: `apps/dashboard/app/(admin)/comunicados/[id]/editar/page.tsx`

Escopo do form: edita **título, variáveis (body_params), valor do botão e filtros de segmento**. Canal e template ficam **read-only** (trocar template muda o schema de variáveis — pra isso, excluir e recriar). Prefill vem do `useCampanha(id)`. As variáveis são casadas pelo template via `useBroadcastTemplates`, mapeando `body_params[indice-1]`.

- [ ] **Step 1: Criar o componente do form**

Criar `apps/dashboard/components/comunicado-edit-form.tsx`:

```tsx
'use client'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Save } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  useBroadcastTemplates,
  useCampanha,
  usePatchCampanha,
  useSegmentoValores,
} from '@/lib/api/queries'
import type { SegmentoFiltros } from '@/lib/api/types'

const EDITAVEL = new Set(['rascunho', 'erro'])

export function ComunicadoEditForm({ id }: { id: string }) {
  const router = useRouter()
  const { data: c, isLoading } = useCampanha(id)
  const { data: templates } = useBroadcastTemplates()
  const { data: valores } = useSegmentoValores()
  const patch = usePatchCampanha()

  const [titulo, setTitulo] = useState('')
  const [vars, setVars] = useState<Record<number, string>>({})
  const [botao, setBotao] = useState('')
  const [filtros, setFiltros] = useState<SegmentoFiltros>({})
  const [carregado, setCarregado] = useState(false)

  const template = useMemo(
    () => templates?.find((t) => t.name === c?.template_name),
    [templates, c?.template_name],
  )
  const botaoDinamico = template?.botoes?.find((b) => b.url_dinamica)

  // Prefill uma vez quando a campanha chega.
  useEffect(() => {
    if (!c || carregado) return
    setTitulo(c.titulo)
    setFiltros(c.segmentacao ?? {})
    const m: Record<number, string> = {}
    ;(c.body_params ?? []).forEach((v, i) => {
      m[i + 1] = v
    })
    setVars(m)
    setCarregado(true)
  }, [c, carregado])

  if (isLoading || !c) return <p className="text-sm text-muted-foreground">Carregando…</p>

  if (!EDITAVEL.has(c.status)) {
    return (
      <p className="text-sm text-muted-foreground">
        Só dá pra editar campanhas em rascunho ou com erro. Esta está “{c.status}”.
      </p>
    )
  }

  function buildBodyParams(): string[] {
    return (template?.variaveis ?? [])
      .slice()
      .sort((a, b) => a.indice - b.indice)
      .map((v) => vars[v.indice] ?? '')
  }

  async function salvar() {
    try {
      await patch.mutateAsync({
        id,
        body: {
          titulo,
          body_params: buildBodyParams(),
          segmentacao: filtros,
          button_param: botaoDinamico ? botao || null : null,
        },
      })
      toast.success('Comunicado atualizado')
      router.push(`/comunicados/${id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <label className="text-sm font-medium">Título</label>
        <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} />
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Template</label>
        <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm font-mono">
          {c.template_name}
        </p>
        <p className="text-xs text-muted-foreground">
          Pra trocar o template ou o canal, exclua e crie de novo.
        </p>
      </div>

      {template?.variaveis.map((v) => (
        <div key={v.indice} className="space-y-1.5">
          <label className="text-sm font-medium">{v.label}</label>
          <Input
            value={vars[v.indice] ?? ''}
            onChange={(e) => setVars((s) => ({ ...s, [v.indice]: e.target.value }))}
            placeholder={v.tipo === 'url' ? 'https://…' : ''}
          />
        </div>
      ))}

      {botaoDinamico && (
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Valor do botão ({botaoDinamico.texto})</label>
          <Input value={botao} onChange={(e) => setBotao(e.target.value)} placeholder="https://…" />
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={filtros.cidade ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, cidade: e.target.value || undefined }))}
        >
          <option value="">Cidade (todas)</option>
          {(valores?.cidades ?? []).map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={filtros.status ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, status: e.target.value || undefined }))}
        >
          <option value="">Status (todos)</option>
          {(valores?.status ?? []).map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={filtros.plano ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, plano: e.target.value || undefined }))}
        >
          <option value="">Plano (todos)</option>
          {(valores?.planos ?? []).map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
      </div>

      <button
        type="button"
        onClick={salvar}
        disabled={!titulo || patch.isPending}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        <Save className="h-4 w-4" /> {patch.isPending ? 'Salvando…' : 'Salvar'}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Criar a rota de edição**

Criar `apps/dashboard/app/(admin)/comunicados/[id]/editar/page.tsx`. Seguir o mesmo formato da rota `[id]/page.tsx` (que renderiza `ComunicadoDetail`). Verificar primeiro como `[id]/page.tsx` recebe params (App Router — pode ser `Promise<{id}>` com `await`, ou objeto direto). Assumindo o padrão Next 15 (params como Promise):

```tsx
import { ComunicadoEditForm } from '@/components/comunicado-edit-form'

export default async function EditarComunicadoPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    <div className="mx-auto max-w-2xl py-6">
      <h1 className="mb-6 text-2xl font-semibold">Editar comunicado</h1>
      <ComunicadoEditForm id={id} />
    </div>
  )
}
```

Se a `[id]/page.tsx` existente usar params como objeto direto (não-Promise), copiar a assinatura de lá em vez desta.

- [ ] **Step 3: Verificar typecheck/lint**

Run: `cd apps/dashboard && pnpm tsc --noEmit && pnpm lint`
Expected: sem erros. (Atenção ao gotcha de import do lucide-react — `Save` existe.)

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/components/comunicado-edit-form.tsx "apps/dashboard/app/(admin)/comunicados/[id]/editar/page.tsx"
git commit -m "feat(comunicados): form e rota de edicao de campanha"
```

---

## Task 6: Botões Editar e Excluir na tela de detalhe

**Files:**
- Modify: `apps/dashboard/components/comunicado-detail.tsx`

- [ ] **Step 1: Atualizar imports e hooks**

Em `apps/dashboard/components/comunicado-detail.tsx`:

Trocar o import do `next/link` e ícones (linhas 2 e 4) e o import de queries (linhas 8-14) para incluir o necessário. Linha 2 vira:

```tsx
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
```

Linha 4 (ícones) vira:

```tsx
import { Download, Pencil, RotateCcw, Trash2 } from 'lucide-react'
```

No bloco de import de `@/lib/api/queries` (linhas 8-14), adicionar `useDeleteCampanha`:

```tsx
import {
  resultadoExportUrl,
  useCampanha,
  useDeleteCampanha,
  useDestinatarios,
  useReenviarFalhas,
  useTestCampanha,
} from '@/lib/api/queries'
```

- [ ] **Step 2: Instanciar router e hook de delete**

Logo após `const reenviar = useReenviarFalhas(id)` (linha 37), adicionar:

```tsx
  const router = useRouter()
  const excluir = useDeleteCampanha()
```

- [ ] **Step 3: Handler de exclusão**

Adicionar a função dentro do componente, após a função `exportar()` (depois da linha 61):

```tsx
  function handleExcluir() {
    if (!window.confirm('Excluir este comunicado? Essa ação não pode ser desfeita.')) return
    excluir.mutate(id, {
      onSuccess: () => {
        toast.success('Comunicado excluído')
        router.push('/comunicados')
      },
      onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro ao excluir'),
    })
  }
```

- [ ] **Step 4: Botões no cabeçalho**

Trocar o bloco do cabeçalho (linhas 65-71, o `<div className="flex items-center justify-between">`) por uma versão com os botões. Editar aparece só em rascunho/erro; Excluir aparece sempre, menos `enviando`:

```tsx
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{c.titulo}</h1>
          <p className="mt-1 text-sm text-muted-foreground font-mono">{c.template_name}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{c.status}</Badge>
          {(c.status === 'rascunho' || c.status === 'erro') && (
            <Link
              href={`/comunicados/${id}/editar`}
              className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent"
            >
              <Pencil className="h-4 w-4" /> Editar
            </Link>
          )}
          {c.status !== 'enviando' && (
            <button
              type="button"
              onClick={handleExcluir}
              disabled={excluir.isPending}
              className="inline-flex items-center gap-2 rounded-md border border-destructive/40 px-3 py-2 text-sm text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" /> Excluir
            </button>
          )}
        </div>
      </div>
```

- [ ] **Step 5: Verificar typecheck/lint**

Run: `cd apps/dashboard && pnpm tsc --noEmit && pnpm lint`
Expected: sem erros. Confirmar que `Pencil` e `Trash2` são exports válidos do lucide-react (são).

- [ ] **Step 6: Commit**

```bash
git add apps/dashboard/components/comunicado-detail.tsx
git commit -m "feat(comunicados): botoes Editar e Excluir na tela de detalhe"
```

---

## Self-Review (preenchido)

**Spec coverage:**
- DELETE qualquer status exceto enviando → Task 3 ✅
- PATCH rascunho/erro → Task 2 ✅
- Schema CampanhaUpdate → Task 1 ✅
- Cascade destinatários → coberto pelo modelo existente + teste em Task 3 ✅
- UI Excluir (some em enviando) → Task 6 ✅
- UI Editar (rascunho/erro) → Task 5 + Task 6 ✅
- Não re-seleciona destinatários ao editar → o form não chama selecionar/importar ✅
- Testes (excluir/editar/404/409) → Tasks 2 e 3 ✅

**Desvio consciente do spec (UI):** o spec lista `template_name`/`canal` como editáveis na API (mantido — PATCH aceita), mas a UI deixa canal/template read-only por segurança (troca de template muda schema de variáveis). Documentado na Task 5. A capacidade da API está completa; é só a superfície de UI que é mais conservadora.

**Placeholder scan:** sem TODO/TBD; todo passo tem código ou comando concreto.

**Type consistency:** `CampanhaUpdate` (Pydantic e TS) batem nos campos; hooks usam `import('./types').CampanhaUpdate`/`CampanhaDetail`; `usePatchCampanha` assina `{id, body}` igual ao consumo na Task 5; `useDeleteCampanha` assina `(id)` igual ao consumo na Task 6.
