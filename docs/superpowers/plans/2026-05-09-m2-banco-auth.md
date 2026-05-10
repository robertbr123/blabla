# M2 — Banco + Auth: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o schema completo do Postgres com migrações Alembic, criptografia de PII (Fernet + HMAC), e auth completo (login/refresh/logout/me, RBAC, audit_log, lockout, CSRF) sobre a fundação do M1.

**Architecture:** SQLAlchemy 2.x async (asyncpg) substitui o pool placeholder do M1. Alembic com `env.py` async-aware. Modelos divididos em `db/models/identity.py` (User/Session/AuditLog) e `db/models/business.py` (clientes, conversas, mensagens particionada, OS, etc). Crypto isolado em `db/crypto.py`. Auth modular em `auth/` (passwords, jwt, lockout, rbac, csrf, audit). Endpoints REST sob `/auth/*`. Tokens em cookie HttpOnly + double-submit CSRF para state-changing. Lockout de 5 tentativas/15min via Redis.

**Tech Stack:** SQLAlchemy 2.x (async), asyncpg, Alembic 1.13+, passlib[argon2], PyJWT, cryptography (Fernet), redis-py, FastAPI dependency injection, pytest-asyncio. Postgres 16 (do M1).

**Pré-requisitos (do M1):**
- Tag `m1-fundacao` aplicada e CI verde
- `apps/api` package instalável via venv local com `pip install -e ".[dev]"`
- docker-compose dev sobe Postgres em 5433 e Redis em 6380 (host)
- Settings em `ondeline_api.config` carrega `JWT_SECRET`, `PII_ENCRYPTION_KEY`, `PII_HASH_PEPPER` do `.env`

---

## File Structure (criados/modificados neste M2)

```
apps/api/
├── pyproject.toml                             # MODIFY — add deps
├── alembic.ini                                # NEW
├── alembic/                                   # NEW
│   ├── env.py                                 # async-aware
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py             # initial migration
├── src/ondeline_api/
│   ├── config.py                              # MODIFY — add token TTLs + cookie config
│   ├── deps.py                                # MODIFY — replace asyncpg pool by SQLAlchemy session
│   ├── main.py                                # MODIFY — register auth router + CSRF middleware
│   ├── api/
│   │   ├── auth.py                            # NEW — /auth/login, /refresh, /logout, /me
│   │   └── health.py                          # MODIFY — adapt to SQLAlchemy session
│   ├── db/
│   │   ├── __init__.py                        # NEW
│   │   ├── engine.py                          # NEW — async engine + session factory
│   │   ├── base.py                            # NEW — DeclarativeBase
│   │   ├── crypto.py                          # NEW — encrypt_pii, decrypt_pii, hash_pii
│   │   └── models/
│   │       ├── __init__.py                    # NEW — re-export models
│   │       ├── identity.py                    # NEW — User, Session, AuditLog, Role
│   │       └── business.py                    # NEW — Cliente, Conversa, Mensagem, OS, etc
│   └── auth/
│       ├── __init__.py                        # NEW
│       ├── passwords.py                       # NEW — argon2id hash/verify
│       ├── jwt.py                             # NEW — encode/decode access+refresh tokens
│       ├── lockout.py                         # NEW — Redis attempt counter
│       ├── rbac.py                            # NEW — require_role dependency
│       ├── csrf.py                            # NEW — double-submit middleware
│       ├── audit.py                           # NEW — write_audit helper
│       └── deps.py                            # NEW — current_user dependency
└── tests/
    ├── conftest.py                            # MODIFY — add db_session + user fixtures
    ├── test_health.py                         # MODIFY — adapt fakes to AsyncSession
    ├── test_crypto.py                         # NEW
    ├── test_passwords.py                      # NEW
    ├── test_jwt.py                            # NEW
    ├── test_lockout.py                        # NEW
    ├── test_auth_login.py                     # NEW
    ├── test_auth_refresh_logout.py            # NEW
    ├── test_auth_me_rbac.py                   # NEW
    ├── test_audit.py                          # NEW
    └── test_csrf.py                           # NEW
```

**Princípio de decomposição:**
- `db/` agrupa tudo que toca Postgres (engine, modelos, crypto). Modelos divididos por domínio (identidade vs negócio) para limitar tamanho.
- `auth/` agrupa tudo que toca autenticação. Cada arquivo uma responsabilidade: hash de senha, JWT, lockout, RBAC, CSRF, audit, deps.
- `api/auth.py` só endpoints HTTP. Toda lógica delegada a módulos `auth/*`.

---

## Task 1: SQLAlchemy async engine + replace asyncpg placeholder

**Files:**
- Modify: `apps/api/pyproject.toml`
- Create: `apps/api/src/ondeline_api/db/__init__.py`
- Create: `apps/api/src/ondeline_api/db/base.py`
- Create: `apps/api/src/ondeline_api/db/engine.py`
- Modify: `apps/api/src/ondeline_api/deps.py`
- Modify: `apps/api/src/ondeline_api/api/health.py`
- Modify: `apps/api/tests/conftest.py`
- Modify: `apps/api/tests/test_health.py`

- [ ] **Step 1.1: Adicionar dependências SQLAlchemy + auth ao pyproject.toml**

Editar `apps/api/pyproject.toml`, substituir o bloco `dependencies = [...]` por:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "alembic>=1.13.0",
    "asyncpg>=0.30.0",
    "psycopg[binary]>=3.2.0",
    "redis>=5.2.0",
    "structlog>=24.4.0",
    "passlib[argon2]>=1.7.4",
    "pyjwt>=2.10.0",
    "cryptography>=43.0.0",
]
```

E adicionar ao bloco `dev`:

```toml
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
    "types-redis>=4.6.0",
    "types-passlib>=1.7.7",
    "freezegun>=1.5.0",
]
```

- [ ] **Step 1.2: Reinstalar venv com novas deps**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pip install -e ".[dev]"
```

Expected: `Successfully installed sqlalchemy-...`, `passlib-...`, `pyjwt-...`, etc.

- [ ] **Step 1.3: Criar `db/__init__.py`**

```python
"""Database layer — engine, session, models, and crypto."""
```

- [ ] **Step 1.4: Criar `db/base.py`**

```python
"""SQLAlchemy declarative base for all ORM models."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single declarative base for the whole app."""
```

- [ ] **Step 1.5: Criar `db/engine.py`**

```python
"""Async engine and session factory.

The engine is created lazily on first use so tests can override the URL
via env vars before import-time wiring runs.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ondeline_api.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, closes on request end."""
    sm = get_sessionmaker()
    async with sm() as session:
        yield session


def reset_engine_cache() -> None:
    """Test helper: drop cached engine/sessionmaker so reload picks up new URL."""
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
```

- [ ] **Step 1.6: Reescrever `deps.py` para delegar ao SQLAlchemy + Redis**

Substituir todo o conteúdo de `apps/api/src/ondeline_api/deps.py` por:

```python
"""Dependency providers for DB and Redis used across the API."""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, Protocol

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.config import get_settings
from ondeline_api.db.engine import get_db_session


class DBSessionLike(Protocol):
    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any: ...


class RedisLike(Protocol):
    async def ping(self) -> bool: ...


@lru_cache(maxsize=1)
def _redis_client() -> Redis:
    return Redis.from_url(str(get_settings().redis_url), decode_responses=True)


async def get_db() -> AsyncIterator[DBSessionLike]:
    async for session in get_db_session():
        yield session


async def get_redis() -> RedisLike:
    return _redis_client()


def reset_redis_cache() -> None:
    """Test helper."""
    _redis_client.cache_clear()
```

- [ ] **Step 1.7: Atualizar `api/health.py` para usar SQLAlchemy `text("SELECT 1")`**

Substituir todo o conteúdo de `apps/api/src/ondeline_api/api/health.py` por:

```python
"""Health and liveness endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text

from ondeline_api.deps import DBSessionLike, RedisLike, get_db, get_redis

router = APIRouter(tags=["health"])


@router.get("/livez")
async def livez() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/healthz")
async def healthz(
    response: Response,
    db: DBSessionLike = Depends(get_db),
    redis: RedisLike = Depends(get_redis),
) -> dict[str, Any]:
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["db"] = f"error: {exc.__class__.__name__}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc.__class__.__name__}"

    all_ok = all(v == "ok" for v in checks.values())
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ok" if all_ok else "degraded", "checks": checks}
```

- [ ] **Step 1.8: Adaptar `tests/conftest.py` (FakeDB com `execute`)**

Substituir `class FakeDB` em `apps/api/tests/conftest.py` por:

```python
class FakeDB:
    """Minimal async-session stub for /healthz tests."""

    def __init__(self, *, alive: bool = True) -> None:
        self._alive = alive

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        if not self._alive:
            raise ConnectionError("db down")
        return None
```

(Manter restante do arquivo intacto — `FakeRedis`, `app`, `client`, `healthy_deps`, `broken_db_deps`.)

- [ ] **Step 1.9: Verificar testes de health continuam passando**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_health.py tests/test_config.py -v
```

Expected: 6 passed.

- [ ] **Step 1.10: Verificar mypy e ruff**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
ruff check src tests
mypy src
```

Expected: ambos sem erros.

- [ ] **Step 1.11: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/pyproject.toml \
  apps/api/src/ondeline_api/db/__init__.py \
  apps/api/src/ondeline_api/db/base.py \
  apps/api/src/ondeline_api/db/engine.py \
  apps/api/src/ondeline_api/deps.py \
  apps/api/src/ondeline_api/api/health.py \
  apps/api/tests/conftest.py
git commit -m "refactor(m2): replace asyncpg pool with SQLAlchemy async engine

- DeclarativeBase em db/base.py
- AsyncEngine + AsyncSession factory em db/engine.py
- deps.py expoe DBSessionLike (execute) em vez de fetchval
- /healthz adaptado para text('SELECT 1')
- FakeDB nos testes implementa execute()"
```

---

## Task 2: Alembic async setup + initial empty migration

**Files:**
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/script.py.mako`
- Create: `apps/api/alembic/versions/.gitkeep`

- [ ] **Step 2.1: Criar `apps/api/alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = src
version_path_separator = os
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2.2: Criar `apps/api/alembic/env.py` (async-aware)**

```python
"""Alembic environment with async engine support."""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ondeline_api.config import get_settings
from ondeline_api.db.base import Base
from ondeline_api.db.models import identity, business  # noqa: F401  -- register models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async() -> None:
    engine: AsyncEngine = create_async_engine(_database_url(), future=True)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_migrations_online_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 2.3: Criar `apps/api/alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 2.4: Criar pasta de versions**

```bash
mkdir -p /root/BLABLA/ondeline-v2/apps/api/alembic/versions
touch /root/BLABLA/ondeline-v2/apps/api/alembic/versions/.gitkeep
```

- [ ] **Step 2.5: Smoke test do Alembic (sem modelos ainda — só verifica que carrega)**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
alembic current 2>&1 | head -10
```

Expected: roda sem erro de import. Pode dizer "Can't connect" se Postgres estiver down — tudo bem nesse passo. Se aparecer `ImportError: cannot import name ...`, voltar e corrigir antes de prosseguir.

- [ ] **Step 2.6: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/alembic.ini \
  apps/api/alembic/env.py \
  apps/api/alembic/script.py.mako \
  apps/api/alembic/versions/.gitkeep
git commit -m "feat(m2): add Alembic with async engine support

- env.py usa create_async_engine + run_sync(do_run_migrations)
- script.py.mako template para gerar migrations
- alembic.ini aponta para src/ no sys.path
- target_metadata = Base.metadata"
```

---

## Task 3: PII crypto module (Fernet + HMAC) — TDD

**Files:**
- Test: `apps/api/tests/test_crypto.py`
- Create: `apps/api/src/ondeline_api/db/crypto.py`

- [ ] **Step 3.1: Escrever testes falhando (`tests/test_crypto.py`)**

```python
"""Tests for PII encryption helpers."""
from __future__ import annotations

import base64

import pytest
from cryptography.fernet import Fernet, InvalidToken

from ondeline_api.db import crypto


@pytest.fixture(autouse=True)
def _crypto_env(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PII_ENCRYPTION_KEY", key)
    monkeypatch.setenv("PII_HASH_PEPPER", "test-pepper-32-bytes-of-randomness!")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://x:x@localhost:5432/x"
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    crypto.reset_caches()


def test_encrypt_decrypt_roundtrip() -> None:
    cipher = crypto.encrypt_pii("12345678900")

    assert cipher != "12345678900"
    assert crypto.decrypt_pii(cipher) == "12345678900"


def test_encrypt_returns_str_not_bytes() -> None:
    cipher = crypto.encrypt_pii("Robério")

    assert isinstance(cipher, str)


def test_encrypt_empty_string_roundtrips() -> None:
    cipher = crypto.encrypt_pii("")
    assert crypto.decrypt_pii(cipher) == ""


def test_decrypt_invalid_ciphertext_raises() -> None:
    with pytest.raises(InvalidToken):
        crypto.decrypt_pii("not-a-fernet-token")


def test_hash_pii_is_deterministic() -> None:
    h1 = crypto.hash_pii("12345678900")
    h2 = crypto.hash_pii("12345678900")

    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_hash_pii_differs_for_different_inputs() -> None:
    assert crypto.hash_pii("11111111111") != crypto.hash_pii("22222222222")


def test_missing_encryption_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_ENCRYPTION_KEY", "")
    crypto.reset_caches()

    with pytest.raises(RuntimeError, match="PII_ENCRYPTION_KEY"):
        crypto.encrypt_pii("x")


def test_missing_pepper_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_HASH_PEPPER", "")
    crypto.reset_caches()

    with pytest.raises(RuntimeError, match="PII_HASH_PEPPER"):
        crypto.hash_pii("x")
```

- [ ] **Step 3.2: Rodar e ver falhar**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_crypto.py -v
```

Expected: collection error com `ModuleNotFoundError: No module named 'ondeline_api.db.crypto'`.

- [ ] **Step 3.3: Implementar `db/crypto.py`**

```python
"""PII encryption (Fernet) + deterministic hashing (HMAC-SHA256 with pepper).

Used by ORM models to store sensitive fields encrypted at rest while
preserving the ability to look up by hash (e.g. CPF).
"""
from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet

from ondeline_api.config import get_settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = get_settings().pii_encryption_key
    if not key:
        raise RuntimeError(
            "PII_ENCRYPTION_KEY not set. Generate with: "
            "python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode())


@lru_cache(maxsize=1)
def _pepper() -> bytes:
    pepper = get_settings().pii_hash_pepper
    if not pepper:
        raise RuntimeError("PII_HASH_PEPPER not set")
    return pepper.encode()


def encrypt_pii(value: str) -> str:
    """Encrypt a UTF-8 string. Returns Fernet token as str (URL-safe base64)."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_pii(token: str) -> str:
    """Decrypt a Fernet token back to UTF-8 string. Raises InvalidToken on tamper."""
    return _fernet().decrypt(token.encode()).decode()


def hash_pii(value: str) -> str:
    """Deterministic HMAC-SHA256 hex digest. Use for indexable fields like cpf_hash."""
    return hmac.new(_pepper(), value.encode(), hashlib.sha256).hexdigest()


def reset_caches() -> None:
    """Test helper: clear cached Fernet and pepper so env reload takes effect."""
    _fernet.cache_clear()
    _pepper.cache_clear()
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
```

- [ ] **Step 3.4: Verificar `get_settings` é cacheada — ajustar `config.py` se preciso**

Abrir `apps/api/src/ondeline_api/config.py`. Se `get_settings()` ainda retorna `Settings()` direto (sem cache), trocar por:

```python
from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy singleton — chamado uma vez via Depends."""
    return Settings()
```

(Se já estiver assim por causa do M1, manter.)

- [ ] **Step 3.5: Rodar testes e verificar que passam**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_crypto.py -v
```

Expected: `7 passed`.

- [ ] **Step 3.6: mypy + ruff**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
ruff check src tests
mypy src
```

Expected: limpo.

- [ ] **Step 3.7: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/db/crypto.py \
  apps/api/src/ondeline_api/config.py \
  apps/api/tests/test_crypto.py
git commit -m "feat(m2): add PII crypto helpers (Fernet + HMAC pepper)

- encrypt_pii/decrypt_pii via Fernet (AES-128-CBC + HMAC-SHA256)
- hash_pii via HMAC-SHA256 com pepper para indexar PII
- erros explicitos quando keys nao setadas
- 7 testes (roundtrip, idempotencia, falhas, key missing)"
```

---

## Task 4: Identity models (User, Session, AuditLog) + Role enum

**Files:**
- Create: `apps/api/src/ondeline_api/db/models/__init__.py`
- Create: `apps/api/src/ondeline_api/db/models/identity.py`

- [ ] **Step 4.1: Criar `db/models/__init__.py`**

```python
"""ORM models. Importing this module registers models on Base.metadata."""
from ondeline_api.db.models import business, identity

__all__ = ["business", "identity"]
```

(Cria `business` placeholder no Task 5; por enquanto vai falhar — adicionar `business.py` vazio temporário.)

- [ ] **Step 4.2: Criar `db/models/business.py` placeholder vazio**

```python
"""Business-domain ORM models. Filled in Task 5."""
```

- [ ] **Step 4.3: Criar `db/models/identity.py`**

```python
"""Identity ORM models: User, Session (refresh token), AuditLog."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ondeline_api.db.base import Base


class Role(str, enum.Enum):
    ADMIN = "admin"
    ATENDENTE = "atendente"
    TECNICO = "tecnico"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role", native_enum=False), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_users_email", "email", unique=True),)


class Session(Base):
    """Refresh-token session. Revogavel via revoked_at."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_user", "user_id"),
        Index("ix_sessions_expires_active", "expires_at", "revoked_at"),
    )


class AuditLog(Base):
    """Imutavel — toda acao admin/atendente."""

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_user_ts", "user_id", "ts"),
        Index("ix_audit_action_ts", "action", "ts"),
    )
```

- [ ] **Step 4.4: Verificar imports + mypy**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
python -c "from ondeline_api.db.models import identity; print(list(identity.Base.metadata.tables.keys()))"
```

Expected: `['users', 'sessions', 'audit_log']`.

```bash
mypy src
```

Expected: limpo.

- [ ] **Step 4.5: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/db/models/__init__.py \
  apps/api/src/ondeline_api/db/models/identity.py \
  apps/api/src/ondeline_api/db/models/business.py
git commit -m "feat(m2): add identity ORM models (User, Session, AuditLog)

- User com Role enum (admin/atendente/tecnico)
- Session com token_hash, expires_at, revoked_at, ip, user_agent
- AuditLog imutavel com before/after JSONB
- Indexes em email, user_id, expires_at, action+ts"
```

---

## Task 5: Business models (todas as demais tabelas do schema)

**Files:**
- Modify: `apps/api/src/ondeline_api/db/models/business.py`

- [ ] **Step 5.1: Substituir `db/models/business.py` pelo schema completo**

```python
"""Business-domain ORM models: clientes, conversas, mensagens, OS, etc.

Mensagens e particionada por mes — a particao em si e definida no migration
inicial via op.execute(). O modelo aqui declara as colunas; o postgresql_partition_by
fica em __table_args__ para o autogenerate gerar a clausula PARTITION BY.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ondeline_api.db.base import Base


class ConversaEstado(str, enum.Enum):
    INICIO = "inicio"
    AGUARDA_OPCAO = "aguarda_opcao"
    LEAD_NOME = "lead_nome"
    LEAD_INTERESSE = "lead_interesse"
    CLIENTE_CPF = "cliente_cpf"
    CLIENTE = "cliente"
    AGUARDA_ATENDENTE = "aguarda_atendente"
    HUMANO = "humano"
    ENCERRADA = "encerrada"


class ConversaStatus(str, enum.Enum):
    BOT = "bot"
    AGUARDANDO = "aguardando"
    HUMANO = "humano"
    ENCERRADA = "encerrada"


class MensagemRole(str, enum.Enum):
    CLIENTE = "cliente"
    BOT = "bot"
    ATENDENTE = "atendente"


class OsStatus(str, enum.Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class LeadStatus(str, enum.Enum):
    NOVO = "novo"
    CONTATO = "contato"
    CONVERTIDO = "convertido"
    PERDIDO = "perdido"


class NotificacaoTipo(str, enum.Enum):
    VENCIMENTO = "vencimento"
    ATRASO = "atraso"
    PAGAMENTO = "pagamento"
    OS_CONCLUIDA = "os_concluida"


class NotificacaoStatus(str, enum.Enum):
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    FALHA = "falha"
    CANCELADA = "cancelada"


class SgpProvider(str, enum.Enum):
    ONDELINE = "ondeline"
    LINKNETAM = "linknetam"


# ════════ Clientes (PII encrypted) ════════

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    cpf_cnpj_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nome_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False)
    plano: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    endereco_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sgp_provider: Mapped[SgpProvider | None] = mapped_column(
        Enum(SgpProvider, name="sgp_provider", native_enum=False), nullable=True
    )
    sgp_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_clientes_cpf_hash",
            "cpf_hash",
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "ix_clientes_retention",
            "retention_until",
            postgresql_where="deleted_at IS NULL",
        ),
        Index("ix_clientes_whatsapp", "whatsapp"),
    )


# ════════ Conversas + Mensagens ════════

class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    cliente_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[ConversaEstado] = mapped_column(
        Enum(ConversaEstado, name="conversa_estado", native_enum=False),
        nullable=False,
        default=ConversaEstado.INICIO,
    )
    atendente_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ConversaStatus] = mapped_column(
        Enum(ConversaStatus, name="conversa_status", native_enum=False),
        nullable=False,
        default=ConversaStatus.BOT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_conversas_whatsapp",
            "whatsapp",
            postgresql_where="deleted_at IS NULL",
        ),
        Index("ix_conversas_status_last", "status", "last_message_at"),
    )


class Mensagem(Base):
    """Particionada por mes (RANGE em created_at).

    Particionamento e configurado no migration inicial via op.execute().
    Aqui declaramos schema que se aplica a tabela-pai e a cada particao.
    """

    __tablename__ = "mensagens"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), default=uuid4)
    conversa_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conversas.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[MensagemRole] = mapped_column(
        Enum(MensagemRole, name="mensagem_role", native_enum=False), nullable=False
    )
    content_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    llm_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_tools_called: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # PK composta para suportar particionamento por created_at
        PrimaryKeyConstraint("id", "created_at", name="pk_mensagens"),
        Index("ix_mensagens_conversa", "conversa_id", "created_at"),
        Index("ix_mensagens_external", "external_id", unique=True),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )


# ════════ Leads ════════

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False)
    interesse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status", native_enum=False),
        nullable=False,
        default=LeadStatus.NOVO,
    )
    atendente_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (Index("ix_leads_status", "status"),)


# ════════ Tecnicos ════════

class Tecnico(Base):
    __tablename__ = "tecnicos"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gps_lat: Mapped[float | None] = mapped_column(nullable=True)
    gps_lng: Mapped[float | None] = mapped_column(nullable=True)
    gps_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TecnicoArea(Base):
    """N:N tecnico x area de atuacao (cidade + rua)."""

    __tablename__ = "tecnico_areas"

    tecnico_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tecnicos.id", ondelete="CASCADE"),
        nullable=False,
    )
    cidade: Mapped[str] = mapped_column(String(80), nullable=False)
    rua: Mapped[str] = mapped_column(String(120), nullable=False)
    prioridade: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    __table_args__ = (
        PrimaryKeyConstraint("tecnico_id", "cidade", "rua", name="pk_tecnico_areas"),
    )


# ════════ Ordens de Servico ════════

class OrdemServico(Base):
    __tablename__ = "ordens_servico"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    cliente_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False
    )
    tecnico_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tecnicos.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[OsStatus] = mapped_column(
        Enum(OsStatus, name="os_status", native_enum=False),
        nullable=False,
        default=OsStatus.PENDENTE,
    )
    problema: Mapped[str] = mapped_column(Text, nullable=False)
    endereco: Mapped[str] = mapped_column(Text, nullable=False)
    agendamento_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    concluida_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fotos: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    assinatura: Mapped[str | None] = mapped_column(Text, nullable=True)
    gps_inicio_lat: Mapped[float | None] = mapped_column(nullable=True)
    gps_inicio_lng: Mapped[float | None] = mapped_column(nullable=True)
    gps_fim_lat: Mapped[float | None] = mapped_column(nullable=True)
    gps_fim_lng: Mapped[float | None] = mapped_column(nullable=True)
    csat: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    nps: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    comentario_cliente: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_os_tecnico_status", "tecnico_id", "status"),)


# ════════ Manutencoes ════════

class Manutencao(Base):
    __tablename__ = "manutencoes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    inicio_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cidades: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    notificar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ════════ Notificacoes ════════

class Notificacao(Base):
    __tablename__ = "notificacoes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    cliente_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[NotificacaoTipo] = mapped_column(
        Enum(NotificacaoTipo, name="notificacao_tipo", native_enum=False), nullable=False
    )
    agendada_para: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enviada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[NotificacaoStatus] = mapped_column(
        Enum(NotificacaoStatus, name="notificacao_status", native_enum=False),
        nullable=False,
        default=NotificacaoStatus.PENDENTE,
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tentativas: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_notif_status_due", "status", "agendada_para"),)


# ════════ Operacional ════════

class SgpCache(Base):
    __tablename__ = "sgp_cache"

    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[SgpProvider] = mapped_column(
        Enum(SgpProvider, name="sgp_provider_cache", native_enum=False), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("cpf_hash", "provider", name="pk_sgp_cache"),
    )


class LlmEvalSample(Base):
    __tablename__ = "llm_eval_samples"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversa_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conversas.id", ondelete="CASCADE"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Config(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
```

- [ ] **Step 5.2: Verificar metadata carrega todas as tabelas**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
python -c "
from ondeline_api.db.base import Base
from ondeline_api.db.models import identity, business
print(sorted(Base.metadata.tables.keys()))
print('count:', len(Base.metadata.tables))
"
```

Expected: lista com 14 tabelas: `audit_log, clientes, config, conversas, leads, llm_eval_samples, manutencoes, mensagens, notificacoes, ordens_servico, sessions, sgp_cache, tecnico_areas, tecnicos, users` (15 ao todo).

- [ ] **Step 5.3: mypy + ruff**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
mypy src
ruff check src
```

Expected: limpo. Se ruff reclamar de imports nao usados, ajustar. Se mypy reclamar de `nullable=True` sem default em `gps_lat`, etc, adicionar `nullable=True` explicito (ja esta).

- [ ] **Step 5.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/db/models/business.py
git commit -m "feat(m2): add business ORM models (clientes, conversas, mensagens, OS, etc)

- Cliente com PII em colunas *_encrypted + cpf_hash indexado parcial
- Conversa com FSM enum (9 estados) + status enum
- Mensagem particionada por mes via postgresql_partition_by
- OrdemServico com fotos jsonb, GPS, csat/nps
- Lead, Tecnico, TecnicoArea (N:N), Manutencao, Notificacao
- SgpCache (PK composta cpf_hash+provider), LlmEvalSample, Config"
```

---

## Task 6: Initial Alembic migration + apply ao Postgres dev

**Files:**
- Create: `apps/api/alembic/versions/0001_initial_schema.py`

- [ ] **Step 6.1: Subir Postgres + Redis dev**

```bash
cd /root/BLABLA/ondeline-v2
docker compose -f infra/docker-compose.dev.yml up -d postgres redis
sleep 5
docker compose -f infra/docker-compose.dev.yml ps
```

Expected: `ondeline-postgres` e `ondeline-redis` com status `healthy`.

- [ ] **Step 6.2: Gerar migration via autogenerate**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
PII_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
PII_HASH_PEPPER=dev-pepper-not-for-prod-32bytes \
JWT_SECRET=dev-jwt-secret-not-for-prod-please \
alembic revision --autogenerate -m "initial schema" --rev-id 0001
```

Expected: cria `alembic/versions/0001_initial_schema.py` com todas as tabelas. Se vier vazio, conferir que `db.models.identity`/`business` foram importados em `env.py`.

- [ ] **Step 6.3: Editar a migration gerada**

Abrir `apps/api/alembic/versions/0001_initial_schema.py`. Aplicar 3 ajustes manuais ao final do `def upgrade()` (apos as `op.create_table` autogeradas):

1. **Remover** o `op.create_table('mensagens', ...)` autogerado (vamos recriar como particionada).
2. **Adicionar** ao final de `upgrade()`:

```python
    # ──────── Mensagens (tabela-pai particionada por mes) ────────
    op.execute("""
        CREATE TABLE mensagens (
            id UUID NOT NULL,
            conversa_id UUID NOT NULL REFERENCES conversas(id) ON DELETE CASCADE,
            external_id VARCHAR(120),
            role VARCHAR(20) NOT NULL,
            content_encrypted TEXT,
            media_url TEXT,
            media_type VARCHAR(40),
            llm_tokens_used INTEGER,
            llm_tools_called JSONB,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT pk_mensagens PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)
    op.execute("""
        CREATE INDEX ix_mensagens_conversa
            ON mensagens (conversa_id, created_at DESC)
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_mensagens_external
            ON mensagens (external_id, created_at)
            WHERE external_id IS NOT NULL
    """)

    # Particoes iniciais: mes corrente + proximo
    op.execute("""
        CREATE TABLE mensagens_2026_05 PARTITION OF mensagens
        FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """)
    op.execute("""
        CREATE TABLE mensagens_2026_06 PARTITION OF mensagens
        FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')
    """)
```

3. **Adicionar** ao topo de `def downgrade()` (antes do que ja estiver la):

```python
    op.execute("DROP TABLE IF EXISTS mensagens_2026_06")
    op.execute("DROP TABLE IF EXISTS mensagens_2026_05")
    op.execute("DROP TABLE IF EXISTS mensagens")
```

E **remover** do `downgrade()` autogerado a linha `op.drop_table('mensagens')` (ja substituida pelo execute acima).

- [ ] **Step 6.4: Aplicar migration**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
PII_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
PII_HASH_PEPPER=dev-pepper \
JWT_SECRET=dev-jwt \
alembic upgrade head
```

Expected: `Running upgrade  -> 0001, initial schema`. Sem erros.

- [ ] **Step 6.5: Verificar tabelas no Postgres**

```bash
docker exec -it ondeline-postgres psql -U ondeline -d ondeline -c "\dt"
```

Expected: 15 tabelas listadas (incluindo `alembic_version`). Mensagens pai + 2 partições visíveis em `\dt+`.

```bash
docker exec -it ondeline-postgres psql -U ondeline -d ondeline -c "\d+ mensagens"
```

Expected: `Partition key: RANGE (created_at)` + lista das particoes.

- [ ] **Step 6.6: Testar downgrade + upgrade (round-trip)**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
PII_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
PII_HASH_PEPPER=dev-pepper \
JWT_SECRET=dev-jwt \
alembic downgrade base && alembic upgrade head
```

Expected: ambos comandos sem erro. Confirma que downgrade limpa tudo e upgrade reconstroi.

- [ ] **Step 6.7: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/alembic/versions/0001_initial_schema.py
git commit -m "feat(m2): initial Alembic migration with full schema

- 14 tabelas autogeradas via SQLAlchemy metadata
- mensagens particionada por mes via op.execute (PARTITION BY RANGE created_at)
- Particoes iniciais: 2026_05 e 2026_06
- Indices parciais (cpf_hash, retention) preservados
- Round-trip downgrade/upgrade validado em Postgres dev"
```

---

## Task 7: Argon2id password hashing — TDD

**Files:**
- Create: `apps/api/src/ondeline_api/auth/__init__.py`
- Create: `apps/api/src/ondeline_api/auth/passwords.py`
- Test: `apps/api/tests/test_passwords.py`

- [ ] **Step 7.1: Criar `auth/__init__.py`**

```python
"""Authentication primitives: passwords, JWT, lockout, RBAC, CSRF, audit."""
```

- [ ] **Step 7.2: Escrever testes falhando (`test_passwords.py`)**

```python
"""Tests for argon2id password hashing."""
from __future__ import annotations

import pytest

from ondeline_api.auth import passwords


def test_hash_and_verify_correct_password() -> None:
    h = passwords.hash_password("s3cret-Pa$$word")

    assert passwords.verify_password("s3cret-Pa$$word", h) is True


def test_verify_wrong_password() -> None:
    h = passwords.hash_password("s3cret-Pa$$word")

    assert passwords.verify_password("wrong", h) is False


def test_hash_uses_argon2id_format() -> None:
    h = passwords.hash_password("anything")

    assert h.startswith("$argon2id$")


def test_verify_invalid_hash_returns_false() -> None:
    assert passwords.verify_password("x", "not-a-hash") is False


def test_two_hashes_differ_due_to_salt() -> None:
    h1 = passwords.hash_password("same")
    h2 = passwords.hash_password("same")

    assert h1 != h2
    assert passwords.verify_password("same", h1)
    assert passwords.verify_password("same", h2)


def test_empty_password_raises() -> None:
    with pytest.raises(ValueError):
        passwords.hash_password("")
```

- [ ] **Step 7.3: Rodar e ver falhar**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_passwords.py -v
```

Expected: collection error com `ModuleNotFoundError: No module named 'ondeline_api.auth.passwords'`.

- [ ] **Step 7.4: Implementar `auth/passwords.py`**

```python
"""Argon2id password hashing via passlib."""
from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__type="ID",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,
    argon2__parallelism=4,
)


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password cannot be empty")
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd_context.verify(password, password_hash)
    except Exception:  # noqa: BLE001 — passlib raises on malformed hashes
        return False
```

- [ ] **Step 7.5: Rodar e verificar passa**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_passwords.py -v
```

Expected: `6 passed`.

- [ ] **Step 7.6: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/auth/__init__.py \
  apps/api/src/ondeline_api/auth/passwords.py \
  apps/api/tests/test_passwords.py
git commit -m "feat(m2): add Argon2id password hashing

- hash_password / verify_password via passlib[argon2]
- argon2__type=ID, 64MB / 3 iters / 4 lanes
- erro em senha vazia
- 6 testes (correct, wrong, format, malformed hash, salt, empty)"
```

---

## Task 8: JWT module (access + refresh) — TDD

**Files:**
- Modify: `apps/api/src/ondeline_api/config.py` (adicionar TTLs e cookie config)
- Create: `apps/api/src/ondeline_api/auth/jwt.py`
- Test: `apps/api/tests/test_jwt.py`

- [ ] **Step 8.1: Adicionar campos a `Settings`**

Editar `apps/api/src/ondeline_api/config.py`. Antes de `# Observabilidade`, adicionar:

```python
    # Token TTLs
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    # Cookies
    cookie_secure: bool = True
    cookie_domain: str = ""
    cookie_samesite: str = "strict"
```

E ajustar a logica para que em `env=development` o `cookie_secure` possa ser `False`. Modificar o `model_config` para aceitar essas variaveis (ja com `extra="ignore"`).

- [ ] **Step 8.2: Escrever testes falhando (`test_jwt.py`)**

```python
"""Tests for JWT encode/decode (access + refresh tokens)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from freezegun import freeze_time

from ondeline_api.auth import jwt as jwt_mod


@pytest.fixture(autouse=True)
def _jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-bytes-minimum-please")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost:5432/x")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_mod.reset_caches()


def test_encode_decode_access_roundtrip() -> None:
    user_id = uuid4()
    token = jwt_mod.encode_access_token(user_id, role="admin")

    payload = jwt_mod.decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


def test_encode_decode_refresh_roundtrip() -> None:
    user_id = uuid4()
    token, jti = jwt_mod.encode_refresh_token(user_id)

    payload = jwt_mod.decode_refresh_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_decode_access_rejects_refresh_token() -> None:
    user_id = uuid4()
    refresh, _ = jwt_mod.encode_refresh_token(user_id)

    with pytest.raises(jwt_mod.InvalidTokenType):
        jwt_mod.decode_access_token(refresh)


def test_decode_refresh_rejects_access_token() -> None:
    user_id = uuid4()
    access = jwt_mod.encode_access_token(user_id, role="admin")

    with pytest.raises(jwt_mod.InvalidTokenType):
        jwt_mod.decode_refresh_token(access)


def test_decode_expired_token_raises() -> None:
    user_id = uuid4()
    with freeze_time("2026-01-01 12:00:00"):
        token = jwt_mod.encode_access_token(user_id, role="admin")
    # Avancar 1h apos exp (15min default)
    with freeze_time("2026-01-01 13:30:00"):
        with pytest.raises(jwt_mod.TokenExpired):
            jwt_mod.decode_access_token(token)


def test_decode_tampered_token_raises() -> None:
    user_id = uuid4()
    token = jwt_mod.encode_access_token(user_id, role="admin")
    tampered = token[:-4] + "AAAA"

    with pytest.raises(jwt_mod.InvalidToken):
        jwt_mod.decode_access_token(tampered)


def test_hash_refresh_token_deterministic() -> None:
    h1 = jwt_mod.hash_refresh_token("abc")
    h2 = jwt_mod.hash_refresh_token("abc")
    assert h1 == h2 and len(h1) == 64
```

- [ ] **Step 8.3: Implementar `auth/jwt.py`**

```python
"""JWT helpers for access and refresh tokens.

- access: 15min, payload {sub, role, type=access, jti, exp, iat}
- refresh: 7d, payload {sub, type=refresh, jti, exp, iat} + token_hash em DB
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from uuid import UUID, uuid4

import jwt as pyjwt

from ondeline_api.config import get_settings

ALGO = "HS256"


class InvalidToken(Exception):
    pass


class InvalidTokenType(InvalidToken):
    pass


class TokenExpired(InvalidToken):
    pass


@lru_cache(maxsize=1)
def _secret() -> str:
    s = get_settings().jwt_secret
    if not s:
        raise RuntimeError("JWT_SECRET not set")
    return s


def reset_caches() -> None:
    _secret.cache_clear()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def encode_access_token(user_id: UUID, role: str) -> str:
    settings = get_settings()
    iat = _now()
    exp = iat + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "jti": str(uuid4()),
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO)


def encode_refresh_token(user_id: UUID) -> tuple[str, str]:
    """Returns (token, jti) so caller can persist jti or token_hash."""
    settings = get_settings()
    iat = _now()
    exp = iat + timedelta(days=settings.refresh_token_ttl_days)
    jti = str(uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO), jti


def _decode(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = pyjwt.decode(token, _secret(), algorithms=[ALGO])
    except pyjwt.ExpiredSignatureError as exc:
        raise TokenExpired(str(exc)) from exc
    except pyjwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenType(f"expected {expected_type}, got {payload.get('type')}")
    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode(token, "access")


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode(token, "refresh")


def hash_refresh_token(token: str) -> str:
    """SHA256 hex — used to persist refresh tokens server-side without raw value."""
    return hashlib.sha256(token.encode()).hexdigest()
```

- [ ] **Step 8.4: Rodar testes**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_jwt.py -v
```

Expected: `7 passed`.

- [ ] **Step 8.5: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/config.py \
  apps/api/src/ondeline_api/auth/jwt.py \
  apps/api/tests/test_jwt.py
git commit -m "feat(m2): add JWT access + refresh tokens

- encode_access_token (15min TTL) com role no payload
- encode_refresh_token (7d TTL) retorna (token, jti)
- decode_* valida type e rejeita expirado/adulterado
- hash_refresh_token (sha256 hex) para persistencia em DB
- Settings: access_token_ttl_minutes, refresh_token_ttl_days, cookie_*
- 7 testes (roundtrip x2, type swap x2, expired, tampered, hash)"
```

---

## Task 9: Login lockout via Redis — TDD

**Files:**
- Create: `apps/api/src/ondeline_api/auth/lockout.py`
- Test: `apps/api/tests/test_lockout.py`

- [ ] **Step 9.1: Escrever testes falhando (`test_lockout.py`)**

```python
"""Tests for login lockout counter (Redis-backed)."""
from __future__ import annotations

from typing import Any

import pytest

from ondeline_api.auth import lockout


class InMemoryRedis:
    """Minimal stub of redis.asyncio.Redis for lockout tests."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = seconds
        return True

    async def get(self, key: str) -> str | None:
        v = self.store.get(key)
        return str(v) if v is not None else None

    async def delete(self, key: str) -> int:
        existed = key in self.store
        self.store.pop(key, None)
        self.ttls.pop(key, None)
        return 1 if existed else 0

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -2)


@pytest.fixture
def redis() -> InMemoryRedis:
    return InMemoryRedis()


@pytest.mark.asyncio
async def test_first_failure_returns_remaining(redis: InMemoryRedis) -> None:
    state = await lockout.record_failure(redis, "user@example.com")

    assert state.locked is False
    assert state.attempts == 1
    assert state.remaining == 4


@pytest.mark.asyncio
async def test_fifth_failure_locks(redis: InMemoryRedis) -> None:
    for _ in range(4):
        await lockout.record_failure(redis, "user@example.com")
    state = await lockout.record_failure(redis, "user@example.com")

    assert state.locked is True
    assert state.attempts == 5


@pytest.mark.asyncio
async def test_is_locked_after_lockout(redis: InMemoryRedis) -> None:
    for _ in range(5):
        await lockout.record_failure(redis, "user@example.com")

    assert await lockout.is_locked(redis, "user@example.com") is True


@pytest.mark.asyncio
async def test_is_locked_when_no_attempts(redis: InMemoryRedis) -> None:
    assert await lockout.is_locked(redis, "user@example.com") is False


@pytest.mark.asyncio
async def test_clear_resets_attempts(redis: InMemoryRedis) -> None:
    await lockout.record_failure(redis, "user@example.com")
    await lockout.clear(redis, "user@example.com")

    assert await lockout.is_locked(redis, "user@example.com") is False


@pytest.mark.asyncio
async def test_isolation_between_users(redis: InMemoryRedis) -> None:
    for _ in range(5):
        await lockout.record_failure(redis, "a@example.com")

    assert await lockout.is_locked(redis, "a@example.com") is True
    assert await lockout.is_locked(redis, "b@example.com") is False
```

- [ ] **Step 9.2: Implementar `auth/lockout.py`**

```python
"""Login lockout counter backed by Redis.

Conta tentativas de login falhadas por email (case-folded). Apos MAX_ATTEMPTS
em uma janela WINDOW_SECONDS, o usuario fica bloqueado pelo restante da janela.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60  # 15 minutos


class RedisCounter(Protocol):
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> int: ...


@dataclass(frozen=True)
class LockoutState:
    attempts: int
    remaining: int
    locked: bool


def _key(email: str) -> str:
    return f"lockout:login:{email.lower().strip()}"


async def record_failure(redis: RedisCounter, email: str) -> LockoutState:
    key = _key(email)
    n = await redis.incr(key)
    if n == 1:
        await redis.expire(key, WINDOW_SECONDS)
    return LockoutState(
        attempts=n,
        remaining=max(0, MAX_ATTEMPTS - n),
        locked=n >= MAX_ATTEMPTS,
    )


async def is_locked(redis: RedisCounter, email: str) -> bool:
    raw = await redis.get(_key(email))
    if raw is None:
        return False
    return int(raw) >= MAX_ATTEMPTS


async def clear(redis: RedisCounter, email: str) -> None:
    await redis.delete(_key(email))
```

- [ ] **Step 9.3: Rodar testes**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_lockout.py -v
```

Expected: `6 passed`.

- [ ] **Step 9.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/auth/lockout.py \
  apps/api/tests/test_lockout.py
git commit -m "feat(m2): add Redis-backed login lockout

- record_failure incrementa contador (TTL 15min na 1a falha)
- is_locked True quando >= 5 tentativas
- clear remove key (chamado em login bem-sucedido)
- isolamento por email case-folded
- 6 testes com InMemoryRedis stub"
```

---

## Task 10: /auth/login endpoint (passwords + JWT + lockout + audit) — TDD

**Files:**
- Create: `apps/api/src/ondeline_api/auth/audit.py` (helper minimo, expandido em Task 13)
- Create: `apps/api/src/ondeline_api/api/auth.py`
- Modify: `apps/api/src/ondeline_api/main.py` (register router)
- Modify: `apps/api/tests/conftest.py` (db_session + user fixtures)
- Test: `apps/api/tests/test_auth_login.py`

- [ ] **Step 10.1: Criar `auth/audit.py` minimal (sera estendido em Task 13)**

```python
"""Helper para escrever audit_log. Versao minima para o login. Estendida em Task 13."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.identity import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=before,
        after=after,
        ip=ip,
    )
    session.add(entry)
    await session.flush()
```

- [ ] **Step 10.2: Adicionar fixtures no `tests/conftest.py`**

Adicionar **ao final** de `apps/api/tests/conftest.py`:

```python
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

INTEGRATION_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline",
)


@pytest.fixture(scope="session")
def _set_secrets() -> None:
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret-32-bytes-minimum-okk")
    os.environ.setdefault(
        "PII_ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    os.environ.setdefault("PII_HASH_PEPPER", "test-pepper-not-for-prod-32-bytes-x")


@pytest_asyncio.fixture
async def db_session(_set_secrets: None) -> AsyncIterator[AsyncSession]:
    """Per-test session with rollback at end. Requires Postgres running."""
    engine = create_async_engine(INTEGRATION_DB_URL, future=True)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with sm(bind=conn) as session:
            yield session
        await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def created_user(db_session: AsyncSession) -> dict[str, object]:
    """Cria um user admin com senha conhecida e retorna dict com email/senha/id."""
    from ondeline_api.auth.passwords import hash_password
    from ondeline_api.db.models.identity import Role, User

    email = f"test-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=Role.ADMIN,
        name="Test Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "email": email, "password": password, "user": user}
```

(Manter as fixtures existentes — `app`, `client`, `healthy_deps`, `broken_db_deps` — intactas. Adicionar `import pytest` e `import pytest_asyncio` no topo se ja nao existirem.)

- [ ] **Step 10.3: Escrever testes de login falhando (`test_auth_login.py`)**

```python
"""Integration tests for POST /auth/login."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.deps import get_db
from ondeline_api.main import create_app


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return app


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_login_with_correct_credentials_returns_tokens(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "Bearer"
    # Refresh token vem em cookie HttpOnly
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": "wrong"},
    )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_with_unknown_email_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "x"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(
    client: AsyncClient, created_user: dict[str, object], db_session: AsyncSession
) -> None:
    user = created_user["user"]
    user.is_active = False
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_locks_after_5_failures(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    for _ in range(5):
        await client.post(
            "/auth/login",
            json={"email": created_user["email"], "password": "wrong"},
        )
    # 6a tentativa, mesmo com senha correta, deve retornar 423
    resp = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )
    assert resp.status_code == 423
```

- [ ] **Step 10.4: Implementar `api/auth.py` com login**

```python
"""Authentication endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth import lockout
from ondeline_api.auth.audit import write_audit
from ondeline_api.auth.passwords import verify_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Session as DBSession, User
from ondeline_api.deps import RedisLike, get_db, get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user_id: str
    role: str


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure if settings.env != "development" else False,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path="/auth",
    )


def _set_csrf_cookie(response: Response, value: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=CSRF_COOKIE,
        value=value,
        httponly=False,  # client lê e devolve no header
        secure=settings.cookie_secure if settings.env != "development" else False,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    redis: RedisLike = Depends(get_redis),
) -> LoginResponse:
    if await lockout.is_locked(redis, payload.email):
        await write_audit(
            session,
            user_id=None,
            action="login.locked",
            resource_type="user",
            resource_id=payload.email,
            ip=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="too many login attempts; try again later",
        )

    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    valid = (
        user is not None
        and user.is_active
        and verify_password(payload.password, user.password_hash)
    )
    if not valid:
        state = await lockout.record_failure(redis, payload.email)
        await write_audit(
            session,
            user_id=user.id if user else None,
            action="login.failed",
            resource_type="user",
            resource_id=payload.email,
            after={"attempts": state.attempts, "locked": state.locked},
            ip=_client_ip(request),
        )
        raise HTTPException(status_code=401, detail="invalid credentials")

    assert user is not None  # narrow for mypy
    await lockout.clear(redis, payload.email)

    access_token = jwt_mod.encode_access_token(user.id, role=user.role.value)
    refresh_token, jti = jwt_mod.encode_refresh_token(user.id)

    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_ttl_days
    )
    db_session = DBSession(
        user_id=user.id,
        token_hash=jwt_mod.hash_refresh_token(refresh_token),
        expires_at=expires_at,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    session.add(db_session)
    user.last_login_at = datetime.now(timezone.utc)

    await write_audit(
        session,
        user_id=user.id,
        action="login.success",
        resource_type="user",
        resource_id=str(user.id),
        ip=_client_ip(request),
    )
    await session.flush()

    _set_refresh_cookie(response, refresh_token)
    _set_csrf_cookie(response, jti)  # double-submit token

    return LoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        role=user.role.value,
    )
```

- [ ] **Step 10.5: Atualizar `main.py` para registrar router**

Substituir conteudo de `apps/api/src/ondeline_api/main.py`:

```python
"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from ondeline_api import __version__
from ondeline_api.api import auth, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ondeline API",
        version=__version__,
        description="WhatsApp bot + admin API for Ondeline Telecom",
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
```

- [ ] **Step 10.6: Rodar testes (Postgres precisa estar up)**

```bash
cd /root/BLABLA/ondeline-v2
docker compose -f infra/docker-compose.dev.yml up -d postgres redis
sleep 3
cd apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
TEST_DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
pytest tests/test_auth_login.py -v
```

Expected: `5 passed`. Se 423 falhar por causa de lockout deixado de teste anterior, garantir que o teste limpa o Redis no teardown — ajustar fixture se preciso (FLUSHDB no namespace de test).

- [ ] **Step 10.7: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/auth/audit.py \
  apps/api/src/ondeline_api/api/auth.py \
  apps/api/src/ondeline_api/main.py \
  apps/api/tests/conftest.py \
  apps/api/tests/test_auth_login.py
git commit -m "feat(m2): add POST /auth/login

- valida email+senha contra users.password_hash (argon2id)
- rejeita user inativo
- lockout 5 falhas/15min retorna 423
- gera access (15min) + refresh (7d em cookie HttpOnly)
- persiste session com token_hash, ip, user_agent
- audit_log: login.success / login.failed / login.locked
- 5 testes integration (correct, wrong, unknown, inactive, locked)"
```

---

## Task 11: /auth/refresh + /auth/logout — TDD

**Files:**
- Modify: `apps/api/src/ondeline_api/api/auth.py`
- Test: `apps/api/tests/test_auth_refresh_logout.py`

- [ ] **Step 11.1: Escrever testes (`test_auth_refresh_logout.py`)**

```python
"""Tests for POST /auth/refresh and POST /auth/logout."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.db.models.identity import Session as DBSession
from ondeline_api.deps import get_db
from ondeline_api.main import create_app


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return app


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, user: dict[str, object]) -> dict[str, str]:
    r = await client.post(
        "/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert r.status_code == 200
    return {
        "access_token": r.json()["access_token"],
        "refresh_token": r.cookies["refresh_token"],
    }


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    tokens = await _login(client, created_user)
    client.cookies.set("refresh_token", tokens["refresh_token"], path="/auth")

    resp = await client.post("/auth/refresh")

    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    assert new_access != tokens["access_token"]


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient) -> None:
    client.cookies.set("refresh_token", "garbage", path="/auth")
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(
    client: AsyncClient,
    created_user: dict[str, object],
    db_session: AsyncSession,
) -> None:
    tokens = await _login(client, created_user)
    client.cookies.set("refresh_token", tokens["refresh_token"], path="/auth")

    resp = await client.post("/auth/logout")
    assert resp.status_code == 204

    # refresh apos logout deve falhar
    resp2 = await client.post("/auth/refresh")
    assert resp2.status_code == 401

    # sessao no DB deve ter revoked_at preenchido
    th = jwt_mod.hash_refresh_token(tokens["refresh_token"])
    res = await db_session.execute(
        select(DBSession).where(DBSession.token_hash == th)
    )
    db_sess = res.scalar_one()
    assert db_sess.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_without_cookie_idempotent(client: AsyncClient) -> None:
    resp = await client.post("/auth/logout")
    assert resp.status_code == 204
```

- [ ] **Step 11.2: Adicionar handlers em `api/auth.py`**

Adicionar **ao final** de `apps/api/src/ondeline_api/api/auth.py`:

```python
class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="missing refresh token")
    try:
        payload = jwt_mod.decode_refresh_token(raw)
    except jwt_mod.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    token_hash = jwt_mod.hash_refresh_token(raw)
    res = await session.execute(
        select(DBSession).where(DBSession.token_hash == token_hash)
    )
    db_session = res.scalar_one_or_none()
    if db_session is None or db_session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="session revoked or unknown")

    user = await session.get(User, db_session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user inactive")

    access = jwt_mod.encode_access_token(user.id, role=user.role.value)
    return RefreshResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> Response:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        token_hash = jwt_mod.hash_refresh_token(raw)
        res = await session.execute(
            select(DBSession).where(DBSession.token_hash == token_hash)
        )
        db_session = res.scalar_one_or_none()
        if db_session and db_session.revoked_at is None:
            db_session.revoked_at = datetime.now(timezone.utc)
            await write_audit(
                session,
                user_id=db_session.user_id,
                action="logout",
                resource_type="session",
                resource_id=str(db_session.id),
                ip=_client_ip(request),
            )
            await session.flush()

    response.delete_cookie(REFRESH_COOKIE, path="/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return Response(status_code=204)
```

- [ ] **Step 11.3: Rodar testes**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
TEST_DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
pytest tests/test_auth_refresh_logout.py -v
```

Expected: `5 passed`.

- [ ] **Step 11.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/api/auth.py \
  apps/api/tests/test_auth_refresh_logout.py
git commit -m "feat(m2): add POST /auth/refresh and /auth/logout

- /refresh valida refresh-cookie, checa session.revoked_at, emite novo access
- /logout marca session.revoked_at, limpa cookies, audit_log
- /logout idempotente (204 sem cookie)
- 5 testes (refresh ok, sem cookie, invalido, logout revoga, logout idempotente)"
```

---

## Task 12: /auth/me + RBAC `require_role` — TDD

**Files:**
- Create: `apps/api/src/ondeline_api/auth/deps.py`
- Create: `apps/api/src/ondeline_api/auth/rbac.py`
- Modify: `apps/api/src/ondeline_api/api/auth.py`
- Test: `apps/api/tests/test_auth_me_rbac.py`

- [ ] **Step 12.1: Criar `auth/deps.py` (current_user)**

```python
"""FastAPI dependencies for extracting the current user from access token."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.db.models.identity import User
from ondeline_api.deps import get_db


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    return auth.removeprefix("Bearer ").strip()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User:
    token = _bearer_token(request)
    try:
        payload = jwt_mod.decode_access_token(token)
    except jwt_mod.TokenExpired:
        raise HTTPException(status_code=401, detail="token expired") from None
    except jwt_mod.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    from uuid import UUID

    user = await session.get(User, UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user inactive or unknown")
    return user
```

- [ ] **Step 12.2: Criar `auth/rbac.py`**

```python
"""Role-based access control dependency."""
from __future__ import annotations

from collections.abc import Callable
from typing import Awaitable

from fastapi import Depends, HTTPException, status

from ondeline_api.auth.deps import get_current_user
from ondeline_api.db.models.identity import Role, User


def require_role(*allowed: Role) -> Callable[[User], Awaitable[User]]:
    """Returns a FastAPI dependency that 403s when user role not in `allowed`."""
    allowed_set = set(allowed)

    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient role",
            )
        return user

    return _dep
```

- [ ] **Step 12.3: Adicionar `/auth/me` em `api/auth.py`**

Adicionar **ao final** de `apps/api/src/ondeline_api/api/auth.py`:

```python
from ondeline_api.auth.deps import get_current_user


class MeResponse(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    is_active: bool


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
    )
```

- [ ] **Step 12.4: Escrever testes (`test_auth_me_rbac.py`)**

```python
"""Tests for /auth/me and require_role dependency."""
from __future__ import annotations

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.passwords import hash_password
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.main import create_app


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    test = APIRouter()

    @test.get("/admin-only")
    async def admin_only(user: User = Depends(require_role(Role.ADMIN))) -> dict[str, str]:
        return {"ok": user.email}

    @test.get("/atendente-or-admin")
    async def both(
        user: User = Depends(require_role(Role.ADMIN, Role.ATENDENTE)),
    ) -> dict[str, str]:
        return {"ok": user.email}

    app.include_router(test)
    return app


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_me_returns_user(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    token = await _login(client, created_user["email"], created_user["password"])
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200
    body = r.json()
    assert body["email"] == created_user["email"]
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_me_without_token_401(client: AsyncClient) -> None:
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_only_allows_admin(
    client: AsyncClient, created_user: dict[str, object]
) -> None:
    token = await _login(client, created_user["email"], created_user["password"])
    r = await client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_only_blocks_tecnico(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = User(
        email="tec@example.com",
        password_hash=hash_password("Pa$$w0rd"),
        role=Role.TECNICO,
        name="Tec",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = await _login(client, "tec@example.com", "Pa$$w0rd")
    r = await client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_combined_role_allows_both(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    atendente = User(
        email="at@example.com",
        password_hash=hash_password("Pa$$w0rd"),
        role=Role.ATENDENTE,
        name="At",
        is_active=True,
    )
    db_session.add(atendente)
    await db_session.flush()

    token = await _login(client, "at@example.com", "Pa$$w0rd")
    r = await client.get(
        "/atendente-or-admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
```

- [ ] **Step 12.5: Rodar testes**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
TEST_DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
pytest tests/test_auth_me_rbac.py -v
```

Expected: `5 passed`.

- [ ] **Step 12.6: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/auth/deps.py \
  apps/api/src/ondeline_api/auth/rbac.py \
  apps/api/src/ondeline_api/api/auth.py \
  apps/api/tests/test_auth_me_rbac.py
git commit -m "feat(m2): add /auth/me and require_role dependency

- get_current_user dep extrai access token de Bearer header
- require_role(*roles) factory de dependency 403 para roles fora
- /auth/me retorna {user_id, email, name, role, is_active}
- 5 testes (me ok, sem token, admin-only ok/blocked, combinada ok)"
```

---

## Task 13: Audit log writer expandido

**Files:**
- Modify: `apps/api/src/ondeline_api/auth/audit.py`
- Test: `apps/api/tests/test_audit.py`

Em Task 10 criamos um `write_audit()` minimo. Aqui adicionamos um helper `audit_action()` (context manager) que captura before/after automaticamente em modificacoes de admin.

- [ ] **Step 13.1: Escrever testes (`test_audit.py`)**

```python
"""Tests for audit log helpers."""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.audit import audit_action, write_audit
from ondeline_api.db.models.identity import AuditLog, Role, User


@pytest.mark.asyncio
async def test_write_audit_persists_row(db_session: AsyncSession) -> None:
    user = User(
        email="a@example.com",
        password_hash="x",
        role=Role.ADMIN,
        name="A",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    await write_audit(
        db_session,
        user_id=user.id,
        action="user.update",
        resource_type="user",
        resource_id=str(user.id),
        before={"name": "A"},
        after={"name": "A2"},
        ip="10.0.0.1",
    )
    await db_session.flush()

    rows = (await db_session.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "user.update"
    assert rows[0].before == {"name": "A"}
    assert rows[0].after == {"name": "A2"}


@pytest.mark.asyncio
async def test_audit_action_captures_before_and_after(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="b@example.com",
        password_hash="x",
        role=Role.ATENDENTE,
        name="B",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    snapshot = {"name": user.name, "role": user.role.value}

    async with audit_action(
        db_session,
        user_id=user.id,
        action="user.rename",
        resource_type="user",
        resource_id=str(user.id),
        before=snapshot,
    ) as ctx:
        user.name = "B-renamed"
        ctx.after = {"name": user.name, "role": user.role.value}

    await db_session.flush()
    rows = (await db_session.execute(select(AuditLog))).scalars().all()
    assert rows[0].action == "user.rename"
    assert rows[0].before == {"name": "B", "role": "atendente"}
    assert rows[0].after == {"name": "B-renamed", "role": "atendente"}
```

- [ ] **Step 13.2: Estender `auth/audit.py`**

Substituir o conteudo de `apps/api/src/ondeline_api/auth/audit.py` por:

```python
"""Audit log helpers.

`write_audit` escreve uma entrada diretamente. `audit_action` e um async
context manager que captura before/after e escreve ao final do bloco.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.identity import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=before,
        after=after,
        ip=ip,
    )
    session.add(entry)
    await session.flush()


@dataclass
class AuditContext:
    after: dict[str, Any] | None = field(default=None)


@asynccontextmanager
async def audit_action(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    before: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AsyncIterator[AuditContext]:
    """Captura before/after num bloco. Quem usa preenche ctx.after."""
    ctx = AuditContext()
    yield ctx
    await write_audit(
        session,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=before,
        after=ctx.after,
        ip=ip,
    )
```

- [ ] **Step 13.3: Rodar testes**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
TEST_DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
pytest tests/test_audit.py -v
```

Expected: `2 passed`.

- [ ] **Step 13.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/auth/audit.py \
  apps/api/tests/test_audit.py
git commit -m "feat(m2): add audit_action context manager

- write_audit (ja existia) persiste linha simples
- audit_action async cm captura before/after; chamador preenche ctx.after
- 2 testes (write direto + context manager com mutacao)"
```

---

## Task 14: CSRF double-submit middleware — TDD

**Files:**
- Create: `apps/api/src/ondeline_api/auth/csrf.py`
- Modify: `apps/api/src/ondeline_api/main.py` (registrar middleware)
- Test: `apps/api/tests/test_csrf.py`

- [ ] **Step 14.1: Escrever testes (`test_csrf.py`)**

```python
"""Tests for CSRF double-submit middleware."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ondeline_api.auth.csrf import CSRFMiddleware


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CSRFMiddleware, exempt_paths=["/auth/login", "/auth/refresh", "/webhook"])

    @app.get("/safe")
    async def safe() -> dict[str, str]:
        return {"ok": "yes"}

    @app.post("/state-change")
    async def state_change() -> dict[str, str]:
        return {"ok": "yes"}

    return app


@pytest.mark.asyncio
async def test_get_passes_without_csrf() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/safe")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_post_without_csrf_blocked() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "abc")
        r = await c.post("/state-change")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_post_with_matching_csrf_passes() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "abc")
        r = await c.post("/state-change", headers={"X-CSRF": "abc"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_post_with_mismatched_csrf_blocked() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "abc")
        r = await c.post("/state-change", headers={"X-CSRF": "xyz"})
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_exempt_path_skipped() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Login bate em path exempted; sem cookie nem header
        r = await c.post("/auth/login", json={})
        # 404 (rota inexistente em make_app) mas nao 403 do CSRF
        assert r.status_code != 403
```

- [ ] **Step 14.2: Implementar `auth/csrf.py`**

```python
"""Double-submit cookie CSRF middleware.

Para qualquer metodo nao-safe, exige que o header `X-CSRF` tenha o mesmo
valor do cookie `csrf_token`. Bypass para `exempt_paths`.

O cookie nao e HttpOnly (cliente JS precisa ler para devolver no header),
mas o JWT que importa fica no cookie HttpOnly separado.
"""
from __future__ import annotations

import hmac
from collections.abc import Sequence

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
COOKIE_NAME = "csrf_token"
HEADER_NAME = "x-csrf"


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exempt_paths: Sequence[str] = ()) -> None:
        super().__init__(app)
        self._exempt = tuple(exempt_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in self._exempt):
            return await call_next(request)

        cookie = request.cookies.get(COOKIE_NAME, "")
        header = request.headers.get(HEADER_NAME, "")
        if not cookie or not header or not hmac.compare_digest(cookie, header):
            return JSONResponse({"detail": "csrf check failed"}, status_code=403)

        return await call_next(request)
```

- [ ] **Step 14.3: Registrar middleware em `main.py`**

Substituir `apps/api/src/ondeline_api/main.py`:

```python
"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from ondeline_api import __version__
from ondeline_api.api import auth, health
from ondeline_api.auth.csrf import CSRFMiddleware


CSRF_EXEMPT_PATHS = ["/auth/login", "/auth/refresh", "/webhook", "/healthz", "/livez"]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ondeline API",
        version=__version__,
        description="WhatsApp bot + admin API for Ondeline Telecom",
    )
    app.add_middleware(CSRFMiddleware, exempt_paths=CSRF_EXEMPT_PATHS)
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
```

- [ ] **Step 14.4: Rodar testes**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest tests/test_csrf.py -v
```

Expected: `5 passed`. (Esses testes nao tocam DB, rodam mesmo sem Postgres.)

- [ ] **Step 14.5: Rodar suite completa**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
TEST_DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
REDIS_URL=redis://localhost:6380/0 \
PII_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
PII_HASH_PEPPER=test-pepper \
JWT_SECRET=test-jwt-secret-32-bytes-minimum-okk \
pytest -v
```

Expected: todos os testes passam (~50 testes total: 6 health/config + 7 crypto + 6 passwords + 7 jwt + 6 lockout + 5 login + 5 refresh/logout + 5 me/rbac + 2 audit + 5 csrf = ~54 testes). Ajustar contagem se proximo.

- [ ] **Step 14.6: mypy + ruff**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
ruff check src tests
mypy src
```

Expected: limpo.

- [ ] **Step 14.7: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/auth/csrf.py \
  apps/api/src/ondeline_api/main.py \
  apps/api/tests/test_csrf.py
git commit -m "feat(m2): add CSRF double-submit middleware

- bloqueia metodos nao-safe sem X-CSRF == cookie csrf_token
- exempt: /auth/login, /auth/refresh, /webhook, /healthz, /livez
- comparacao constant-time via hmac.compare_digest
- 5 testes (GET pass, POST sem/com/mismatch/exempt)"
```

---

## Task 15: CI integration + smoke E2E + tag m2

**Files:**
- Modify: `.github/workflows/ci.yml` (rodar Alembic + secrets de test)
- Modify: `apps/api/Dockerfile` (instalar pacote em vez de deps inline) — opcional se a build atual nao copia pyproject.toml ainda

- [ ] **Step 15.1: Atualizar CI para rodar migrations + secrets de test**

Editar `.github/workflows/ci.yml`. Substituir step `Pytest` por:

```yaml
      - name: Generate test secrets
        id: secrets
        run: |
          PII_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
          echo "pii_key=$PII_KEY" >> $GITHUB_OUTPUT

      - name: Alembic upgrade
        env:
          DATABASE_URL: postgresql+asyncpg://ondeline:ondeline@localhost:5432/ondeline
          REDIS_URL: redis://localhost:6379/0
          PII_ENCRYPTION_KEY: ${{ steps.secrets.outputs.pii_key }}
          PII_HASH_PEPPER: ci-pepper-not-for-prod-32-bytes-min
          JWT_SECRET: ci-jwt-secret-not-for-prod-32-bytes
        run: alembic upgrade head

      - name: Pytest
        env:
          DATABASE_URL: postgresql+asyncpg://ondeline:ondeline@localhost:5432/ondeline
          TEST_DATABASE_URL: postgresql+asyncpg://ondeline:ondeline@localhost:5432/ondeline
          REDIS_URL: redis://localhost:6379/0
          PII_ENCRYPTION_KEY: ${{ steps.secrets.outputs.pii_key }}
          PII_HASH_PEPPER: ci-pepper-not-for-prod-32-bytes-min
          JWT_SECRET: ci-jwt-secret-not-for-prod-32-bytes
        run: pytest -v
```

- [ ] **Step 15.2: Smoke E2E local — login real**

```bash
cd /root/BLABLA/ondeline-v2
docker compose -f infra/docker-compose.dev.yml up -d
sleep 10

# Cria user admin via psql
docker exec -it ondeline-postgres psql -U ondeline -d ondeline -c "
INSERT INTO users (id, email, password_hash, role, name, is_active, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'admin@ondeline.dev',
  '\$argon2id\$v=19\$m=65536,t=3,p=4\$REPLACE_ME',
  'admin', 'Admin', true, NOW(), NOW()
);
"
```

Mais simples: usar um script Python pra criar o user com hash correto:

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline \
PII_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
PII_HASH_PEPPER=dev \
JWT_SECRET=dev-jwt-secret-32-bytes-minimum-please \
REDIS_URL=redis://localhost:6380/0 \
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.models.identity import User, Role

async def main():
    eng = create_async_engine('postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline')
    sm = async_sessionmaker(eng, expire_on_commit=False)
    async with sm() as s:
        u = User(email='admin@ondeline.dev', password_hash=hash_password('admin123'),
                 role=Role.ADMIN, name='Admin', is_active=True)
        s.add(u)
        await s.commit()
    await eng.dispose()
asyncio.run(main())
"
```

- [ ] **Step 15.3: Login + me + logout via curl**

Como a stack docker-compose roda a api com `JWT_SECRET=` vazio (o `.env` original do M1 nao define), precisamos preencher antes. Editar `.env` manualmente:

```bash
cd /root/BLABLA/ondeline-v2
# Atualizar .env com secrets reais (NAO commitar)
python -c "from cryptography.fernet import Fernet; print('PII_ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env
echo "PII_HASH_PEPPER=$(openssl rand -hex 32)" >> .env
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env

# Restart api para pegar novos vars
docker compose -f infra/docker-compose.dev.yml up -d --build api
sleep 5

# 1. Login
RESP=$(curl -sc /tmp/cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ondeline.dev","password":"admin123"}')
echo "Login response: $RESP"
ACCESS=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. /auth/me
curl -s http://localhost:8000/auth/me -H "Authorization: Bearer $ACCESS" | python3 -m json.tool

# 3. /auth/refresh (manda cookie)
curl -sb /tmp/cookies.txt -X POST http://localhost:8000/auth/refresh | python3 -m json.tool

# 4. /auth/logout
curl -sb /tmp/cookies.txt -X POST -w "%{http_code}\n" http://localhost:8000/auth/logout
```

Expected:
- Login retorna `{"access_token":"...","token_type":"Bearer","user_id":"...","role":"admin"}`
- /auth/me retorna `{"email":"admin@ondeline.dev","role":"admin","is_active":true,...}`
- /auth/refresh retorna novo `access_token`
- /auth/logout retorna 204

- [ ] **Step 15.4: Verificar audit_log entries**

```bash
docker exec -it ondeline-postgres psql -U ondeline -d ondeline -c \
  "SELECT action, resource_type, ts FROM audit_log ORDER BY ts DESC LIMIT 5;"
```

Expected: ver `login.success` e `logout` recentes.

- [ ] **Step 15.5: Commit + push**

```bash
cd /root/BLABLA/ondeline-v2
git add .github/workflows/ci.yml
git commit -m "ci(m2): run alembic upgrade + add auth secrets

- gera PII_ENCRYPTION_KEY no setup do job
- exporta PII_HASH_PEPPER, JWT_SECRET, TEST_DATABASE_URL para pytest
- alembic upgrade head antes do pytest"
git push
```

- [ ] **Step 15.6: Verificar CI verde**

```bash
sleep 5
gh run list --limit 3
gh run watch
```

Expected: `completed success`.

- [ ] **Step 15.7: Tag m2 e push**

```bash
cd /root/BLABLA/ondeline-v2
git tag -a m2-banco-auth -m "M2: Banco + Auth concluido

- SQLAlchemy 2.x async + Alembic com env.py async-aware
- 14 tabelas (User, Session, AuditLog + clientes, conversas, mensagens particionada, OS, etc)
- PII crypto: Fernet (AES-128-CBC + HMAC) + HMAC-SHA256 pepper
- Argon2id para senhas
- JWT access (15min) + refresh (7d em cookie HttpOnly)
- Lockout 5 tentativas/15min via Redis
- /auth/login, /refresh, /logout, /me
- RBAC require_role(*roles)
- audit_log com login.* / logout / write_audit / audit_action cm
- CSRF double-submit middleware (exempt: login/refresh/webhook/health)
- ~54 testes (unit + integration), CI verde"
git push --tags
```

- [ ] **Step 15.8: Cleanup**

```bash
cd /root/BLABLA/ondeline-v2
make down
```

---

## Definition of Done — M2

- [ ] `alembic upgrade head` aplica todas as 14 tabelas + particoes de mensagens em Postgres limpo
- [ ] `alembic downgrade base` remove tudo sem erro
- [ ] PII helpers (`encrypt_pii`, `decrypt_pii`, `hash_pii`) testados (roundtrip + hash determinismo)
- [ ] `hash_password` / `verify_password` (argon2id) testados
- [ ] JWT encode/decode (access + refresh) testados (roundtrip, type swap, expired, tampered)
- [ ] `lockout.record_failure / is_locked / clear` testados
- [ ] `POST /auth/login` retorna access_token + cookie refresh, audita login.success/failed/locked
- [ ] `POST /auth/refresh` emite novo access_token, valida session.revoked_at
- [ ] `POST /auth/logout` revoga session, idempotente
- [ ] `GET /auth/me` retorna user info; 401 sem token
- [ ] `require_role(*roles)` 403 quando role nao permitido
- [ ] `audit_action` cm captura before/after corretamente
- [ ] CSRF middleware bloqueia POST sem header X-CSRF == cookie csrf_token; exempt paths funcionam
- [ ] `make test` passa (todos os testes verdes); `make lint` limpo (ruff + mypy --strict)
- [ ] CI verde no GitHub Actions
- [ ] Smoke E2E (login → me → refresh → logout via curl) verde
- [ ] Tag `m2-banco-auth` criada e pushada

## Proximos passos (nao fazem parte do M2)

- M3 (Bot core sem IA): webhook HMAC + Celery + FSM + persistencia
- M4 (SGP + Hermes + tools): integracao com SGPs e LLM
- Particoes mensais auto-criadas via Celery beat (M3+)
- LGPD: endpoints `/clientes/{id}/export` e DELETE com purge agendado (M8)

## Notas operacionais

- `mensagens` ja vem particionada por mes; particoes 2026_05 e 2026_06 criadas no migration. Auto-criacao mensal sera Celery beat em M3+.
- Em desenvolvimento local, `cookie_secure=False` e aplicado automaticamente via `env=development` para evitar perda de cookies em HTTP.
- O `.env` real precisa receber `JWT_SECRET`, `PII_ENCRYPTION_KEY`, `PII_HASH_PEPPER` antes do `make dev`. Smoke E2E (Step 15.3) gera valores para uso local.
- Testes integration que tocam Postgres dependem do docker-compose dev rodando (`make dev` antes de `make test`). Em CI o service Postgres e iniciado pelo runner.
