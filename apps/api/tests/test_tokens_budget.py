from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis
from ondeline_api.services.tokens_budget import TokensBudget

pytestmark = pytest.mark.asyncio


async def test_add_e_over_threshold() -> None:
    b = TokensBudget(FakeRedis(decode_responses=False), daily_limit=100)
    assert (await b.add("c1", 30)) == 30
    assert (await b.add("c1", 30)) == 60
    assert await b.is_over("c1") is False
    assert (await b.add("c1", 50)) == 110
    assert await b.is_over("c1") is True


async def test_outra_conversa_independente() -> None:
    b = TokensBudget(FakeRedis(decode_responses=False), daily_limit=100)
    await b.add("c1", 110)
    assert await b.is_over("c2") is False
