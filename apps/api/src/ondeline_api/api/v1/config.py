"""Config k/v endpoints — admin only."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.config import ConfigOut, ConfigSet
from ondeline_api.auth.audit import write_audit
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import Config
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.config import ConfigRepo

router = APIRouter(prefix="/api/v1/config", tags=["config"])
_admin_dep = Depends(require_role(Role.ADMIN))


@router.get("/{key}", response_model=ConfigOut, dependencies=[_admin_dep])
async def get_config(
    key: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConfigOut:
    stmt = select(Config).where(Config.key == key)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="config key not found")
    return ConfigOut.model_validate(row)


@router.put("/{key}", response_model=ConfigOut, dependencies=[_admin_dep])
async def set_config(
    key: str,
    body: ConfigSet,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ConfigOut:
    repo = ConfigRepo(session)
    # snapshot old value for audit
    old = await repo.get(key)
    await repo.set(key, body.value)
    await session.flush()

    # fetch fresh row (upsert won't populate ORM identity map)
    stmt = select(Config).where(Config.key == key)
    row = (await session.execute(stmt)).scalar_one()
    row.updated_by = user.id
    await session.flush()
    await session.refresh(row)

    await write_audit(
        session,
        user_id=user.id,
        action="config.set",
        resource_type="config",
        resource_id=key,
        before={"value": old},
        after={"value": body.value},
    )
    return ConfigOut.model_validate(row)
