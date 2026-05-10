"""ConfigRepo — get/set jsonb por chave."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Config


class ConfigRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> Any:
        row = (
            await self._session.execute(select(Config.value).where(Config.key == key))
        ).scalar_one_or_none()
        return row

    async def set(self, key: str, value: Any) -> None:
        stmt = pg_insert(Config).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(index_elements=["key"], set_={"value": value})
        await self._session.execute(stmt)
