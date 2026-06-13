# Comunicados / Disparo em Massa via WhatsApp Cloud API — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que um admin dispare mensagens WhatsApp em massa (comunicados/links/promoções) para a base de clientes, segmentando por cidade/status/plano (ou base inteira), via template aprovado da Meta Cloud API, e exporte o recorte em CSV/Excel.

**Architecture:** Abordagem C (híbrida). Modelo próprio de Campanha + Destinatário para tracking e UI; o envio reaproveita as primitivas já provadas (`adapter.send_template`, `record_sent`, `extract_wamid`) num sender dedicado de broadcast — **sem** refatorar o `send_one`/`notify_sender` ativo de produção. Uma função `resolver_segmento` única alimenta preview, export e lista de destinatários. Task Celery na fila `notifications`. Webhook Cloud existente estendido (aditivo, fail-open) para atualizar o status de entrega/leitura por `wamid`.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Celery (Redis), Pydantic, Next.js (App Router), React Query, shadcn/ui, openpyxl (export XLSX).

---

## ⚠️ Convenções deste repo (ler antes de começar)

- **Não rodar testes/alembic/docker localmente.** Código é escrito, commitado e testado na máquina de deploy/CI após o push. Os passos "rodar teste" abaixo são executados no CI/deploy — aqui a verificação é escrever o teste + passar `ruff`/`mypy` (gate de CI).
- **Eu (Claude) commito; o PUSH é sempre do Robert.** Cada task termina com `git commit`. Nunca rodar `git push`.
- **CI gotchas:** `ruff` e `mypy` são gate. Imports não usados quebram. No frontend, ícones `lucide-react` precisam existir no pacote. Type hints completos (mypy estrito).
- **`Base`** vem de `ondeline_api.db.base`. **Sem mixin de timestamp** — declarar `created_at`/`updated_at` inline.
- **Migrations:** `id` UUID PK **sem** server default (default `uuid4` é app-side no ORM); JSONB = `postgresql.JSONB`; FK = `sa.ForeignKey("tabela.id", ondelete="CASCADE")`.
- **`send_template` recebe `body_params: list[str]`** (lista ordenada, não dict). Guardamos `body_params` como lista JSONB.
- **Arquivo de produção tocado:** `api/webhook_cloud.py` (caminho Cloud novo, liberado editar — mas recebe tráfego real; a mudança é aditiva e fail-open). Sinalizado no Task 12.

---

## Estrutura de arquivos

**Backend (`apps/api/src/ondeline_api/`)**
- `db/models/business.py` — **modificar**: 3 classes novas (`Campanha`, `CampanhaDestinatario`, `BroadcastTemplate`) + 2 colunas em `Cliente`.
- `alembic/versions/0049_comunicados_broadcast.py` — **criar**: tabelas + colunas + seed de templates.
- `services/segmento.py` — **criar**: `resolver_segmento`, `contar_segmento`, `amostra_segmento`.
- `services/broadcast_sender.py` — **criar**: `enviar_destinatario`, `atualizar_status_por_wamid`.
- `repositories/campanha.py` — **criar**: `CampanhaRepo`.
- `workers/broadcast.py` — **criar**: `send_campanha_task` + `_send_campanha`.
- `workers/celery_app.py` — **modificar**: `include` + `task_routes`.
- `config.py` — **modificar**: 2 settings de ritmo de envio.
- `api/schemas/comunicado.py` — **criar**: schemas Pydantic.
- `api/v1/comunicados.py` — **criar**: router.
- `api/webhook_cloud.py` — **modificar**: atualizar destinatário por wamid (aditivo).
- `main.py` — **modificar**: registrar router.

**Frontend (`apps/dashboard/`)**
- `lib/api/types.ts` — **modificar**: tipos.
- `lib/api/queries.ts` — **modificar**: hooks.
- `app/(admin)/comunicados/page.tsx` — **criar**: lista.
- `app/(admin)/comunicados/nova/page.tsx` — **criar**: nova campanha.
- `app/(admin)/comunicados/[id]/page.tsx` — **criar**: detalhe.
- `components/comunicado-list.tsx`, `components/comunicado-form.tsx`, `components/comunicado-detail.tsx` — **criar**.
- `components/nav-sidebar.tsx` — **modificar**: entrada "Comunicados".

**Testes (`apps/api/tests/`)**
- `test_segmento.py`, `test_broadcast_task.py`, `test_comunicados_api.py` — **criar**.

---

## FASE 1 — Backend

### Task 1: Modelos ORM (Campanha, CampanhaDestinatario, BroadcastTemplate) + colunas opt-out

**Files:**
- Modify: `apps/api/src/ondeline_api/db/models/business.py`

- [ ] **Step 1: Adicionar as 3 classes no fim de `business.py`** (antes de qualquer bloco `# --- end ---` se houver; senão append). Os imports necessários (`JSONB`, `ForeignKey`, `Index`, `String`, `Integer`, `Text`, `Boolean`, `DateTime`, `func`, `PgUUID`, `Mapped`, `mapped_column`, `uuid4`, `datetime`, `Any`) **já existem** no topo do arquivo.

```python
class BroadcastTemplate(Base):
    """Registro local dos templates aprovados na Meta (espelho p/ o dashboard).

    O cadastro do template na Meta é manual (WhatsApp Manager). Esta tabela só
    descreve nome/idioma/variáveis pro form do dashboard renderizar os campos.
    """

    __tablename__ = "broadcast_templates"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="pt_BR")
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="MARKETING")
    # [{"indice": 1, "label": "Link do app", "tipo": "url"}, ...]
    variaveis: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    # 'none' | 'image'
    header_tipo: Mapped[str] = mapped_column(
        String(10), nullable=False, default="none", server_default="none"
    )
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Campanha(Base):
    """Disparo em massa de WhatsApp para um segmento de clientes."""

    __tablename__ = "campanhas"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    canal_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("canal.id", ondelete="RESTRICT"), nullable=False
    )
    template_name: Mapped[str] = mapped_column(String(64), nullable=False)
    template_language: Mapped[str] = mapped_column(String(10), nullable=False, default="pt_BR")
    # Lista ordenada de valores das variáveis, ex: ["https://apps.apple.com/..."]
    body_params: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    header_media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # {"cidade": "Manaus", "status": "Ativo", "plano": "100MB"} — chaves ausentes = sem filtro
    segmentacao: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # rascunho | enviando | concluida | cancelada | erro
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="rascunho", server_default="rascunho"
    )
    total_destinatarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    enviadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    falhas: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    agendada_para: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_campanhas_status", "status"),)


class CampanhaDestinatario(Base):
    """Uma linha por cliente de um disparo — fonte de verdade do progresso."""

    __tablename__ = "campanha_destinatarios"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    campanha_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False
    )
    cliente_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    whatsapp: Mapped[str] = mapped_column(String(64), nullable=False)
    # pendente | enviada | entregue | lida | falha
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendente", server_default="pendente"
    )
    wamid: Mapped[str | None] = mapped_column(String(80), nullable=True)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    enviada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_campanha_dest_campanha_status", "campanha_id", "status"),
        Index("ix_campanha_dest_wamid", "wamid"),
    )
```

- [ ] **Step 2: Adicionar as 2 colunas de opt-out de marketing na classe `Cliente`** (logo após `cobranca_optout_at`, antes de `asr_aviso_enviado_at`):

```python
    marketing_optout: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    marketing_optout_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 3: Verificar lint/type** (CI): `ruff check apps/api/src/ondeline_api/db/models/business.py` e `mypy`. Esperado: sem erros (todos os símbolos já importados).

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/db/models/business.py
git commit -m "feat(comunicados): modelos Campanha/Destinatario/BroadcastTemplate + opt-out marketing"
```

---

### Task 2: Migration 0049 (tabelas + colunas + seed de templates)

**Files:**
- Create: `apps/api/alembic/versions/0049_comunicados_broadcast.py`

- [ ] **Step 1: Criar a migration**

```python
"""Comunicados/disparo em massa: campanhas + destinatarios + templates + opt-out marketing.

Revision ID: 0049_comunicados_broadcast
Revises: 0048_promocoes_leads
Create Date: 2026-06-13
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0049_comunicados_broadcast"
down_revision: str | None = "0048_promocoes_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- opt-out de marketing em clientes ---
    op.add_column(
        "clientes",
        sa.Column("marketing_optout", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "clientes",
        sa.Column("marketing_optout_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- broadcast_templates ---
    op.create_table(
        "broadcast_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="pt_BR"),
        sa.Column("category", sa.String(20), nullable=False, server_default="MARKETING"),
        sa.Column("variaveis", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("header_tipo", sa.String(10), nullable=False, server_default="none"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- campanhas ---
    op.create_table(
        "campanhas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column(
            "canal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canal.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("template_name", sa.String(64), nullable=False),
        sa.Column("template_language", sa.String(10), nullable=False, server_default="pt_BR"),
        sa.Column("body_params", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("header_media_url", sa.Text(), nullable=True),
        sa.Column("segmentacao", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("total_destinatarios", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enviadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("falhas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agendada_para", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_campanhas_status", "campanhas", ["status"])

    # --- campanha_destinatarios ---
    op.create_table(
        "campanha_destinatarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "campanha_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campanhas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cliente_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("whatsapp", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("wamid", sa.String(80), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("enviada_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_campanha_dest_campanha_status",
        "campanha_destinatarios",
        ["campanha_id", "status"],
    )
    op.create_index("ix_campanha_dest_wamid", "campanha_destinatarios", ["wamid"])

    # --- seed dos templates iniciais (espelham o que será aprovado na Meta) ---
    bt = sa.table(
        "broadcast_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("language", sa.String),
        sa.column("category", sa.String),
        sa.column("variaveis", postgresql.JSONB),
        sa.column("header_tipo", sa.String),
        sa.column("ativo", sa.Boolean),
    )
    op.bulk_insert(
        bt,
        [
            {
                "id": uuid.uuid4(),
                "name": "comunicado_geral",
                "language": "pt_BR",
                "category": "MARKETING",
                "variaveis": [{"indice": 1, "label": "Mensagem", "tipo": "texto"}],
                "header_tipo": "none",
                "ativo": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "promocao",
                "language": "pt_BR",
                "category": "MARKETING",
                "variaveis": [
                    {"indice": 1, "label": "Descrição da promoção", "tipo": "texto"},
                    {"indice": 2, "label": "Link", "tipo": "url"},
                ],
                "header_tipo": "none",
                "ativo": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "lancamento_app",
                "language": "pt_BR",
                "category": "MARKETING",
                "variaveis": [{"indice": 1, "label": "Link de download do app", "tipo": "url"}],
                "header_tipo": "none",
                "ativo": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_campanha_dest_wamid", table_name="campanha_destinatarios")
    op.drop_index("ix_campanha_dest_campanha_status", table_name="campanha_destinatarios")
    op.drop_table("campanha_destinatarios")
    op.drop_index("ix_campanhas_status", table_name="campanhas")
    op.drop_table("campanhas")
    op.drop_table("broadcast_templates")
    op.drop_column("clientes", "marketing_optout_at")
    op.drop_column("clientes", "marketing_optout")
```

> **Importante:** os `name` semeados (`comunicado_geral`, `promocao`, `lancamento_app`) **precisam bater exatamente** com o nome dos templates aprovados no WhatsApp Manager. Ver Task 18 (pré-requisito operacional).

- [ ] **Step 2: Commit** (alembic roda no deploy)

```bash
git add apps/api/alembic/versions/0049_comunicados_broadcast.py
git commit -m "feat(comunicados): migration 0049 (campanhas, destinatarios, templates, opt-out)"
```

---

### Task 3: Resolver de segmento (TDD)

**Files:**
- Create: `apps/api/src/ondeline_api/services/segmento.py`
- Test: `apps/api/tests/test_segmento.py`

- [ ] **Step 1: Escrever o teste primeiro**

```python
# apps/api/tests/test_segmento.py
from __future__ import annotations

import pytest
from sqlalchemy import select

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.services.segmento import (
    amostra_segmento,
    contar_segmento,
    resolver_segmento,
)


async def _mk(session, *, nome, whatsapp, cidade=None, status=None, plano=None,
              deleted=False, optout=False):
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("000"),
        cpf_hash=hash_pii(whatsapp),  # hash único por teste
        nome_encrypted=encrypt_pii(nome),
        whatsapp=whatsapp,
        cidade=cidade,
        status=status,
        plano=plano,
        marketing_optout=optout,
    )
    if deleted:
        from datetime import UTC, datetime
        c.deleted_at = datetime.now(tz=UTC)
    session.add(c)
    await session.flush()
    return c


@pytest.mark.asyncio
async def test_resolver_filtra_cidade_status_plano(db_session):
    await _mk(db_session, nome="A", whatsapp="5592111", cidade="Manaus", status="Ativo", plano="100MB")
    await _mk(db_session, nome="B", whatsapp="5592222", cidade="Itacoatiara", status="Ativo", plano="100MB")
    await _mk(db_session, nome="C", whatsapp="5592333", cidade="Manaus", status="Cancelado", plano="100MB")

    total = await contar_segmento(db_session, {"cidade": "Manaus", "status": "Ativo"})
    assert total == 1


@pytest.mark.asyncio
async def test_resolver_exclui_deleted_optout_e_sem_whatsapp(db_session):
    await _mk(db_session, nome="ok", whatsapp="5592444", cidade="Manaus")
    await _mk(db_session, nome="del", whatsapp="5592555", cidade="Manaus", deleted=True)
    await _mk(db_session, nome="opt", whatsapp="5592666", cidade="Manaus", optout=True)
    await _mk(db_session, nome="vazio", whatsapp="", cidade="Manaus")

    total = await contar_segmento(db_session, {"cidade": "Manaus"})
    assert total == 1


@pytest.mark.asyncio
async def test_base_inteira_sem_filtro(db_session):
    await _mk(db_session, nome="A", whatsapp="5592777")
    await _mk(db_session, nome="B", whatsapp="5592888")
    total = await contar_segmento(db_session, {})
    assert total == 2


@pytest.mark.asyncio
async def test_amostra_decripta_nome(db_session):
    await _mk(db_session, nome="João Silva", whatsapp="5592999", cidade="Manaus")
    amostra = await amostra_segmento(db_session, {"cidade": "Manaus"}, limite=5)
    assert amostra[0]["nome"] == "João Silva"
    assert amostra[0]["whatsapp"] == "5592999"
```

- [ ] **Step 2: Rodar teste — deve FALHAR** (CI/deploy): `pytest apps/api/tests/test_segmento.py -v`. Esperado: `ModuleNotFoundError: ondeline_api.services.segmento`.

- [ ] **Step 3: Implementar o resolver**

```python
# apps/api/src/ondeline_api/services/segmento.py
"""Resolver de segmento de clientes — peça única p/ preview, export e disparo.

Aplica sempre os invariantes de elegibilidade (não-deletado, sem opt-out de
marketing, com WhatsApp) + filtros opcionais (cidade, status, plano).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente


def resolver_segmento(filtros: dict[str, Any]) -> Select[tuple[Cliente]]:
    """Monta o SELECT base de clientes elegíveis para o segmento."""
    stmt = select(Cliente).where(
        Cliente.deleted_at.is_(None),
        Cliente.marketing_optout.is_(False),
        Cliente.whatsapp != "",
    )
    cidade = (filtros.get("cidade") or "").strip()
    status = (filtros.get("status") or "").strip()
    plano = (filtros.get("plano") or "").strip()
    if cidade:
        stmt = stmt.where(Cliente.cidade == cidade)
    if status:
        stmt = stmt.where(Cliente.status == status)
    if plano:
        stmt = stmt.where(Cliente.plano == plano)
    return stmt


async def contar_segmento(session: AsyncSession, filtros: dict[str, Any]) -> int:
    base = resolver_segmento(filtros).subquery()
    total = (await session.execute(select(func.count()).select_from(base))).scalar_one()
    return int(total)


async def amostra_segmento(
    session: AsyncSession, filtros: dict[str, Any], *, limite: int = 10
) -> list[dict[str, Any]]:
    stmt = resolver_segmento(filtros).order_by(Cliente.created_at.desc()).limit(limite)
    rows = list((await session.execute(stmt)).scalars().all())
    out: list[dict[str, Any]] = []
    for c in rows:
        try:
            nome = decrypt_pii(c.nome_encrypted) if c.nome_encrypted else None
        except Exception:
            nome = None
        out.append(
            {"id": str(c.id), "nome": nome, "whatsapp": c.whatsapp, "cidade": c.cidade}
        )
    return out
```

- [ ] **Step 4: Rodar teste — deve PASSAR** (CI/deploy): `pytest apps/api/tests/test_segmento.py -v`. Esperado: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/segmento.py apps/api/tests/test_segmento.py
git commit -m "feat(comunicados): resolver_segmento (preview/export/disparo) + testes"
```

---

### Task 4: Settings de ritmo de envio

**Files:**
- Modify: `apps/api/src/ondeline_api/config.py`

- [ ] **Step 1: Adicionar 2 campos junto ao bloco `whatsapp_cloud_*`**

```python
    # Disparo em massa (comunicados). Ritmo p/ respeitar o tier da Meta.
    broadcast_batch_size: int = 50
    broadcast_pause_seconds: float = 1.0
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/config.py
git commit -m "feat(comunicados): settings de ritmo de disparo (batch + pausa)"
```

---

### Task 5: Repository de campanha

**Files:**
- Create: `apps/api/src/ondeline_api/repositories/campanha.py`

- [ ] **Step 1: Implementar `CampanhaRepo`**

```python
# apps/api/src/ondeline_api/repositories/campanha.py
"""CampanhaRepo — CRUD de campanhas + agregação de status dos destinatários."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Campanha, CampanhaDestinatario


class CampanhaRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Campanha]:
        stmt = select(Campanha).order_by(Campanha.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_id(self, campanha_id: UUID) -> Campanha | None:
        stmt = select(Campanha).where(Campanha.id == campanha_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def status_counts(self, campanha_id: UUID) -> dict[str, int]:
        """Conta destinatários por status (pendente/enviada/entregue/lida/falha)."""
        stmt = (
            select(CampanhaDestinatario.status, func.count())
            .where(CampanhaDestinatario.campanha_id == campanha_id)
            .group_by(CampanhaDestinatario.status)
        )
        rows = (await self._session.execute(stmt)).all()
        return {status: int(n) for status, n in rows}
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/campanha.py
git commit -m "feat(comunicados): CampanhaRepo"
```

---

### Task 6: Broadcast sender (envio de 1 destinatário + atualização por wamid)

**Files:**
- Create: `apps/api/src/ondeline_api/services/broadcast_sender.py`

> Reaproveita as primitivas provadas (`adapter.send_template`, `record_sent`, `extract_wamid`) **sem** mexer no `send_one`/`notify_sender` ativo de produção.

- [ ] **Step 1: Implementar o sender**

```python
# apps/api/src/ondeline_api/services/broadcast_sender.py
"""Envio de mensagens de campanha (broadcast) — uma por destinatário.

Usa as mesmas primitivas do notify_sender (send_template + record_sent), mas é
isolado do pipeline de notificações transacionais.
"""
from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp import WhatsAppAdapter, WhatsAppError
from ondeline_api.db.models.business import Campanha, CampanhaDestinatario
from ondeline_api.services.whatsapp_message_log import extract_wamid, record_sent

log = structlog.get_logger(__name__)


async def enviar_destinatario(
    session: AsyncSession,
    adapter: WhatsAppAdapter,
    campanha: Campanha,
    destinatario: CampanhaDestinatario,
) -> bool:
    """Envia o template da campanha para 1 destinatário. Atualiza o status dele.

    Returns True se enviado, False se falhou.
    """
    try:
        send_result = await adapter.send_template(
            destinatario.whatsapp,
            name=campanha.template_name,
            language=campanha.template_language,
            body_params=list(campanha.body_params or []),
            header_media_url=campanha.header_media_url,
        )
    except WhatsAppError as e:
        destinatario.status = "falha"
        destinatario.erro = str(e)[:500]
        log.warning("broadcast.send_failed", dest_id=str(destinatario.id), error=str(e))
        return False
    except NotImplementedError:
        destinatario.status = "falha"
        destinatario.erro = "canal não suporta template (provider != cloud)"
        return False

    wamid = extract_wamid(send_result)
    destinatario.status = "enviada"
    destinatario.wamid = wamid
    destinatario.enviada_em = datetime.now(tz=UTC)
    await record_sent(
        session,
        wamid=wamid,
        template_name=campanha.template_name,
        recipient_jid=destinatario.whatsapp,
    )
    return True


# status Meta -> status do destinatário
_STATUS_MAP = {"delivered": "entregue", "read": "lida", "failed": "falha"}


async def atualizar_status_por_wamid(
    session: AsyncSession, *, wamid: str, status_meta: str
) -> None:
    """Atualiza o destinatário (se existir) a partir de um status do webhook Cloud.

    Fail-open: erro de DB não propaga. Não "rebaixa" status (read não vira
    delivered) — só aplica delivered->entregue, read->lida, failed->falha.
    """
    novo = _STATUS_MAP.get(status_meta)
    if not novo or not wamid:
        return
    try:
        stmt = (
            update(CampanhaDestinatario)
            .where(CampanhaDestinatario.wamid == wamid)
            .values(status=novo)
        )
        await session.execute(stmt)
    except Exception as e:
        log.warning("broadcast.status_update_failed", wamid=wamid, error=str(e))
```

- [ ] **Step 2: Verificar lint/type** (CI): `ruff check` + `mypy` no arquivo. Esperado: limpo.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/services/broadcast_sender.py
git commit -m "feat(comunicados): broadcast_sender (envio por destinatario + update por wamid)"
```

---

### Task 7: Celery task de disparo (TDD da idempotência)

**Files:**
- Create: `apps/api/src/ondeline_api/workers/broadcast.py`
- Test: `apps/api/tests/test_broadcast_task.py`

- [ ] **Step 1: Escrever o teste primeiro** (foco: materializa destinatários, conta enviadas/falhas, idempotência ao re-rodar)

```python
# apps/api/tests/test_broadcast_task.py
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Campanha,
    CampanhaDestinatario,
    Canal,
    Cliente,
)
from ondeline_api.workers.broadcast import _send_campanha


class _FakeAdapter:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_template(self, jid, *, name, language="pt_BR",
                            body_params=None, header_media_url=None, **_):
        self.sent.append(jid)
        return {"messages": [{"id": f"wamid.{jid}"}]}

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_send_campanha_materializa_e_envia(db_session, monkeypatch):
    canal = Canal(slug="com", nome="Comercial", provider="cloud",
                  cloud_phone_id="123", cloud_waba_id="456")
    db_session.add(canal)
    for i in range(3):
        db_session.add(Cliente(
            cpf_cnpj_encrypted=encrypt_pii("0"), cpf_hash=hash_pii(f"c{i}"),
            nome_encrypted=encrypt_pii(f"Cli {i}"), whatsapp=f"55920000{i}",
            cidade="Manaus", status="Ativo",
        ))
    await db_session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="comunicado_geral",
                    body_params=["oi"], segmentacao={"cidade": "Manaus"}, status="rascunho")
    db_session.add(camp)
    await db_session.flush()

    fake = _FakeAdapter()
    monkeypatch.setattr("ondeline_api.workers.broadcast.build_for_canal", lambda c, s: fake)

    result = await _send_campanha(db_session, camp.id)

    assert result["enviadas"] == 3
    assert result["falhas"] == 0
    assert len(fake.sent) == 3
    await db_session.refresh(camp)
    assert camp.status == "concluida"
    assert camp.total_destinatarios == 3
    n_dest = (await db_session.execute(
        select(func.count()).select_from(CampanhaDestinatario)
        .where(CampanhaDestinatario.campanha_id == camp.id)
    )).scalar_one()
    assert n_dest == 3


@pytest.mark.asyncio
async def test_send_campanha_idempotente(db_session, monkeypatch):
    canal = Canal(slug="c2", nome="C2", provider="cloud", cloud_phone_id="1", cloud_waba_id="2")
    db_session.add(canal)
    db_session.add(Cliente(
        cpf_cnpj_encrypted=encrypt_pii("0"), cpf_hash=hash_pii("u1"),
        nome_encrypted=encrypt_pii("U"), whatsapp="5592123", cidade="Manaus",
    ))
    await db_session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="comunicado_geral",
                    body_params=["oi"], segmentacao={"cidade": "Manaus"}, status="rascunho")
    db_session.add(camp)
    await db_session.flush()

    fake = _FakeAdapter()
    monkeypatch.setattr("ondeline_api.workers.broadcast.build_for_canal", lambda c, s: fake)

    await _send_campanha(db_session, camp.id)
    await _send_campanha(db_session, camp.id)  # re-rodar não redispara

    assert len(fake.sent) == 1
```

- [ ] **Step 2: Rodar teste — deve FALHAR** (CI/deploy): `pytest apps/api/tests/test_broadcast_task.py -v`. Esperado: `ImportError`.

- [ ] **Step 3: Implementar a task** (`_send_campanha` recebe a session para ser testável; o wrapper Celery abre a session)

```python
# apps/api/src/ondeline_api/workers/broadcast.py
"""Celery task de disparo em massa (comunicados).

Materializa os destinatários do segmento (idempotente), envia o template em
lotes respeitando o ritmo configurado, e atualiza contadores/status.
"""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select

from ondeline_api.adapters.whatsapp import build_for_canal
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import (
    Campanha,
    CampanhaDestinatario,
    Canal,
)
from ondeline_api.services.broadcast_sender import enviar_destinatario
from ondeline_api.services.segmento import resolver_segmento
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _materializar_destinatarios(session: Any, campanha: Campanha) -> int:
    """Cria as linhas de destinatário se ainda não existirem. Idempotente."""
    existing = (
        await session.execute(
            select(CampanhaDestinatario.id)
            .where(CampanhaDestinatario.campanha_id == campanha.id)
            .limit(1)
        )
    ).first()
    if existing is not None:
        return campanha.total_destinatarios

    clientes = list(
        (await session.execute(resolver_segmento(campanha.segmentacao))).scalars().all()
    )
    for c in clientes:
        session.add(
            CampanhaDestinatario(
                campanha_id=campanha.id,
                cliente_id=c.id,
                whatsapp=c.whatsapp,
                status="pendente",
            )
        )
    campanha.total_destinatarios = len(clientes)
    await session.flush()
    return len(clientes)


async def _send_campanha(session: Any, campanha_id: UUID) -> dict[str, int]:
    s = get_settings()
    campanha = (
        await session.execute(select(Campanha).where(Campanha.id == campanha_id))
    ).scalar_one_or_none()
    if campanha is None:
        return {"enviadas": 0, "falhas": 0}
    if campanha.status in {"concluida", "cancelada"}:
        return {"enviadas": campanha.enviadas, "falhas": campanha.falhas}

    canal = (
        await session.execute(select(Canal).where(Canal.id == campanha.canal_id))
    ).scalar_one_or_none()
    if canal is None or canal.provider != "cloud":
        campanha.status = "erro"
        await session.commit()
        return {"enviadas": 0, "falhas": 0}

    from datetime import UTC, datetime

    campanha.status = "enviando"
    if campanha.started_at is None:
        campanha.started_at = datetime.now(tz=UTC)
    await _materializar_destinatarios(session, campanha)
    await session.commit()

    adapter = build_for_canal(canal, s)
    enviadas = campanha.enviadas
    falhas = campanha.falhas
    try:
        while True:
            pendentes = list(
                (
                    await session.execute(
                        select(CampanhaDestinatario)
                        .where(
                            CampanhaDestinatario.campanha_id == campanha.id,
                            CampanhaDestinatario.status == "pendente",
                        )
                        .limit(s.broadcast_batch_size)
                    )
                )
                .scalars()
                .all()
            )
            if not pendentes:
                break
            for dest in pendentes:
                ok = await enviar_destinatario(session, adapter, campanha, dest)
                if ok:
                    enviadas += 1
                else:
                    falhas += 1
            campanha.enviadas = enviadas
            campanha.falhas = falhas
            await session.commit()
            await asyncio.sleep(s.broadcast_pause_seconds)
    finally:
        try:
            await adapter.aclose()
        except Exception as e:
            log.warning("broadcast.adapter_close_failed", error=str(e))

    campanha.status = "concluida"
    campanha.finished_at = datetime.now(tz=UTC)
    await session.commit()
    log.info("broadcast.done", campanha_id=str(campanha.id), enviadas=enviadas, falhas=falhas)
    return {"enviadas": enviadas, "falhas": falhas}


@celery_app.task(name="ondeline_api.workers.broadcast.send_campanha_task", bind=True)
def send_campanha_task(self: Any, campanha_id: str) -> dict[str, int]:
    async def _run() -> dict[str, int]:
        async with task_session() as session:
            return await _send_campanha(session, UUID(campanha_id))

    try:
        result: dict[str, int] = run_task(_run)
        log.info("broadcast.task.completed", campanha_id=campanha_id, **result)
        return result
    except Exception as e:
        log.error("broadcast.task.failed", campanha_id=campanha_id, error=str(e), exc_info=True)
        raise
```

> **Nota de teste:** `_send_campanha` recebe `session` (injetável no teste). O wrapper Celery `send_campanha_task` abre a própria session via `task_session()`. No teste, `build_for_canal` é monkeypatchado para um fake adapter.

- [ ] **Step 4: Rodar teste — deve PASSAR** (CI/deploy): `pytest apps/api/tests/test_broadcast_task.py -v`. Esperado: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/workers/broadcast.py apps/api/tests/test_broadcast_task.py
git commit -m "feat(comunicados): celery task send_campanha_task (idempotente, em lotes) + testes"
```

---

### Task 8: Registrar a task no Celery

**Files:**
- Modify: `apps/api/src/ondeline_api/workers/celery_app.py`

- [ ] **Step 1: Adicionar ao `include=[...]`** (após `"ondeline_api.workers.cobranca_jobs",`):

```python
            "ondeline_api.workers.broadcast",
```

- [ ] **Step 2: Adicionar ao `task_routes`** (após a linha do `notify_sender.flush_pending`):

```python
            "ondeline_api.workers.broadcast.send_campanha_task": {"queue": "notifications"},
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/workers/celery_app.py
git commit -m "feat(comunicados): registra send_campanha_task no Celery (fila notifications)"
```

> **Gotcha conhecido:** task nova que não entra no `include` não é descoberta pelo worker. Conferir que a linha do Step 1 está presente.

---

### Task 9: Schemas Pydantic

**Files:**
- Create: `apps/api/src/ondeline_api/api/schemas/comunicado.py`

- [ ] **Step 1: Implementar os schemas**

```python
# apps/api/src/ondeline_api/api/schemas/comunicado.py
"""Schemas da API de comunicados/disparo em massa."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SegmentoFiltros(BaseModel):
    cidade: str | None = None
    status: str | None = None
    plano: str | None = None


class PreviewOut(BaseModel):
    total: int
    amostra: list[dict[str, Any]]


class TemplateVar(BaseModel):
    indice: int
    label: str
    tipo: str


class BroadcastTemplateOut(BaseModel):
    id: UUID
    name: str
    language: str
    category: str
    variaveis: list[TemplateVar]
    header_tipo: str


class CampanhaCreate(BaseModel):
    titulo: str
    canal_id: UUID
    template_name: str
    template_language: str = "pt_BR"
    body_params: list[str] = []
    header_media_url: str | None = None
    segmentacao: SegmentoFiltros = SegmentoFiltros()


class CampanhaListItem(BaseModel):
    id: UUID
    titulo: str
    template_name: str
    status: str
    total_destinatarios: int
    enviadas: int
    falhas: int
    created_at: datetime


class CampanhaDetail(CampanhaListItem):
    canal_id: UUID
    template_language: str
    body_params: list[str]
    header_media_url: str | None
    segmentacao: SegmentoFiltros
    started_at: datetime | None
    finished_at: datetime | None
    # contagem viva por status dos destinatários
    status_counts: dict[str, int]


class TestSendIn(BaseModel):
    whatsapp: str
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/comunicado.py
git commit -m "feat(comunicados): schemas Pydantic"
```

---

### Task 10: Router da API (TDD do fluxo principal)

**Files:**
- Create: `apps/api/src/ondeline_api/api/v1/comunicados.py`
- Test: `apps/api/tests/test_comunicados_api.py`

- [ ] **Step 1: Escrever o teste primeiro** (criar → preview → disparar enfileira task)

```python
# apps/api/tests/test_comunicados_api.py
from __future__ import annotations

import pytest

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Canal, Cliente


@pytest.mark.asyncio
async def test_criar_preview_e_disparar(admin_client, db_session, monkeypatch):
    canal = Canal(slug="com", nome="Comercial", provider="cloud",
                  cloud_phone_id="1", cloud_waba_id="2")
    db_session.add(canal)
    db_session.add(Cliente(
        cpf_cnpj_encrypted=encrypt_pii("0"), cpf_hash=hash_pii("x1"),
        nome_encrypted=encrypt_pii("João"), whatsapp="5592111", cidade="Manaus",
    ))
    await db_session.commit()

    # templates seedados existem
    r = await admin_client.get("/api/v1/admin/comunicados/templates")
    assert r.status_code == 200
    assert any(t["name"] == "comunicado_geral" for t in r.json())

    # criar campanha
    r = await admin_client.post("/api/v1/admin/comunicados", json={
        "titulo": "Lançamento", "canal_id": str(canal.id),
        "template_name": "lancamento_app", "body_params": ["https://app"],
        "segmentacao": {"cidade": "Manaus"},
    })
    assert r.status_code == 201
    camp_id = r.json()["id"]

    # preview
    r = await admin_client.post("/api/v1/admin/comunicados/preview",
                                json={"cidade": "Manaus"})
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # disparar — mocka o enfileiramento
    calls = {}
    monkeypatch.setattr(
        "ondeline_api.api.v1.comunicados.send_campanha_task.delay",
        lambda cid: calls.setdefault("id", cid),
    )
    r = await admin_client.post(f"/api/v1/admin/comunicados/{camp_id}/send")
    assert r.status_code == 200
    assert calls["id"] == camp_id


@pytest.mark.asyncio
async def test_rejeita_canal_nao_cloud(admin_client, db_session):
    canal = Canal(slug="ev", nome="Evo", provider="evolution", evolution_instance="i1")
    db_session.add(canal)
    await db_session.commit()
    r = await admin_client.post("/api/v1/admin/comunicados", json={
        "titulo": "x", "canal_id": str(canal.id),
        "template_name": "comunicado_geral", "body_params": ["oi"],
        "segmentacao": {},
    })
    assert r.status_code == 400
```

> **Nota:** o teste usa fixtures `admin_client` (HTTP client autenticado como ADMIN) e `db_session`. Se os nomes das fixtures no repo forem outros, adaptar para os existentes em `apps/api/tests/conftest.py` (procurar a fixture de client admin já usada em `test_*_api.py`).

- [ ] **Step 2: Rodar teste — deve FALHAR** (CI/deploy). Esperado: 404 (rota inexistente).

- [ ] **Step 3: Implementar o router**

```python
# apps/api/src/ondeline_api/api/v1/comunicados.py
"""POST/GET /api/v1/admin/comunicados — campanhas de disparo em massa + export."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp import WhatsAppError, build_for_canal
from ondeline_api.api.schemas.comunicado import (
    BroadcastTemplateOut,
    CampanhaCreate,
    CampanhaDetail,
    CampanhaListItem,
    PreviewOut,
    SegmentoFiltros,
    TestSendIn,
)
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    BroadcastTemplate,
    Campanha,
    Canal,
    Cliente,
)
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.campanha import CampanhaRepo
from ondeline_api.services.segmento import amostra_segmento, contar_segmento, resolver_segmento
from ondeline_api.workers.broadcast import send_campanha_task

router = APIRouter(prefix="/api/v1/admin/comunicados", tags=["comunicados"])
_admin_dep = Depends(require_role(Role.ADMIN))


def _to_list_item(c: Campanha) -> CampanhaListItem:
    return CampanhaListItem(
        id=c.id, titulo=c.titulo, template_name=c.template_name, status=c.status,
        total_destinatarios=c.total_destinatarios, enviadas=c.enviadas,
        falhas=c.falhas, created_at=c.created_at,
    )


@router.get("/templates", dependencies=[_admin_dep])
async def list_templates(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[BroadcastTemplateOut]:
    stmt = select(BroadcastTemplate).where(BroadcastTemplate.ativo.is_(True))
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        BroadcastTemplateOut(
            id=t.id, name=t.name, language=t.language, category=t.category,
            variaveis=t.variaveis, header_tipo=t.header_tipo,
        )
        for t in rows
    ]


@router.get("", dependencies=[_admin_dep])
async def list_campanhas(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CampanhaListItem]:
    repo = CampanhaRepo(session)
    return [_to_list_item(c) for c in await repo.list_all()]


@router.post("", status_code=201, dependencies=[_admin_dep])
async def create_campanha(
    body: CampanhaCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> CampanhaListItem:
    canal = (
        await session.execute(select(Canal).where(Canal.id == body.canal_id))
    ).scalar_one_or_none()
    if canal is None:
        raise HTTPException(status_code=404, detail="canal não encontrado")
    if canal.provider != "cloud":
        raise HTTPException(
            status_code=400, detail="disparo em massa exige canal Cloud (Meta)"
        )
    camp = Campanha(
        titulo=body.titulo, canal_id=body.canal_id, template_name=body.template_name,
        template_language=body.template_language, body_params=body.body_params,
        header_media_url=body.header_media_url,
        segmentacao=body.segmentacao.model_dump(exclude_none=True),
        status="rascunho", created_by=user.id,
    )
    session.add(camp)
    await session.commit()
    await session.refresh(camp)
    return _to_list_item(camp)


@router.post("/preview", dependencies=[_admin_dep])
async def preview(
    filtros: SegmentoFiltros,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PreviewOut:
    f = filtros.model_dump(exclude_none=True)
    total = await contar_segmento(session, f)
    amostra = await amostra_segmento(session, f, limite=10)
    return PreviewOut(total=total, amostra=amostra)


@router.get("/{campanha_id}", dependencies=[_admin_dep])
async def get_campanha(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CampanhaDetail:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    counts = await repo.status_counts(campanha_id)
    return CampanhaDetail(
        id=c.id, titulo=c.titulo, template_name=c.template_name, status=c.status,
        total_destinatarios=c.total_destinatarios, enviadas=c.enviadas, falhas=c.falhas,
        created_at=c.created_at, canal_id=c.canal_id, template_language=c.template_language,
        body_params=list(c.body_params or []), header_media_url=c.header_media_url,
        segmentacao=SegmentoFiltros(**(c.segmentacao or {})),
        started_at=c.started_at, finished_at=c.finished_at, status_counts=counts,
    )


@router.post("/{campanha_id}/send", dependencies=[_admin_dep])
async def send_campanha(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if c.status not in {"rascunho", "erro"}:
        raise HTTPException(status_code=409, detail=f"campanha já está '{c.status}'")
    send_campanha_task.delay(str(campanha_id))
    return {"status": "enfileirada"}


@router.post("/{campanha_id}/cancel", dependencies=[_admin_dep])
async def cancel_campanha(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if c.status == "concluida":
        raise HTTPException(status_code=409, detail="campanha já concluída")
    c.status = "cancelada"
    await session.commit()
    return {"status": "cancelada"}


@router.post("/{campanha_id}/test", dependencies=[_admin_dep])
async def test_send(
    campanha_id: UUID,
    body: TestSendIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    canal = (
        await session.execute(select(Canal).where(Canal.id == c.canal_id))
    ).scalar_one_or_none()
    if canal is None or canal.provider != "cloud":
        raise HTTPException(status_code=400, detail="canal inválido")
    adapter = build_for_canal(canal, get_settings())
    try:
        await adapter.send_template(
            body.whatsapp, name=c.template_name, language=c.template_language,
            body_params=list(c.body_params or []), header_media_url=c.header_media_url,
        )
    except WhatsAppError as e:
        raise HTTPException(status_code=502, detail=f"falha no envio: {e}") from e
    finally:
        await adapter.aclose()
    return {"status": "enviado"}


@router.get("/export/clientes", dependencies=[_admin_dep])
async def export_clientes(
    session: Annotated[AsyncSession, Depends(get_db)],
    cidade: Annotated[str | None, Query()] = None,
    status_f: Annotated[str | None, Query(alias="status")] = None,
    plano: Annotated[str | None, Query()] = None,
    fmt: Annotated[str, Query(alias="format")] = "csv",
) -> StreamingResponse:
    filtros = {"cidade": cidade, "status": status_f, "plano": plano}
    stmt = resolver_segmento(filtros).order_by(Cliente.created_at.desc())
    clientes = list((await session.execute(stmt)).scalars().all())

    colunas = ["nome", "cpf_cnpj", "whatsapp", "cidade", "plano", "status", "sgp_id"]

    def _row(c: Cliente) -> dict[str, str]:
        try:
            nome = decrypt_pii(c.nome_encrypted) if c.nome_encrypted else ""
        except Exception:
            nome = ""
        try:
            cpf = decrypt_pii(c.cpf_cnpj_encrypted) if c.cpf_cnpj_encrypted else ""
        except Exception:
            cpf = ""
        return {
            "nome": nome, "cpf_cnpj": cpf, "whatsapp": c.whatsapp,
            "cidade": c.cidade or "", "plano": c.plano or "",
            "status": c.status or "", "sgp_id": c.sgp_id or "",
        }

    stamp = datetime.now(tz=UTC).strftime("%Y%m%d")
    if fmt == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "clientes"
        ws.append(colunas)
        for c in clientes:
            r = _row(c)
            ws.append([r[k] for k in colunas])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="clientes-{stamp}.xlsx"'},
        )

    # CSV com BOM (Excel-friendly)
    sbuf = io.StringIO()
    sbuf.write("﻿")
    writer = csv.DictWriter(sbuf, fieldnames=colunas)
    writer.writeheader()
    for c in clientes:
        writer.writerow(_row(c))
    data = sbuf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="clientes-{stamp}.csv"'},
    )
```

> **Nota de rota:** o endpoint de export usa o caminho `/export/clientes` (não `/{campanha_id}/...`) para não colidir com `/{campanha_id}`. O alias `format`→`fmt` e `status`→`status_f` evita sombrear nomes reservados.

- [ ] **Step 4: Rodar teste — deve PASSAR** (CI/deploy): `pytest apps/api/tests/test_comunicados_api.py -v`. Esperado: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/comunicados.py apps/api/tests/test_comunicados_api.py
git commit -m "feat(comunicados): router /api/v1/admin/comunicados (CRUD, preview, send, test, export)"
```

---

### Task 11: Registrar o router no app + dependência openpyxl

**Files:**
- Modify: `apps/api/src/ondeline_api/main.py`
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Importar e registrar o router em `main.py`** — seguir o padrão dos outros `include_router`. Localizar o bloco de imports `from ondeline_api.api.v1 import (...)` (ou imports individuais) e adicionar `comunicados`; depois adicionar:

```python
    app.include_router(comunicados.router)
```

(usar exatamente o mesmo estilo de import/registro já usado para `clientes` e `canais` no arquivo).

- [ ] **Step 2: Adicionar `openpyxl` às dependências em `pyproject.toml`** (na lista `dependencies`):

```toml
    "openpyxl>=3.1",
```

> O `uv lock` / instalação acontece na máquina de deploy. Se preferir não adicionar dependência, remover o ramo `xlsx` do export no Task 10 e deixar só CSV (que já abre no Excel via BOM).

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/main.py apps/api/pyproject.toml
git commit -m "feat(comunicados): registra router + dependencia openpyxl (export xlsx)"
```

---

### Task 12: Webhook Cloud atualiza status do destinatário por wamid

**Files:**
- Modify: `apps/api/src/ondeline_api/api/webhook_cloud.py`

> ⚠️ **Toca caminho que recebe tráfego real da Meta.** Mudança é **aditiva e fail-open**: só acrescenta um update no destinatário da campanha após o `record_status_update` existente; nenhum comportamento atual é alterado.

- [ ] **Step 1: Adicionar import** no topo do `webhook_cloud.py` (junto ao import de `record_status_update`):

```python
from ondeline_api.services.broadcast_sender import atualizar_status_por_wamid
```

- [ ] **Step 2: Dentro do loop `for st in statuses:`, logo após a chamada `await record_status_update(...)`**, acrescentar:

```python
            # Espelha o status na campanha (se este wamid for de um disparo).
            await atualizar_status_por_wamid(
                session, wamid=st["id"], status_meta=st["status"]
            )
```

- [ ] **Step 3: Verificar lint/type** (CI). Esperado: limpo.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/api/webhook_cloud.py
git commit -m "feat(comunicados): webhook Cloud espelha delivered/read/failed no destinatario"
```

---

## FASE 2 — Frontend (Dashboard)

### Task 13: Tipos + hooks de API

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: Adicionar tipos em `types.ts`**

```typescript
export interface BroadcastTemplateVar {
  indice: number
  label: string
  tipo: string
}
export interface BroadcastTemplate {
  id: string
  name: string
  language: string
  category: string
  variaveis: BroadcastTemplateVar[]
  header_tipo: string
}
export interface SegmentoFiltros {
  cidade?: string | null
  status?: string | null
  plano?: string | null
}
export interface PreviewResult {
  total: number
  amostra: Array<{ id: string; nome: string | null; whatsapp: string; cidade: string | null }>
}
export interface CampanhaListItem {
  id: string
  titulo: string
  template_name: string
  status: string
  total_destinatarios: number
  enviadas: number
  falhas: number
  created_at: string
}
export interface CampanhaDetail extends CampanhaListItem {
  canal_id: string
  template_language: string
  body_params: string[]
  header_media_url: string | null
  segmentacao: SegmentoFiltros
  started_at: string | null
  finished_at: string | null
  status_counts: Record<string, number>
}
export interface CampanhaCreate {
  titulo: string
  canal_id: string
  template_name: string
  template_language?: string
  body_params: string[]
  header_media_url?: string | null
  segmentacao: SegmentoFiltros
}
```

- [ ] **Step 2: Adicionar hooks em `queries.ts`** (usar os tipos via `import type` ou `import('./types').X`, conforme o arquivo já faz):

```typescript
export function useBroadcastTemplates() {
  return useQuery<import('./types').BroadcastTemplate[]>({
    queryKey: ['broadcast-templates'],
    queryFn: () => apiFetch('/api/v1/admin/comunicados/templates'),
    staleTime: 300_000,
  })
}

export function useCampanhas() {
  return useQuery<import('./types').CampanhaListItem[]>({
    queryKey: ['campanhas'],
    queryFn: () => apiFetch('/api/v1/admin/comunicados'),
  })
}

export function useCampanha(id: string) {
  return useQuery<import('./types').CampanhaDetail>({
    queryKey: ['campanha', id],
    queryFn: () => apiFetch(`/api/v1/admin/comunicados/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data?.status === 'enviando' ? 3000 : false,
  })
}

export function useCreateCampanha() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('./types').CampanhaCreate) =>
      apiFetch<import('./types').CampanhaListItem>('/api/v1/admin/comunicados', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campanhas'] }),
  })
}

export function usePreviewSegmento() {
  return useMutation({
    mutationFn: (filtros: import('./types').SegmentoFiltros) =>
      apiFetch<import('./types').PreviewResult>('/api/v1/admin/comunicados/preview', {
        method: 'POST',
        body: JSON.stringify(filtros),
      }),
  })
}

export function useSendCampanha() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ status: string }>(`/api/v1/admin/comunicados/${id}/send`, {
        method: 'POST',
      }),
    onSuccess: (_d, id) => {
      qc.invalidateQueries({ queryKey: ['campanhas'] })
      qc.invalidateQueries({ queryKey: ['campanha', id] })
    },
  })
}

export function useTestCampanha(id: string) {
  return useMutation({
    mutationFn: (whatsapp: string) =>
      apiFetch<{ status: string }>(`/api/v1/admin/comunicados/${id}/test`, {
        method: 'POST',
        body: JSON.stringify({ whatsapp }),
      }),
  })
}

export function exportClientesUrl(f: import('./types').SegmentoFiltros, fmt: 'csv' | 'xlsx') {
  const p = new URLSearchParams()
  if (f.cidade) p.set('cidade', f.cidade)
  if (f.status) p.set('status', f.status)
  if (f.plano) p.set('plano', f.plano)
  p.set('format', fmt)
  return `/api/v1/admin/comunicados/export/clientes?${p.toString()}`
}
```

> **Atenção export:** `apiFetch` retorna JSON; para download de arquivo, o componente fará `fetch` direto com o header Authorization (ver Task 15) usando `exportClientesUrl`, porque o browser não pode anexar o Bearer num `<a href>` simples.

- [ ] **Step 3: Verificar build/types** (CI): `npm run lint` / `tsc`. Esperado: limpo.

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(comunicados): tipos + hooks React Query do dashboard"
```

---

### Task 14: Página de lista + componente de lista

**Files:**
- Create: `apps/dashboard/app/(admin)/comunicados/page.tsx`
- Create: `apps/dashboard/components/comunicado-list.tsx`

- [ ] **Step 1: Criar a página**

```tsx
// apps/dashboard/app/(admin)/comunicados/page.tsx
import { ComunicadoList } from '@/components/comunicado-list'

export default function ComunicadosPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Comunicados</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Disparo em massa de WhatsApp para a base, segmentado por cidade, status ou plano.
          </p>
        </div>
      </div>
      <ComunicadoList />
    </div>
  )
}
```

- [ ] **Step 2: Criar o componente de lista**

```tsx
// apps/dashboard/components/comunicado-list.tsx
'use client'
import Link from 'next/link'
import { Megaphone, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { useCampanhas } from '@/lib/api/queries'

const STATUS_VARIANT: Record<string, string> = {
  rascunho: 'outline',
  enviando: 'default',
  concluida: 'secondary',
  cancelada: 'outline',
  erro: 'destructive',
}

export function ComunicadoList() {
  const { data, isLoading, error } = useCampanhas()

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Link
          href="/comunicados/nova"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> Nova campanha
        </Link>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon={Megaphone}
          title="Nenhuma campanha ainda"
          description="Crie um comunicado para disparar em massa para os clientes."
        />
      )}

      {data && data.length > 0 && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Título</th>
                <th className="px-4 py-2.5 font-semibold">Template</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Enviadas</th>
                <th className="px-4 py-2.5 font-semibold">Falhas</th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 transition-colors hover:bg-accent/40">
                  <td className="px-4 py-3">
                    <Link href={`/comunicados/${c.id}`} className="font-medium hover:underline">
                      {c.titulo}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{c.template_name}</td>
                  <td className="px-4 py-3">
                    <Badge variant={(STATUS_VARIANT[c.status] ?? 'outline') as never}>{c.status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.enviadas}/{c.total_destinatarios}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{c.falhas}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/app/\(admin\)/comunicados/page.tsx apps/dashboard/components/comunicado-list.tsx
git commit -m "feat(comunicados): pagina + lista de campanhas no dashboard"
```

---

### Task 15: Formulário de nova campanha (template + variáveis + filtros + preview + export + disparo)

**Files:**
- Create: `apps/dashboard/app/(admin)/comunicados/nova/page.tsx`
- Create: `apps/dashboard/components/comunicado-form.tsx`

- [ ] **Step 1: Criar a página**

```tsx
// apps/dashboard/app/(admin)/comunicados/nova/page.tsx
import { ComunicadoForm } from '@/components/comunicado-form'

export default function NovaCampanhaPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Nova campanha</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Escolha o template, preencha as variáveis e segmente quem vai receber.
        </p>
      </div>
      <ComunicadoForm />
    </div>
  )
}
```

- [ ] **Step 2: Criar o formulário** (usa `useCanais` já existente para listar canais; filtra provider cloud no cliente)

```tsx
// apps/dashboard/components/comunicado-form.tsx
'use client'
import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Download, Send } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { getAccessToken } from '@/lib/api/token'
import {
  exportClientesUrl,
  useBroadcastTemplates,
  useCanais,
  useCreateCampanha,
  usePreviewSegmento,
  useSendCampanha,
} from '@/lib/api/queries'
import type { SegmentoFiltros } from '@/lib/api/types'

export function ComunicadoForm() {
  const router = useRouter()
  const { data: templates } = useBroadcastTemplates()
  const { data: canais } = useCanais()
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
  const [filtros, setFiltros] = useState<SegmentoFiltros>({})

  const template = templates?.find((t) => t.name === templateName)

  function runPreview() {
    preview.mutate(filtros)
  }

  async function handleExport(fmt: 'csv' | 'xlsx') {
    const url = exportClientesUrl(filtros, fmt)
    const res = await fetch(url, {
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

  async function handleDisparar() {
    if (!template) return
    const body_params = (template.variaveis ?? [])
      .slice()
      .sort((a, b) => a.indice - b.indice)
      .map((v) => vars[v.indice] ?? '')
    try {
      const camp = await createCampanha.mutateAsync({
        titulo,
        canal_id: canalId,
        template_name: templateName,
        body_params,
        segmentacao: filtros,
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

  const podeDisparar = titulo && canalId && templateName

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
        {cloudCanais.length === 0 && (
          <p className="text-xs text-destructive">
            Nenhum canal Cloud cadastrado. Cadastre um em Canais WhatsApp.
          </p>
        )}
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
          <Input
            value={vars[v.indice] ?? ''}
            onChange={(e) => setVars((s) => ({ ...s, [v.indice]: e.target.value }))}
            placeholder={v.tipo === 'url' ? 'https://…' : ''}
          />
        </div>
      ))}

      <div className="rounded-md border p-4 space-y-3">
        <p className="text-sm font-medium">Segmentação</p>
        <div className="grid grid-cols-3 gap-3">
          <Input placeholder="Cidade" value={filtros.cidade ?? ''}
                 onChange={(e) => setFiltros((f) => ({ ...f, cidade: e.target.value || undefined }))} />
          <Input placeholder="Status" value={filtros.status ?? ''}
                 onChange={(e) => setFiltros((f) => ({ ...f, status: e.target.value || undefined }))} />
          <Input placeholder="Plano" value={filtros.plano ?? ''}
                 onChange={(e) => setFiltros((f) => ({ ...f, plano: e.target.value || undefined }))} />
        </div>
        <p className="text-xs text-muted-foreground">Sem filtros = base inteira.</p>
        <div className="flex items-center gap-3">
          <button onClick={runPreview} type="button"
                  className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
            Calcular alcance
          </button>
          {preview.data && (
            <span className="text-sm font-medium">
              {preview.data.total} cliente(s) vão receber
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => handleExport('csv')}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent">
          <Download className="h-4 w-4" /> Exportar CSV
        </button>
        <button type="button" onClick={() => handleExport('xlsx')}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent">
          <Download className="h-4 w-4" /> Exportar Excel
        </button>
        <button type="button" onClick={handleDisparar} disabled={!podeDisparar}
                className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
          <Send className="h-4 w-4" /> Disparar
        </button>
      </div>
    </div>
  )
}
```

> **Nota:** o tipo `CanalOut` (de `useCanais`) precisa expor `provider`, `id`, `nome`. Conferir em `types.ts`; se faltar `provider`, adicionar o campo lá (a API já retorna). O "Enviar teste" foi movido para a tela de detalhe (Task 16) por depender de uma campanha já criada.

- [ ] **Step 3: Commit**

```bash
git add "apps/dashboard/app/(admin)/comunicados/nova/page.tsx" apps/dashboard/components/comunicado-form.tsx
git commit -m "feat(comunicados): formulario de nova campanha (template, segmento, preview, export, disparo)"
```

---

### Task 16: Página de detalhe (progresso + métricas + teste + cancelar)

**Files:**
- Create: `apps/dashboard/app/(admin)/comunicados/[id]/page.tsx`
- Create: `apps/dashboard/components/comunicado-detail.tsx`

- [ ] **Step 1: Criar a página**

```tsx
// apps/dashboard/app/(admin)/comunicados/[id]/page.tsx
import { ComunicadoDetail } from '@/components/comunicado-detail'

export default async function CampanhaDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    <div className="space-y-6">
      <ComunicadoDetail id={id} />
    </div>
  )
}
```

- [ ] **Step 2: Criar o componente de detalhe**

```tsx
// apps/dashboard/components/comunicado-detail.tsx
'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { useCampanha, useTestCampanha } from '@/lib/api/queries'

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
  const [testNum, setTestNum] = useState('')

  if (isLoading || !c) return <p className="text-sm text-muted-foreground">Carregando…</p>

  const counts = c.status_counts ?? {}

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

      <div className="rounded-md border p-4 space-y-3 max-w-md">
        <p className="text-sm font-medium">Enviar teste</p>
        <div className="flex gap-3">
          <Input placeholder="5592999999999" value={testNum}
                 onChange={(e) => setTestNum(e.target.value)} />
          <button
            type="button"
            onClick={() =>
              testSend.mutate(testNum, {
                onSuccess: () => toast.success('Teste enviado'),
                onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
              })
            }
            className="rounded-md border px-3 py-2 text-sm hover:bg-accent whitespace-nowrap"
          >
            Enviar
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add "apps/dashboard/app/(admin)/comunicados/[id]/page.tsx" apps/dashboard/components/comunicado-detail.tsx
git commit -m "feat(comunicados): tela de detalhe da campanha (progresso, metricas, teste)"
```

---

### Task 17: Entrada no menu lateral

**Files:**
- Modify: `apps/dashboard/components/nav-sidebar.tsx`

- [ ] **Step 1: Adicionar a entrada "Comunicados"** na seção `Sistema` (ou a seção mais adequada), seguindo o padrão existente. `Megaphone` já está importado de `lucide-react`:

```typescript
      { href: '/comunicados', label: 'Comunicados', icon: Megaphone, roles: ['admin'] },
```

- [ ] **Step 2: Verificar build** (CI): `npm run lint`. Esperado: limpo.

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/components/nav-sidebar.tsx
git commit -m "feat(comunicados): item Comunicados no menu lateral"
```

---

## FASE 3 — Operacional

### Task 18: Pré-requisito — cadastrar templates na Meta (Robert)

Não é código. Antes do primeiro disparo real:

- [ ] No **WhatsApp Manager → Modelos de mensagem**, criar os 3 templates com **exatamente** estes nomes (têm que bater com o seed da migration 0049):
  - `comunicado_geral` — categoria Marketing — corpo com 1 variável `{{1}}` (mensagem).
  - `promocao` — categoria Marketing — corpo com `{{1}}` (descrição) e `{{2}}` (link).
  - `lancamento_app` — categoria Marketing — corpo com `{{1}}` (link de download).
- [ ] Idioma: **Português (BR)** → `pt_BR`.
- [ ] Aguardar **aprovação da Meta** (de minutos a algumas horas). Só dá pra disparar depois de aprovado.
- [ ] Conferir que existe um **Canal com `provider=cloud`** cadastrado no dashboard (Canais WhatsApp) apontando pro phone number / WABA corretos.

> Se o nome aprovado divergir do seed, ajustar o registro em `broadcast_templates` (ou re-seed) para bater.

---

## Self-review (cobertura do spec)

- ✅ Templates misto → seed de 3 + tabela `broadcast_templates` extensível (Tasks 1, 2, 9, 10).
- ✅ Segmentação cidade/status/plano/base inteira → `resolver_segmento` (Task 3) usado em preview/export/disparo.
- ✅ Opt-out de marketing → coluna + filtro sempre aplicado (Tasks 1, 2, 3).
- ✅ Envio reaproveitando primitivas, sem tocar `send_one` ativo → `broadcast_sender` (Task 6) + task (Task 7).
- ✅ Throttling por tier → batch + pausa configuráveis (Tasks 4, 7).
- ✅ Webhook atualiza entregue/lida/falha → Task 12.
- ✅ Export ligado ao filtro (CSV + XLSX) → Task 10/11, UI Task 15.
- ✅ Dashboard: lista, nova, detalhe, menu → Tasks 14–17.
- ✅ Agendamento como campo reservado (MVP só "enviar agora") → `agendada_para` existe, sem beat task.
- ✅ Idempotência do disparo → materialização guardada + envio só de `pendente` (Task 7 + teste).
- ✅ Validação canal não-cloud rejeitado → Task 10 + teste.

## Fora de escopo (extensões futuras)
Agendamento real (beat), auto-opt-out por "SAIR"/"PARAR", submissão de templates via Graph API, métricas agregadas por período.
