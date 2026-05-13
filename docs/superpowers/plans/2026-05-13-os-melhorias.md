# OS Melhorias (itens 1–8) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 8 operational improvements: manual OS reassignment, required-technician creation, OS from conversation, duplicate OS alert, safe active/inactive routing, OS deletion with notification, and deterministic follow-up handling.

**Architecture:** One DB migration adds all new columns; backend work lands in Group 1 (Tasks 1–8); frontend work in Group 2 (Tasks 9–14, parallelisable with Group 1 once schemas are defined). FSM gets a new `AGUARDA_FOLLOWUP_OS` state handled deterministically before calling the LLM.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 async, Alembic, Celery, Next.js 14, React Query v5, Zod, Tailwind

---

## File Map

**Create:**
- `apps/api/alembic/versions/0005_os_followup_reatribuicao.py`
- `apps/api/src/ondeline_api/workers/followup.py`
- `apps/dashboard/components/dialog-reatribuir-tecnico.tsx`
- `apps/dashboard/components/dialog-abrir-os-from-conversa.tsx`
- `apps/api/tests/test_fsm_followup.py`
- `apps/api/tests/test_v1_ordens_servico.py`
- `apps/api/tests/test_v1_conversas_cliente_embutido.py`

**Modify:**
- `apps/api/src/ondeline_api/db/models/business.py`
- `apps/api/src/ondeline_api/api/schemas/os.py`
- `apps/api/src/ondeline_api/api/schemas/conversa.py`
- `apps/api/src/ondeline_api/repositories/ordem_servico.py`
- `apps/api/src/ondeline_api/repositories/conversa.py`
- `apps/api/src/ondeline_api/api/v1/ordens_servico.py`
- `apps/api/src/ondeline_api/api/v1/conversas.py`
- `apps/api/src/ondeline_api/domain/fsm.py`
- `apps/api/src/ondeline_api/services/inbound.py`
- `apps/api/src/ondeline_api/workers/runtime.py`
- `apps/dashboard/lib/api/types.ts`
- `apps/dashboard/lib/api/queries.ts`
- `apps/dashboard/components/form-os-create.tsx`
- `apps/dashboard/components/os-list.tsx`
- `apps/dashboard/components/conversa-chat.tsx`
- `apps/dashboard/components/conversa-list.tsx`

---

## Task 1: Alembic migration 0005

**Files:**
- Create: `apps/api/alembic/versions/0005_os_followup_reatribuicao.py`

- [ ] **Create the migration file**

```python
"""os_followup_reatribuicao — new fields for follow-up and reassignment.

Revision ID: 0005_os_followup_reatribuicao
Revises: 0004
Create Date: 2026-05-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID

revision: str = "0005_os_followup_reatribuicao"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # ordens_servico: reatribuição
    op.add_column("ordens_servico", sa.Column("reatribuido_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ordens_servico", sa.Column(
        "reatribuido_por", PgUUID(as_uuid=True), nullable=True
    ))
    op.create_foreign_key(
        "fk_os_reatribuido_por_users",
        "ordens_servico", "users",
        ["reatribuido_por"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column("ordens_servico", sa.Column(
        "historico_reatribuicoes", JSONB, nullable=True, server_default="'[]'::jsonb"
    ))

    # ordens_servico: follow-up
    op.add_column("ordens_servico", sa.Column("follow_up_resposta", sa.Text, nullable=True))
    op.add_column("ordens_servico", sa.Column("follow_up_respondido_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ordens_servico", sa.Column("follow_up_resultado", sa.String(20), nullable=True))

    # conversas: follow-up OS reference
    op.add_column("conversas", sa.Column("followup_os_id", PgUUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_conversas_followup_os",
        "conversas", "ordens_servico",
        ["followup_os_id"], ["id"],
        ondelete="SET NULL",
    )

    # new conversa_estado enum value
    op.execute("ALTER TYPE conversa_estado ADD VALUE IF NOT EXISTS 'aguarda_followup_os'")


def downgrade() -> None:
    op.drop_constraint("fk_conversas_followup_os", "conversas", type_="foreignkey")
    op.drop_column("conversas", "followup_os_id")
    op.drop_constraint("fk_os_reatribuido_por_users", "ordens_servico", type_="foreignkey")
    op.drop_column("ordens_servico", "reatribuido_em")
    op.drop_column("ordens_servico", "reatribuido_por")
    op.drop_column("ordens_servico", "historico_reatribuicoes")
    op.drop_column("ordens_servico", "follow_up_resposta")
    op.drop_column("ordens_servico", "follow_up_respondido_em")
    op.drop_column("ordens_servico", "follow_up_resultado")
    # Cannot remove enum value in PostgreSQL; downgrade leaves 'aguarda_followup_os' in enum
```

- [ ] **Apply the migration**

```bash
cd apps/api && uv run alembic upgrade head
```

Expected: `Running upgrade 0004 -> 0005_os_followup_reatribuicao, os_followup_reatribuicao`

- [ ] **Commit**

```bash
git add apps/api/alembic/versions/0005_os_followup_reatribuicao.py
git commit -m "feat(db): migration 0005 — reatribuicao + follow-up fields"
```

---

## Task 2: Model updates

**Files:**
- Modify: `apps/api/src/ondeline_api/db/models/business.py`

- [ ] **Add AGUARDA_FOLLOWUP_OS to ConversaEstado**

In `business.py`, in the `ConversaEstado` class add:
```python
AGUARDA_FOLLOWUP_OS = "aguarda_followup_os"
```

- [ ] **Add new fields to OrdemServico model**

After the existing `comentario_cliente` mapped column, add:
```python
reatribuido_em: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
reatribuido_por: Mapped[UUID | None] = mapped_column(
    PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
historico_reatribuicoes: Mapped[list[dict[str, Any]] | None] = mapped_column(
    JSONB, nullable=True
)
follow_up_resposta: Mapped[str | None] = mapped_column(Text, nullable=True)
follow_up_respondido_em: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
follow_up_resultado: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

- [ ] **Add followup_os_id to Conversa model**

In the `Conversa` class, after `deleted_at`:
```python
followup_os_id: Mapped[UUID | None] = mapped_column(
    PgUUID(as_uuid=True), ForeignKey("ordens_servico.id", ondelete="SET NULL"), nullable=True
)
```

- [ ] **Commit**

```bash
git add apps/api/src/ondeline_api/db/models/business.py
git commit -m "feat(models): add reatribuicao + follow-up fields to OS and Conversa"
```

---

## Task 3: API schemas

**Files:**
- Modify: `apps/api/src/ondeline_api/api/schemas/os.py`
- Modify: `apps/api/src/ondeline_api/api/schemas/conversa.py`

- [ ] **Update os.py schemas**

Replace the entire `apps/api/src/ondeline_api/api/schemas/os.py` with:

```python
"""DTOs for OrdemServico (OS)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OsListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    codigo: str
    cliente_id: UUID
    tecnico_id: UUID | None
    status: str
    problema: str
    endereco: str
    agendamento_at: datetime | None
    criada_em: datetime
    concluida_em: datetime | None
    reatribuido_em: datetime | None = None
    reatribuido_por: UUID | None = None


class OsOut(OsListItem):
    fotos: list[dict[str, Any]] | None
    csat: int | None
    comentario_cliente: str | None
    historico_reatribuicoes: list[dict[str, Any]] | None = None
    follow_up_resposta: str | None = None
    follow_up_respondido_em: datetime | None = None
    follow_up_resultado: str | None = None


class OsCreate(BaseModel):
    cliente_id: UUID
    tecnico_id: UUID
    problema: str = Field(min_length=1, max_length=2000)
    endereco: str = Field(min_length=1, max_length=500)
    agendamento_at: datetime | None = None


class OsPatch(BaseModel):
    status: str | None = None
    tecnico_id: UUID | None = None
    agendamento_at: datetime | None = None


class OsConcluirIn(BaseModel):
    csat: int | None = Field(default=None, ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=2000)


class OsReatribuirIn(BaseModel):
    tecnico_id: UUID


class OsDeleteOut(BaseModel):
    notif_tecnico: bool
```

- [ ] **Update conversa.py schemas — add ClienteEmbutido + update ConversaOut**

Replace `apps/api/src/ondeline_api/api/schemas/conversa.py` with:

```python
"""DTOs for Conversa."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ondeline_api.api.schemas.mensagem import MensagemOut


class ClienteEmbutido(BaseModel):
    id: UUID
    nome: str
    cpf_cnpj: str
    whatsapp: str
    plano: str | None
    cidade: str | None
    endereco: str | None


class ConversaListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    whatsapp: str
    estado: str
    status: str
    cliente_id: UUID | None
    atendente_id: UUID | None
    created_at: datetime
    last_message_at: datetime | None


class ConversaOut(ConversaListItem):
    mensagens: list[MensagemOut] = Field(default_factory=list)
    cliente: ClienteEmbutido | None = None


class ResponderIn(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
```

- [ ] **Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/os.py apps/api/src/ondeline_api/api/schemas/conversa.py
git commit -m "feat(schemas): OsCreate requires tecnico_id; OsOut + ConversaOut enriched"
```

---

## Task 4: Repository updates

**Files:**
- Modify: `apps/api/src/ondeline_api/repositories/ordem_servico.py`
- Modify: `apps/api/src/ondeline_api/repositories/conversa.py`

- [ ] **Write failing test for cliente_id filter**

Create `apps/api/tests/test_v1_ordens_servico.py`:

```python
"""Tests for OS endpoints (reatribuir, delete, create with tecnico)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
    OrdemServico,
    OsStatus,
    Tecnico,
)
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _make_cliente(session: AsyncSession) -> Cliente:
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Joao"),
        whatsapp="5511111@s",
    )
    session.add(c)
    await session.flush()
    return c


async def _make_tecnico(session: AsyncSession, ativo: bool = True) -> Tecnico:
    t = Tecnico(nome=f"Tec-{uuid4().hex[:6]}", ativo=ativo)
    session.add(t)
    await session.flush()
    return t


async def _make_os(session: AsyncSession, cliente: Cliente, tecnico: Tecnico) -> OrdemServico:
    from ondeline_api.domain.os_sequence import next_codigo
    codigo = await next_codigo(session)
    repo = OrdemServicoRepo(session)
    return await repo.create(
        codigo=codigo,
        cliente_id=cliente.id,
        tecnico_id=tecnico.id,
        problema="sem internet",
        endereco="Rua A, 10",
    )


async def test_list_paginated_by_cliente_id(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    tec = await _make_tecnico(db_session)
    os1 = await _make_os(db_session, cliente, tec)

    outros_cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("99988877766"),
        cpf_hash=hash_pii("99988877766"),
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5599999@s",
    )
    db_session.add(outros_cliente)
    await db_session.flush()
    tec2 = await _make_tecnico(db_session)
    from ondeline_api.domain.os_sequence import next_codigo
    codigo2 = await next_codigo(db_session)
    await OrdemServicoRepo(db_session).create(
        codigo=codigo2, cliente_id=outros_cliente.id, tecnico_id=tec2.id,
        problema="outro", endereco="Rua B"
    )

    repo = OrdemServicoRepo(db_session)
    rows, _ = await repo.list_paginated(cliente_id=cliente.id)
    assert len(rows) == 1
    assert rows[0].id == os1.id
```

- [ ] **Run test to confirm it fails**

```bash
cd apps/api && uv run pytest tests/test_v1_ordens_servico.py::test_list_paginated_by_cliente_id -v
```

Expected: FAIL — `list_paginated() got an unexpected keyword argument 'cliente_id'`

- [ ] **Add cliente_id filter to OrdemServicoRepo.list_paginated**

In `repositories/ordem_servico.py`, update `list_paginated` signature and body:

```python
async def list_paginated(
    self,
    *,
    status: str | None = None,
    tecnico_id: UUID | None = None,
    cliente_id: UUID | None = None,
    cidade: str | None = None,
    cursor: datetime | None = None,
    limit: int = 50,
) -> tuple[list[OrdemServico], datetime | None]:
    from sqlalchemy import desc, select

    stmt = select(OrdemServico)
    if status:
        stmt = stmt.where(OrdemServico.status == status)
    if tecnico_id:
        stmt = stmt.where(OrdemServico.tecnico_id == tecnico_id)
    if cliente_id:
        stmt = stmt.where(OrdemServico.cliente_id == cliente_id)
    if cursor is not None:
        stmt = stmt.where(OrdemServico.criada_em < cursor)
    stmt = stmt.order_by(desc(OrdemServico.criada_em)).limit(limit + 1)
    rows = list((await self._session.execute(stmt)).scalars().all())
    if len(rows) > limit:
        next_cursor = rows[limit].criada_em
        rows = rows[:limit]
    else:
        next_cursor = None
    return rows, next_cursor
```

- [ ] **Run test to confirm it passes**

```bash
cd apps/api && uv run pytest tests/test_v1_ordens_servico.py::test_list_paginated_by_cliente_id -v
```

Expected: PASS

- [ ] **Add find_active_by_cliente_id to ConversaRepo**

In `repositories/conversa.py`, add the method after `soft_delete`:

```python
async def find_active_by_cliente_id(self, cliente_id: UUID) -> "Conversa | None":
    """Returns the most recent non-encerrada conversa for a client."""
    from sqlalchemy import desc, select
    from ondeline_api.db.models.business import ConversaStatus

    stmt = (
        select(Conversa)
        .where(
            Conversa.cliente_id == cliente_id,
            Conversa.deleted_at.is_(None),
            Conversa.status != ConversaStatus.ENCERRADA,
        )
        .order_by(desc(Conversa.created_at))
        .limit(1)
    )
    return (await self._session.execute(stmt)).scalar_one_or_none()
```

- [ ] **Commit**

```bash
git add apps/api/src/ondeline_api/repositories/ordem_servico.py \
        apps/api/src/ondeline_api/repositories/conversa.py \
        apps/api/tests/test_v1_ordens_servico.py
git commit -m "feat(repos): add cliente_id filter to OS list; add find_active_by_cliente to ConversaRepo"
```

---

## Task 5: OS endpoints — reatribuir, delete, create update

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/ordens_servico.py`

- [ ] **Write failing tests for reatribuir and delete endpoints**

Add to `apps/api/tests/test_v1_ordens_servico.py`:

```python
from typing import Any

import pytest_asyncio
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis


def _make_app(db_session: AsyncSession, redis_client: Any) -> FastAPI:
    app = create_app()

    async def _override_db() -> Any:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


async def _make_admin(session: AsyncSession) -> dict[str, Any]:
    email = f"admin-{uuid4().hex[:6]}@test.com"
    pwd = "Admin1234!"
    user = User(
        email=email, password_hash=hash_password(pwd),
        role=Role.ADMIN, name="Admin", is_active=True,
    )
    session.add(user)
    await session.flush()
    return {"email": email, "password": pwd, "user": user}


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


async def test_reatribuir_troca_tecnico(db_session: AsyncSession) -> None:
    from unittest.mock import AsyncMock, patch

    cliente = await _make_cliente(db_session)
    tec1 = await _make_tecnico(db_session)
    tec1.whatsapp = "5511111@s"
    tec2 = await _make_tecnico(db_session)
    tec2.whatsapp = "5522222@s"
    await db_session.flush()
    os_ = await _make_os(db_session, cliente, tec1)
    admin = await _make_admin(db_session)

    app = _make_app(db_session, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        with patch("ondeline_api.api.v1.ordens_servico._send_whatsapp", new_callable=AsyncMock):
            r = await c.post(
                f"/api/v1/os/{os_.id}/reatribuir",
                json={"tecnico_id": str(tec2.id)},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tecnico_id"] == str(tec2.id)
    assert data["reatribuido_por"] == str(admin["user"].id)
    assert len(data["historico_reatribuicoes"]) == 1
    assert data["historico_reatribuicoes"][0]["de"] == str(tec1.id)


async def test_reatribuir_concluida_retorna_422(db_session: AsyncSession) -> None:
    from unittest.mock import AsyncMock, patch

    cliente = await _make_cliente(db_session)
    tec1 = await _make_tecnico(db_session)
    tec2 = await _make_tecnico(db_session)
    os_ = await _make_os(db_session, cliente, tec1)
    os_.status = OsStatus.CONCLUIDA
    await db_session.flush()
    admin = await _make_admin(db_session)

    app = _make_app(db_session, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        with patch("ondeline_api.api.v1.ordens_servico._send_whatsapp", new_callable=AsyncMock):
            r = await c.post(
                f"/api/v1/os/{os_.id}/reatribuir",
                json={"tecnico_id": str(tec2.id)},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 422


async def test_delete_os(db_session: AsyncSession) -> None:
    from unittest.mock import AsyncMock, patch

    cliente = await _make_cliente(db_session)
    tec = await _make_tecnico(db_session)
    tec.whatsapp = "5533333@s"
    await db_session.flush()
    os_ = await _make_os(db_session, cliente, tec)
    admin = await _make_admin(db_session)

    app = _make_app(db_session, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        with patch("ondeline_api.api.v1.ordens_servico._send_whatsapp", new_callable=AsyncMock):
            r = await c.delete(
                f"/api/v1/os/{os_.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 200
    assert r.json()["notif_tecnico"] is True
```

- [ ] **Run tests to confirm they fail**

```bash
cd apps/api && uv run pytest tests/test_v1_ordens_servico.py::test_reatribuir_troca_tecnico tests/test_v1_ordens_servico.py::test_reatribuir_concluida_retorna_422 tests/test_v1_ordens_servico.py::test_delete_os -v
```

Expected: FAIL — routes not found (404)

- [ ] **Implement reatribuir and delete endpoints in ordens_servico.py**

Replace the full content of `apps/api/src/ondeline_api/api/v1/ordens_servico.py` with:

```python
"""GET/POST/PATCH/DELETE /api/v1/os* — Ordens de Servico."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.os import (
    OsConcluirIn,
    OsCreate,
    OsDeleteOut,
    OsListItem,
    OsOut,
    OsPatch,
    OsReatribuirIn,
)
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import ConversaEstado, OsStatus
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.domain.os_sequence import next_codigo
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo

router = APIRouter(prefix="/api/v1/os", tags=["ordens-servico"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))
_admin_dep = Depends(require_role(Role.ADMIN))

FOTOS_DIR = Path("/tmp/ondeline_os_fotos")
FOLLOWUP_MSG = (
    "Olá! 👋 O técnico concluiu o atendimento. O serviço ficou ok para você? "
    "Responda *SIM* se tudo resolveu ou *NÃO* se ainda há problema."
)

log = structlog.get_logger(__name__)


async def _send_whatsapp(whatsapp: str, msg: str) -> None:
    """Best-effort WhatsApp notification. Never raises."""
    try:
        from ondeline_api.adapters.evolution import EvolutionAdapter
        from ondeline_api.config import get_settings
        s = get_settings()
        evo = EvolutionAdapter(base_url=s.evolution_url, instance=s.evolution_instance, api_key=s.evolution_key)
        try:
            await evo.send_text(whatsapp, msg)
        finally:
            await evo.aclose()
    except Exception:
        log.warning("os.whatsapp_send_failed", whatsapp=whatsapp)


@router.get("", response_model=CursorPage[OsListItem], dependencies=[_role_dep])
async def list_os(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    tecnico: Annotated[UUID | None, Query()] = None,
    cliente_id: Annotated[UUID | None, Query()] = None,
) -> CursorPage[OsListItem]:
    repo = OrdemServicoRepo(session)
    rows, next_cur = await repo.list_paginated(
        status=status_filter,
        tecnico_id=tecnico,
        cliente_id=cliente_id,
        cursor=parse_cursor(cursor),
        limit=parse_limit(limit),
    )
    items = [OsListItem.model_validate(o) for o in rows]
    return CursorPage[OsListItem](
        items=items,
        next_cursor=encode_cursor(next_cur) if next_cur else None,
    )


@router.post("", response_model=OsOut, status_code=status.HTTP_201_CREATED, dependencies=[_role_dep])
async def create_os(
    body: OsCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    tecnico = await TecnicoRepo(session).get_by_id(body.tecnico_id)
    if tecnico is None:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    if not tecnico.ativo:
        raise HTTPException(status_code=422, detail="Técnico inativo")
    codigo = await next_codigo(session)
    os_ = await repo.create(
        codigo=codigo,
        cliente_id=body.cliente_id,
        tecnico_id=body.tecnico_id,
        problema=body.problema,
        endereco=body.endereco,
    )
    if body.agendamento_at:
        os_.agendamento_at = body.agendamento_at
        await session.flush()
    if tecnico.whatsapp:
        from ondeline_api.db.crypto import decrypt_pii
        from ondeline_api.db.models.business import Cliente
        from sqlalchemy import select
        cliente_row = (await session.execute(
            select(Cliente).where(Cliente.id == body.cliente_id)
        )).scalar_one_or_none()
        nome_cliente = decrypt_pii(cliente_row.nome_encrypted) if cliente_row else "Cliente"
        msg = (
            f"Nova OS {codigo}\n"
            f"Cliente: {nome_cliente}\n"
            f"Endereço: {body.endereco}\n"
            f"Problema: {body.problema}"
        )
        await _send_whatsapp(tecnico.whatsapp, msg)
    return OsOut.model_validate(os_)


@router.get("/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def get_os(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    return OsOut.model_validate(os_)


@router.patch("/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def patch_os(
    os_id: UUID,
    body: OsPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    await repo.update(
        os_,
        status=body.status,
        tecnico_id=body.tecnico_id,
        agendamento_at=body.agendamento_at,
    )
    return OsOut.model_validate(os_)


@router.post("/{os_id}/reatribuir", response_model=OsOut, dependencies=[_role_dep])
async def reatribuir_os(
    os_id: UUID,
    body: OsReatribuirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS não encontrada")
    if os_.status == OsStatus.CONCLUIDA:
        raise HTTPException(status_code=422, detail="OS concluída não pode ser reatribuída")

    tec_repo = TecnicoRepo(session)
    novo_tec = await tec_repo.get_by_id(body.tecnico_id)
    if novo_tec is None:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    if not novo_tec.ativo:
        raise HTTPException(status_code=422, detail="Técnico inativo não pode receber OS")

    old_tecnico_id = os_.tecnico_id
    old_tec = await tec_repo.get_by_id(old_tecnico_id) if old_tecnico_id else None

    historico = list(os_.historico_reatribuicoes or [])
    historico.append({
        "de": str(old_tecnico_id) if old_tecnico_id else None,
        "para": str(body.tecnico_id),
        "em": datetime.now(tz=UTC).isoformat(),
        "por": str(current_user.id),
    })
    os_.tecnico_id = body.tecnico_id
    os_.reatribuido_em = datetime.now(tz=UTC)
    os_.reatribuido_por = current_user.id
    os_.historico_reatribuicoes = historico
    await session.flush()

    if old_tec and old_tec.whatsapp:
        await _send_whatsapp(
            old_tec.whatsapp,
            f"A OS {os_.codigo} foi reatribuída para outro técnico. Obrigado!"
        )
    if novo_tec.whatsapp:
        msg = (
            f"OS reatribuída para você: {os_.codigo}\n"
            f"Endereço: {os_.endereco}\n"
            f"Problema: {os_.problema}"
        )
        await _send_whatsapp(novo_tec.whatsapp, msg)

    return OsOut.model_validate(os_)


@router.delete("/{os_id}", response_model=OsDeleteOut, dependencies=[_admin_dep])
async def delete_os(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsDeleteOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS não encontrada")

    notif_sent = False
    if os_.tecnico_id:
        tec = await TecnicoRepo(session).get_by_id(os_.tecnico_id)
        if tec and tec.whatsapp:
            await _send_whatsapp(
                tec.whatsapp,
                f"A OS {os_.codigo} foi cancelada no sistema."
            )
            notif_sent = True

    await session.delete(os_)
    await session.flush()
    return OsDeleteOut(notif_tecnico=notif_sent)


@router.post("/{os_id}/foto", response_model=OsOut, dependencies=[_role_dep])
async def upload_foto(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")
    target_dir = FOTOS_DIR / str(os_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid4().hex}{Path(file.filename or 'foto.jpg').suffix or '.jpg'}"
    fpath = target_dir / fname
    contents = await file.read()
    fpath.write_bytes(contents)
    fpath.chmod(0o600)
    await repo.add_foto(
        os_,
        {
            "url": str(fpath),
            "ts": datetime.now(tz=UTC).isoformat(),
            "size": len(contents),
            "mime": file.content_type,
        },
    )
    return OsOut.model_validate(os_)


@router.post("/{os_id}/concluir", response_model=OsOut, dependencies=[_role_dep])
async def concluir_os(
    os_id: UUID,
    body: OsConcluirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    await repo.concluir(os_, csat=body.csat, comentario=body.comentario)

    if os_.cliente_id:
        conversa = await ConversaRepo(session).find_active_by_cliente_id(os_.cliente_id)
        if conversa:
            await _send_whatsapp(conversa.whatsapp, FOLLOWUP_MSG)
            conversa.estado = ConversaEstado.AGUARDA_FOLLOWUP_OS
            conversa.followup_os_id = os_.id
            await session.flush()

    return OsOut.model_validate(os_)
```

- [ ] **Run tests to confirm they pass**

```bash
cd apps/api && uv run pytest tests/test_v1_ordens_servico.py -v
```

Expected: All PASS

- [ ] **Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/ordens_servico.py apps/api/tests/test_v1_ordens_servico.py
git commit -m "feat(api): OS reatribuir, delete, create with tecnico, concluir sends follow-up"
```

---

## Task 6: Conversa endpoint — enrich with cliente

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/conversas.py`
- Create: `apps/api/tests/test_v1_conversas_cliente_embutido.py`

- [ ] **Write failing test**

Create `apps/api/tests/test_v1_conversas_cliente_embutido.py`:

```python
"""Test GET /api/v1/conversas/{id} returns embedded cliente."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Conversa, ConversaEstado, ConversaStatus, Cliente
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _make_app(db_session: AsyncSession) -> FastAPI:
    app = create_app()

    async def _override_db() -> Any:
        yield db_session

    async def _override_redis() -> Any:
        return None

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


async def test_get_conversa_inclui_cliente_embutido(db_session: AsyncSession) -> None:
    email = f"adm-{uuid4().hex[:6]}@test.com"
    user = User(
        email=email, password_hash=hash_password("Admin1234!"),
        role=Role.ADMIN, name="A", is_active=True,
    )
    db_session.add(user)
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Maria"),
        whatsapp="5511999@s",
        plano="Fibra 200",
        cidade="Manaus",
    )
    db_session.add(cliente)
    await db_session.flush()

    conv = Conversa(
        whatsapp="5511999@s",
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
        cliente_id=cliente.id,
    )
    db_session.add(conv)
    await db_session.flush()

    app = _make_app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/auth/login", json={"email": email, "password": "Admin1234!"})
        assert r.status_code == 200
        token = r.json()["access_token"]
        r2 = await c.get(
            f"/api/v1/conversas/{conv.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["cliente"] is not None
    assert data["cliente"]["nome"] == "Maria"
    assert data["cliente"]["plano"] == "Fibra 200"
```

- [ ] **Run test to confirm it fails**

```bash
cd apps/api && uv run pytest tests/test_v1_conversas_cliente_embutido.py -v
```

Expected: FAIL — `'cliente': None`

- [ ] **Update GET /conversas/{id} to embed cliente**

In `apps/api/src/ondeline_api/api/v1/conversas.py`, update `get_conversa`:

```python
from ondeline_api.api.schemas.conversa import (
    ClienteEmbutido,
    ConversaListItem,
    ConversaOut,
    ResponderIn,
)
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente, Mensagem
```

Replace the `get_conversa` function body:

```python
@router.get("/{conversa_id}", response_model=ConversaOut, dependencies=[_role_dep])
async def get_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConversaOut:
    from sqlalchemy import select
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")
    msgs, _ = await repo.list_messages(c.id, limit=50)
    out = ConversaOut.model_validate(c)
    out.mensagens = [_to_msg_out(m) for m in msgs]

    if c.cliente_id is not None:
        cliente_row = (
            await session.execute(select(Cliente).where(Cliente.id == c.cliente_id))
        ).scalar_one_or_none()
        if cliente_row is not None:
            out.cliente = ClienteEmbutido(
                id=cliente_row.id,
                nome=decrypt_pii(cliente_row.nome_encrypted) if cliente_row.nome_encrypted else "",
                cpf_cnpj=decrypt_pii(cliente_row.cpf_cnpj_encrypted) if cliente_row.cpf_cnpj_encrypted else "",
                whatsapp=cliente_row.whatsapp,
                plano=cliente_row.plano,
                cidade=cliente_row.cidade,
                endereco=decrypt_pii(cliente_row.endereco_encrypted) if cliente_row.endereco_encrypted else None,
            )
    return out
```

- [ ] **Run test to confirm it passes**

```bash
cd apps/api && uv run pytest tests/test_v1_conversas_cliente_embutido.py -v
```

Expected: PASS

- [ ] **Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/conversas.py apps/api/tests/test_v1_conversas_cliente_embutido.py
git commit -m "feat(api): GET /conversas/{id} embeds cliente data for OS pre-fill"
```

---

## Task 7: FSM follow-up state

**Files:**
- Modify: `apps/api/src/ondeline_api/domain/fsm.py`
- Create: `apps/api/tests/test_fsm_followup.py`

- [ ] **Write failing tests**

Create `apps/api/tests/test_fsm_followup.py`:

```python
"""FSM: AGUARDA_FOLLOWUP_OS transitions."""
from __future__ import annotations

import pytest

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.domain.fsm import ActionKind, Event, EventKind, Fsm

pytestmark = pytest.mark.asyncio


def _event(text: str) -> Event:
    return Event(kind=EventKind.MSG_CLIENTE_TEXT, text=text)


def test_sim_retorna_confirmar() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("sim"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_ok_retorna_confirmar() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("ok, obrigado!"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_nao_retorna_escalar() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("não, continua sem internet"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_ATENDENTE
    assert any(a.kind is ActionKind.FOLLOWUP_OS_ESCALAR for a in d.actions)


def test_ambiguo_chama_llm() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("e as duas horas quanto vai demorar"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_FOLLOWUP_OS
    assert any(a.kind is ActionKind.LLM_TURN for a in d.actions)
```

- [ ] **Run tests to confirm they fail**

```bash
cd apps/api && uv run pytest tests/test_fsm_followup.py -v
```

Expected: FAIL — `ActionKind has no attribute FOLLOWUP_OS_CONFIRMAR`

- [ ] **Update fsm.py with new ActionKinds and state handling**

Replace the full content of `apps/api/src/ondeline_api/domain/fsm.py`:

```python
"""Maquina de estados da Conversa."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus


class EventKind(StrEnum):
    MSG_CLIENTE_TEXT = "msg_cliente_text"
    MSG_CLIENTE_MEDIA = "msg_cliente_media"
    MSG_FROM_ME = "msg_from_me"


class ActionKind(StrEnum):
    SEND_ACK = "send_ack"
    LLM_TURN = "llm_turn"
    FOLLOWUP_OS_CONFIRMAR = "followup_os_confirmar"
    FOLLOWUP_OS_ESCALAR = "followup_os_escalar"


@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind
    text: str | None


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionKind
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FsmDecision:
    new_estado: ConversaEstado
    new_status: ConversaStatus
    actions: list[Action]


class InvalidTransition(Exception):
    pass


_PALAVRAS_OK = {"sim", "ok", "obrigado", "certo", "tudo bem", "já está", "resolveu", "funcionou", "ótimo", "otimo"}
_PALAVRAS_NOK = {"não", "nao", "ainda não", "ainda nao", "continua", "sem sinal", "sem internet", "mesmo problema", "não resolveu", "nao resolveu"}


class Fsm:
    @staticmethod
    def transition(
        estado: ConversaEstado,
        status: ConversaStatus,
        event: Event,
    ) -> FsmDecision:
        if event.kind is EventKind.MSG_FROM_ME:
            raise InvalidTransition(
                "FSM should never receive MSG_FROM_ME — filter before invoking."
            )

        if estado in (ConversaEstado.HUMANO, ConversaEstado.AGUARDA_ATENDENTE):
            return FsmDecision(new_estado=estado, new_status=status, actions=[])

        if estado is ConversaEstado.AGUARDA_FOLLOWUP_OS:
            text_norm = (event.text or "").lower().strip()
            if any(p in text_norm for p in _PALAVRAS_OK):
                return FsmDecision(
                    new_estado=ConversaEstado.ENCERRADA,
                    new_status=ConversaStatus.ENCERRADA,
                    actions=[Action(kind=ActionKind.FOLLOWUP_OS_CONFIRMAR)],
                )
            if any(p in text_norm for p in _PALAVRAS_NOK):
                return FsmDecision(
                    new_estado=ConversaEstado.AGUARDA_ATENDENTE,
                    new_status=ConversaStatus.AGUARDANDO,
                    actions=[Action(kind=ActionKind.FOLLOWUP_OS_ESCALAR)],
                )
            return FsmDecision(
                new_estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
                new_status=ConversaStatus.BOT,
                actions=[Action(kind=ActionKind.LLM_TURN)],
            )

        if estado is ConversaEstado.ENCERRADA:
            return FsmDecision(
                new_estado=ConversaEstado.AGUARDA_OPCAO,
                new_status=ConversaStatus.BOT,
                actions=[Action(kind=ActionKind.LLM_TURN)],
            )

        if estado is ConversaEstado.INICIO:
            new_estado = ConversaEstado.AGUARDA_OPCAO
        else:
            new_estado = estado

        return FsmDecision(
            new_estado=new_estado,
            new_status=ConversaStatus.BOT,
            actions=[Action(kind=ActionKind.LLM_TURN)],
        )
```

- [ ] **Run tests to confirm they pass**

```bash
cd apps/api && uv run pytest tests/test_fsm_followup.py tests/test_fsm_m4.py -v
```

Expected: All PASS

- [ ] **Commit**

```bash
git add apps/api/src/ondeline_api/domain/fsm.py apps/api/tests/test_fsm_followup.py
git commit -m "feat(fsm): AGUARDA_FOLLOWUP_OS state with deterministic confirm/escalar handling"
```

---

## Task 8: Inbound service + runtime — handle follow-up actions

**Files:**
- Modify: `apps/api/src/ondeline_api/services/inbound.py`
- Modify: `apps/api/src/ondeline_api/workers/runtime.py`
- Create: `apps/api/src/ondeline_api/workers/followup.py`

- [ ] **Create followup.py worker**

Create `apps/api/src/ondeline_api/workers/followup.py`:

```python
"""Task Celery: atualiza OS e envia mensagem de resultado do follow-up."""
from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select

from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, reset_redis_cache, task_session

log = structlog.get_logger(__name__)

_MSG_CONFIRMAR = "Fico feliz que tenha resolvido! 😊 Qualquer dúvida estamos aqui."
_MSG_ESCALAR = (
    "Entendido, vou acionar nossa equipe para verificar o que aconteceu. "
    "Em breve um atendente entrará em contato. 🙏"
)


async def _run_followup(conversa_id: UUID, resultado: str, resposta: str) -> None:
    from ondeline_api.adapters.evolution import EvolutionAdapter
    from ondeline_api.config import get_settings
    from ondeline_api.db.models.business import Conversa, OrdemServico

    s = get_settings()
    evo = EvolutionAdapter(base_url=s.evolution_url, instance=s.evolution_instance, api_key=s.evolution_key)
    try:
        async with task_session() as session:
            conversa = (
                await session.execute(select(Conversa).where(Conversa.id == conversa_id))
            ).scalar_one_or_none()
            if conversa is None:
                log.warning("followup.conversa_not_found", conversa_id=str(conversa_id))
                return

            msg = _MSG_CONFIRMAR if resultado == "ok" else _MSG_ESCALAR
            try:
                await evo.send_text(conversa.whatsapp, msg)
            except Exception:
                log.warning("followup.send_failed", whatsapp=conversa.whatsapp)

            if conversa.followup_os_id:
                from datetime import UTC, datetime
                os_ = (
                    await session.execute(
                        select(OrdemServico).where(OrdemServico.id == conversa.followup_os_id)
                    )
                ).scalar_one_or_none()
                if os_:
                    os_.follow_up_resultado = resultado
                    os_.follow_up_resposta = resposta
                    os_.follow_up_respondido_em = datetime.now(tz=UTC)
            conversa.followup_os_id = None
    finally:
        await evo.aclose()


@celery_app.task(
    name="ondeline_api.workers.followup.followup_os_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def followup_os_task(self: Any, *, conversa_id: str, resultado: str, resposta: str) -> None:
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            from ondeline_api.db.engine import reset_engine_cache
            reset_engine_cache()
            reset_redis_cache()

            def _in_thread() -> None:
                reset_engine_cache()
                reset_redis_cache()
                asyncio.run(_run_followup(UUID(conversa_id), resultado, resposta))

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(_in_thread).result()
        else:
            asyncio.run(_run_followup(UUID(conversa_id), resultado, resposta))
    except Exception as e:
        raise self.retry(exc=e) from e
```

- [ ] **Add enqueue_followup_os to the queue protocol and implementations**

In `apps/api/src/ondeline_api/services/inbound.py`, add to `_OutboundQueueProto`:

```python
def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None: ...
```

In `apps/api/src/ondeline_api/workers/runtime.py`, add to `CeleryOutboundEnqueuer`:

```python
def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None:
    from ondeline_api.workers.followup import followup_os_task
    followup_os_task.delay(conversa_id=str(conversa_id), resultado=resultado, resposta=resposta)
```

And add to `BufferedOutboundEnqueuer`:

```python
_pending_followup: list[dict[str, Any]] = field(default_factory=list)

def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None:
    self._pending_followup.append({
        "conversa_id": str(conversa_id), "resultado": resultado, "resposta": resposta
    })
```

In `BufferedOutboundEnqueuer.flush()`, add:

```python
from ondeline_api.workers.followup import followup_os_task
for item in self._pending_followup:
    followup_os_task.delay(**item)
self._pending_followup.clear()
```

- [ ] **Handle FOLLOWUP_OS_CONFIRMAR and FOLLOWUP_OS_ESCALAR in inbound.py**

In `process_inbound_message`, in the action loop, after the `LLM_TURN` and `SEND_ACK` handlers, add:

```python
elif action.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR:
    deps.outbound.enqueue_followup_os(
        conversa.id, resultado="ok", resposta=evt.text or ""
    )
elif action.kind is ActionKind.FOLLOWUP_OS_ESCALAR:
    deps.outbound.enqueue_followup_os(
        conversa.id, resultado="nao_ok", resposta=evt.text or ""
    )
```

- [ ] **Run existing inbound tests to confirm nothing broke**

```bash
cd apps/api && uv run pytest tests/test_fsm_m4.py tests/test_fsm_followup.py -v
```

Expected: All PASS

- [ ] **Commit**

```bash
git add apps/api/src/ondeline_api/workers/followup.py \
        apps/api/src/ondeline_api/services/inbound.py \
        apps/api/src/ondeline_api/workers/runtime.py
git commit -m "feat(bot): follow-up OS actions wired through inbound service and Celery worker"
```

---

## Task 9: Frontend types + queries

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/lib/api/queries.ts`

- [ ] **Update types.ts**

Replace full content of `apps/dashboard/lib/api/types.ts`:

```typescript
// Generated by openapi-typescript. Run `pnpm gen:types` to regenerate.
export type CursorPage<T> = { items: T[]; next_cursor: string | null }
export interface MeOut { id: string; email: string; role: 'admin' | 'atendente' | 'tecnico'; name: string }

export interface ClienteEmbutido {
  id: string
  nome: string
  cpf_cnpj: string
  whatsapp: string
  plano: string | null
  cidade: string | null
  endereco: string | null
}

export interface ConversaListItem {
  id: string
  whatsapp: string
  estado: string
  status: string
  cliente_id: string | null
  atendente_id: string | null
  created_at: string
  last_message_at: string | null
}

export interface MensagemOut {
  id: string
  conversa_id: string
  role: 'cliente' | 'bot' | 'atendente'
  content: string | null
  media_type: string | null
  media_url: string | null
  created_at: string
}

export interface ConversaDetail extends ConversaListItem {
  mensagens: MensagemOut[]
  cliente: ClienteEmbutido | null
}

export interface OsListItem {
  id: string
  codigo: string
  cliente_id: string
  tecnico_id: string | null
  status: string
  problema: string
  endereco: string
  agendamento_at: string | null
  criada_em: string
  concluida_em: string | null
  reatribuido_em: string | null
  reatribuido_por: string | null
}

export interface OsFoto {
  url: string
  ts: string
  size: number
  mime: string
}

export interface OsOut extends OsListItem {
  fotos: OsFoto[] | null
  csat: number | null
  comentario_cliente: string | null
  historico_reatribuicoes: Array<{de: string|null, para: string, em: string, por: string}> | null
  follow_up_resposta: string | null
  follow_up_respondido_em: string | null
  follow_up_resultado: string | null
}

export interface OsCreate {
  cliente_id: string
  tecnico_id: string
  problema: string
  endereco: string
  agendamento_at?: string | null
}

export interface OsPatch {
  status?: string | null
  tecnico_id?: string | null
  agendamento_at?: string | null
}

export interface OsConcluirIn {
  csat?: number | null
  comentario?: string | null
}

export interface OsReatribuirIn {
  tecnico_id: string
}

export interface OsDeleteOut {
  notif_tecnico: boolean
}

// Leads
export interface LeadOut {
  id: string
  nome: string
  whatsapp: string
  interesse: string | null
  status: string
  atendente_id: string | null
  notas: string | null
  created_at: string
  updated_at: string
}
export interface LeadCreate {
  nome: string
  whatsapp: string
  interesse?: string | null
  atendente_id?: string | null
  notas?: string | null
}
export interface LeadPatch {
  nome?: string | null
  interesse?: string | null
  status?: string | null
  atendente_id?: string | null
  notas?: string | null
}

// Clientes
export interface ClienteListItem {
  id: string
  whatsapp: string
  plano: string | null
  status: string | null
  cidade: string | null
  sgp_provider: string | null
  sgp_id: string | null
  created_at: string
  last_seen_at: string | null
}
export interface ClienteDetail extends ClienteListItem {
  nome: string
  cpf_cnpj: string
  endereco: string | null
  retention_until: string | null
}

// Tecnicos
export interface TecnicoListItem {
  id: string
  nome: string
  whatsapp: string | null
  ativo: boolean
  user_id: string | null
  gps_lat: number | null
  gps_lng: number | null
  gps_ts: string | null
}
export interface AreaOut {
  cidade: string
  rua: string
  prioridade: number
}
export interface TecnicoOut extends TecnicoListItem {
  areas: AreaOut[]
}
export interface TecnicoCreate {
  nome: string
  whatsapp?: string | null
  ativo?: boolean
  user_id?: string | null
}
export interface TecnicoPatch {
  nome?: string | null
  whatsapp?: string | null
  ativo?: boolean | null
  gps_lat?: number | null
  gps_lng?: number | null
}
export interface AreaCreate {
  cidade: string
  rua: string
  prioridade?: number
}

// Manutencoes
export interface ManutencaoOut {
  id: string
  titulo: string
  descricao: string | null
  inicio_at: string
  fim_at: string
  cidades: string[] | null
  notificar: boolean
  criada_em: string
}
export interface ManutencaoCreate {
  titulo: string
  descricao?: string | null
  inicio_at: string
  fim_at: string
  cidades?: string[] | null
  notificar?: boolean
}
export interface ManutencaoPatch {
  titulo?: string | null
  descricao?: string | null
  inicio_at?: string | null
  fim_at?: string | null
  cidades?: string[] | null
  notificar?: boolean | null
}

// Config
export interface ConfigOut {
  key: string
  value: unknown
  updated_by: string | null
  updated_at: string
}

// Metricas
export interface MetricasOut {
  conversas_aguardando: number
  conversas_humano: number
  msgs_24h: number
  os_abertas: number
  os_concluidas_24h: number
  csat_avg_30d: number | null
  leads_novos_7d: number
}
```

- [ ] **Add useReatribuirOs, useDeleteOs, useOsListByCliente to queries.ts**

In `apps/dashboard/lib/api/queries.ts`, add after `useConcluirOs`:

```typescript
export function useReatribuirOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OsReatribuirIn) =>
      apiFetch<OsOut>(`/api/v1/os/${id}/reatribuir`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['os-detail', id] })
      qc.invalidateQueries({ queryKey: ['os'] })
    },
  })
}

export function useDeleteOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<OsDeleteOut>(`/api/v1/os/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['os'] }),
  })
}
```

Also add `OsReatribuirIn` and `OsDeleteOut` to the import from `./types` at the top of `queries.ts`.

- [ ] **Verify TypeScript compiles**

```bash
cd apps/dashboard && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Commit**

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(dashboard): types and queries for reatribuir, delete OS, ClienteEmbutido"
```

---

## Task 10: form-os-create — required tecnico selector

**Files:**
- Modify: `apps/dashboard/components/form-os-create.tsx`

- [ ] **Replace form-os-create.tsx with tecnico selector**

```typescript
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useCreateOs, useTecnicos } from '@/lib/api/queries'

const schema = z.object({
  cliente_id: z.string().uuid('UUID inválido'),
  tecnico_id: z.string().uuid('Selecione o técnico responsável'),
  problema: z.string().min(1, 'Obrigatório').max(2000),
  endereco: z.string().min(1, 'Obrigatório').max(500),
  agendamento_at: z.string().optional().nullable(),
})

type FormValues = z.infer<typeof schema>

export function FormOsCreate() {
  const router = useRouter()
  const createOs = useCreateOs()
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    const created = await createOs.mutateAsync({
      cliente_id: values.cliente_id,
      tecnico_id: values.tecnico_id,
      problema: values.problema,
      endereco: values.endereco,
      agendamento_at: values.agendamento_at || null,
    })
    router.push(`/os/${created.id}`)
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Nova OS</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label htmlFor="cliente_id">Cliente ID</Label>
            <Input id="cliente_id" {...register('cliente_id')} />
            {errors.cliente_id && (
              <p className="mt-1 text-xs text-destructive">{errors.cliente_id.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="tecnico_id">Técnico responsável *</Label>
            <Select id="tecnico_id" {...register('tecnico_id')} defaultValue="">
              <option value="" disabled>Selecione o técnico responsável</option>
              {tecnicos?.items.map((t) => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </Select>
            {errors.tecnico_id && (
              <p className="mt-1 text-xs text-destructive">{errors.tecnico_id.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="problema">Problema</Label>
            <Textarea id="problema" {...register('problema')} />
            {errors.problema && (
              <p className="mt-1 text-xs text-destructive">{errors.problema.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="endereco">Endereço</Label>
            <Input id="endereco" {...register('endereco')} />
            {errors.endereco && (
              <p className="mt-1 text-xs text-destructive">{errors.endereco.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="agendamento_at">Agendamento (opcional)</Label>
            <Input id="agendamento_at" type="datetime-local" {...register('agendamento_at')} />
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Criando…' : 'Criar OS'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Verify TypeScript compiles**

```bash
cd apps/dashboard && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Commit**

```bash
git add apps/dashboard/components/form-os-create.tsx
git commit -m "feat(dashboard): form-os-create requires tecnico responsavel"
```

---

## Task 11: os-list — reatribuir + delete + dialog-reatribuir

**Files:**
- Create: `apps/dashboard/components/dialog-reatribuir-tecnico.tsx`
- Modify: `apps/dashboard/components/os-list.tsx`

- [ ] **Create dialog-reatribuir-tecnico.tsx**

```typescript
'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { useReatribuirOs, useTecnicos } from '@/lib/api/queries'

interface Props {
  osId: string
  onClose: () => void
}

export function DialogReatribuirTecnico({ osId, onClose }: Props) {
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const reatribuir = useReatribuirOs(osId)
  const [tecnicoId, setTecnicoId] = useState('')

  async function handleConfirm() {
    if (!tecnicoId) return
    await reatribuir.mutateAsync({ tecnico_id: tecnicoId })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-sm rounded-lg border bg-card p-6 shadow-lg space-y-4">
        <h2 className="text-lg font-semibold">Reatribuir técnico</h2>
        <div>
          <Label htmlFor="novo-tecnico">Novo técnico</Label>
          <Select
            id="novo-tecnico"
            value={tecnicoId}
            onChange={(e) => setTecnicoId(e.target.value)}
            className="mt-1"
          >
            <option value="" disabled>Selecione o técnico</option>
            {tecnicos?.items.map((t) => (
              <option key={t.id} value={t.id}>{t.nome}</option>
            ))}
          </Select>
        </div>
        {reatribuir.error && (
          <p className="text-xs text-destructive">
            {reatribuir.error instanceof Error ? reatribuir.error.message : 'Erro'}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={reatribuir.isPending}>
            Cancelar
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!tecnicoId || reatribuir.isPending}
          >
            {reatribuir.isPending ? 'Reatribuindo…' : 'Confirmar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Update os-list.tsx with Reatribuir + Excluir actions**

Replace full content of `apps/dashboard/components/os-list.tsx`:

```typescript
'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Plus, Trash2, UserCog } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { useDeleteOs, useOsList } from '@/lib/api/queries'
import { DialogReatribuirTecnico } from './dialog-reatribuir-tecnico'
import type { OsListItem } from '@/lib/api/types'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pendente: 'destructive',
  em_andamento: 'default',
  concluida: 'secondary',
  cancelada: 'outline',
}

function DeleteButton({ osId }: { osId: string }) {
  const deleteOs = useDeleteOs(osId)
  async function handleDelete() {
    if (!confirm('Excluir esta OS? O técnico será notificado.')) return
    await deleteOs.mutateAsync()
  }
  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-7 w-7 text-destructive hover:text-destructive"
      onClick={handleDelete}
      disabled={deleteOs.isPending}
      title="Excluir OS"
    >
      <Trash2 className="h-3.5 w-3.5" />
    </Button>
  )
}

export function OsList() {
  const [status, setStatus] = useState('')
  const [reatribuirOsId, setReatribuirOsId] = useState<string | null>(null)
  const { data, isLoading, error } = useOsList({ status: status || undefined })

  return (
    <div className="space-y-4">
      {reatribuirOsId && (
        <DialogReatribuirTecnico
          osId={reatribuirOsId}
          onClose={() => setReatribuirOsId(null)}
        />
      )}
      <div className="flex items-center gap-3">
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="max-w-[200px]"
        >
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="em_andamento">Em andamento</option>
          <option value="concluida">Concluída</option>
          <option value="cancelada">Cancelada</option>
        </Select>
        <div className="ml-auto">
          <Link href="/os/nova">
            <Button>
              <Plus className="h-4 w-4" /> Nova OS
            </Button>
          </Link>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Problema</th>
                <th className="px-4 py-3">Endereço</th>
                <th className="px-4 py-3">Criada</th>
                <th className="px-4 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-muted-foreground">
                    Nenhuma OS
                  </td>
                </tr>
              )}
              {data.items.map((o: OsListItem) => (
                <tr key={o.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link href={`/os/${o.id}`} className="font-medium hover:underline">
                      {o.codigo}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANTS[o.status] ?? 'outline'}>
                      {o.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate">{o.problema}</td>
                  <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">
                    {o.endereco}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(o.criada_em).toLocaleString('pt-BR')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {o.status !== 'concluida' && o.status !== 'cancelada' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => setReatribuirOsId(o.id)}
                          title="Reatribuir técnico"
                        >
                          <UserCog className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      <DeleteButton osId={o.id} />
                    </div>
                  </td>
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

- [ ] **Verify TypeScript compiles**

```bash
cd apps/dashboard && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Commit**

```bash
git add apps/dashboard/components/os-list.tsx apps/dashboard/components/dialog-reatribuir-tecnico.tsx
git commit -m "feat(dashboard): os-list with reatribuir + delete actions"
```

---

## Task 12: dialog-abrir-os-from-conversa

**Files:**
- Create: `apps/dashboard/components/dialog-abrir-os-from-conversa.tsx`

- [ ] **Create dialog-abrir-os-from-conversa.tsx**

```typescript
'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useCreateOs, useConversa, useTecnicos } from '@/lib/api/queries'
import type { ClienteEmbutido } from '@/lib/api/types'

const schema = z.object({
  tecnico_id: z.string().uuid('Selecione o técnico responsável'),
  problema: z.string().min(1, 'Obrigatório').max(2000),
  endereco: z.string().min(1, 'Obrigatório').max(500),
  agendamento_at: z.string().optional().nullable(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  conversaId: string
  onClose: () => void
}

export function DialogAbrirOsFromConversa({ conversaId, onClose }: Props) {
  const router = useRouter()
  const { data: conversa } = useConversa(conversaId)
  const createOs = useCreateOs()
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const cliente: ClienteEmbutido | null = conversa?.cliente ?? null

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      endereco: cliente?.endereco ?? '',
    },
  })

  async function onSubmit(values: FormValues) {
    if (!conversa?.cliente_id) return
    const created = await createOs.mutateAsync({
      cliente_id: conversa.cliente_id,
      tecnico_id: values.tecnico_id,
      problema: values.problema,
      endereco: values.endereco,
      agendamento_at: values.agendamento_at || null,
    })
    onClose()
    router.push(`/os/${created.id}`)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <h2 className="text-lg font-semibold">Abrir OS</h2>

        {cliente && (
          <div className="rounded-md bg-muted p-3 text-sm space-y-1">
            <p><span className="font-medium">Cliente:</span> {cliente.nome}</p>
            {cliente.whatsapp && <p><span className="font-medium">WhatsApp:</span> {cliente.whatsapp}</p>}
            {cliente.plano && <p><span className="font-medium">Plano:</span> {cliente.plano}</p>}
            {cliente.cidade && <p><span className="font-medium">Cidade:</span> {cliente.cidade}</p>}
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label htmlFor="tecnico_id">Técnico responsável *</Label>
            <Select id="tecnico_id" {...register('tecnico_id')} defaultValue="">
              <option value="" disabled>Selecione o técnico responsável</option>
              {tecnicos?.items.map((t) => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </Select>
            {errors.tecnico_id && (
              <p className="mt-1 text-xs text-destructive">{errors.tecnico_id.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="problema">Problema *</Label>
            <Textarea id="problema" {...register('problema')} placeholder="Descreva o problema…" />
            {errors.problema && (
              <p className="mt-1 text-xs text-destructive">{errors.problema.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="endereco">Endereço *</Label>
            <Input
              id="endereco"
              {...register('endereco')}
              defaultValue={cliente?.endereco ?? ''}
            />
            {errors.endereco && (
              <p className="mt-1 text-xs text-destructive">{errors.endereco.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="agendamento_at">Agendamento (opcional)</Label>
            <Input id="agendamento_at" type="datetime-local" {...register('agendamento_at')} />
          </div>
          {createOs.error && (
            <p className="text-xs text-destructive">
              {createOs.error instanceof Error ? createOs.error.message : 'Erro ao criar OS'}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting || !conversa?.cliente_id}>
              {isSubmitting ? 'Criando…' : 'Abrir OS'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Verify TypeScript compiles**

```bash
cd apps/dashboard && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Commit**

```bash
git add apps/dashboard/components/dialog-abrir-os-from-conversa.tsx
git commit -m "feat(dashboard): dialog-abrir-os-from-conversa with client pre-fill"
```

---

## Task 13: conversa-chat — OS alert + Abrir OS button

**Files:**
- Modify: `apps/dashboard/components/conversa-chat.tsx`

- [ ] **Update conversa-chat.tsx**

Replace full content of `apps/dashboard/components/conversa-chat.tsx`:

```typescript
'use client'
import { useEffect, useRef, useState } from 'react'
import { Send, UserCheck, Wrench, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  useAtender,
  useConversa,
  useEncerrar,
  useOsList,
  useResponder,
} from '@/lib/api/queries'
import type { MensagemOut } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { DialogAbrirOsFromConversa } from './dialog-abrir-os-from-conversa'

interface SseEvent {
  type: string
  id?: string
  role?: string
  text?: string | null
  ts?: string | null
}

const ROLE_LABEL: Record<string, string> = {
  cliente: 'Cliente',
  bot: 'Bot',
  atendente: 'Atendente',
}

const OS_STATUS_ABERTA = ['pendente', 'em_andamento']

export function ConversaChat({ conversaId }: { conversaId: string }) {
  const { data, isLoading, refetch } = useConversa(conversaId)
  const responder = useResponder(conversaId)
  const atender = useAtender(conversaId)
  const encerrar = useEncerrar(conversaId)
  const [text, setText] = useState('')
  const [liveMsgs, setLiveMsgs] = useState<MensagemOut[]>([])
  const [showAbrirOs, setShowAbrirOs] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const clienteId = data?.cliente_id ?? undefined
  const { data: osAberta } = useOsList(
    clienteId ? { cliente_id: clienteId } : {}
  )
  const osAbertas = (osAberta?.items ?? []).filter((o) =>
    OS_STATUS_ABERTA.includes(o.status)
  )

  useEffect(() => {
    if (!conversaId) return
    const es = new EventSource(`/api/v1/conversas/${conversaId}/stream`, {
      withCredentials: true,
    })
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data as string) as SseEvent
        if (payload.type !== 'msg' || !payload.role || !payload.text) return
        setLiveMsgs((prev) => [
          ...prev,
          {
            id: payload.id ?? `live-${Date.now()}`,
            conversa_id: conversaId,
            role: payload.role as MensagemOut['role'],
            content: payload.text ?? null,
            media_type: null,
            media_url: null,
            created_at: payload.ts ?? new Date().toISOString(),
          },
        ])
      } catch {
        // ignore malformed
      }
    }
    es.onerror = () => {}
    return () => es.close()
  }, [conversaId])

  const allMsgs = [...(data?.mensagens ?? []), ...liveMsgs]
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [allMsgs.length])

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando conversa…</p>
  }
  if (!data) {
    return <p className="text-sm text-destructive">Conversa não encontrada</p>
  }

  async function handleSend() {
    const trimmed = text.trim()
    if (!trimmed) return
    await responder.mutateAsync(trimmed)
    setText('')
    void refetch()
  }

  return (
    <div className="flex h-full flex-col gap-4">
      {showAbrirOs && (
        <DialogAbrirOsFromConversa
          conversaId={conversaId}
          onClose={() => setShowAbrirOs(false)}
        />
      )}

      {/* OS abertas alert */}
      {osAbertas.length > 0 && (
        <div className="rounded-md border border-yellow-400 bg-yellow-50 dark:bg-yellow-950/20 p-3 text-sm space-y-1">
          <p className="font-semibold text-yellow-800 dark:text-yellow-300">
            ⚠️ OS(s) em aberto para este cliente
          </p>
          {osAbertas.map((o) => (
            <p key={o.id} className="text-yellow-700 dark:text-yellow-400">
              #{o.codigo} · {o.status} · {o.problema.slice(0, 60)}
            </p>
          ))}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between rounded-md border bg-card p-4">
        <div>
          <div className="font-semibold">{data.whatsapp}</div>
          <div className="text-xs text-muted-foreground">
            Estado: {data.estado} · Status: {data.status}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowAbrirOs(true)}
            title="Abrir OS para este cliente"
          >
            <Wrench className="h-4 w-4" /> Abrir OS
          </Button>
          {data.status === 'aguardando' && (
            <Button
              size="sm"
              variant="default"
              onClick={() => atender.mutate()}
              disabled={atender.isPending}
            >
              <UserCheck className="h-4 w-4" /> Atender
            </Button>
          )}
          {data.status !== 'encerrada' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => encerrar.mutate()}
              disabled={encerrar.isPending}
            >
              <X className="h-4 w-4" /> Encerrar
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto rounded-md border bg-card p-4"
      >
        {allMsgs.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">Sem mensagens</p>
        )}
        {allMsgs.map((m) => (
          <div
            key={m.id}
            className={cn(
              'max-w-[70%] rounded-lg px-3 py-2 text-sm',
              m.role === 'cliente'
                ? 'bg-muted'
                : m.role === 'bot'
                ? 'ml-auto bg-secondary text-secondary-foreground'
                : 'ml-auto bg-primary text-primary-foreground',
            )}
          >
            <div className="mb-1 flex items-center gap-2 text-xs opacity-70">
              <Badge variant="outline" className="capitalize">
                {ROLE_LABEL[m.role] ?? m.role}
              </Badge>
              <span>{new Date(m.created_at).toLocaleTimeString('pt-BR')}</span>
            </div>
            <div className="whitespace-pre-wrap">{m.content}</div>
          </div>
        ))}
      </div>

      {/* Composer */}
      {data.status !== 'encerrada' && (
        <div className="rounded-md border bg-card p-3">
          <Textarea
            placeholder="Digite sua resposta…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault()
                void handleSend()
              }
            }}
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Ctrl/Cmd + Enter para enviar</span>
            <Button
              onClick={() => void handleSend()}
              disabled={responder.isPending || !text.trim()}
            >
              <Send className="h-4 w-4" /> Enviar
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Update useOsList in queries.ts to accept cliente_id**

In `apps/dashboard/lib/api/queries.ts`, update `OsListFilters`:

```typescript
export interface OsListFilters {
  status?: string
  tecnico?: string
  cliente_id?: string
}
```

And update `useOsList`:

```typescript
export function useOsList(filters: OsListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.tecnico) params.set('tecnico', filters.tecnico)
  if (filters.cliente_id) params.set('cliente_id', filters.cliente_id)
  const qs = params.toString()
  return useQuery<CursorPage<OsListItem>>({
    queryKey: ['os', filters],
    queryFn: () => apiFetch(`/api/v1/os${qs ? `?${qs}` : ''}`),
    refetchInterval: 30_000,
    enabled: filters.cliente_id !== undefined ? Boolean(filters.cliente_id) : true,
  })
}
```

- [ ] **Verify TypeScript compiles**

```bash
cd apps/dashboard && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Commit**

```bash
git add apps/dashboard/components/conversa-chat.tsx apps/dashboard/lib/api/queries.ts
git commit -m "feat(dashboard): conversa-chat OS alert + Abrir OS button"
```

---

## Task 14: conversa-list — Abrir OS button

**Files:**
- Modify: `apps/dashboard/components/conversa-list.tsx`

- [ ] **Update conversa-list.tsx to add Abrir OS per row**

Replace full content of `apps/dashboard/components/conversa-list.tsx`:

```typescript
'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Wrench } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useConversas } from '@/lib/api/queries'
import { DialogAbrirOsFromConversa } from './dialog-abrir-os-from-conversa'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  bot: 'secondary',
  aguardando: 'destructive',
  humano: 'default',
  encerrada: 'outline',
}

export function ConversaList() {
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [abrirOsConversaId, setAbrirOsConversaId] = useState<string | null>(null)
  const { data, isLoading, error } = useConversas({
    status: status || undefined,
    q: q || undefined,
  })

  return (
    <div className="space-y-4">
      {abrirOsConversaId && (
        <DialogAbrirOsFromConversa
          conversaId={abrirOsConversaId}
          onClose={() => setAbrirOsConversaId(null)}
        />
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Buscar por whatsapp…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="max-w-[200px]"
        >
          <option value="">Todos os status</option>
          <option value="aguardando">Aguardando</option>
          <option value="humano">Humano</option>
          <option value="bot">Bot</option>
          <option value="encerrada">Encerrada</option>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">WhatsApp</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Última msg</th>
                <th className="px-4 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted-foreground">
                    Nenhuma conversa
                  </td>
                </tr>
              )}
              {data.items.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link href={`/conversas/${c.id}`} className="font-medium hover:underline">
                      {c.whatsapp}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANTS[c.status] ?? 'outline'}>
                      {c.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{c.estado}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.last_message_at
                      ? new Date(c.last_message_at).toLocaleString('pt-BR')
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {c.cliente_id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 gap-1 text-xs"
                        onClick={() => setAbrirOsConversaId(c.id)}
                        title="Abrir OS para este cliente"
                      >
                        <Wrench className="h-3 w-3" /> Abrir OS
                      </Button>
                    )}
                  </td>
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

- [ ] **Verify TypeScript compiles**

```bash
cd apps/dashboard && pnpm tsc --noEmit
```

Expected: No errors

- [ ] **Run full API test suite to ensure no regressions**

```bash
cd apps/api && uv run pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests PASS

- [ ] **Commit**

```bash
git add apps/dashboard/components/conversa-list.tsx
git commit -m "feat(dashboard): conversa-list Abrir OS button per row"
```

---

## Post-implementation checklist

- [ ] Confirm migration applied: `cd apps/api && uv run alembic current` → shows `0005_os_followup_reatribuicao`
- [ ] Run full API test suite: `cd apps/api && uv run pytest tests/ -v`
- [ ] Run TypeScript check: `cd apps/dashboard && pnpm tsc --noEmit`
- [ ] Manual smoke: create OS with tecnico required, reatribuir, delete, check OS alert in conversa, abrir OS from conversa
