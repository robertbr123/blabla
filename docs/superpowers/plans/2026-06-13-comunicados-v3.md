# Comunicados v3 — Import filtrável + acompanhamento de entrega (Implementação)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** CSV importado vira base filtrável (cidade/status/plano) que se dispara por recorte; e a tela da campanha mostra status por contato com filtro, reenvio de falhas e export do resultado.

**Architecture:** Destinatários ganham snapshot `csv_cidade/csv_status/csv_plano` do CSV. Import cria todos como `pendente`; um passo de "selecionar" marca os fora do filtro como `excluido`; a task de envio (inalterada) manda só os `pendente`. A tela de detalhe lista destinatários por status, reenfileira falhas e exporta resultado.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Pydantic, csv (stdlib), Next.js + React Query.

---

## ⚠️ Convenções deste repo (gotchas de CI já aprendidos)

- **Não rodar pytest/alembic/docker/uv localmente.** Testes rodam no CI/deploy. Pode rodar `ruff check`/`mypy`/`tsc` se disponível, senão pular.
- **Claude commita; PUSH é do Robert.** Nunca `git push`.
- **ruff (gate):** sem imports não usados (F401); `import X` antes de `from Y`; **todos os `from ondeline_api...` juntos e ANTES de `from sqlalchemy...`** (ordem alfabética: o<s); sem linha em branco entre grupo third-party e first-party; import multi-linha colapsa pra 1 linha se couber ≤88 chars; sem `.encode()` em str literal (UP012); sem var desempacotada não usada (RUF059).
- **mypy strict + plugin pydantic:** passar `dict`/`list[dict]` a campo tipado de schema → usar `Model.model_validate(...)`; dict literal `str|None` → anotar `: dict[str, Any]`; lib sem stubs → override. **`disallow_untyped_calls` vale em testes** → função de teste **tipada (`-> None`) NÃO pode chamar helper sem anotação**; ou deixe o teste sem `-> None`, ou anote o helper.
- **Banco de teste do CI roda migrations (seed presente) e é compartilhado entre testes que commitam** → use valores únicos (uuid4) em dados com unique/contagem; cidade única quando a contagem importa.
- **Migration mais recente:** `0050_comunicados_v2`. A nova é `0051`.
- **Padrões:** modelos em `db/models/business.py`; router `api/v1/comunicados.py` (deps `_admin_dep`); repo `repositories/campanha.py` (`CampanhaRepo(session)`, `self._session`); upload `file: Annotated[UploadFile, File()]` + `await file.read()`.

---

## Estrutura de arquivos
- `db/models/business.py` — **modificar**: 3 colunas em `CampanhaDestinatario`.
- `alembic/versions/0051_comunicados_v3.py` — **criar**.
- `services/broadcast_import.py` — **modificar**: capturar cidade/status/plano.
- `repositories/campanha.py` — **modificar**: métodos novos.
- `api/schemas/comunicado.py` — **modificar**: schemas novos.
- `api/v1/comunicados.py` — **modificar**: endpoints novos + import estendido.
- `lib/api/types.ts`, `lib/api/queries.ts` — **modificar**.
- `components/comunicado-form.tsx` — **modificar**: fluxo Importar→filtrar→Disparar.
- `components/comunicado-detail.tsx` — **modificar**: lista + filtro + reenviar + export.
- Testes: `test_broadcast_import.py` (modificar), `test_campanha_repo_v3.py` (criar).

---

## FASE 1 — Backend dados + parser

### Task 1: Colunas csv_ no destinatário

**Files:** Modify `apps/api/src/ondeline_api/db/models/business.py`

- [ ] **Step 1:** Na classe `CampanhaDestinatario`, após o campo `button_param` (o do destinatário, adicionado no v2), adicionar:

```python
    # snapshot do CSV importado, p/ filtrar quem recebe (separado de `status`, que é o status de envio)
    csv_cidade: Mapped[str | None] = mapped_column(String(80), nullable=True)
    csv_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    csv_plano: Mapped[str | None] = mapped_column(String(80), nullable=True)
```

(`String`, `Mapped`, `mapped_column` já importados.)

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/db/models/business.py
git commit -m "feat(comunicados-v3): colunas csv_cidade/status/plano no destinatario"
```

---

### Task 2: Migration 0051

**Files:** Create `apps/api/alembic/versions/0051_comunicados_v3.py`

- [ ] **Step 1:**

```python
"""Comunicados v3: snapshot csv_cidade/status/plano no destinatario (base filtravel).

Revision ID: 0051_comunicados_v3
Revises: 0050_comunicados_v2
Create Date: 2026-06-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0051_comunicados_v3"
down_revision: str | None = "0050_comunicados_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campanha_destinatarios", sa.Column("csv_cidade", sa.String(80), nullable=True))
    op.add_column("campanha_destinatarios", sa.Column("csv_status", sa.String(40), nullable=True))
    op.add_column("campanha_destinatarios", sa.Column("csv_plano", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("campanha_destinatarios", "csv_plano")
    op.drop_column("campanha_destinatarios", "csv_status")
    op.drop_column("campanha_destinatarios", "csv_cidade")
```

Antes de commitar: confirme com `ls apps/api/alembic/versions/ | sort | tail -3` que `0050_comunicados_v2` é o head.

- [ ] **Step 2: Commit**

```bash
git add apps/api/alembic/versions/0051_comunicados_v3.py
git commit -m "feat(comunicados-v3): migration 0051 (csv_ no destinatario)"
```

---

### Task 3: Parser captura cidade/status/plano (TDD)

**Files:** Modify `apps/api/src/ondeline_api/services/broadcast_import.py`; Modify `apps/api/tests/test_broadcast_import.py`

- [ ] **Step 1: Adicionar teste** ao fim de `apps/api/tests/test_broadcast_import.py`:

```python
def test_captura_cidade_status_plano() -> None:
    csv_bytes = b"telefone,cidade,status,plano\n5592111111111,Manaus,Ativo,100MB\n"
    rows, _invalidos = parse_csv_destinatarios(csv_bytes, [])
    assert rows[0]["csv_cidade"] == "Manaus"
    assert rows[0]["csv_status"] == "Ativo"
    assert rows[0]["csv_plano"] == "100MB"


def test_sem_colunas_seg_fica_none() -> None:
    csv_bytes = b"telefone\n5592111111111\n"
    rows, _invalidos = parse_csv_destinatarios(csv_bytes, [])
    assert rows[0]["csv_cidade"] is None
    assert rows[0]["csv_status"] is None
    assert rows[0]["csv_plano"] is None
```

- [ ] **Step 2: Rodar (CI) — FAIL** (`csv_cidade` ausente no dict).

- [ ] **Step 3: Implementar** em `services/broadcast_import.py`. Adicionar o mapa de colunas de segmento (perto de `_PHONE_COLS`/`_BTN_COLS`):

```python
_SEG_COLS = {"cidade": "csv_cidade", "status": "csv_status", "plano": "csv_plano"}
```

Dentro de `parse_csv_destinatarios`, depois de montar `fieldmap` e antes do loop, resolver as colunas de segmento:

```python
    seg_real = {dest: fieldmap[src] for src, dest in _SEG_COLS.items() if src in fieldmap}
```

E no loop, ao montar o dict de cada row, incluir os 3 campos (sempre presentes, None se a coluna não veio). Trocar o `rows.append({...})` por:

```python
        row: dict[str, Any] = {
            "whatsapp": jid,
            "body_params": body_params,
            "button_param": button_param,
            "csv_cidade": None,
            "csv_status": None,
            "csv_plano": None,
        }
        for dest, real in seg_real.items():
            row[dest] = raw.get(real) or None
        rows.append(row)
```

- [ ] **Step 4: Rodar (CI) — PASS**.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/broadcast_import.py apps/api/tests/test_broadcast_import.py
git commit -m "feat(comunicados-v3): parser captura cidade/status/plano do CSV + testes"
```

---

## FASE 2 — Backend repo + schemas + API

### Task 4: Métodos no CampanhaRepo (TDD)

**Files:** Modify `apps/api/src/ondeline_api/repositories/campanha.py`; Create `apps/api/tests/test_campanha_repo_v3.py`

- [ ] **Step 1: Teste** — criar `apps/api/tests/test_campanha_repo_v3.py`:

```python
# apps/api/tests/test_campanha_repo_v3.py
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.models.business import Campanha, CampanhaDestinatario, Canal
from ondeline_api.repositories.campanha import CampanhaRepo


async def _campanha_com_destinatarios(session):
    canal = Canal(slug=f"k-{uuid4().hex[:8]}", nome="K", provider="cloud",
                  cloud_phone_id="1", cloud_waba_id="2")
    session.add(canal)
    await session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="x",
                    body_params=[], segmentacao={}, origem="importado",
                    status="rascunho")
    session.add(camp)
    await session.flush()
    dados = [
        ("5592000001", "Manaus", "Ativo"),
        ("5592000002", "Manaus", "Cancelado"),
        ("5592000003", "Itacoatiara", "Ativo"),
    ]
    for tel, cid, st in dados:
        session.add(CampanhaDestinatario(
            campanha_id=camp.id, cliente_id=None, whatsapp=tel,
            status="pendente", csv_cidade=cid, csv_status=st,
        ))
    await session.flush()
    return camp


@pytest.mark.asyncio
async def test_contar_selecionados_com_filtro(db_session):
    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    n = await repo.contar_selecionados(camp.id, {"cidade": "Manaus", "status": "Ativo"})
    assert n == 1
    n_todos = await repo.contar_selecionados(camp.id, {})
    assert n_todos == 3


@pytest.mark.asyncio
async def test_marcar_excluidos_mantem_so_o_recorte(db_session):
    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    selecionados = await repo.marcar_excluidos(camp.id, {"cidade": "Manaus"})
    assert selecionados == 2
    # os de outra cidade viraram excluido
    from sqlalchemy import func, select
    n_excl = (await db_session.execute(
        select(func.count()).select_from(CampanhaDestinatario).where(
            CampanhaDestinatario.campanha_id == camp.id,
            CampanhaDestinatario.status == "excluido",
        )
    )).scalar_one()
    assert n_excl == 1


@pytest.mark.asyncio
async def test_reenviar_falhas_reseta(db_session):
    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    # marca um como falha
    from sqlalchemy import select
    dest = (await db_session.execute(
        select(CampanhaDestinatario).where(CampanhaDestinatario.campanha_id == camp.id).limit(1)
    )).scalar_one()
    dest.status = "falha"
    dest.erro = "x"
    dest.wamid = "w"
    camp.falhas = 1
    await db_session.flush()

    n = await repo.reenviar_falhas(camp.id)
    assert n == 1
    await db_session.refresh(dest)
    assert dest.status == "pendente"
    assert dest.erro is None
    assert dest.wamid is None


@pytest.mark.asyncio
async def test_list_destinatarios_filtra_status(db_session):
    camp = await _campanha_com_destinatarios(db_session)
    repo = CampanhaRepo(db_session)
    todos = await repo.list_destinatarios(camp.id, status=None, limit=50, offset=0)
    assert len(todos) == 3
    # marca excluido um e confere que some da listagem padrão
    await repo.marcar_excluidos(camp.id, {"cidade": "Manaus"})
    visiveis = await repo.list_destinatarios(camp.id, status=None, limit=50, offset=0)
    assert all(d.status != "excluido" for d in visiveis)
```

- [ ] **Step 2: Rodar (CI) — FAIL**.

- [ ] **Step 3: Implementar** — adicionar a `repositories/campanha.py`. Garantir imports no topo: `from sqlalchemy import and_, func, select, true, update` e `from typing import Any`, e `from ondeline_api.db.models.business import Campanha, CampanhaDestinatario` (Campanha já importado). Adicionar métodos à classe `CampanhaRepo`:

```python
    @staticmethod
    def _match_csv(filtros: dict[str, Any]) -> Any:
        conds = []
        if (filtros.get("cidade") or "").strip():
            conds.append(CampanhaDestinatario.csv_cidade == filtros["cidade"])
        if (filtros.get("status") or "").strip():
            conds.append(CampanhaDestinatario.csv_status == filtros["status"])
        if (filtros.get("plano") or "").strip():
            conds.append(CampanhaDestinatario.csv_plano == filtros["plano"])
        return and_(*conds) if conds else true()

    async def contar_selecionados(self, campanha_id: UUID, filtros: dict[str, Any]) -> int:
        stmt = (
            select(func.count())
            .select_from(CampanhaDestinatario)
            .where(
                CampanhaDestinatario.campanha_id == campanha_id,
                CampanhaDestinatario.status == "pendente",
                self._match_csv(filtros),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def marcar_excluidos(self, campanha_id: UUID, filtros: dict[str, Any]) -> int:
        """Marca como 'excluido' os pendentes que NÃO casam o filtro. Retorna os selecionados."""
        stmt = (
            update(CampanhaDestinatario)
            .where(
                CampanhaDestinatario.campanha_id == campanha_id,
                CampanhaDestinatario.status == "pendente",
                ~self._match_csv(filtros),
            )
            .values(status="excluido")
        )
        await self._session.execute(stmt)
        return await self.contar_selecionados(campanha_id, filtros)

    async def valores_import(self, campanha_id: UUID) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for chave, coluna in (
            ("cidades", CampanhaDestinatario.csv_cidade),
            ("status", CampanhaDestinatario.csv_status),
            ("planos", CampanhaDestinatario.csv_plano),
        ):
            stmt = (
                select(coluna)
                .where(
                    CampanhaDestinatario.campanha_id == campanha_id,
                    coluna.is_not(None),
                    coluna != "",
                )
                .distinct()
                .order_by(coluna)
            )
            out[chave] = [v for (v,) in (await self._session.execute(stmt)).all() if v is not None]
        return out

    async def list_destinatarios(
        self, campanha_id: UUID, *, status: str | None, limit: int, offset: int
    ) -> list[CampanhaDestinatario]:
        stmt = select(CampanhaDestinatario).where(
            CampanhaDestinatario.campanha_id == campanha_id
        )
        if status:
            stmt = stmt.where(CampanhaDestinatario.status == status)
        else:
            stmt = stmt.where(CampanhaDestinatario.status != "excluido")
        stmt = stmt.order_by(CampanhaDestinatario.id).limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars().all())

    async def reenviar_falhas(self, campanha_id: UUID) -> int:
        falhas = list(
            (
                await self._session.execute(
                    select(CampanhaDestinatario).where(
                        CampanhaDestinatario.campanha_id == campanha_id,
                        CampanhaDestinatario.status == "falha",
                    )
                )
            )
            .scalars()
            .all()
        )
        for d in falhas:
            d.status = "pendente"
            d.erro = None
            d.wamid = None
        return len(falhas)
```

Confirme que `UUID` está importado no arquivo (já está, do v1).

- [ ] **Step 4: Rodar (CI) — PASS**.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/campanha.py apps/api/tests/test_campanha_repo_v3.py
git commit -m "feat(comunicados-v3): CampanhaRepo (selecionar/contar/valores/listar/reenviar) + testes"
```

---

### Task 5: Schemas

**Files:** Modify `apps/api/src/ondeline_api/api/schemas/comunicado.py`

- [ ] **Step 1:** Alterar `ImportResult` para incluir `valores` e adicionar schemas novos. Localizar `class ImportResult(BaseModel):` e substituir por:

```python
class ImportResult(BaseModel):
    importados: int
    invalidos: int
    amostra_invalidos: list[str]
    valores: SegmentoValores
```

Adicionar ao fim do arquivo:

```python
class ContagemOut(BaseModel):
    total: int


class SelecionarOut(BaseModel):
    selecionados: int


class DestinatarioOut(BaseModel):
    whatsapp: str
    status: str
    erro: str | None
    enviada_em: datetime | None


class ReenviarResult(BaseModel):
    reenfileirados: int
```

(`SegmentoValores`, `datetime` já existem no arquivo.)

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/comunicado.py
git commit -m "feat(comunicados-v3): schemas (valores no import, contagem, selecionar, destinatario, reenviar)"
```

---

### Task 6: Endpoints — import estendido + contagem + selecionar

**Files:** Modify `apps/api/src/ondeline_api/api/v1/comunicados.py`

- [ ] **Step 1: Imports.** Adicionar aos schemas importados: `ContagemOut`, `SelecionarOut`. (Merge no bloco `from ondeline_api.api.schemas.comunicado import (...)`.)

- [ ] **Step 2: Estender `importar_destinatarios`.** No corpo atual, ao criar cada `CampanhaDestinatario`, passar também os csv_; e mudar o retorno pra incluir `valores`. Substituir o loop + return por:

```python
    for r in rows:
        session.add(
            CampanhaDestinatario(
                campanha_id=camp.id,
                cliente_id=None,
                whatsapp=r["whatsapp"],
                body_params=r["body_params"],
                button_param=r["button_param"],
                csv_cidade=r["csv_cidade"],
                csv_status=r["csv_status"],
                csv_plano=r["csv_plano"],
                status="pendente",
            )
        )
    camp.origem = "importado"
    camp.total_destinatarios = len(rows)
    await session.commit()
    valores = await repo.valores_import(camp.id)
    return ImportResult(
        importados=len(rows),
        invalidos=len(invalidos),
        amostra_invalidos=invalidos[:10],
        valores=SegmentoValores(
            cidades=valores["cidades"], status=valores["status"], planos=valores["planos"]
        ),
    )
```

(`repo = CampanhaRepo(session)` já existe no início da função.)

- [ ] **Step 3: Adicionar contagem + selecionar** (perto dos outros `/{campanha_id}/...`):

```python
@router.post("/{campanha_id}/destinatarios/contagem", dependencies=[_admin_dep])
async def contagem_destinatarios(
    campanha_id: UUID,
    filtros: SegmentoFiltros,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ContagemOut:
    repo = CampanhaRepo(session)
    total = await repo.contar_selecionados(campanha_id, filtros.model_dump(exclude_none=True))
    return ContagemOut(total=total)


@router.post("/{campanha_id}/destinatarios/selecionar", dependencies=[_admin_dep])
async def selecionar_destinatarios(
    campanha_id: UUID,
    filtros: SegmentoFiltros,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SelecionarOut:
    repo = CampanhaRepo(session)
    camp = await repo.get_by_id(campanha_id)
    if camp is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    selecionados = await repo.marcar_excluidos(campanha_id, filtros.model_dump(exclude_none=True))
    camp.total_destinatarios = selecionados
    await session.commit()
    return SelecionarOut(selecionados=selecionados)
```

- [ ] **Step 4: Verificar ruff/mypy** (CI). Confirmar ordem de rotas: as 2 novas são `/{campanha_id}/destinatarios/...` (3 segmentos), não conflitam com `/{campanha_id}`.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/comunicados.py
git commit -m "feat(comunicados-v3): import retorna valores + endpoints contagem/selecionar"
```

---

### Task 7: Endpoints — listar destinatários + reenviar falhas + export resultado

**Files:** Modify `apps/api/src/ondeline_api/api/v1/comunicados.py`

- [ ] **Step 1: Imports.** Adicionar aos schemas: `DestinatarioOut`, `ReenviarResult`. (Merge no bloco existente.)

- [ ] **Step 2: Adicionar os 3 endpoints:**

```python
@router.get("/{campanha_id}/destinatarios", dependencies=[_admin_dep])
async def list_destinatarios(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    status_f: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DestinatarioOut]:
    repo = CampanhaRepo(session)
    rows = await repo.list_destinatarios(
        campanha_id, status=status_f, limit=limit, offset=offset
    )
    return [
        DestinatarioOut(
            whatsapp=d.whatsapp, status=d.status, erro=d.erro, enviada_em=d.enviada_em
        )
        for d in rows
    ]


@router.post("/{campanha_id}/reenviar-falhas", dependencies=[_admin_dep])
async def reenviar_falhas(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReenviarResult:
    repo = CampanhaRepo(session)
    camp = await repo.get_by_id(campanha_id)
    if camp is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    n = await repo.reenviar_falhas(campanha_id)
    if n > 0:
        camp.falhas = max(0, camp.falhas - n)
        camp.status = "enviando"
        await session.commit()
        send_campanha_task.delay(str(campanha_id))
    else:
        await session.commit()
    return ReenviarResult(reenfileirados=n)


@router.get("/{campanha_id}/resultado/export", dependencies=[_admin_dep])
async def export_resultado(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    repo = CampanhaRepo(session)
    rows = await repo.list_destinatarios(campanha_id, status=None, limit=100000, offset=0)
    sbuf = io.StringIO()
    sbuf.write("﻿")
    writer = csv.DictWriter(sbuf, fieldnames=["telefone", "status", "erro"])
    writer.writeheader()
    for d in rows:
        writer.writerow({"telefone": d.whatsapp, "status": d.status, "erro": d.erro or ""})
    data = sbuf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="resultado-{campanha_id}.csv"'},
    )
```

(`io`, `csv`, `StreamingResponse`, `Query` já importados do v1/v2.)

- [ ] **Step 3: Verificar ruff/mypy** (CI).

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/comunicados.py
git commit -m "feat(comunicados-v3): endpoints listar destinatarios, reenviar-falhas, export resultado"
```

---

## FASE 3 — Frontend

### Task 8: Tipos + hooks

**Files:** Modify `apps/dashboard/lib/api/types.ts`, `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: Tipos** — em `types.ts`, alterar `ImportResult` (adicionar `valores`) e adicionar tipos. Localizar `export interface ImportResult` e substituir por:

```typescript
export interface ImportResult {
  importados: number
  invalidos: number
  amostra_invalidos: string[]
  valores: SegmentoValores
}
export interface Destinatario {
  whatsapp: string
  status: string
  erro: string | null
  enviada_em: string | null
}
```

- [ ] **Step 2: Hooks** — em `queries.ts`, adicionar:

```typescript
export function useContagemImport(campanhaId: string) {
  return useMutation({
    mutationFn: (filtros: import('./types').SegmentoFiltros) =>
      apiFetch<{ total: number }>(
        `/api/v1/admin/comunicados/${campanhaId}/destinatarios/contagem`,
        { method: 'POST', body: JSON.stringify(filtros) },
      ),
  })
}

export function useSelecionarImport(campanhaId: string) {
  return useMutation({
    mutationFn: (filtros: import('./types').SegmentoFiltros) =>
      apiFetch<{ selecionados: number }>(
        `/api/v1/admin/comunicados/${campanhaId}/destinatarios/selecionar`,
        { method: 'POST', body: JSON.stringify(filtros) },
      ),
  })
}

export function useDestinatarios(campanhaId: string, status: string | null, ativo: boolean) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return useQuery<import('./types').Destinatario[]>({
    queryKey: ['destinatarios', campanhaId, status],
    queryFn: () => apiFetch(`/api/v1/admin/comunicados/${campanhaId}/destinatarios${qs}`),
    enabled: ativo && Boolean(campanhaId),
    refetchInterval: 5000,
  })
}

export function useReenviarFalhas(campanhaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<{ reenfileirados: number }>(
        `/api/v1/admin/comunicados/${campanhaId}/reenviar-falhas`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campanha', campanhaId] })
      qc.invalidateQueries({ queryKey: ['destinatarios', campanhaId] })
    },
  })
}

export function resultadoExportUrl(campanhaId: string) {
  return `/api/v1/admin/comunicados/${campanhaId}/resultado/export`
}
```

- [ ] **Step 3: Verificar tsc** (CI). Commit:

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(comunicados-v3): tipos + hooks (contagem, selecionar, destinatarios, reenviar)"
```

---

### Task 9: Form — Importar → filtrar → Disparar

**Files:** Modify `apps/dashboard/components/comunicado-form.tsx`

- [ ] **Step 1: Reescrever o componente** com o fluxo de dois passos para origem importada. Conteúdo completo:

```tsx
'use client'
import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Download, Send, Upload } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { getAccessToken } from '@/lib/api/token'
import {
  exportClientesUrl,
  useBroadcastTemplates,
  useCanais,
  useContagemImport,
  useCreateCampanha,
  usePreviewSegmento,
  useSegmentoValores,
  useSelecionarImport,
  useSendCampanha,
} from '@/lib/api/queries'
import type { ImportResult, SegmentoFiltros, SegmentoValores } from '@/lib/api/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

export function ComunicadoForm() {
  const router = useRouter()
  const { data: templates } = useBroadcastTemplates()
  const { data: canais } = useCanais()
  const { data: valores } = useSegmentoValores()
  const preview = usePreviewSegmento()
  const createCampanha = useCreateCampanha()
  const sendCampanha = useSendCampanha()

  const cloudCanais = useMemo(
    () => (canais ?? []).filter((c) => c.provider === 'cloud'),
    [canais],
  )

  const [titulo, setTitulo] = useState('')
  const [canalId, setCanalId] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [vars, setVars] = useState<Record<number, string>>({})
  const [botao, setBotao] = useState('')
  const [filtros, setFiltros] = useState<SegmentoFiltros>({})
  const [origem, setOrigem] = useState<'segmento' | 'importado'>('segmento')
  const [csvFile, setCsvFile] = useState<File | null>(null)

  // estado do import (após "Importar")
  const [campanhaId, setCampanhaId] = useState<string | null>(null)
  const [valoresImport, setValoresImport] = useState<SegmentoValores | null>(null)
  const [importInfo, setImportInfo] = useState<ImportResult | null>(null)
  const [importando, setImportando] = useState(false)
  const [contagem, setContagem] = useState<number | null>(null)
  const contar = useContagemImport(campanhaId ?? '')
  const selecionar = useSelecionarImport(campanhaId ?? '')

  const template = templates?.find((t) => t.name === templateName)
  const botaoDinamico = template?.botoes?.find((b) => b.url_dinamica)

  function buildBodyParams(): string[] {
    return (template?.variaveis ?? [])
      .slice()
      .sort((a, b) => a.indice - b.indice)
      .map((v) => vars[v.indice] ?? '')
  }

  function runPreview() {
    preview.mutate(filtros)
  }

  async function handleExport(fmt: 'csv' | 'xlsx') {
    const path = exportClientesUrl(filtros, fmt)
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
      credentials: 'include',
    })
    if (!res.ok) {
      toast.error('Falha ao exportar')
      return
    }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `clientes.${fmt}`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  async function handleImportar() {
    if (!template || !csvFile) {
      toast.error('Escolha template e arquivo')
      return
    }
    setImportando(true)
    try {
      const camp = await createCampanha.mutateAsync({
        titulo,
        canal_id: canalId,
        template_name: templateName,
        body_params: buildBodyParams(),
        segmentacao: {},
        origem: 'importado',
        button_param: botaoDinamico ? botao || null : null,
      })
      const fd = new FormData()
      fd.append('file', csvFile)
      const res = await fetch(
        `${API_URL}/api/v1/admin/comunicados/${camp.id}/destinatarios/importar`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
          credentials: 'include',
          body: fd,
        },
      )
      if (!res.ok) {
        toast.error('Falha ao importar CSV')
        return
      }
      const imp = (await res.json()) as ImportResult
      setCampanhaId(camp.id)
      setValoresImport(imp.valores)
      setImportInfo(imp)
      setContagem(imp.importados)
      setFiltros({})
      toast.success(`${imp.importados} importados, ${imp.invalidos} inválidos`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao importar')
    } finally {
      setImportando(false)
    }
  }

  function recontar(novos: SegmentoFiltros) {
    setFiltros(novos)
    contar.mutate(novos, { onSuccess: (r) => setContagem(r.total) })
  }

  async function handleDispararSegmento() {
    if (!template) return
    try {
      const camp = await createCampanha.mutateAsync({
        titulo,
        canal_id: canalId,
        template_name: templateName,
        body_params: buildBodyParams(),
        segmentacao: filtros,
        origem: 'segmento',
        button_param: botaoDinamico ? botao || null : null,
      })
      const total = preview.data?.total ?? 0
      if (!window.confirm(`Disparar para ${total} cliente(s)?`)) return
      await sendCampanha.mutateAsync(camp.id)
      toast.success('Campanha enfileirada')
      router.push(`/comunicados/${camp.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao disparar')
    }
  }

  async function handleDispararImport() {
    if (!campanhaId) return
    try {
      const sel = await selecionar.mutateAsync(filtros)
      if (!window.confirm(`Disparar para ${sel.selecionados} contato(s)?`)) return
      await sendCampanha.mutateAsync(campanhaId)
      toast.success('Campanha enfileirada')
      router.push(`/comunicados/${campanhaId}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao disparar')
    }
  }

  const cabecalhoOk = titulo && canalId && templateName

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <label className="text-sm font-medium">Título</label>
        <Input value={titulo} onChange={(e) => setTitulo(e.target.value)}
               placeholder="Ex: Lançamento do app" />
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Canal (Cloud)</label>
        <select className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={canalId} onChange={(e) => setCanalId(e.target.value)}>
          <option value="">Selecione…</option>
          {cloudCanais.map((c) => (
            <option key={c.id} value={c.id}>{c.nome}</option>
          ))}
        </select>
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Template</label>
        <select className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={templateName}
                onChange={(e) => { setTemplateName(e.target.value); setVars({}) }}>
          <option value="">Selecione…</option>
          {(templates ?? []).map((t) => (
            <option key={t.id} value={t.name}>{t.name}</option>
          ))}
        </select>
      </div>

      {template?.variaveis.map((v) => (
        <div key={v.indice} className="space-y-1.5">
          <label className="text-sm font-medium">{v.label}</label>
          <Input value={vars[v.indice] ?? ''}
                 onChange={(e) => setVars((s) => ({ ...s, [v.indice]: e.target.value }))}
                 placeholder={v.tipo === 'url' ? 'https://…' : ''} />
        </div>
      ))}

      {botaoDinamico && (
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Valor do botão ({botaoDinamico.texto})</label>
          <Input value={botao} onChange={(e) => setBotao(e.target.value)} placeholder="https://…" />
        </div>
      )}

      <div className="rounded-md border p-4 space-y-3">
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="radio" checked={origem === 'segmento'}
                   onChange={() => { setOrigem('segmento'); setCampanhaId(null) }} /> Segmento da base
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" checked={origem === 'importado'}
                   onChange={() => setOrigem('importado')} /> Importar CSV
          </label>
        </div>

        {origem === 'segmento' && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.cidade ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, cidade: e.target.value || undefined }))}>
                <option value="">Cidade (todas)</option>
                {(valores?.cidades ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.status ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, status: e.target.value || undefined }))}>
                <option value="">Status (todos)</option>
                {(valores?.status ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.plano ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, plano: e.target.value || undefined }))}>
                <option value="">Plano (todos)</option>
                {(valores?.planos ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <button onClick={runPreview} type="button"
                      className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">Calcular alcance</button>
              {preview.data && (
                <span className="text-sm font-medium">{preview.data.total} cliente(s) vão receber</span>
              )}
              <button type="button" onClick={() => handleExport('csv')}
                      className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
                <Download className="h-4 w-4" /> CSV
              </button>
              <button type="button" onClick={() => handleExport('xlsx')}
                      className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
                <Download className="h-4 w-4" /> Excel
              </button>
            </div>
            <button type="button" onClick={handleDispararSegmento} disabled={!cabecalhoOk}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              <Send className="h-4 w-4" /> Disparar
            </button>
          </>
        )}

        {origem === 'importado' && !campanhaId && (
          <div className="space-y-2">
            <input type="file" accept=".csv,text/csv"
                   onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)} />
            <p className="text-xs text-muted-foreground">
              CSV com coluna de telefone + (opcional) cidade, status, plano e colunas das variáveis.
            </p>
            <button type="button" onClick={handleImportar} disabled={!cabecalhoOk || !csvFile || importando}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              <Upload className="h-4 w-4" /> {importando ? 'Importando…' : 'Importar'}
            </button>
          </div>
        )}

        {origem === 'importado' && campanhaId && (
          <>
            <p className="text-sm text-muted-foreground">
              {importInfo?.importados} importados, {importInfo?.invalidos} inválidos. Filtre quem recebe:
            </p>
            <div className="grid grid-cols-3 gap-3">
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.cidade ?? ''}
                      onChange={(e) => recontar({ ...filtros, cidade: e.target.value || undefined })}>
                <option value="">Cidade (todas)</option>
                {(valoresImport?.cidades ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.status ?? ''}
                      onChange={(e) => recontar({ ...filtros, status: e.target.value || undefined })}>
                <option value="">Status (todos)</option>
                {(valoresImport?.status ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.plano ?? ''}
                      onChange={(e) => recontar({ ...filtros, plano: e.target.value || undefined })}>
                <option value="">Plano (todos)</option>
                {(valoresImport?.planos ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <p className="text-sm font-medium">{contagem ?? 0} contato(s) vão receber</p>
            <button type="button" onClick={handleDispararImport}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
              <Send className="h-4 w-4" /> Disparar
            </button>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar tsc/lint** (CI). Commit:

```bash
git add apps/dashboard/components/comunicado-form.tsx
git commit -m "feat(comunicados-v3): form Importar -> filtrar -> Disparar"
```

---

### Task 10: Detalhe — lista + filtro + reenviar + export

**Files:** Modify `apps/dashboard/components/comunicado-detail.tsx`

- [ ] **Step 1: Reescrever o componente** acrescentando lista/filtro/reenviar/export ao que já existe (métricas + teste). Conteúdo completo:

```tsx
'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { Download, RotateCcw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { getAccessToken } from '@/lib/api/token'
import {
  resultadoExportUrl,
  useCampanha,
  useDestinatarios,
  useReenviarFalhas,
  useTestCampanha,
} from '@/lib/api/queries'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''
const STATUS_TABS: Array<{ key: string | null; label: string }> = [
  { key: null, label: 'Todos' },
  { key: 'enviada', label: 'Enviadas' },
  { key: 'entregue', label: 'Entregues' },
  { key: 'lida', label: 'Lidas' },
  { key: 'falha', label: 'Falhas' },
]

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-card p-4">
      <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  )
}

export function ComunicadoDetail({ id }: { id: string }) {
  const { data: c, isLoading } = useCampanha(id)
  const testSend = useTestCampanha(id)
  const reenviar = useReenviarFalhas(id)
  const [testNum, setTestNum] = useState('')
  const [statusFiltro, setStatusFiltro] = useState<string | null>(null)
  const { data: destinatarios } = useDestinatarios(id, statusFiltro, !isLoading)

  if (isLoading || !c) return <p className="text-sm text-muted-foreground">Carregando…</p>

  const counts = c.status_counts ?? {}

  async function exportar() {
    const res = await fetch(`${API_URL}${resultadoExportUrl(id)}`, {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
      credentials: 'include',
    })
    if (!res.ok) {
      toast.error('Falha ao exportar')
      return
    }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `resultado-${id}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{c.titulo}</h1>
          <p className="mt-1 text-sm text-muted-foreground font-mono">{c.template_name}</p>
        </div>
        <Badge variant="outline">{c.status}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Metric label="Total" value={c.total_destinatarios} />
        <Metric label="Enviadas" value={c.enviadas} />
        <Metric label="Entregues" value={counts.entregue ?? 0} />
        <Metric label="Lidas" value={counts.lida ?? 0} />
        <Metric label="Falhas" value={c.falhas} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {c.falhas > 0 && (
          <button type="button"
                  onClick={() => reenviar.mutate(undefined, {
                    onSuccess: (r) => toast.success(`${r.reenfileirados} reenfileirados`),
                    onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
                  })}
                  disabled={reenviar.isPending}
                  className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50">
            <RotateCcw className="h-4 w-4" /> Reenviar falhas
          </button>
        )}
        <button type="button" onClick={exportar}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent">
          <Download className="h-4 w-4" /> Exportar resultado
        </button>
      </div>

      <div className="space-y-3">
        <div className="flex gap-2 flex-wrap">
          {STATUS_TABS.map((t) => (
            <button key={t.label} type="button" onClick={() => setStatusFiltro(t.key)}
                    className={`rounded-md border px-3 py-1.5 text-sm ${statusFiltro === t.key ? 'bg-accent' : 'hover:bg-accent'}`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Telefone</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Erro</th>
              </tr>
            </thead>
            <tbody>
              {(destinatarios ?? []).map((d, i) => (
                <tr key={`${d.whatsapp}-${i}`} className="border-b last:border-b-0">
                  <td className="px-4 py-2.5 font-mono text-xs">{d.whatsapp}</td>
                  <td className="px-4 py-2.5">
                    <Badge variant="outline">{d.status}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{d.erro ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {destinatarios && destinatarios.length === 0 && (
            <p className="px-4 py-6 text-sm text-muted-foreground">Nenhum contato neste filtro.</p>
          )}
        </div>
      </div>

      <div className="rounded-md border p-4 space-y-3 max-w-md">
        <p className="text-sm font-medium">Enviar teste</p>
        <div className="flex gap-3">
          <Input placeholder="5592999999999" value={testNum}
                 onChange={(e) => setTestNum(e.target.value)} />
          <button type="button"
                  onClick={() => testSend.mutate(testNum, {
                    onSuccess: () => toast.success('Teste enviado'),
                    onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
                  })}
                  className="rounded-md border px-3 py-2 text-sm hover:bg-accent whitespace-nowrap">
            Enviar
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar tsc/lint** (CI). Confirmar que `RotateCcw` e `Download` existem no lucide-react. Commit:

```bash
git add apps/dashboard/components/comunicado-detail.tsx
git commit -m "feat(comunicados-v3): detalhe com lista por status, reenviar falhas e export resultado"
```

---

## Self-review (cobertura do spec)

- ✅ CSV base filtrável: Task 1/2 (csv_ cols), Task 3 (parser), Task 4 (contar/marcar/valores), Task 6 (import retorna valores + contagem/selecionar), Task 9 (form 2 passos).
- ✅ Acompanhamento: Task 4 (list/reenviar), Task 7 (endpoints), Task 10 (UI lista+filtro+reenviar+export).
- ✅ Filtro aplica exclusão sem tocar a task de envio: Task 4 (`marcar_excluidos`), worker inalterado (envia só `pendente`).
- ✅ Reenviar falhas: Task 4/7/10.
- ✅ Export resultado: Task 7/10.
- ✅ Migration 0051: Task 2.

## Follow-ups (fora do MVP)
- Paginação por cursor na lista (hoje offset/limit, default 200).
- Dedup de telefones repetidos no CSV; salvar listas entre campanhas; limite de reenvio.
