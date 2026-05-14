# Ranking de Técnicos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar endpoint de ranking mensal de técnicos por OS concluídas, CSAT médio e tempo médio — com exportação CSV — e exibir em página dedicada `/tecnicos/ranking` no dashboard.

**Architecture:** Dois endpoints novos em `/api/v1/metricas/tecnicos` adicionados ao router existente de métricas. Query SQL agrega OS concluídas por técnico no mês filtrado. Frontend com página dedicada, filtro de mês e download CSV via `Content-Disposition: attachment`.

**Tech Stack:** FastAPI, SQLAlchemy async (func.avg, func.count, func.extract), Pydantic v2, Python csv stdlib, Next.js 14, TanStack Query, shadcn/ui

---

## File Map

| Ação | Arquivo |
|------|---------|
| Modify | `apps/api/src/ondeline_api/api/schemas/metrica.py` |
| Modify | `apps/api/src/ondeline_api/api/v1/metricas.py` |
| Create | `apps/api/tests/test_ranking_tecnicos.py` |
| Modify | `apps/dashboard/lib/api/types.ts` |
| Modify | `apps/dashboard/lib/api/queries.ts` |
| Create | `apps/dashboard/app/(admin)/tecnicos/ranking/page.tsx` |
| Modify | `apps/dashboard/components/nav-sidebar.tsx` |

---

### Task 1: Schema e Endpoints de Ranking + Testes

**Files:**
- Modify: `apps/api/src/ondeline_api/api/schemas/metrica.py`
- Modify: `apps/api/src/ondeline_api/api/v1/metricas.py`
- Create: `apps/api/tests/test_ranking_tecnicos.py`

- [ ] **Step 1: Escrever os testes (TDD)**

```python
# apps/api/tests/test_ranking_tecnicos.py
"""Testes de integração para GET /api/v1/metricas/tecnicos."""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import OrdemServico, OsStatus, Tecnico
from ondeline_api.db.models.identity import Role, User
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


async def _seed_tecnico_com_os(
    db_session: AsyncSession,
    nome: str,
    os_count: int,
    csat: int | None = None,
    mes: datetime | None = None,
) -> Tecnico:
    """Cria um técnico e N OS concluídas no banco."""
    tecnico = Tecnico(nome=nome, ativo=True)
    db_session.add(tecnico)
    await db_session.flush()

    concluida = mes or datetime(2026, 5, 15, tzinfo=UTC)
    for _ in range(os_count):
        os_ = OrdemServico(
            codigo=f"OS-{uuid4().hex[:6]}",
            problema="Teste",
            endereco="Rua X, 1",
            status=OsStatus.CONCLUIDA,
            tecnico_id=tecnico.id,
            criada_em=datetime(2026, 5, 15, 8, 0, tzinfo=UTC),
            concluida_em=concluida,
            csat=csat,
        )
        db_session.add(os_)
    await db_session.flush()
    return tecnico


@pytest.mark.asyncio
async def test_ranking_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/metricas/tecnicos")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ranking_returns_list(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    await _seed_tecnico_com_os(db_session, "Carlos", os_count=5, csat=5)
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos?mes=2026-05",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    tecnico = next((t for t in data if t["nome"] == "Carlos"), None)
    assert tecnico is not None
    assert tecnico["os_concluidas"] == 5
    assert tecnico["csat_avg"] == 5.0


@pytest.mark.asyncio
async def test_ranking_ordered_by_os_desc(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    await _seed_tecnico_com_os(db_session, "Ana", os_count=3)
    await _seed_tecnico_com_os(db_session, "Pedro", os_count=7)
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos?mes=2026-05",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    os_counts = [t["os_concluidas"] for t in data if t["nome"] in ("Ana", "Pedro")]
    assert os_counts == sorted(os_counts, reverse=True)


@pytest.mark.asyncio
async def test_ranking_default_mes_current_month(
    client: AsyncClient, created_user: dict[str, Any]
) -> None:
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_ranking_export_csv(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    await _seed_tecnico_com_os(db_session, "ExportTec", os_count=2)
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos/export?mes=2026-05",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "")
    lines = r.text.strip().split("\n")
    assert lines[0].startswith("Tecnico,")  # header
    assert any("ExportTec" in line for line in lines[1:])
```

- [ ] **Step 2: Rodar testes para confirmar que falham**

```bash
cd apps/api && pytest tests/test_ranking_tecnicos.py -v 2>&1 | head -20
```

Expected: FAILED (rotas não existem)

- [ ] **Step 3: Adicionar schema `RankingTecnicoOut` em `metrica.py`**

Adicionar ao final de `apps/api/src/ondeline_api/api/schemas/metrica.py`:

```python
class RankingTecnicoOut(BaseModel):
    tecnico_id: str
    nome: str
    os_concluidas: int
    csat_avg: float | None
    tempo_medio_min: int | None
    ultima_os_em: str | None
```

- [ ] **Step 4: Implementar endpoints em `metricas.py`**

Adicionar ao topo de `apps/api/src/ondeline_api/api/v1/metricas.py`:

1. Adicionar imports stdlib após os imports existentes:
```python
import csv
import io
from calendar import monthrange
```

2. Adicionar `StreamingResponse` ao import do FastAPI já existente:
```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
```

3. Adicionar `RankingTecnicoOut` ao import de schemas já existente:
```python
from ondeline_api.api.schemas.metrica import MetricasOut, RankingTecnicoOut
```

4. Adicionar `Tecnico` ao import de models já existente:
```python
from ondeline_api.db.models.business import (
    Conversa,
    ConversaStatus,
    Lead,
    LeadStatus,
    Mensagem,
    OrdemServico,
    OsStatus,
    Tecnico,
)
```

Adicionar os dois endpoints ao final do arquivo:

```python
@router.get("/tecnicos", response_model=list[RankingTecnicoOut], dependencies=[_role_dep])
async def get_ranking_tecnicos(
    session: Annotated[AsyncSession, Depends(get_db)],
    mes: str | None = None,
) -> list[RankingTecnicoOut]:
    """Ranking de técnicos por OS concluídas no mês (formato: YYYY-MM)."""
    now = datetime.now(tz=UTC)
    if mes:
        year, month = int(mes.split("-")[0]), int(mes.split("-")[1])
    else:
        year, month = now.year, now.month

    inicio = datetime(year, month, 1, tzinfo=UTC)
    last_day = monthrange(year, month)[1]
    fim = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

    rows = (
        await session.execute(
            select(
                Tecnico.id,
                Tecnico.nome,
                func.count(OrdemServico.id).label("os_concluidas"),
                func.avg(OrdemServico.csat).label("csat_avg"),
                func.avg(
                    func.extract("epoch", OrdemServico.concluida_em - OrdemServico.criada_em) / 60
                ).label("tempo_medio_min"),
                func.max(OrdemServico.concluida_em).label("ultima_os_em"),
            )
            .outerjoin(
                OrdemServico,
                (OrdemServico.tecnico_id == Tecnico.id)
                & (OrdemServico.status == OsStatus.CONCLUIDA)
                & (OrdemServico.concluida_em >= inicio)
                & (OrdemServico.concluida_em <= fim),
            )
            .where(Tecnico.ativo.is_(True))
            .group_by(Tecnico.id, Tecnico.nome)
            .order_by(func.count(OrdemServico.id).desc())
        )
    ).all()

    return [
        RankingTecnicoOut(
            tecnico_id=str(row.id),
            nome=row.nome,
            os_concluidas=int(row.os_concluidas or 0),
            csat_avg=round(float(row.csat_avg), 2) if row.csat_avg is not None else None,
            tempo_medio_min=int(row.tempo_medio_min) if row.tempo_medio_min is not None else None,
            ultima_os_em=row.ultima_os_em.isoformat() if row.ultima_os_em else None,
        )
        for row in rows
    ]


@router.get("/tecnicos/export", dependencies=[_role_dep])
async def export_ranking_tecnicos_csv(
    session: Annotated[AsyncSession, Depends(get_db)],
    mes: str | None = None,
) -> StreamingResponse:
    """Exporta ranking de técnicos como CSV para download."""
    ranking = await get_ranking_tecnicos(session=session, mes=mes)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tecnico", "OS Concluidas", "CSAT Medio", "Tempo Medio (min)", "Mes"])
    mes_label = mes or datetime.now(tz=UTC).strftime("%Y-%m")
    for r in ranking:
        writer.writerow([
            r.nome,
            r.os_concluidas,
            f"{r.csat_avg:.2f}" if r.csat_avg is not None else "",
            str(r.tempo_medio_min) if r.tempo_medio_min is not None else "",
            mes_label,
        ])

    filename = f"ranking-tecnicos-{mes_label}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

```bash
cd apps/api && pytest tests/test_ranking_tecnicos.py -v
```

Expected: todos PASSED

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/metrica.py \
        apps/api/src/ondeline_api/api/v1/metricas.py \
        apps/api/tests/test_ranking_tecnicos.py
git commit -m "feat(ranking): endpoints /metricas/tecnicos e /metricas/tecnicos/export"
```

---

### Task 2: Frontend — Tipos, Queries e Página de Ranking

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/lib/api/queries.ts`
- Create: `apps/dashboard/app/(admin)/tecnicos/ranking/page.tsx`
- Modify: `apps/dashboard/components/nav-sidebar.tsx`

- [ ] **Step 1: Adicionar tipo `RankingTecnicoOut` em `types.ts`**

Adicionar ao final de `apps/dashboard/lib/api/types.ts`:

```typescript
export interface RankingTecnicoOut {
  tecnico_id: string
  nome: string
  os_concluidas: number
  csat_avg: number | null
  tempo_medio_min: number | null
  ultima_os_em: string | null
}
```

- [ ] **Step 2: Adicionar queries de ranking em `queries.ts`**

Adicionar `RankingTecnicoOut` ao import de types existente e adicionar as funções ao final do arquivo:

```typescript
// ── Ranking de Técnicos ─────────────────────────────────────────────

export function useRankingTecnicos(mes?: string) {
  const qs = mes ? `?mes=${mes}` : ''
  return useQuery<RankingTecnicoOut[]>({
    queryKey: ['ranking-tecnicos', mes],
    queryFn: () => apiFetch(`/api/v1/metricas/tecnicos${qs}`),
  })
}

export function downloadRankingCsv(mes?: string): void {
  const qs = mes ? `?mes=${mes}` : ''
  window.open(`/api/v1/metricas/tecnicos/export${qs}`, '_blank')
}
```

- [ ] **Step 3: Criar a página de ranking**

```typescript
// apps/dashboard/app/(admin)/tecnicos/ranking/page.tsx
'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useRankingTecnicos, downloadRankingCsv } from '@/lib/api/queries'

function formatTempo(min: number | null): string {
  if (min === null) return '—'
  const h = Math.floor(min / 60)
  const m = min % 60
  return h > 0 ? `${h}h${m.toString().padStart(2, '0')}` : `${m}min`
}

function medalha(pos: number): string {
  if (pos === 0) return '🥇'
  if (pos === 1) return '🥈'
  if (pos === 2) return '🥉'
  return String(pos + 1)
}

export default function RankingTecnicosPage() {
  const now = new Date()
  const defaultMes = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const [mes, setMes] = useState(defaultMes)

  const { data, isLoading, error } = useRankingTecnicos(mes)

  const totalOs = (data ?? []).reduce((sum, t) => sum + t.os_concluidas, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ranking de Técnicos</h1>
        <p className="text-sm text-muted-foreground">
          OS concluídas, CSAT médio e tempo médio por técnico no período
        </p>
      </div>

      <div className="flex items-center gap-3">
        <input
          type="month"
          value={mes}
          onChange={(e) => setMes(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        />
        <Button variant="outline" onClick={() => downloadRankingCsv(mes)}>
          ⬇️ Exportar CSV
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && <p className="text-sm text-destructive">Erro ao carregar ranking</p>}

      {data && (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left">#</th>
                  <th className="px-4 py-2 text-left">Técnico</th>
                  <th className="px-4 py-2 text-center">OS Concluídas</th>
                  <th className="px-4 py-2 text-center">CSAT Médio</th>
                  <th className="px-4 py-2 text-center">Tempo Médio</th>
                </tr>
              </thead>
              <tbody>
                {data.map((tec, i) => (
                  <tr
                    key={tec.tecnico_id}
                    className={`border-t ${i === 0 ? 'bg-yellow-50' : ''}`}
                  >
                    <td className="px-4 py-3 font-medium">{medalha(i)}</td>
                    <td className="px-4 py-3 font-medium">{tec.nome}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          tec.os_concluidas >= 30
                            ? 'bg-green-100 text-green-800'
                            : tec.os_concluidas >= 10
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {tec.os_concluidas}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {tec.csat_avg !== null ? `⭐ ${tec.csat_avg.toFixed(1)}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-center text-muted-foreground">
                      {formatTempo(tec.tempo_medio_min)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-right text-xs text-muted-foreground">
            Total: {totalOs} OS concluídas no período
          </p>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Adicionar link no menu lateral**

Em `apps/dashboard/components/nav-sidebar.tsx`, adicionar import de `Trophy` do Lucide e inserir item no array `ITEMS` após o item de técnicos:

Adicionar ao import de ícones:
```typescript
import { BarChart3, CalendarClock, ClipboardList, MessageSquare, Package, Settings, Trophy, UserPlus, Users, Wrench } from 'lucide-react'
```

Inserir após `{ href: '/tecnicos', ... }`:
```typescript
  { href: '/tecnicos/ranking', label: 'Ranking Técnicos', icon: Trophy, roles: ['admin'] },
```

- [ ] **Step 5: Verificar TypeScript**

```bash
cd apps/dashboard && pnpm tsc --noEmit 2>&1 | grep -E "ranking|nav-sidebar" | head -10
```

Expected: sem erros

- [ ] **Step 6: Commit**

```bash
git add apps/dashboard/lib/api/types.ts \
        apps/dashboard/lib/api/queries.ts \
        apps/dashboard/app/(admin)/tecnicos/ranking/page.tsx \
        apps/dashboard/components/nav-sidebar.tsx
git commit -m "feat(ranking): página /tecnicos/ranking com tabela e exportação CSV"
```

---

### Task 3: Smoke test visual

- [ ] **Step 1: Subir o servidor de desenvolvimento**

```bash
cd apps/dashboard && pnpm dev
```

- [ ] **Step 2: Verificar no browser**

1. Navegar para `http://localhost:3000/tecnicos/ranking`
2. Confirmar que a tabela carrega (pode estar vazia se não houver OS no banco de dev)
3. Mudar o mês no filtro — tabela deve recarregar
4. Clicar "Exportar CSV" — deve fazer download de um arquivo CSV
5. Verificar que o link "Ranking Técnicos" aparece no menu lateral

- [ ] **Step 3: Commit final**

```bash
git add -A
git commit -m "feat(ranking): ranking de técnicos completo com CSV e filtro por mês"
```
