"""Conversation event pub/sub via Redis.

Producers (responder, inbound worker) call `publish(conversa_id, event)`.
Consumers (SSE endpoint) call `subscribe(conversa_id)` and yield events.

Channel naming: `conv_events:{conversa_id}`. JSON-encoded payloads.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
import structlog

log = structlog.get_logger(__name__)


def _channel(conversa_id: UUID) -> str:
    return f"conv_events:{conversa_id}"


async def publish(redis: aioredis.Redis[bytes], conversa_id: UUID, event: dict[str, Any]) -> int:
    """Publish event to the conversa channel. Returns number of subscribers."""
    payload = json.dumps(event, default=str).encode("utf-8")
    n = await redis.publish(_channel(conversa_id), payload)
    log.debug("conv_events.published", conversa_id=str(conversa_id), subs=n)
    return int(n)


async def subscribe(
    redis: aioredis.Redis[bytes], conversa_id: UUID
) -> AsyncIterator[dict[str, Any]]:
    """Subscribe to events for a conversa. Yields decoded event dicts."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(_channel(conversa_id))
    try:
        async for raw in pubsub.listen():
            if raw is None or raw.get("type") != "message":
                continue
            data = raw.get("data")
            if isinstance(data, bytes):
                try:
                    yield json.loads(data.decode("utf-8"))
                except json.JSONDecodeError:
                    log.warning("conv_events.bad_payload")
                    continue
    finally:
        try:
            await pubsub.unsubscribe(_channel(conversa_id))
            await pubsub.aclose()  # type: ignore[attr-defined]
        except Exception:
            pass
