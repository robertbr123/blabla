"""Measure Celery queue depth by reading Redis broker list lengths."""
from __future__ import annotations

from ondeline_api.deps import RedisLike

CELERY_QUEUES = ("default", "llm", "sgp", "notifications")


async def queue_depths(redis: RedisLike) -> dict[str, int]:
    """Return {queue_name: pending_task_count} for all configured queues.

    Celery 5 stores tasks in Redis as a LIST keyed by the queue name.
    LLEN returns 0 for missing keys, so unconfigured queues report cleanly.
    """
    depths: dict[str, int] = {}
    for q in CELERY_QUEUES:
        depths[q] = int(await redis.llen(q))
    return depths
