"""os_sequence.next_codigo — atomico, formato fixo, sequencial por dia."""
from __future__ import annotations

from datetime import date

import pytest
from ondeline_api.domain.os_sequence import next_codigo
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_codigos_sequenciais_no_mesmo_dia(db_session: AsyncSession) -> None:
    # Use a far-future date unlikely to collide with other test runs.
    d = date(2099, 1, 1)
    a = await next_codigo(db_session, today=d)
    b = await next_codigo(db_session, today=d)
    c = await next_codigo(db_session, today=d)
    assert a == "OS-20990101-001"
    assert b == "OS-20990101-002"
    assert c == "OS-20990101-003"


async def test_dia_diferente_reseta(db_session: AsyncSession) -> None:
    a = await next_codigo(db_session, today=date(2099, 2, 1))
    b = await next_codigo(db_session, today=date(2099, 2, 2))
    assert a == "OS-20990201-001"
    assert b == "OS-20990202-001"
