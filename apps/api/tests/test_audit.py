"""Tests for audit log helpers."""
from __future__ import annotations

import pytest
from ondeline_api.auth.audit import audit_action, write_audit
from ondeline_api.db.models.identity import AuditLog, Role, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_write_audit_persists_row(db_session: AsyncSession) -> None:
    user = User(
        email="audit-write@example.com",
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

    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "user.update")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].before == {"name": "A"}
    assert rows[0].after == {"name": "A2"}


@pytest.mark.asyncio
async def test_audit_action_captures_before_and_after(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="audit-cm@example.com",
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
    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "user.rename")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].before == {"name": "B", "role": "atendente"}
    assert rows[0].after == {"name": "B-renamed", "role": "atendente"}
