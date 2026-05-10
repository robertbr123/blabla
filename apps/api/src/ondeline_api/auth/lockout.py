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
