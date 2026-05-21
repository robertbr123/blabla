# Cliente App — Fase 1: Fundação Backend + Auth Cliente

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o backend completo de autenticação do app do cliente final — registro via CPF + OTP WhatsApp, login com senha, JWT separado do staff com isolamento garantido por testes.

**Architecture:** Novo subdomínio `/api/v1/cliente-app/auth/*` no mesmo `apps/api/`. Reaproveita `db.crypto` (PII), `auth.passwords` (Argon2id), `adapters/evolution` (OTP via WhatsApp), `slowapi` (rate-limit). JWT ganha claim `kind` (`staff` ou `cliente`); deps existentes (`get_current_user`) passam a rejeitar `kind=cliente` e nova dep `get_current_cliente_user` rejeita `kind=staff`. Duas tabelas novas: `cliente_app_users` e `cliente_app_otp`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, PyJWT, passlib/argon2, slowapi, redis.asyncio, pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-05-21-cliente-mobile-app-design.md` (seções 3 e 6).

---

## File Structure

**Create:**
- `apps/api/alembic/versions/0026_cliente_app_users.py` — migration
- `apps/api/src/ondeline_api/db/models/cliente_app.py` — ORM models (ClienteAppUser, ClienteAppOtp)
- `apps/api/src/ondeline_api/repositories/cliente_app_user.py` — repo (get/create/update/list)
- `apps/api/src/ondeline_api/services/cliente_app_otp.py` — gerar/persistir/enviar/verificar OTP
- `apps/api/src/ondeline_api/auth/cliente_deps.py` — `get_current_cliente_user` + helpers
- `apps/api/src/ondeline_api/api/v1/cliente_app_auth.py` — router `/cliente-app/auth/*`
- `apps/api/src/ondeline_api/api/schemas/cliente_app_auth.py` — Pydantic models de I/O
- `apps/api/tests/test_cliente_app_auth.py` — testes E2E + isolamento de audience

**Modify:**
- `apps/api/src/ondeline_api/auth/jwt.py` — adicionar claim `kind` em encode/decode (compat: default staff)
- `apps/api/src/ondeline_api/auth/deps.py` — `get_current_user` rejeita `kind != staff`
- `apps/api/src/ondeline_api/main.py` — registrar novo router

---

## Task 1: Migration `0026_cliente_app_users`

**Files:**
- Create: `apps/api/alembic/versions/0026_cliente_app_users.py`

- [ ] **Step 1: Criar a migration**

```python
"""Cliente app users — tabela de usuarios do app do cliente final.

Separada de `users` (staff). cpf_hash unico identifica o cliente,
cpf_encrypted/nome_encrypted/telefone_encrypted seguem padrao PII do
projeto. cliente_app_otp armazena codigos efemeros (10min) com hash.

Revision ID: 0026_cliente_app_users
Revises: 0025_nome_normalized
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_cliente_app_users"
down_revision: str | None = "0025_nome_normalized"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cpf_hash", sa.String(length=64), nullable=False),
        sa.Column("cpf_last4", sa.String(length=4), nullable=False),
        sa.Column("cpf_encrypted", sa.Text(), nullable=False),
        sa.Column("nome_encrypted", sa.Text(), nullable=False),
        sa.Column("telefone_encrypted", sa.Text(), nullable=False),
        sa.Column("email_encrypted", sa.Text(), nullable=True),
        sa.Column("sgp_id", sa.String(length=64), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("push_token", sa.String(length=512), nullable=True),
        sa.Column("biometric_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending_otp'"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_cliente_app_users_cpf_hash", "cliente_app_users", ["cpf_hash"], unique=True)
    op.create_index("ix_cliente_app_users_sgp_id", "cliente_app_users", ["sgp_id"])

    op.create_table(
        "cliente_app_otp",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cpf_hash", sa.String(length=64), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),  # register|reset_pwd
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_cliente_app_otp_cpf_hash", "cliente_app_otp", ["cpf_hash"])


def downgrade() -> None:
    op.drop_index("ix_cliente_app_otp_cpf_hash", table_name="cliente_app_otp")
    op.drop_table("cliente_app_otp")
    op.drop_index("ix_cliente_app_users_sgp_id", table_name="cliente_app_users")
    op.drop_index("ix_cliente_app_users_cpf_hash", table_name="cliente_app_users")
    op.drop_table("cliente_app_users")
```

- [ ] **Step 2: Rodar a migration localmente**

```bash
cd apps/api && uv run alembic upgrade head
```
Expected: `Running upgrade 0025_nome_normalized -> 0026_cliente_app_users`.

- [ ] **Step 3: Commit**

```bash
git add apps/api/alembic/versions/0026_cliente_app_users.py
git commit -m "feat(cliente-app): migration 0026 - cliente_app_users + cliente_app_otp"
```

---

## Task 2: ORM Models

**Files:**
- Create: `apps/api/src/ondeline_api/db/models/cliente_app.py`

- [ ] **Step 1: Criar models**

```python
"""ORM models para o app do cliente final."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ondeline_api.db.base import Base


class ClienteAppUser(Base):
    __tablename__ = "cliente_app_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpf_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    cpf_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    cpf_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    nome_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    telefone_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    email_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    sgp_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    push_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    biometric_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending_otp")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ClienteAppOtp(Base):
    __tablename__ = "cliente_app_otp"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
```

- [ ] **Step 2: Garantir import no `db/models/__init__.py`**

Adicionar linha no `apps/api/src/ondeline_api/db/models/__init__.py`:

```python
from ondeline_api.db.models.cliente_app import ClienteAppOtp, ClienteAppUser  # noqa: F401
```

- [ ] **Step 3: Verificar que importa sem erro**

```bash
cd apps/api && uv run python -c "from ondeline_api.db.models.cliente_app import ClienteAppUser; print(ClienteAppUser.__tablename__)"
```
Expected: `cliente_app_users`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/db/models/cliente_app.py apps/api/src/ondeline_api/db/models/__init__.py
git commit -m "feat(cliente-app): ORM models ClienteAppUser + ClienteAppOtp"
```

---

## Task 3: JWT — adicionar claim `kind`

**Files:**
- Modify: `apps/api/src/ondeline_api/auth/jwt.py`
- Modify: `apps/api/src/ondeline_api/auth/deps.py`
- Test: `apps/api/tests/test_jwt_kind.py` (criar)

- [ ] **Step 1: Escrever teste falhante de isolamento**

Criar `apps/api/tests/test_jwt_kind.py`:

```python
"""JWT — claim `kind` separa staff de cliente."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.auth import jwt as jwt_mod


def test_staff_token_default_kind_staff() -> None:
    uid = uuid4()
    tok = jwt_mod.encode_access_token(uid, role="admin")
    payload = jwt_mod.decode_access_token(tok)
    assert payload["kind"] == "staff"
    assert payload["sub"] == str(uid)


def test_cliente_token_has_kind_cliente() -> None:
    uid = uuid4()
    tok = jwt_mod.encode_cliente_access_token(uid)
    payload = jwt_mod.decode_cliente_access_token(tok)
    assert payload["kind"] == "cliente"


def test_decode_cliente_rejects_staff_token() -> None:
    uid = uuid4()
    staff_tok = jwt_mod.encode_access_token(uid, role="admin")
    with pytest.raises(jwt_mod.InvalidTokenKind):
        jwt_mod.decode_cliente_access_token(staff_tok)


def test_decode_staff_rejects_cliente_token() -> None:
    uid = uuid4()
    cliente_tok = jwt_mod.encode_cliente_access_token(uid)
    with pytest.raises(jwt_mod.InvalidTokenKind):
        jwt_mod.decode_access_token(cliente_tok)
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd apps/api && uv run pytest tests/test_jwt_kind.py -x
```
Expected: FAIL (`AttributeError` em `encode_cliente_access_token`).

- [ ] **Step 3: Implementar no `auth/jwt.py`**

Adicionar no topo do arquivo após a classe `TokenExpired`:

```python
class InvalidTokenKind(InvalidToken):
    pass
```

Modificar `encode_access_token` para incluir `kind`:

```python
def encode_access_token(user_id: UUID, role: str) -> str:
    settings = get_settings()
    iat = _now()
    exp = iat + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "kind": "staff",
        "type": "access",
        "jti": str(uuid4()),
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO)
```

Adicionar no fim do arquivo:

```python
def encode_cliente_access_token(user_id: UUID) -> str:
    settings = get_settings()
    iat = _now()
    # TTL bem mais longo pro app do cliente — UX de banco
    exp = iat + timedelta(days=30)
    payload = {
        "sub": str(user_id),
        "kind": "cliente",
        "type": "access",
        "jti": str(uuid4()),
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO)


def _decode_with_kind(token: str, expected_kind: str) -> dict[str, Any]:
    payload = _decode(token, "access")
    if payload.get("kind") != expected_kind:
        raise InvalidTokenKind(
            f"expected kind={expected_kind}, got {payload.get('kind')}"
        )
    return payload


def decode_cliente_access_token(token: str) -> dict[str, Any]:
    return _decode_with_kind(token, "cliente")
```

Modificar `decode_access_token` para exigir `kind=staff`:

```python
def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_with_kind(token, "staff")
```

- [ ] **Step 4: Rodar testes do jwt — devem passar**

```bash
cd apps/api && uv run pytest tests/test_jwt_kind.py -x
```
Expected: 4 passed.

- [ ] **Step 5: Rodar suite de auth para garantir compat**

```bash
cd apps/api && uv run pytest tests/test_auth_login.py tests/test_auth_refresh_logout.py tests/test_auth_me_rbac.py -x
```
Expected: all green (tokens existentes mantém compat porque `encode_access_token` continua emitindo `kind=staff` por padrão).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/auth/jwt.py apps/api/tests/test_jwt_kind.py
git commit -m "feat(auth): claim 'kind' separa tokens staff de cliente"
```

---

## Task 4: Repositório `cliente_app_user`

**Files:**
- Create: `apps/api/src/ondeline_api/repositories/cliente_app_user.py`

- [ ] **Step 1: Implementar repo**

```python
"""Repositorio para ClienteAppUser."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser


def _cpf_clean(cpf: str) -> str:
    return "".join(c for c in cpf if c.isdigit())


async def get_by_cpf_hash(session: AsyncSession, cpf_hash: str) -> ClienteAppUser | None:
    stmt = select(ClienteAppUser).where(ClienteAppUser.cpf_hash == cpf_hash)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: UUID) -> ClienteAppUser | None:
    return await session.get(ClienteAppUser, user_id)


async def create_pending(
    session: AsyncSession,
    *,
    cpf: str,
    nome: str,
    telefone: str,
    sgp_id: str | None,
    email: str | None = None,
) -> ClienteAppUser:
    cpf_digits = _cpf_clean(cpf)
    if len(cpf_digits) != 11:
        raise ValueError("CPF must have 11 digits")
    user = ClienteAppUser(
        cpf_hash=hash_pii(cpf_digits),
        cpf_last4=cpf_digits[-4:],
        cpf_encrypted=encrypt_pii(cpf_digits),
        nome_encrypted=encrypt_pii(nome),
        telefone_encrypted=encrypt_pii(telefone),
        email_encrypted=encrypt_pii(email) if email else None,
        sgp_id=sgp_id,
        status="pending_otp",
    )
    session.add(user)
    await session.flush()
    return user


async def set_password(session: AsyncSession, user: ClienteAppUser, password_hash: str) -> None:
    user.password_hash = password_hash
    user.status = "active"
    await session.flush()


async def mark_login(session: AsyncSession, user: ClienteAppUser) -> None:
    user.last_login_at = datetime.now(UTC)
    await session.flush()
```

- [ ] **Step 2: Smoke test de import**

```bash
cd apps/api && uv run python -c "from ondeline_api.repositories.cliente_app_user import create_pending; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/cliente_app_user.py
git commit -m "feat(cliente-app): repositorio ClienteAppUser"
```

---

## Task 5: Service de OTP

**Files:**
- Create: `apps/api/src/ondeline_api/services/cliente_app_otp.py`

- [ ] **Step 1: Implementar service**

```python
"""OTP via WhatsApp para auth do app cliente.

- Gera codigo numerico 6 digitos.
- Persiste como hash + expires_at (10min).
- Manda via EvolutionAdapter (mesma instancia do bot).
- Verifica com tolerancia de 5 tentativas antes de invalidar.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.db.models.cliente_app import ClienteAppOtp

OTP_TTL_MIN = 10
OTP_MAX_ATTEMPTS = 5


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


async def issue(
    session: AsyncSession,
    *,
    cpf_hash: str,
    telefone: str,
    purpose: str,
    evolution: EvolutionAdapter,
) -> None:
    """Gera, persiste e envia OTP. Idempotente: invalida OTPs anteriores."""
    # Invalida pendentes anteriores
    stmt = select(ClienteAppOtp).where(
        ClienteAppOtp.cpf_hash == cpf_hash,
        ClienteAppOtp.purpose == purpose,
        ClienteAppOtp.consumed_at.is_(None),
    )
    for old in (await session.execute(stmt)).scalars():
        old.consumed_at = datetime.now(UTC)

    code = f"{secrets.randbelow(1_000_000):06d}"
    otp = ClienteAppOtp(
        cpf_hash=cpf_hash,
        code_hash=_hash_code(code),
        purpose=purpose,
        expires_at=datetime.now(UTC) + timedelta(minutes=OTP_TTL_MIN),
    )
    session.add(otp)
    await session.flush()

    jid = _digits(telefone)
    if not jid.startswith("55"):
        jid = "55" + jid
    jid = jid + "@s.whatsapp.net"

    await evolution.send_text(
        jid,
        (
            f"Ondeline: seu codigo de acesso e *{code}*. "
            f"Valido por {OTP_TTL_MIN} minutos. "
            f"Se voce nao solicitou, ignore esta mensagem."
        ),
    )


class OtpInvalid(Exception):
    pass


class OtpExpired(OtpInvalid):
    pass


class OtpExhausted(OtpInvalid):
    pass


async def verify(session: AsyncSession, *, cpf_hash: str, code: str, purpose: str) -> None:
    stmt = (
        select(ClienteAppOtp)
        .where(
            ClienteAppOtp.cpf_hash == cpf_hash,
            ClienteAppOtp.purpose == purpose,
            ClienteAppOtp.consumed_at.is_(None),
        )
        .order_by(desc(ClienteAppOtp.created_at))
        .limit(1)
    )
    otp = (await session.execute(stmt)).scalar_one_or_none()
    if otp is None:
        raise OtpInvalid("no active otp")

    if otp.expires_at < datetime.now(UTC):
        otp.consumed_at = datetime.now(UTC)
        await session.flush()
        raise OtpExpired("otp expired")

    if otp.attempts >= OTP_MAX_ATTEMPTS:
        otp.consumed_at = datetime.now(UTC)
        await session.flush()
        raise OtpExhausted("too many attempts")

    if otp.code_hash != _hash_code(code):
        otp.attempts += 1
        await session.flush()
        raise OtpInvalid("wrong code")

    otp.consumed_at = datetime.now(UTC)
    await session.flush()
```

- [ ] **Step 2: Smoke import**

```bash
cd apps/api && uv run python -c "from ondeline_api.services.cliente_app_otp import issue, verify, OtpInvalid; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/services/cliente_app_otp.py
git commit -m "feat(cliente-app): service de OTP via WhatsApp"
```

---

## Task 6: Dep `get_current_cliente_user`

**Files:**
- Create: `apps/api/src/ondeline_api/auth/cliente_deps.py`

- [ ] **Step 1: Implementar**

```python
"""FastAPI deps para usuario do app cliente."""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    return auth.removeprefix("Bearer ").strip()


async def get_current_cliente_user(
    request: Request,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ClienteAppUser:
    token = _bearer(request)
    try:
        payload = jwt_mod.decode_cliente_access_token(token)
    except jwt_mod.TokenExpired:
        raise HTTPException(status_code=401, detail="token expired") from None
    except jwt_mod.InvalidTokenKind:
        raise HTTPException(status_code=401, detail="invalid token kind") from None
    except jwt_mod.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = await session.get(ClienteAppUser, UUID(payload["sub"]))
    if user is None or user.status != "active":
        raise HTTPException(status_code=401, detail="user inactive or unknown")
    return user
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/auth/cliente_deps.py
git commit -m "feat(cliente-app): dep get_current_cliente_user"
```

---

## Task 7: Schemas Pydantic

**Files:**
- Create: `apps/api/src/ondeline_api/api/schemas/cliente_app_auth.py`

- [ ] **Step 1: Implementar**

```python
"""Pydantic schemas para /cliente-app/auth/*."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _cpf_digits(v: str) -> str:
    return "".join(c for c in v if c.isdigit())


class RegisterStartIn(BaseModel):
    cpf: str

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        digits = _cpf_digits(v)
        if len(digits) != 11:
            raise ValueError("cpf invalido")
        return digits


class RegisterStartOut(BaseModel):
    masked_phone: str  # ex: "(92) ****-1234"


class RegisterVerifyIn(BaseModel):
    cpf: str
    code: str = Field(min_length=6, max_length=6)

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        digits = _cpf_digits(v)
        if len(digits) != 11:
            raise ValueError("cpf invalido")
        return digits


class RegisterVerifyOut(BaseModel):
    setup_token: str  # JWT curto (10min) que autoriza POST /register/password


class RegisterPasswordIn(BaseModel):
    setup_token: str
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    cpf: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        digits = _cpf_digits(v)
        if len(digits) != 11:
            raise ValueError("cpf invalido")
        return digits


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class ForgotIn(BaseModel):
    cpf: str

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        digits = _cpf_digits(v)
        if len(digits) != 11:
            raise ValueError("cpf invalido")
        return digits
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/cliente_app_auth.py
git commit -m "feat(cliente-app): schemas Pydantic de auth"
```

---

## Task 8: Router `/cliente-app/auth/*`

**Files:**
- Create: `apps/api/src/ondeline_api/api/v1/cliente_app_auth.py`

- [ ] **Step 1: Helper de setup_token (token efêmero pra fluxo de cadastro)**

No topo do mesmo arquivo do router. Implementação inline (não vale criar módulo só pra isso):

```python
"""Router /api/v1/cliente-app/auth/* — registro, OTP, login.

Setup token: JWT curto (10min) entre `register/verify` e `register/password`
para evitar criar usuario sem senha em estado pendente persistido.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.api.schemas.cliente_app_auth import (
    ForgotIn,
    LoginIn,
    RegisterPasswordIn,
    RegisterStartIn,
    RegisterStartOut,
    RegisterVerifyIn,
    RegisterVerifyOut,
    TokenOut,
)
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.passwords import hash_password, verify_password
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db, get_evolution_adapter
from ondeline_api.repositories import cliente_app_user as repo
from ondeline_api.services import cliente_app_otp as otp_svc
from ondeline_api.services.sgp_cache import get_or_fetch_cliente_by_cpf

router = APIRouter(prefix="/cliente-app/auth", tags=["cliente-app:auth"])
limiter = Limiter(key_func=get_remote_address)

SETUP_TTL_MIN = 10


def _setup_token(cpf_hash: str) -> str:
    secret = get_settings().jwt_secret.get_secret_value()
    iat = datetime.now(UTC)
    payload = {
        "cpf_hash": cpf_hash,
        "purpose": "register_setup",
        "iat": int(iat.timestamp()),
        "exp": int((iat + timedelta(minutes=SETUP_TTL_MIN)).timestamp()),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _decode_setup(token: str) -> dict[str, Any]:
    secret = get_settings().jwt_secret.get_secret_value()
    try:
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="setup token expired") from None
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=400, detail="invalid setup token") from None
    if payload.get("purpose") != "register_setup":
        raise HTTPException(status_code=400, detail="invalid setup purpose")
    return payload


def _mask_phone(telefone: str) -> str:
    digits = "".join(c for c in telefone if c.isdigit())
    if len(digits) < 4:
        return "****"
    return f"****-{digits[-4:]}"
```

- [ ] **Step 2: Endpoint `register/start`**

Continuar no mesmo arquivo:

```python
@router.post("/register/start", response_model=RegisterStartOut)
@limiter.limit("5/hour")
async def register_start(
    request: Request,  # noqa: ARG001 — usado pelo slowapi
    body: RegisterStartIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    evolution: EvolutionAdapter = Depends(get_evolution_adapter),  # noqa: B008
) -> RegisterStartOut:
    cpf_hash = hash_pii(body.cpf)
    user = await repo.get_by_cpf_hash(session, cpf_hash)

    if user and user.status == "active":
        # Ja cadastrado — nao revela; mas tambem nao gasta OTP.
        # Cliente que esqueceu senha usa /auth/forgot.
        raise HTTPException(status_code=409, detail="usuario ja cadastrado")

    if user is None:
        # Busca no SGP pra obter telefone e nome
        sgp_cliente = await get_or_fetch_cliente_by_cpf(session, body.cpf)
        if sgp_cliente is None:
            # Resposta generica pra nao revelar quem e/nao e cliente
            raise HTTPException(status_code=404, detail="cpf nao encontrado")
        nome = sgp_cliente.nome
        telefone = sgp_cliente.telefone
        sgp_id = sgp_cliente.sgp_id
        user = await repo.create_pending(
            session,
            cpf=body.cpf,
            nome=nome,
            telefone=telefone,
            sgp_id=sgp_id,
        )
    else:
        telefone = decrypt_pii(user.telefone_encrypted)

    await otp_svc.issue(
        session,
        cpf_hash=cpf_hash,
        telefone=telefone,
        purpose="register",
        evolution=evolution,
    )
    await session.commit()
    return RegisterStartOut(masked_phone=_mask_phone(telefone))
```

- [ ] **Step 3: Endpoint `register/verify`**

```python
@router.post("/register/verify", response_model=RegisterVerifyOut)
@limiter.limit("10/hour")
async def register_verify(
    request: Request,  # noqa: ARG001
    body: RegisterVerifyIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> RegisterVerifyOut:
    cpf_hash = hash_pii(body.cpf)
    try:
        await otp_svc.verify(session, cpf_hash=cpf_hash, code=body.code, purpose="register")
    except otp_svc.OtpExpired:
        await session.commit()
        raise HTTPException(status_code=400, detail="codigo expirado") from None
    except otp_svc.OtpExhausted:
        await session.commit()
        raise HTTPException(status_code=400, detail="muitas tentativas") from None
    except otp_svc.OtpInvalid:
        await session.commit()
        raise HTTPException(status_code=400, detail="codigo invalido") from None
    await session.commit()
    return RegisterVerifyOut(setup_token=_setup_token(cpf_hash))
```

- [ ] **Step 4: Endpoint `register/password`**

```python
@router.post("/register/password", response_model=TokenOut)
@limiter.limit("10/hour")
async def register_password(
    request: Request,  # noqa: ARG001
    body: RegisterPasswordIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenOut:
    payload = _decode_setup(body.setup_token)
    cpf_hash = payload["cpf_hash"]
    user = await repo.get_by_cpf_hash(session, cpf_hash)
    if user is None:
        raise HTTPException(status_code=400, detail="setup invalido")

    await repo.set_password(session, user, hash_password(body.password))
    await repo.mark_login(session, user)
    await session.commit()

    access = jwt_mod.encode_cliente_access_token(user.id)
    return TokenOut(access_token=access, expires_in_seconds=30 * 86400)
```

- [ ] **Step 5: Endpoint `login`**

```python
@router.post("/login", response_model=TokenOut)
@limiter.limit("10/hour")
async def login(
    request: Request,  # noqa: ARG001
    body: LoginIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenOut:
    cpf_hash = hash_pii(body.cpf)
    user = await repo.get_by_cpf_hash(session, cpf_hash)
    # Sempre rodar verify mesmo se user nao existir, pra evitar timing attack
    valid_hash = user.password_hash if (user and user.password_hash) else "$argon2id$v=19$m=65536,t=3,p=4$invalid$invalid"
    ok = verify_password(body.password, valid_hash)
    if user is None or not user.password_hash or user.status != "active" or not ok:
        await session.commit()
        raise HTTPException(status_code=401, detail="credenciais invalidas")

    await repo.mark_login(session, user)
    await session.commit()
    access = jwt_mod.encode_cliente_access_token(user.id)
    return TokenOut(access_token=access, expires_in_seconds=30 * 86400)
```

- [ ] **Step 6: Endpoint `forgot`**

```python
@router.post("/forgot", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/hour")
async def forgot(
    request: Request,  # noqa: ARG001
    body: ForgotIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    evolution: EvolutionAdapter = Depends(get_evolution_adapter),  # noqa: B008
) -> dict[str, str]:
    cpf_hash = hash_pii(body.cpf)
    user = await repo.get_by_cpf_hash(session, cpf_hash)
    # Resposta sempre 202 — nao revelamos se CPF existe
    if user is not None and user.status == "active":
        telefone = decrypt_pii(user.telefone_encrypted)
        await otp_svc.issue(
            session,
            cpf_hash=cpf_hash,
            telefone=telefone,
            purpose="reset_pwd",
            evolution=evolution,
        )
    await session.commit()
    return {"status": "ok"}
```

- [ ] **Step 7: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/cliente_app_auth.py
git commit -m "feat(cliente-app): router /cliente-app/auth/* (register, login, forgot)"
```

---

## Task 9: Wire do router no `main.py`

**Files:**
- Modify: `apps/api/src/ondeline_api/main.py`

- [ ] **Step 1: Localizar onde routers v1 são incluídos**

```bash
grep -n "include_router\|api/v1" apps/api/src/ondeline_api/main.py
```

- [ ] **Step 2: Importar e incluir o novo router**

No topo do `main.py`, junto com os outros imports de `api.v1`:

```python
from ondeline_api.api.v1 import cliente_app_auth as cliente_app_auth_router
```

Onde os routers v1 são incluídos (procure `include_router` que use prefix `/api/v1`):

```python
app.include_router(cliente_app_auth_router.router, prefix="/api/v1")
```

- [ ] **Step 3: Smoke test — app sobe**

```bash
cd apps/api && uv run python -c "from ondeline_api.main import create_app; a = create_app(); print([r.path for r in a.routes if 'cliente-app' in r.path])"
```
Expected: lista contendo `/api/v1/cliente-app/auth/register/start`, `/login`, etc.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/main.py
git commit -m "feat(cliente-app): registra router de auth no main"
```

---

## Task 10: Teste E2E + isolamento de audience

**Files:**
- Create: `apps/api/tests/test_cliente_app_auth.py`

- [ ] **Step 1: Escrever o teste E2E**

```python
"""E2E cliente-app: register, login e ISOLAMENTO de audience.

O teste de isolamento e a garantia critica da fase: token cliente NUNCA
pode acessar endpoints staff, e token staff NUNCA pode acessar
endpoints cliente.
"""
from __future__ import annotations

import collections.abc
import os
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.db.crypto import hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppOtp, ClienteAppUser
from ondeline_api.deps import get_db, get_evolution_adapter, get_redis
from ondeline_api.main import create_app
from ondeline_api.services import cliente_app_otp as otp_svc
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/0")

# CPF de teste (DV valido — calcular ou usar conhecido)
TEST_CPF = "11144477735"


class FakeEvolution:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, jid: str, text: str) -> dict[str, Any]:
        self.sent.append((jid, text))
        return {"status": "ok"}


@pytest_asyncio.fixture
async def redis_client() -> collections.abc.AsyncIterator[Redis]:
    client: Redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def fake_evolution() -> FakeEvolution:
    return FakeEvolution()


@pytest.fixture
def app(
    db_session: AsyncSession,
    redis_client: Redis,
    fake_evolution: FakeEvolution,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    async def _override_evolution() -> EvolutionAdapter:
        return fake_evolution  # type: ignore[return-value]

    # Mock SGP cache pra retornar nome+telefone+sgp_id
    async def _fake_sgp(_session: AsyncSession, _cpf: str) -> Any:
        class _Stub:
            nome = "Cliente Teste"
            telefone = "92981234567"
            sgp_id = "12345"
        return _Stub()

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_auth.get_or_fetch_cliente_by_cpf",
        _fake_sgp,
    )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_evolution_adapter] = _override_evolution
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> collections.abc.AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_full_register_and_login(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_evolution: FakeEvolution,
) -> None:
    # 1. register/start
    r = await client.post("/api/v1/cliente-app/auth/register/start", json={"cpf": TEST_CPF})
    assert r.status_code == 200, r.text
    assert "****" in r.json()["masked_phone"]
    assert len(fake_evolution.sent) == 1
    sent_text = fake_evolution.sent[0][1]

    # Extrai o codigo da mensagem (formato "*123456*")
    import re

    m = re.search(r"\*(\d{6})\*", sent_text)
    assert m, f"codigo nao encontrado em: {sent_text}"
    code = m.group(1)

    # 2. register/verify
    r = await client.post(
        "/api/v1/cliente-app/auth/register/verify",
        json={"cpf": TEST_CPF, "code": code},
    )
    assert r.status_code == 200, r.text
    setup_token = r.json()["setup_token"]

    # 3. register/password
    r = await client.post(
        "/api/v1/cliente-app/auth/register/password",
        json={"setup_token": setup_token, "password": "SenhaForte123!"},
    )
    assert r.status_code == 200, r.text
    access1 = r.json()["access_token"]
    payload = jwt_mod.decode_cliente_access_token(access1)
    assert payload["kind"] == "cliente"

    # 4. login com a senha
    r = await client.post(
        "/api/v1/cliente-app/auth/login",
        json={"cpf": TEST_CPF, "password": "SenhaForte123!"},
    )
    assert r.status_code == 200, r.text
    access2 = r.json()["access_token"]
    assert jwt_mod.decode_cliente_access_token(access2)["kind"] == "cliente"

    # 5. login com senha errada — 401
    r = await client.post(
        "/api/v1/cliente-app/auth/login",
        json={"cpf": TEST_CPF, "password": "errada123"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_register_start_unknown_cpf_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _none(_s, _c) -> None:
        return None

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_auth.get_or_fetch_cliente_by_cpf", _none
    )
    r = await client.post(
        "/api/v1/cliente-app/auth/register/start", json={"cpf": "12345678909"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_isolation_cliente_token_rejected_by_staff_endpoint(
    client: AsyncClient,
) -> None:
    """Token de cliente NUNCA pode acessar endpoint staff."""
    cliente_token = jwt_mod.encode_cliente_access_token(uuid4())
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {cliente_token}"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_isolation_staff_token_rejected_by_cliente_endpoint(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Token de staff NUNCA pode acessar endpoint cliente-app.

    Usa /me do cliente-app — mas ele ainda nao existe na Fase 1. Em
    vez disso, valida via decode direto. Quando /me for criado na
    Fase 3, este teste vira request HTTP."""
    staff_token = jwt_mod.encode_access_token(uuid4(), role="admin")
    with pytest.raises(jwt_mod.InvalidTokenKind):
        jwt_mod.decode_cliente_access_token(staff_token)
```

- [ ] **Step 2: Rodar o teste — deve passar**

```bash
cd apps/api && uv run pytest tests/test_cliente_app_auth.py -x -v
```
Expected: 4 passed.

- [ ] **Step 3: Rodar suite full pra garantir que nada quebrou**

```bash
cd apps/api && uv run pytest -x
```
Expected: tudo verde.

- [ ] **Step 4: Lint + types**

```bash
cd apps/api && uv run ruff check . && uv run mypy src
```
Expected: clean (ou apenas erros pré-existentes).

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_cliente_app_auth.py
git commit -m "test(cliente-app): E2E register+login + isolamento de audience"
```

---

## Pontos de atenção para o executor

1. **`get_or_fetch_cliente_by_cpf`**: confira o caminho real desse helper em `services/sgp_cache.py` ou similar. Se o nome divergir, ajuste o import na Task 8 e no monkeypatch da Task 10 pra refletir a localização exata, mantendo a mesma assinatura (recebe `session` e `cpf`, retorna objeto com `nome`/`telefone`/`sgp_id` ou `None`).

2. **`get_evolution_adapter`**: idem — confirme nome em `deps.py`. Se não existir uma dep pronta, criar uma simples retornando `EvolutionAdapter` do container/settings.

3. **CPF de teste `11144477735`** tem DVs válidos. Se o sistema usar `cpf_validator` em algum lugar do pipeline, mantém esse valor.

4. **CSP/CORS**: não tocamos nesta fase. O app Flutter chama via Dio com `Authorization: Bearer ...` direto — sem cookies, sem CSRF.

5. **Migration `down_revision`**: confirme com `alembic history` que o head atual é `0025_nome_normalized` antes de rodar a Task 1. Se outra migration entrou no meio, ajuste.

6. **slowapi**: o app deve ter o `Limiter` global registrado em `main.py` (`app.state.limiter = limiter`). Se o `limiter` local do router não estiver herdando, registrar explicitamente. Caso o setup atual em `webhook.py` use um limiter global no `state`, importe e use o mesmo.

7. **DB session em testes**: o fixture `db_session` deve existir em `conftest.py` (visto em `test_auth_login.py`). Se a session for por-teste com rollback, OK; se for compartilhada, o teste E2E pode precisar de cleanup manual de `ClienteAppUser`/`ClienteAppOtp` no final.
