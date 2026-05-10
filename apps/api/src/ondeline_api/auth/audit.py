"""Audit log helpers.

`write_audit` escreve uma entrada diretamente. `audit_action` e um async
context manager que captura before/after e escreve ao final do bloco.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
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
