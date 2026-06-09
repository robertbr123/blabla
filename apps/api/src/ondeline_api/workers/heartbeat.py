"""Heartbeat do worker — alimenta o /healthz para detectar processamento parado.

O Beat agenda `worker_heartbeat_task` a cada 1 min; o worker executa e grava um
timestamp em Redis (`health:worker:heartbeat`, TTL 1h). Se o worker (ou o beat)
parar, a chave envelhece e o /healthz passa a reportar `worker: stale`.

Testa o pipeline real enqueue→consume — a mesma classe de falha do bug de task
não-registrada (task enfileirada mas nunca consumida).
"""
from __future__ import annotations

import time
from typing import Any

import structlog

from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, run_task

log = structlog.get_logger(__name__)

HEARTBEAT_KEY = "health:worker:heartbeat"
HEARTBEAT_TTL_S = 3600  # 1h — chave sobrevive pra /healthz computar a idade mesmo bem velha


async def _write_heartbeat() -> int:
    redis = await get_redis()
    now = int(time.time())
    await redis.set(HEARTBEAT_KEY, str(now), ex=HEARTBEAT_TTL_S)
    return now


@celery_app.task(
    name="ondeline_api.workers.heartbeat.worker_heartbeat_task",
    queue="default",
)
def worker_heartbeat_task() -> dict[str, Any]:
    ts = run_task(_write_heartbeat)
    return {"ok": True, "ts": ts}
