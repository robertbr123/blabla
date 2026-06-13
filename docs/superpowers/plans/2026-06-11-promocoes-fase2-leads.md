# Promoções Fase 2 (página + landing CTA + leads) + Tema padrão light — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar o funil de promoções: página dedicada `/promocoes` no app + landing de detalhe com botão "Tenho interesse" que vira lead com workflow de status na dashboard; e tema padrão do app vira light no primeiro uso (seletor system/light/dark mantido).

**Architecture:** Spec aprovado em `docs/superpowers/specs/2026-06-11-promocoes-fase2-pagina-cta-leads-design.md`. Fatia 1 = API (migration `0048` com campos `descricao_longa`/`regulamento` + tabela `promocoes_leads`, endpoints cliente e admin) + dashboard (form + aba Leads). Fatia 2 = app Flutter (rotas `/promocoes` e `/promocoes/:id` com hero animation, PromoCard compartilhado, botão de interesse). Cada fatia funciona sozinha.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Pydantic v2; Next.js 15 + React Query + shadcn/ui; Flutter 3.44 + Riverpod 2 + GoRouter 14.

**Regras gerais:**
- Commits locais por task, **NUNCA git push** (Robert dá OK no final).
- Python: `from __future__ import annotations` colado na docstring; SEM anotações entre aspas (ruff UP037); validar local com `cd /Users/robertalbino/Developer/blabla && uvx ruff check apps/api/src apps/api/tests` e `cd apps/api && .venv/bin/mypy src/ondeline_api/<arquivo>`. **pytest NÃO roda local** — testes são escritos e rodam no CI após push.
- Flutter: `flutter analyze` (warning/error quebram) + `flutter test`; convenção `withValues(alpha:)`.
- Dashboard: `pnpm build` local antes de considerar done (barrel optimization do lucide só quebra em build). Ícones lucide: conferir que existem (grep no projeto antes de usar nome novo).

---

## FATIA 0 — Tema padrão light (app)

### Task 1: Default light no ThemeModeNotifier

**Files:**
- Modify: `apps/cliente-mobile/lib/core/theme/theme_mode_controller.dart`

Hoje: estado inicial `ThemeMode.system` e fallback do load também system → quem baixa o app abre no tema do celular (dark em muita gente). Robert quer: **primeiro uso abre light**; seletor do perfil (system/light/dark) continua funcionando e persistindo.

- [ ] **Step 1: Trocar default**

O arquivo inteiro vira:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  // Light por padrão: primeiro uso abre claro (decisão de produto);
  // quem preferir escuro/sistema escolhe no Perfil e fica persistido.
  ThemeModeNotifier() : super(ThemeMode.light) {
    _load();
  }
  static const _key = 'theme_mode';

  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    final v = p.getString(_key);
    state = switch (v) {
      'system' => ThemeMode.system,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.light,
    };
  }

  Future<void> set(ThemeMode m) async {
    state = m;
    final p = await SharedPreferences.getInstance();
    await p.setString(_key, m.name);
  }
}

final themeModeProvider =
    StateNotifierProvider<ThemeModeNotifier, ThemeMode>(
        (ref) => ThemeModeNotifier());
```

Nota: usuários existentes que nunca tocaram no seletor (sem chave salva) passam a abrir light — comportamento desejado. Quem já salvou 'system'/'dark' não muda.

- [ ] **Step 2: Conferir o seletor do perfil**

Grep `themeModeProvider` em `lib/features/perfil/perfil_screen.dart` — confirmar que o seletor oferece as 3 opções e chama `.set(...)`. Não deve precisar de mudança; se o seletor assumir system como "default visual" em algum label, ajustar o texto.

- [ ] **Step 3: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla/apps/cliente-mobile && flutter analyze && flutter test`
Expected: limpo / 11 PASS.

```bash
git add lib/core/theme/theme_mode_controller.dart
git commit -m "feat(app): tema padrao light no primeiro uso (seletor mantido)"
```

---

## FATIA 1 — Backend (API)

### Task 2: Modelo + migration 0048 + schemas

**Files:**
- Modify: `apps/api/src/ondeline_api/db/models/promocoes.py`
- Create: `apps/api/alembic/versions/0048_promocoes_leads.py`
- Modify: `apps/api/src/ondeline_api/api/schemas/promocao.py`

- [ ] **Step 1: Campos novos + modelo PromocaoLead**

Em `db/models/promocoes.py`, adicionar na classe `Promocao` (depois de `icon`):

```python
    # Landing de detalhe no app (Fase 2). Opcionais — promo sem descrição
    # continua funcionando só com subtítulo.
    descricao_longa: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulamento: Mapped[str | None] = mapped_column(Text, nullable=True)
```

E no fim do arquivo, a classe nova (imports já existentes no arquivo: `UniqueConstraint` precisa entrar no import de sqlalchemy):

```python
class PromocaoLead(Base):
    """Lead de "Tenho interesse" — cliente demonstrou interesse numa promo.

    Snapshot de nome/telefone na hora do clique pra equipe de vendas não
    precisar cruzar com SGP. Unique por (promocao, user): sem lead duplicado.
    """

    __tablename__ = "promocoes_leads"
    __table_args__ = (
        UniqueConstraint(
            "promocao_id", "cliente_app_user_id", name="uq_promo_lead_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    promocao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promocoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    cliente_app_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    contrato_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nome_snapshot: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    telefone_snapshot: Mapped[str] = mapped_column(
        String(32), nullable=False, default=""
    )
    # novo → contatado → convertido | descartado
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="novo")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
```

- [ ] **Step 2: Migration**

`apps/api/alembic/versions/0048_promocoes_leads.py` (estilo das migrations do repo; CUIDADO: dentro de `sa.text(...)` nunca usar `:valor` colado — bind param gotcha):

```python
"""Promoções Fase 2: landing de detalhe + leads de interesse.

- `promocoes.descricao_longa` / `promocoes.regulamento` — conteúdo da landing.
- `promocoes_leads` — "Tenho interesse" vira lead com workflow de status
  (novo → contatado → convertido | descartado). Unique (promocao, user).

Revision ID: 0048_promocoes_leads
Revises: 0047_os_sinal
Create Date: 2026-06-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0048_promocoes_leads"
down_revision: str | None = "0047_os_sinal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("promocoes", sa.Column("descricao_longa", sa.Text(), nullable=True))
    op.add_column("promocoes", sa.Column("regulamento", sa.Text(), nullable=True))

    op.create_table(
        "promocoes_leads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "promocao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("promocoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cliente_app_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contrato_id", sa.String(64), nullable=True),
        sa.Column("nome_snapshot", sa.String(160), nullable=False, server_default=""),
        sa.Column("telefone_snapshot", sa.String(32), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="novo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "promocao_id", "cliente_app_user_id", name="uq_promo_lead_user"
        ),
    )
    op.create_index(
        "ix_promocoes_leads_status", "promocoes_leads", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_promocoes_leads_status", table_name="promocoes_leads")
    op.drop_table("promocoes_leads")
    op.drop_column("promocoes", "regulamento")
    op.drop_column("promocoes", "descricao_longa")
```

(Confira numa migration recente se o projeto usa `gen_random_uuid()` server_default ou deixa o default por conta do Python — se as tabelas existentes não usam server_default no id, remova e siga o padrão delas.)

- [ ] **Step 3: Schemas**

Em `api/schemas/promocao.py`:

1. `PromocaoBaseIn` ganha (depois de `icon`):
```python
    descricao_longa: str | None = None
    regulamento: str | None = None
```
2. `PromocaoUpdateIn` ganha os mesmos 2 campos opcionais.
3. `PromocaoOut` ganha:
```python
    descricao_longa: str | None
    regulamento: str | None
```
4. `PromocaoAdminOut` ganha `leads_count: int = 0` (depois de `ctr`).
5. Novos schemas no fim do arquivo:

```python
LEAD_STATUSES = {"novo", "contatado", "convertido", "descartado"}


class PromocaoDetalheOut(PromocaoOut):
    """Detalhe pro app: inclui se o user atual já registrou interesse."""

    interesse_registrado: bool = False


class PromocaoInteresseIn(BaseModel):
    contrato_id: str | None = None


class PromocaoInteresseOut(BaseModel):
    ok: bool = True
    ja_registrado: bool = False


class PromocaoLeadAdminOut(BaseModel):
    id: UUID
    promocao_id: UUID
    promocao_titulo: str
    nome: str
    telefone: str
    contrato_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class PromocaoLeadPatchIn(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str) -> str:
        if v not in LEAD_STATUSES:
            raise ValueError(f"status invalido (use: {sorted(LEAD_STATUSES)})")
        return v
```

- [ ] **Step 4: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla && uvx ruff check apps/api/src && (cd apps/api && .venv/bin/mypy src/ondeline_api/db/models/promocoes.py src/ondeline_api/api/schemas/promocao.py)`
Expected: limpo.

```bash
git add apps/api
git commit -m "feat(promocoes): modelo+migration de leads e campos da landing (descricao/regulamento)"
```

### Task 3: Endpoints cliente (detalhe + interesse) com testes

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/cliente_app_promocoes.py`
- Create: `apps/api/tests/test_promocoes_leads.py`

- [ ] **Step 1: Endpoints no `router` (cliente)**

⚠️ **ORDEM DAS ROTAS:** o `GET /{promo_id}` novo NÃO conflita com `POST /{promo_id}/evento` (métodos/paths diferentes), mas declare `GET ""` (lista) antes de `GET /{promo_id}` (já é assim). No `admin_router` da Task 4, as rotas `/leads` DEVEM ser declaradas ANTES de `/{promo_id}` no arquivo (senão "leads" tenta parsear como UUID → 422).

Adicionar no `cliente_app_promocoes.py` (imports novos: `PromocaoDetalheOut`, `PromocaoInteresseIn`, `PromocaoInteresseOut`, `PromocaoLead`, `decrypt_pii` de `ondeline_api.db.crypto`, `IntegrityError` de `sqlalchemy.exc`):

```python
@router.get("/{promo_id}", response_model=PromocaoDetalheOut)
async def detalhe_para_cliente(
    promo_id: UUID,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoDetalheOut:
    """Landing de detalhe. Só promo ativa/válida (mesma regra da lista)."""
    promo = await session.get(Promocao, promo_id)
    if promo is None or not promo.ativa:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    ja = await session.scalar(
        select(PromocaoLead.id).where(
            PromocaoLead.promocao_id == promo_id,
            PromocaoLead.cliente_app_user_id == user.id,
        )
    )
    out = PromocaoDetalheOut.model_validate(promo, from_attributes=True)
    out.interesse_registrado = ja is not None
    return out


@router.post("/{promo_id}/interesse", response_model=PromocaoInteresseOut)
async def registrar_interesse(
    promo_id: UUID,
    body: PromocaoInteresseIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoInteresseOut:
    """Cria lead de interesse. Idempotente: segundo toque → ja_registrado."""
    promo = await session.get(Promocao, promo_id)
    if promo is None or not promo.ativa:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")

    existente = await session.scalar(
        select(PromocaoLead.id).where(
            PromocaoLead.promocao_id == promo_id,
            PromocaoLead.cliente_app_user_id == user.id,
        )
    )
    if existente is not None:
        return PromocaoInteresseOut(ok=True, ja_registrado=True)

    # Snapshot de contato na hora do clique — equipe liga sem cruzar com SGP.
    nome = decrypt_pii(user.nome_encrypted) if user.nome_encrypted else ""
    telefone = decrypt_pii(user.telefone_encrypted) if user.telefone_encrypted else ""
    lead = PromocaoLead(
        promocao_id=promo_id,
        cliente_app_user_id=user.id,
        contrato_id=body.contrato_id,
        nome_snapshot=nome[:160],
        telefone_snapshot=telefone[:32],
    )
    session.add(lead)
    try:
        await session.commit()
    except IntegrityError:
        # Corrida com outro request do mesmo user — unique constraint segura.
        await session.rollback()
        return PromocaoInteresseOut(ok=True, ja_registrado=True)
    return PromocaoInteresseOut(ok=True, ja_registrado=False)
```

Conferir também o endpoint de evento existente: se `PromocaoEventoIn.tipo` tiver validação restrita a `view|click` (no schema ou no endpoint), incluir `detail_view` no set permitido. Se não houver validação, nada a fazer (String(16) comporta).

- [ ] **Step 2: Testes**

`apps/api/tests/test_promocoes_leads.py` — seguir o padrão de fixtures de `tests/test_cliente_app_me.py` (db_session do conftest, ClienteAppUser com `encrypt_pii`, app com dependency_overrides, AsyncClient, login pra obter token — COPIE o mecanismo exato de auth de um teste cliente-app existente; se houver helper de token, use). Casos:

```python
@pytest.mark.asyncio
async def test_interesse_cria_lead(...):
    # cria promo ativa direto na db_session; POST /interesse com token
    # → 200 {ok: true, ja_registrado: false}; SELECT na tabela confirma
    # nome_snapshot == "Cliente Teste" e status == "novo"

@pytest.mark.asyncio
async def test_interesse_idempotente(...):
    # POST 2x → segundo retorna ja_registrado: true; COUNT == 1

@pytest.mark.asyncio
async def test_detalhe_retorna_campos_e_interesse(...):
    # promo com descricao_longa/regulamento; GET /{id} → campos presentes,
    # interesse_registrado false; após POST interesse → true

@pytest.mark.asyncio
async def test_detalhe_promo_inativa_404(...):
    # promo ativa=False → GET /{id} → 404 e POST /interesse → 404
```

(Escreva os testes completos no estilo do arquivo de referência — eles rodam no CI, não local.)

- [ ] **Step 3: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla && uvx ruff check apps/api/src apps/api/tests && (cd apps/api && .venv/bin/mypy src/ondeline_api/api/v1/cliente_app_promocoes.py)`
Expected: limpo.

```bash
git add apps/api
git commit -m "feat(promocoes): endpoints de detalhe + interesse (lead idempotente) com testes"
```

### Task 4: Endpoints admin de leads + leads_count

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/cliente_app_promocoes.py`
- Modify: `apps/api/tests/test_promocoes_leads.py`

- [ ] **Step 1: Endpoints admin**

⚠️ Declarar **ANTES** de qualquer rota `/{promo_id}` do `admin_router` no arquivo (ordem de declaração define o match):

```python
@admin_router.get(
    "/leads",
    response_model=list[PromocaoLeadAdminOut],
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_listar_leads(
    promocao_id: UUID | None = None,
    status_filtro: str | None = None,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoLeadAdminOut]:
    q = (
        select(PromocaoLead, Promocao.titulo)
        .join(Promocao, Promocao.id == PromocaoLead.promocao_id)
        .order_by(PromocaoLead.created_at.desc())
    )
    if promocao_id is not None:
        q = q.where(PromocaoLead.promocao_id == promocao_id)
    if status_filtro:
        q = q.where(PromocaoLead.status == status_filtro)
    rows = (await session.execute(q)).all()
    return [
        PromocaoLeadAdminOut(
            id=lead.id,
            promocao_id=lead.promocao_id,
            promocao_titulo=titulo,
            nome=lead.nome_snapshot,
            telefone=lead.telefone_snapshot,
            contrato_id=lead.contrato_id,
            status=lead.status,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )
        for lead, titulo in rows
    ]


@admin_router.patch(
    "/leads/{lead_id}",
    response_model=PromocaoLeadAdminOut,
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_atualizar_lead(
    lead_id: UUID,
    body: PromocaoLeadPatchIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoLeadAdminOut:
    lead = await session.get(PromocaoLead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead nao encontrado")
    lead.status = body.status
    await session.commit()
    await session.refresh(lead)
    promo = await session.get(Promocao, lead.promocao_id)
    return PromocaoLeadAdminOut(
        id=lead.id,
        promocao_id=lead.promocao_id,
        promocao_titulo=promo.titulo if promo else "",
        nome=lead.nome_snapshot,
        telefone=lead.telefone_snapshot,
        contrato_id=lead.contrato_id,
        status=lead.status,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )
```

Nota: PATCH com role ATENDENTE+ é decisão do spec (atendente trabalha o lead). O query param chama `status_filtro` (não `status`) pra não colidir com `status` do FastAPI/starlette import comum no arquivo — confira como o arquivo importa `status` do fastapi; se não importar, pode chamar `status` mesmo, mas mantenha `status_filtro` por segurança e exponha como `?status_filtro=` (dashboard usa esse nome).

- [ ] **Step 2: leads_count no admin_listar existente**

No endpoint `GET /api/v1/admin/promocoes` (admin_listar), onde monta views/clicks/ctr, adicionar contagem de leads por promo (mesmo padrão da agregação de eventos — um `select(PromocaoLead.promocao_id, func.count()).group_by(...)` e map no loop) e preencher `leads_count=...` no `PromocaoAdminOut`.

- [ ] **Step 3: Testes admin**

Adicionar em `test_promocoes_leads.py` (auth admin: copie o padrão de outro teste admin existente — grep `require_role` ou `admin` em apps/api/tests pra achar como geram token de admin):

```python
@pytest.mark.asyncio
async def test_admin_lista_leads_com_filtro(...):
    # cria 2 leads (status novo e contatado) → GET /admin/promocoes/leads
    # → 2 itens com promocao_titulo; ?status_filtro=novo → 1

@pytest.mark.asyncio
async def test_admin_patch_lead_status(...):
    # PATCH {status: contatado} → 200, status muda
    # PATCH {status: banana} → 422

@pytest.mark.asyncio
async def test_admin_listar_inclui_leads_count(...):
    # promo com 1 lead → GET /admin/promocoes → leads_count == 1
```

- [ ] **Step 4: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla && uvx ruff check apps/api/src apps/api/tests && (cd apps/api && .venv/bin/mypy src/ondeline_api/api/v1/cliente_app_promocoes.py)`
Expected: limpo.

```bash
git add apps/api
git commit -m "feat(promocoes): admin de leads (lista+filtros+status) e leads_count"
```

---

## FATIA 1 — Dashboard

### Task 5: Types + hooks + campos no form

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/lib/api/queries.ts`
- Modify: `apps/dashboard/components/promocao-form-dialog.tsx`

- [ ] **Step 1: Types**

Em `types.ts`: `Promocao` ganha `descricao_longa: string | null` e `regulamento: string | null`; `PromocaoCreate` ganha os 2 como `?: string | null`; `PromocaoAdmin` ganha `leads_count: number`. Tipos novos:

```typescript
export type PromocaoLeadStatus = 'novo' | 'contatado' | 'convertido' | 'descartado'

export interface PromocaoLeadAdmin {
  id: string
  promocao_id: string
  promocao_titulo: string
  nome: string
  telefone: string
  contrato_id: string | null
  status: PromocaoLeadStatus
  created_at: string
  updated_at: string
}
```

- [ ] **Step 2: Hooks**

Em `queries.ts`, junto dos hooks de promoções:

```typescript
export function usePromocaoLeads(filtros?: {
  promocaoId?: string
  status?: import('./types').PromocaoLeadStatus
}) {
  const params = new URLSearchParams()
  if (filtros?.promocaoId) params.set('promocao_id', filtros.promocaoId)
  if (filtros?.status) params.set('status_filtro', filtros.status)
  const qs = params.toString()
  return useQuery<import('./types').PromocaoLeadAdmin[]>({
    queryKey: ['promocoes-leads', filtros?.promocaoId ?? '', filtros?.status ?? ''],
    queryFn: () => apiFetch(`/api/v1/admin/promocoes/leads${qs ? `?${qs}` : ''}`),
  })
}

export function usePatchPromocaoLead(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: { status: import('./types').PromocaoLeadStatus }) =>
      apiFetch<import('./types').PromocaoLeadAdmin>(
        `/api/v1/admin/promocoes/leads/${id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['promocoes-leads'] })
      qc.invalidateQueries({ queryKey: ['promocoes-admin'] })
    },
  })
}
```

(Atenção: a queryKey de leads usa array com filtros; o invalidate sem filtros pega todas pelas partial matches do React Query.)

- [ ] **Step 3: Form**

Em `promocao-form-dialog.tsx`, depois do bloco do Textarea de `subtitulo`, adicionar 2 campos no mesmo padrão (e incluir `descricao_longa`/`regulamento` no `emptyDraft()` e no objeto montado a partir da promo em edição):

```tsx
<div className="space-y-1.5">
  <Label htmlFor="descricao_longa">Descrição completa (landing do app)</Label>
  <Textarea
    id="descricao_longa"
    value={draft.descricao_longa ?? ''}
    onChange={(e) => setField('descricao_longa', e.target.value || null)}
    rows={4}
    placeholder="Texto completo da promoção, em parágrafos. Aparece na página de detalhe do app."
  />
</div>
<div className="space-y-1.5">
  <Label htmlFor="regulamento">Regulamento / condições</Label>
  <Textarea
    id="regulamento"
    value={draft.regulamento ?? ''}
    onChange={(e) => setField('regulamento', e.target.value || null)}
    rows={3}
    placeholder="Regras da promoção. Vira seção expansível 'Regras da promoção' no app."
  />
</div>
```

(Adapte a estrutura de Label/div ao que o form usa de verdade — copie o wrapper do campo subtitulo.)

- [ ] **Step 4: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla && pnpm --filter dashboard build` (ou o comando de build usado no repo — confira o package.json; fallback `cd apps/dashboard && pnpm build`)
Expected: build verde.

```bash
git add apps/dashboard
git commit -m "feat(dashboard/promocoes): campos da landing no form + hooks de leads"
```

### Task 6: Aba Leads na página de promoções

**Files:**
- Modify: `apps/dashboard/app/(admin)/promocoes/page.tsx`
- Create: `apps/dashboard/components/promocao-leads-tab.tsx`

- [ ] **Step 1: Componente da aba**

`promocao-leads-tab.tsx` — novo componente client ('use client'), seguindo padrões do repo (tabela HTML pura como `lead-list.tsx`, status badges como `cliente-app-fidelidade`):

```tsx
'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  usePatchPromocaoLead,
  usePromocaoLeads,
  usePromocoesAdmin,
} from '@/lib/api/queries'
import type { PromocaoLeadAdmin, PromocaoLeadStatus } from '@/lib/api/types'

const STATUS_LABEL: Record<PromocaoLeadStatus, string> = {
  novo: 'Novo',
  contatado: 'Contatado',
  convertido: 'Convertido',
  descartado: 'Descartado',
}

const STATUS_STYLE: Record<PromocaoLeadStatus, string> = {
  novo: 'bg-blue-50 text-blue-700 border border-blue-200',
  contatado: 'bg-amber-50 text-amber-700 border border-amber-200',
  convertido: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  descartado: 'bg-zinc-100 text-zinc-600 border border-zinc-200',
}

const ALL_STATUSES: PromocaoLeadStatus[] = [
  'novo',
  'contatado',
  'convertido',
  'descartado',
]

function LeadStatusSelect({ lead }: { lead: PromocaoLeadAdmin }) {
  const patch = usePatchPromocaoLead(lead.id)
  return (
    <select
      className="rounded-md border bg-background px-2 py-1 text-xs"
      value={lead.status}
      disabled={patch.isPending}
      onChange={(e) => patch.mutate({ status: e.target.value as PromocaoLeadStatus })}
    >
      {ALL_STATUSES.map((s) => (
        <option key={s} value={s}>
          {STATUS_LABEL[s]}
        </option>
      ))}
    </select>
  )
}

export function PromocaoLeadsTab() {
  const [statusFiltro, setStatusFiltro] = useState<PromocaoLeadStatus | ''>('')
  const [promoFiltro, setPromoFiltro] = useState('')
  const { data: promos } = usePromocoesAdmin()
  const { data: leads, isLoading } = usePromocaoLeads({
    promocaoId: promoFiltro || undefined,
    status: statusFiltro || undefined,
  })

  const total = leads?.length ?? 0
  const novos = leads?.filter((l) => l.status === 'novo').length ?? 0
  const convertidos = leads?.filter((l) => l.status === 'convertido').length ?? 0
  const conversao = total > 0 ? Math.round((convertidos / total) * 100) : 0

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Leads novos</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{novos}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Total (filtro atual)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{total}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Conversão</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{conversao}%</CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          className="rounded-md border bg-background px-2 py-1.5 text-sm"
          value={promoFiltro}
          onChange={(e) => setPromoFiltro(e.target.value)}
        >
          <option value="">Todas as promoções</option>
          {(promos ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.titulo}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border bg-background px-2 py-1.5 text-sm"
          value={statusFiltro}
          onChange={(e) => setStatusFiltro(e.target.value as PromocaoLeadStatus | '')}
        >
          <option value="">Todos os status</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-md border bg-card">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-semibold">Cliente</th>
              <th className="px-4 py-2.5 font-semibold">Telefone</th>
              <th className="px-4 py-2.5 font-semibold">Contrato</th>
              <th className="px-4 py-2.5 font-semibold">Promoção</th>
              <th className="px-4 py-2.5 font-semibold">Data</th>
              <th className="px-4 py-2.5 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-6 text-muted-foreground" colSpan={6}>
                  Carregando…
                </td>
              </tr>
            )}
            {!isLoading && (leads ?? []).length === 0 && (
              <tr>
                <td className="px-4 py-6 text-muted-foreground" colSpan={6}>
                  Nenhum lead ainda. Quando um cliente tocar em “Tenho interesse” no
                  app, ele aparece aqui.
                </td>
              </tr>
            )}
            {(leads ?? []).map((l) => (
              <tr key={l.id} className="border-b last:border-b-0 hover:bg-accent/40">
                <td className="px-4 py-3 font-medium">{l.nome || '—'}</td>
                <td className="px-4 py-3">{l.telefone || '—'}</td>
                <td className="px-4 py-3 text-muted-foreground">{l.contrato_id ?? '—'}</td>
                <td className="px-4 py-3 text-muted-foreground">{l.promocao_titulo}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {new Date(l.created_at).toLocaleDateString('pt-BR')}
                </td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-2">
                    <Badge className={STATUS_STYLE[l.status]} variant="outline">
                      {STATUS_LABEL[l.status]}
                    </Badge>
                    <LeadStatusSelect lead={l} />
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Tabs na página + leads_count na lista**

Em `promocoes/page.tsx`:
1. `const [tab, setTab] = useState<'promos' | 'leads'>('promos')` + barra de tabs no padrão do repo (botões com `border-b-2`, ver `cliente-app-os/page.tsx` linhas ~299-378). Labels: "Promoções" e "Leads".
2. `{tab === 'leads' ? <PromocaoLeadsTab /> : (<conteúdo atual>)}`.
3. Na linha de stats de cada promo (onde mostra views/clicks/CTR), adicionar `leads_count` com label "Leads".
4. Badge de contagem de leads novos na própria aba (opcional barato: usar `usePromocaoLeads({status:'novo'})` no page e mostrar `Leads (N)`） — se complicar o build, deixar só "Leads".

- [ ] **Step 3: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla/apps/dashboard && pnpm build`
Expected: verde.

```bash
git add apps/dashboard
git commit -m "feat(dashboard/promocoes): aba Leads com filtros, status inline e metricas"
```

---

## FATIA 2 — App Flutter

### Task 7: DTO + repository + PromoCard compartilhado

**Files:**
- Modify: `apps/cliente-mobile/lib/core/api/dto.dart`
- Modify: `apps/cliente-mobile/lib/core/api/promocoes_repository.dart`
- Create: `apps/cliente-mobile/lib/features/promocoes/widgets/promo_card.dart`
- Modify: `apps/cliente-mobile/lib/features/home/widgets/promo_carousel.dart`

- [ ] **Step 1: DTO**

`PromocaoDto` (dto.dart linha ~404) ganha campos + parse:

```dart
  // construtor: adicionar
    this.descricaoLonga,
    this.regulamento,
    this.validoAte,
  // fromJson: adicionar
        descricaoLonga: j['descricao_longa'] as String?,
        regulamento: j['regulamento'] as String?,
        validoAte: j['valido_ate'] == null
            ? null
            : DateTime.tryParse(j['valido_ate'] as String),
  // campos:
  final String? descricaoLonga;
  final String? regulamento;
  final DateTime? validoAte;
```

E DTO novo no mesmo arquivo (depois do PromocaoDto):

```dart
class PromocaoDetalheDto extends PromocaoDto {
  PromocaoDetalheDto({
    required super.id,
    required super.titulo,
    required super.subtitulo,
    required super.imagemUrl,
    required super.ctaLabel,
    required super.ctaAction,
    required super.tipo,
    required super.gradientFrom,
    required super.gradientTo,
    required super.icon,
    super.descricaoLonga,
    super.regulamento,
    super.validoAte,
    required this.interesseRegistrado,
  });

  factory PromocaoDetalheDto.fromJson(Map<String, dynamic> j) {
    final base = PromocaoDto.fromJson(j);
    return PromocaoDetalheDto(
      id: base.id,
      titulo: base.titulo,
      subtitulo: base.subtitulo,
      imagemUrl: base.imagemUrl,
      ctaLabel: base.ctaLabel,
      ctaAction: base.ctaAction,
      tipo: base.tipo,
      gradientFrom: base.gradientFrom,
      gradientTo: base.gradientTo,
      icon: base.icon,
      descricaoLonga: base.descricaoLonga,
      regulamento: base.regulamento,
      validoAte: base.validoAte,
      interesseRegistrado: (j['interesse_registrado'] as bool?) ?? false,
    );
  }

  final bool interesseRegistrado;
}
```

(Se `PromocaoDto` tiver construtor com `required this.x` posicional impossibilitando super-params, adapte: campos novos opcionais no construtor com `this.`.)

- [ ] **Step 2: Repository**

`promocoes_repository.dart` ganha:

```dart
  Future<PromocaoDetalheDto> detalhe(String id) async {
    final r = await _dio.get('$_base/$id');
    return PromocaoDetalheDto.fromJson(r.data as Map<String, dynamic>);
  }

  /// Registra interesse (lead). NÃO é fire-and-forget — lead é dado de
  /// negócio; erro sobe pro caller mostrar retry.
  Future<bool> registrarInteresse(String id, {String? contratoId}) async {
    final r = await _dio.post(
      '$_base/$id/interesse',
      data: {'contrato_id': contratoId},
    );
    final data = r.data as Map<String, dynamic>;
    return (data['ja_registrado'] as bool?) ?? false;
  }
```

E provider de detalhe:

```dart
final promocaoDetalheProvider =
    FutureProvider.family<PromocaoDetalheDto, String>(
  (ref, id) => ref.watch(promocoesRepositoryProvider).detalhe(id),
);
```

- [ ] **Step 3: Extrair PromoCard compartilhado**

Criar `lib/features/promocoes/widgets/promo_card.dart` movendo o `_PromoCard` de `promo_carousel.dart` pra classe pública `PromoCard` (mesmo visual: gradiente com fallback `BrandTokens.promoFallbackFrom/To`, imagem 35%, CTA ghost, ícone circular; manter o `PressableScale`). Adicionar `Hero` com tag `'promo-${item.id}'` envolvendo o Container (dentro do PressableScale):

```dart
    return PressableScale(
      onTap: () => onTap(item),
      child: Hero(
        tag: 'promo-${item.id}',
        child: Container(
          // ... (visual inalterado)
        ),
      ),
    );
```

`promo_carousel.dart`: remover `_PromoCard`, importar `../../promocoes/widgets/promo_card.dart`, usar `PromoCard(item: ..., onTap: ...)`. Imports órfãos (hex_color, promo_icon_map, api_client) saem do carousel se só o card usava — conferir.

- [ ] **Step 4: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib
git commit -m "feat(app/promocoes): DTO detalhe + repository de interesse + PromoCard compartilhado com Hero"
```

### Task 8: Página /promocoes (lista) + "Ver todas" na home + rotas

**Files:**
- Create: `apps/cliente-mobile/lib/features/promocoes/promocoes_screen.dart`
- Modify: `apps/cliente-mobile/lib/features/home/home_screen.dart`
- Modify: `apps/cliente-mobile/lib/router.dart`

- [ ] **Step 1: Tela de lista**

`promocoes_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/dto.dart';
import '../../core/api/promocoes_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/async_states.dart';
import '../../core/ui/glass_app_bar.dart';

/// Página dedicada de promoções: mesma vitrine do carrossel, em lista
/// vertical. Tap no card abre a landing de detalhe (/promocoes/:id).
class PromocoesScreen extends ConsumerWidget {
  const PromocoesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(promocoesProvider);
    final topPad =
        MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd;

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: const GlassAppBar(title: 'Promoções'),
      body: RefreshIndicator(
        edgeOffset: MediaQuery.paddingOf(context).top + kToolbarHeight,
        onRefresh: () async {
          ref.invalidate(promocoesProvider);
          await ref.read(promocoesProvider.future);
        },
        child: AsyncBuilder<List<PromocaoDto>>(
          value: async,
          loading: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.only(top: topPad),
            children: const [Center(child: CircularProgressIndicator())],
          ),
          error: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.fromLTRB(
              BrandTokens.spaceMd, topPad, BrandTokens.spaceMd, BrandTokens.spaceMd,
            ),
            children: [
              ErrorCard(onRetry: () => ref.invalidate(promocoesProvider)),
            ],
          ),
          builder: (promos) {
            if (promos.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.only(top: topPad),
                children: const [
                  EmptyState(
                    icon: Icons.local_offer_outlined,
                    title: 'Nenhuma promoção no momento',
                    subtitle: 'Quando rolar novidade boa, ela aparece aqui.',
                  ),
                ],
              );
            }
            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: EdgeInsets.fromLTRB(
                BrandTokens.spaceMd, topPad, BrandTokens.spaceMd, BrandTokens.spaceXl,
              ),
              itemCount: promos.length,
              separatorBuilder: (_, __) =>
                  const SizedBox(height: BrandTokens.spaceMd),
              itemBuilder: (_, i) => SizedBox(
                height: 172,
                child: PromoCard(
                  item: promos[i],
                  onTap: (p) => context.push('/promocoes/${p.id}'),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
```

(Import do PromoCard: `import 'widgets/promo_card.dart';`.)

- [ ] **Step 2: Card do carrossel passa a abrir o detalhe + "Ver todas" na home**

Em `promo_carousel.dart`, no `_onTap`: o tap continua registrando `click`, mas agora navega pro detalhe em vez de executar a ação direto (a ação original vive no botão da landing):

```dart
  Future<void> _onTap(PromocaoDto p) async {
    ref.read(promocoesRepositoryProvider).registrarEvento(p.id, 'click');
    if (!mounted) return;
    context.push('/promocoes/${p.id}');
  }
```

(Remover os branches url/tela/info do `_onTap` do carrossel e os imports que ficarem órfãos — `url_launcher` sai se só ele usava.)

Em `home_screen.dart` (linhas ~98-110), trocar o `_SectionLabel` simples por cabeçalho com ação quando 2+ promos:

```dart
              ...promosAsync.when(
                data: (promos) {
                  if (promos.isEmpty) return const <Widget>[];
                  return [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const _SectionLabel(label: 'Pra você'),
                        if (promos.length > 1)
                          TextButton(
                            onPressed: () => context.push('/promocoes'),
                            child: const Text('Ver todas →'),
                          ),
                      ],
                    ),
                    const SizedBox(height: BrandTokens.spaceSm),
                    PromoCarousel(items: promos),
                    const SizedBox(height: BrandTokens.spaceLg),
                  ];
                },
                loading: () => const <Widget>[],
                error: (_, __) => const <Widget>[],
              ),
```

(Conferir se `_SectionLabel` já vem dentro de Padding — ajustar pra Row não desalinha; e se home_screen importa go_router — importa, usa context.push em outros pontos.)

- [ ] **Step 3: Rotas**

Em `router.dart`, junto das rotas internas (usando o `_glassPage` existente; a rota `:id` vem DEPOIS da fixa):

```dart
      GoRoute(
        path: '/promocoes',
        pageBuilder: (_, state) => _glassPage(state, const PromocoesScreen()),
      ),
      GoRoute(
        path: '/promocoes/:id',
        pageBuilder: (_, state) => _glassPage(
          state,
          PromocaoDetalheScreen(promoId: state.pathParameters['id']!),
        ),
      ),
```

**IMPORTANTE — divisão entre Task 8 e 9 (pra cada commit compilar e funcionar sozinho):**
- Task 8 registra SÓ a rota `/promocoes`. A rota `/promocoes/:id` entra na Task 9 (a tela de detalhe nasce lá).
- Nesta Task 8, o `onTap` da lista usa TEMPORARIAMENTE a mesma lógica do carrossel (registrar click + executar url/tela/info) — copie do `_onTap` do carrossel. O `_onTap` do carrossel em si NÃO muda nesta task.
- Na Task 9, os DOIS onTaps (carrossel e lista) passam a navegar pro detalhe.

- [ ] **Step 4: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib
git commit -m "feat(app/promocoes): pagina /promocoes + Ver todas na home"
```

### Task 9: Landing de detalhe + botão "Tenho interesse"

**Files:**
- Create: `apps/cliente-mobile/lib/features/promocoes/promocao_detalhe_screen.dart`
- Modify: `apps/cliente-mobile/lib/router.dart` (rota `:id`)
- Modify: `apps/cliente-mobile/lib/features/home/widgets/promo_carousel.dart` (_onTap → detalhe)
- Modify: `apps/cliente-mobile/lib/features/promocoes/promocoes_screen.dart` (onTap → detalhe)

- [ ] **Step 1: Tela de detalhe**

`promocao_detalhe_screen.dart` — estrutura completa:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/api/dto.dart';
import '../../core/api/promocoes_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/contrato/contrato_atual_provider.dart';
import '../../core/ui/async_states.dart';
import '../../core/ui/hex_color.dart';
import '../home/promo_icon_map.dart';

/// Landing CTA da promoção: hero com o gradiente do card, descrição longa,
/// regras expansíveis e botão fixo de ação ("Tenho interesse" → lead, ou a
/// ação original quando a promo tem cta de url/tela — ex: indicacao).
class PromocaoDetalheScreen extends ConsumerStatefulWidget {
  const PromocaoDetalheScreen({super.key, required this.promoId});
  final String promoId;

  @override
  ConsumerState<PromocaoDetalheScreen> createState() =>
      _PromocaoDetalheScreenState();
}

enum _CtaState { idle, sending, done }

class _PromocaoDetalheScreenState
    extends ConsumerState<PromocaoDetalheScreen> {
  _CtaState _cta = _CtaState.idle;
  bool _viewTracked = false;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(promocaoDetalheProvider(widget.promoId));

    // Tracking de view do detalhe (1x por abertura, fire-and-forget).
    async.whenData((p) {
      if (!_viewTracked) {
        _viewTracked = true;
        ref
            .read(promocoesRepositoryProvider)
            .registrarEvento(p.id, 'detail_view');
      }
    });

    return Scaffold(
      body: AsyncBuilder<PromocaoDetalheDto>(
        value: async,
        loading: const Center(child: CircularProgressIndicator()),
        error: Center(
          child: Padding(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            child: ErrorCard(
              message: 'Não conseguimos abrir essa promoção agora.',
              onRetry: () =>
                  ref.invalidate(promocaoDetalheProvider(widget.promoId)),
            ),
          ),
        ),
        builder: (p) => _Conteudo(
          promo: p,
          cta: p.interesseRegistrado ? _CtaState.done : _cta,
          onCta: () => _executarCta(p),
        ),
      ),
    );
  }

  Future<void> _executarCta(PromocaoDetalheDto p) async {
    final action = p.ctaAction;
    // Promo com ação própria (indicacao, url externa, tela) → executa a
    // ação original em vez de gerar lead. Não quebra o que existe.
    if (action.startsWith('tela:')) {
      context.push(action.substring(5));
      return;
    }
    if (action.startsWith('url:')) {
      final uri = Uri.tryParse(action.substring(4));
      if (uri != null) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
      return;
    }
    // "info" → lead "Tenho interesse".
    if (_cta != _CtaState.idle) return;
    setState(() => _cta = _CtaState.sending);
    try {
      final contrato = ref.read(contratoAtualProvider);
      await ref
          .read(promocoesRepositoryProvider)
          .registrarInteresse(p.id, contratoId: contrato);
      if (!mounted) return;
      setState(() => _cta = _CtaState.done);
    } catch (_) {
      if (!mounted) return;
      setState(() => _cta = _CtaState.idle);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Não conseguimos registrar agora. Tenta de novo?'),
        ),
      );
    }
  }
}

class _Conteudo extends StatelessWidget {
  const _Conteudo({
    required this.promo,
    required this.cta,
    required this.onCta,
  });

  final PromocaoDetalheDto promo;
  final _CtaState cta;
  final VoidCallback onCta;

  @override
  Widget build(BuildContext context) {
    final from = hexColor(promo.gradientFrom) ?? BrandTokens.promoFallbackFrom;
    final to = hexColor(promo.gradientTo) ?? BrandTokens.promoFallbackTo;
    final imagemUrl = promo.imagemUrl;
    final imagemAbs = imagemUrl == null
        ? null
        : (imagemUrl.startsWith('http') ? imagemUrl : '$apiBaseUrl$imagemUrl');
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondary =
        isDark ? BrandTokens.textSecondaryDark : BrandTokens.textSecondary;

    return Stack(
      children: [
        CustomScrollView(
          slivers: [
            SliverAppBar(
              expandedHeight: 240,
              pinned: true,
              backgroundColor: from,
              foregroundColor: Colors.white,
              flexibleSpace: FlexibleSpaceBar(
                background: Hero(
                  tag: 'promo-${promo.id}',
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [from, to],
                      ),
                      image: imagemAbs == null
                          ? null
                          : DecorationImage(
                              image: NetworkImage(imagemAbs),
                              fit: BoxFit.cover,
                              opacity: 0.35,
                            ),
                    ),
                    child: Center(
                      child: Container(
                        width: 88,
                        height: 88,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.18),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          promoIconOf(promo.icon),
                          color: Colors.white,
                          size: 42,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            SliverPadding(
              padding: EdgeInsets.fromLTRB(
                BrandTokens.spaceLg,
                BrandTokens.spaceLg,
                BrandTokens.spaceLg,
                // espaço pro botão fixo não cobrir o fim do conteúdo
                120 + MediaQuery.paddingOf(context).bottom,
              ),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  Text(
                    promo.titulo,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                    ),
                  ),
                  if (promo.subtitulo.isNotEmpty) ...[
                    const SizedBox(height: BrandTokens.spaceSm),
                    Text(
                      promo.subtitulo,
                      style: TextStyle(
                        fontSize: 15,
                        color: secondary,
                        height: 1.4,
                      ),
                    ),
                  ],
                  if ((promo.descricaoLonga ?? '').isNotEmpty) ...[
                    const SizedBox(height: BrandTokens.spaceLg),
                    Text(
                      promo.descricaoLonga!,
                      style: const TextStyle(fontSize: 15, height: 1.55),
                    ),
                  ],
                  if ((promo.regulamento ?? '').isNotEmpty ||
                      promo.validoAte != null) ...[
                    const SizedBox(height: BrandTokens.spaceLg),
                    _RegrasExpansivel(
                      regulamento: promo.regulamento,
                      validoAte: promo.validoAte,
                    ),
                  ],
                ]),
              ),
            ),
          ],
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: _CtaBar(promo: promo, cta: cta, onCta: onCta),
        ),
      ],
    );
  }
}

class _RegrasExpansivel extends StatelessWidget {
  const _RegrasExpansivel({required this.regulamento, required this.validoAte});
  final String? regulamento;
  final DateTime? validoAte;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondary =
        isDark ? BrandTokens.textSecondaryDark : BrandTokens.textSecondary;
    return Container(
      decoration: BoxDecoration(
        color: BrandTokens.primary.withValues(alpha: isDark ? 0.08 : 0.05),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          title: const Text(
            'Regras da promoção',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
          childrenPadding: const EdgeInsets.fromLTRB(
            BrandTokens.spaceMd, 0, BrandTokens.spaceMd, BrandTokens.spaceMd,
          ),
          children: [
            if ((regulamento ?? '').isNotEmpty)
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  regulamento!,
                  style: TextStyle(fontSize: 13, height: 1.5, color: secondary),
                ),
              ),
            if (validoAte != null) ...[
              const SizedBox(height: BrandTokens.spaceSm),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Válida até ${DateFormat('dd/MM/yyyy').format(validoAte!.toLocal())}',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: secondary,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _CtaBar extends StatelessWidget {
  const _CtaBar({required this.promo, required this.cta, required this.onCta});
  final PromocaoDetalheDto promo;
  final _CtaState cta;
  final VoidCallback onCta;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? BrandTokens.surfaceDark : BrandTokens.surface;
    final temAcaoPropria =
        promo.ctaAction.startsWith('tela:') || promo.ctaAction.startsWith('url:');
    final label = temAcaoPropria
        ? promo.ctaLabel
        : switch (cta) {
            _CtaState.idle => 'Tenho interesse',
            _CtaState.sending => 'Enviando…',
            _CtaState.done => '✓ Recebemos! Logo entramos em contato',
          };
    final done = cta == _CtaState.done && !temAcaoPropria;

    return Container(
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        BrandTokens.spaceMd,
        BrandTokens.spaceLg,
        BrandTokens.spaceMd + MediaQuery.paddingOf(context).bottom,
      ),
      decoration: BoxDecoration(
        color: bg.withValues(alpha: 0.92),
        border: Border(
          top: BorderSide(
            color: isDark
                ? Colors.white.withValues(alpha: 0.06)
                : BrandTokens.divider,
          ),
        ),
      ),
      child: FilledButton(
        onPressed: done || cta == _CtaState.sending ? null : onCta,
        style: done
            ? FilledButton.styleFrom(
                disabledBackgroundColor:
                    BrandTokens.success.withValues(alpha: 0.15),
                disabledForegroundColor: BrandTokens.accentDark,
              )
            : null,
        child: Text(label),
      ),
    );
  }
}
```

⚠️ **`contratoAtualProvider`:** confira o tipo real em `lib/core/contrato/contrato_atual_provider.dart` antes de usar — pode ser `StateNotifierProvider` cujo estado é um objeto (não String). Extraia o id do contrato do jeito que outras telas fazem (grep `contratoAtualProvider` em faturas/conexão) e passe como `contratoId`. Se o estado for null (cliente de contrato único), mandar null é ok — o backend aceita.

- [ ] **Step 2: Rota `:id` + onTaps**

1. `router.dart`: adicionar a rota `/promocoes/:id` (DEPOIS da `/promocoes`) com `_glassPage` e import da tela (código na Task 8 Step 3).
2. `promo_carousel.dart` `_onTap`: trocar pra navegar (`context.push('/promocoes/${p.id}')` mantendo o `registrarEvento('click')`; remover branches url/tela/info e imports órfãos).
3. `promocoes_screen.dart`: `onTap: (p) => context.push('/promocoes/${p.id}')` (remover a lógica temporária da Task 8).

- [ ] **Step 3: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib
git commit -m "feat(app/promocoes): landing de detalhe com hero + botao Tenho interesse (lead)"
```

### Task 10: Verificação final da fase

- [ ] **Step 1:** `flutter analyze && flutter test` (app) → limpo / PASS.
- [ ] **Step 2:** `uvx ruff check apps/api/src apps/api/tests` + mypy nos arquivos tocados → limpo.
- [ ] **Step 3:** `cd apps/dashboard && pnpm build` → verde.
- [ ] **Step 4:** Smoke conceitual: ler o fluxo completo (admin cadastra com descrição → app lista → detalhe → interesse → lead na dashboard → status) e conferir que nomes de campos batem entre API/dashboard/app (descricao_longa, regulamento, interesse_registrado, ja_registrado, status_filtro).
- [ ] **Step 5:** Aguardar OK do Robert pra push (CI roda ruff/mypy/pytest/flutter analyze; migration aplica no deploy).
