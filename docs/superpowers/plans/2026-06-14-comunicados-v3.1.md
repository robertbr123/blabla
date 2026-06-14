# Comunicados v3.1 — CSV exemplo só-audiência + lista de quem recebe (Implementação)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** CSV de exemplo vira só-audiência (link/variável digitados no form) e o formulário mostra, antes de disparar, uma amostra (até 30) + total de quem vai receber — nos modos segmento e import.

**Architecture:** Sem mudança de banco. `/preview` (segmento) já retorna amostra — só sobe limite e exibe. Para import, o repo ganha `amostra_selecionados`; `import` e `contagem` passam a retornar `{total, amostra}`. Frontend renderiza as tabelas.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, Next.js + React Query.

---

## ⚠️ Convenções (gotchas de CI deste repo)
- Não rodar pytest/docker localmente. Pode rodar `ruff check`/`mypy` (de apps/api)/`tsc` se disponível, senão pular. NUNCA `git push` (Robert pusha). Claude commita.
- ruff: sem import não usado; `import X` antes de `from Y`; todos `from ondeline_api` juntos ANTES de `from sqlalchemy`; sem blank entre third-party e first-party; multi-linha colapsa ≤88; sem var desempacotada não usada (RUF059); sem `.encode()` em str literal (UP012).
- mypy strict + pydantic plugin: dict/list[dict]→campo de schema use `model_validate`; `disallow_untyped_calls` vale em testes → teste com `-> None` não pode chamar helper sem anotação (deixe o teste SEM `-> None`).
- Banco de teste roda migrations e é compartilhado entre testes que commitam → usar uuid4 em dados únicos.

---

## FASE 1 — Backend

### Task 1: Schemas (amostra)

**Files:** Modify `apps/api/src/ondeline_api/api/schemas/comunicado.py`

- [ ] **Step 1:** Adicionar `AmostraDestinatario` (perto de `DestinatarioOut`) e incluir `amostra` em `ContagemOut` e `ImportResult`.

Adicionar:
```python
class AmostraDestinatario(BaseModel):
    whatsapp: str
    cidade: str | None
    status: str | None
```

Alterar `ContagemOut`:
```python
class ContagemOut(BaseModel):
    total: int
    amostra: list[AmostraDestinatario] = []
```

Alterar `ImportResult` (adicionar o campo `amostra`, mantendo os demais):
```python
class ImportResult(BaseModel):
    importados: int
    invalidos: int
    amostra_invalidos: list[str]
    valores: SegmentoValores
    amostra: list[AmostraDestinatario] = []
```

- [ ] **Step 2: Commit**
```bash
git add apps/api/src/ondeline_api/api/schemas/comunicado.py
git commit -m "feat(comunicados-v3.1): schema amostra em ContagemOut e ImportResult"
```

---

### Task 2: Repo `amostra_selecionados` (TDD)

**Files:** Modify `apps/api/src/ondeline_api/repositories/campanha.py`; Create `apps/api/tests/test_campanha_amostra.py`

- [ ] **Step 1: Teste** — criar `apps/api/tests/test_campanha_amostra.py`:
```python
# apps/api/tests/test_campanha_amostra.py
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.models.business import Campanha, CampanhaDestinatario, Canal
from ondeline_api.repositories.campanha import CampanhaRepo


async def _camp(session, n_manaus, n_outras):
    canal = Canal(slug=f"a-{uuid4().hex[:8]}", nome="A", provider="cloud",
                  cloud_phone_id="1", cloud_waba_id="2")
    session.add(canal)
    await session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="x",
                    body_params=[], segmentacao={}, origem="importado", status="rascunho")
    session.add(camp)
    await session.flush()
    for i in range(n_manaus):
        session.add(CampanhaDestinatario(
            campanha_id=camp.id, cliente_id=None, whatsapp=f"55920{i:05d}",
            status="pendente", csv_cidade="Manaus", csv_status="Ativo"))
    for i in range(n_outras):
        session.add(CampanhaDestinatario(
            campanha_id=camp.id, cliente_id=None, whatsapp=f"55921{i:05d}",
            status="pendente", csv_cidade="Outra", csv_status="Ativo"))
    await session.flush()
    return camp


@pytest.mark.asyncio
async def test_amostra_respeita_filtro_e_limite(db_session):
    camp = await _camp(db_session, n_manaus=40, n_outras=5)
    repo = CampanhaRepo(db_session)
    amostra = await repo.amostra_selecionados(camp.id, {"cidade": "Manaus"}, limite=30)
    assert len(amostra) == 30
    assert all(d.csv_cidade == "Manaus" for d in amostra)


@pytest.mark.asyncio
async def test_amostra_sem_filtro_pega_todos_ate_limite(db_session):
    camp = await _camp(db_session, n_manaus=3, n_outras=2)
    repo = CampanhaRepo(db_session)
    amostra = await repo.amostra_selecionados(camp.id, {}, limite=30)
    assert len(amostra) == 5
```
(ruff: `import pytest` então `from ondeline_api...` sem blank; testes sem `-> None`; helper sem anotação OK.)

- [ ] **Step 2: Rodar (CI) — FAIL**.

- [ ] **Step 3: Implementar** — adicionar método à classe `CampanhaRepo` (usa `_match_csv` já existente):
```python
    async def amostra_selecionados(
        self, campanha_id: UUID, filtros: dict[str, Any], *, limite: int = 30
    ) -> list[CampanhaDestinatario]:
        stmt = (
            select(CampanhaDestinatario)
            .where(
                CampanhaDestinatario.campanha_id == campanha_id,
                CampanhaDestinatario.status == "pendente",
                self._match_csv(filtros),
            )
            .order_by(CampanhaDestinatario.id)
            .limit(limite)
        )
        return list((await self._session.execute(stmt)).scalars().all())
```

- [ ] **Step 4: Rodar (CI) — PASS**.

- [ ] **Step 5: Commit**
```bash
git add apps/api/src/ondeline_api/repositories/campanha.py apps/api/tests/test_campanha_amostra.py
git commit -m "feat(comunicados-v3.1): CampanhaRepo.amostra_selecionados + testes"
```

---

### Task 3: API — preview limite 30 + amostra no import e contagem

**Files:** Modify `apps/api/src/ondeline_api/api/v1/comunicados.py`

- [ ] **Step 1: Imports.** Adicionar `AmostraDestinatario` ao bloco `from ondeline_api.api.schemas.comunicado import (...)` (mantendo ordenado).

- [ ] **Step 2: `/preview` limite 30.** No endpoint `preview`, trocar `amostra = await amostra_segmento(session, f, limite=10)` por `limite=30`.

- [ ] **Step 3: import retorna amostra.** No `importar_destinatarios`, antes do `return ImportResult(...)`, adicionar o cálculo da amostra e incluir no retorno. Após `valores = await repo.valores_import(camp.id)` acrescentar:
```python
    amostra = await repo.amostra_selecionados(camp.id, {}, limite=30)
```
E no `return ImportResult(...)` adicionar o campo:
```python
        amostra=[
            AmostraDestinatario(whatsapp=d.whatsapp, cidade=d.csv_cidade, status=d.csv_status)
            for d in amostra
        ],
```

- [ ] **Step 4: contagem retorna amostra.** Substituir o corpo de `contagem_destinatarios` por:
```python
    repo = CampanhaRepo(session)
    f = filtros.model_dump(exclude_none=True)
    total = await repo.contar_selecionados(campanha_id, f)
    amostra = await repo.amostra_selecionados(campanha_id, f, limite=30)
    return ContagemOut(
        total=total,
        amostra=[
            AmostraDestinatario(whatsapp=d.whatsapp, cidade=d.csv_cidade, status=d.csv_status)
            for d in amostra
        ],
    )
```

- [ ] **Step 5: ruff/mypy** (CI). Commit:
```bash
git add apps/api/src/ondeline_api/api/v1/comunicados.py
git commit -m "feat(comunicados-v3.1): preview limite 30 + amostra no import e contagem"
```

---

## FASE 2 — Frontend

### Task 4: Tipos + hook

**Files:** Modify `apps/dashboard/lib/api/types.ts`, `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: types.ts** — adicionar tipo e estender. Adicionar:
```typescript
export interface AmostraDestinatario {
  whatsapp: string
  cidade: string | null
  status: string | null
}
```
Em `ImportResult`, adicionar o campo:
```typescript
  amostra: AmostraDestinatario[]
```
(`PreviewResult.amostra` já existe com `{id, nome, whatsapp, cidade}` — não mexer.)

- [ ] **Step 2: queries.ts** — atualizar `useContagemImport` para o novo retorno:
```typescript
export function useContagemImport(campanhaId: string) {
  return useMutation({
    mutationFn: (filtros: import('./types').SegmentoFiltros) =>
      apiFetch<{ total: number; amostra: import('./types').AmostraDestinatario[] }>(
        `/api/v1/admin/comunicados/${campanhaId}/destinatarios/contagem`,
        { method: 'POST', body: JSON.stringify(filtros) },
      ),
  })
}
```

- [ ] **Step 3: tsc** (CI). Commit:
```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(comunicados-v3.1): tipos AmostraDestinatario + contagem retorna amostra"
```

---

### Task 5: Form — exemplo só-audiência + tabelas de amostra

**Files:** Modify `apps/dashboard/components/comunicado-form.tsx`

- [ ] **Step 1: Exemplo só-audiência.** Em `baixarExemplo`, trocar a string `exemplo` por:
```typescript
    const exemplo =
      'telefone;cidade;status;plano\n' +
      '5592991112222;Manaus;Ativo;100MB\n' +
      '559784272884;Eirunepe;Ativo;50MB\n'
```

- [ ] **Step 2: Texto de ajuda.** Trocar o `<p className="text-xs text-muted-foreground">` da seção de import por:
```tsx
            <p className="text-xs text-muted-foreground">
              CSV com a coluna de telefone + (opcional) cidade, status, plano para filtrar.
              O conteúdo da mensagem (links etc.) você preenche acima no formulário.
            </p>
```

- [ ] **Step 3: Estado da amostra do import.** Adicionar um state novo (perto de `const [contagem, setContagem] = useState<number | null>(null)`):
```typescript
  const [amostraImport, setAmostraImport] = useState<import('@/lib/api/types').AmostraDestinatario[]>([])
```

- [ ] **Step 4: Popular amostra no import.** No `handleImportar`, após `setContagem(imp.importados)`, adicionar:
```typescript
      setAmostraImport(imp.amostra)
```

- [ ] **Step 5: Popular amostra ao recontar.** Em `recontar`, trocar o `onSuccess` por:
```typescript
    contar.mutate(novos, {
      onSuccess: (r) => {
        setContagem(r.total)
        setAmostraImport(r.amostra)
      },
    })
```

- [ ] **Step 6: Tabela no segmento.** Na seção `origem === 'segmento'`, logo após o bloco do "X cliente(s) vão receber" (a `<div className="flex items-center gap-3 flex-wrap">…</div>`), adicionar uma tabela da amostra do preview:
```tsx
            {preview.data && preview.data.amostra.length > 0 && (
              <div className="rounded-md border bg-card overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Nome</th>
                      <th className="px-3 py-2 font-semibold">Telefone</th>
                      <th className="px-3 py-2 font-semibold">Cidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.data.amostra.map((a) => (
                      <tr key={a.id} className="border-b last:border-b-0">
                        <td className="px-3 py-2">{a.nome ?? '—'}</td>
                        <td className="px-3 py-2 font-mono text-xs">{a.whatsapp}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.cidade ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="px-3 py-2 text-xs text-muted-foreground">
                  mostrando {preview.data.amostra.length} de {preview.data.total}
                </p>
              </div>
            )}
```

- [ ] **Step 7: Tabela no import.** Na seção `origem === 'importado' && campanhaId`, logo após o `<p className="text-sm font-medium">{contagem ?? 0} contato(s) vão receber</p>`, adicionar:
```tsx
            {amostraImport.length > 0 && (
              <div className="rounded-md border bg-card overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Telefone</th>
                      <th className="px-3 py-2 font-semibold">Cidade</th>
                      <th className="px-3 py-2 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {amostraImport.map((a, i) => (
                      <tr key={`${a.whatsapp}-${i}`} className="border-b last:border-b-0">
                        <td className="px-3 py-2 font-mono text-xs">{a.whatsapp}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.cidade ?? '—'}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.status ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="px-3 py-2 text-xs text-muted-foreground">
                  mostrando {amostraImport.length} de {contagem ?? 0}
                </p>
              </div>
            )}
```

- [ ] **Step 8: tsc/lint** (CI). Commit:
```bash
git add apps/dashboard/components/comunicado-form.tsx
git commit -m "feat(comunicados-v3.1): exemplo CSV so-audiencia + tabela de quem recebe (segmento e import)"
```

---

## Self-review (cobertura do spec)
- ✅ CSV exemplo só-audiência: Task 5 (steps 1-2).
- ✅ Lista segmento (nome/telefone/cidade) amostra+total: Task 3 (preview 30) + Task 5 (step 6).
- ✅ Lista import (telefone/cidade/status) amostra+total: Task 1/2/3 (amostra_selecionados, import+contagem retornam amostra) + Task 4 (tipos/hook) + Task 5 (steps 3-7).
- ✅ Sem mudança de banco.
- ✅ Teste de amostra (filtro+limite): Task 2.
