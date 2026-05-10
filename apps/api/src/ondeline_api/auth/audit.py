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
