"""Geracao atomica de codigo OS-YYYYMMDD-NNN.

Estrategia: tabela `os_sequence (date PK, n int)` + UPSERT atomico que
incrementa `n` numa unica round-trip (`INSERT ... ON CONFLICT DO UPDATE
SET n = os_sequence.n + 1 RETURNING n`).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def next_codigo(session: AsyncSession, *, today: date | None = None) -> str:
    d = today or date.today()
    stmt = text(
        """
        INSERT INTO os_sequence (date, n)
        VALUES (:d, 1)
        ON CONFLICT (date) DO UPDATE SET n = os_sequence.n + 1
        RETURNING n
        """
    )
    result = await session.execute(stmt, {"d": d})
    n = int(result.scalar_one())
    return f"OS-{d.strftime('%Y%m%d')}-{n:03d}"
