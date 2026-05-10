"""Circuit breaker simples por tokens/conversa/dia.

Usa Redis com chave `llm_budget:<conversa_id>:<YYYYMMDD>` (counter incremental
com TTL ate fim do dia + 1h). Quando excede o limite, sinaliza ao loop pra
escalar humano em vez de chamar LLM.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class _RedisProto(Protocol):
    async def incrby(self, key: str, amount: int) -> int: ...
    async def expire(self, key: str, seconds: int) -> int: ...
    async def get(self, key: str) -> bytes | None: ...


class TokensBudget:
    def __init__(self, redis: _RedisProto, *, daily_limit: int) -> None:
        self._redis = redis
        self._limit = daily_limit

    def _key(self, conversa_id: str) -> str:
        ymd = datetime.now(tz=UTC).strftime("%Y%m%d")
        return f"llm_budget:{conversa_id}:{ymd}"

    async def add(self, conversa_id: str, tokens: int) -> int:
        key = self._key(conversa_id)
        total = int(await self._redis.incrby(key, max(0, tokens)))
        # TTL ate amanha 00:00 UTC + 1h
        now = datetime.now(tz=UTC)
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = max(60, int((tomorrow - now).total_seconds()) + 3600)
        await self._redis.expire(key, ttl)
        return total

    async def is_over(self, conversa_id: str) -> bool:
        raw = await self._redis.get(self._key(conversa_id))
        if not raw:
            return False
        try:
            return int(raw) >= self._limit
        except ValueError:
            return False
