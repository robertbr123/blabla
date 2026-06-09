"""Health and liveness endpoints."""
from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text

from ondeline_api.config import get_settings
from ondeline_api.deps import DBSessionLike, RedisLike, get_db, get_redis
from ondeline_api.observability.celery_queue import queue_depths

router = APIRouter(tags=["health"])

# Mantém em sincronia com workers/heartbeat.py:HEARTBEAT_KEY. Definido inline pra
# o processo da API não importar o módulo Celery do worker.
_WORKER_HEARTBEAT_KEY = "health:worker:heartbeat"
_WORKER_HEARTBEAT_MAX_AGE_S = 180  # 3 batidas de 60s sem processar => stale


@router.get("/livez")
async def livez() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/healthz")
async def healthz(
    response: Response,
    db: DBSessionLike = Depends(get_db),  # noqa: B008
    redis: RedisLike = Depends(get_redis),  # noqa: B008
) -> dict[str, Any]:
    checks: dict[str, str] = {}
    celery: dict[str, int] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc.__class__.__name__}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    try:
        s = get_settings()
        url = f"{s.evolution_url.rstrip('/')}/instance/connectionState/{s.evolution_instance}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, headers={"apikey": s.evolution_key})
        if r.status_code == 200:
            state = r.json().get("instance", {}).get("state", "unknown")
            checks["evolution"] = "ok" if state == "open" else f"disconnected ({state})"
        else:
            checks["evolution"] = f"error: HTTP {r.status_code}"
    except Exception as exc:
        checks["evolution"] = f"error: {exc.__class__.__name__}"

    # Worker liveness — heartbeat gravado pelo worker via beat (workers/heartbeat.py).
    # Chave velha/ausente => worker (ou beat) parou de processar. É crítico:
    # entra no 503. NÃO use /healthz como healthcheck do container (o container
    # usa /livez) — senão worker morto reinicia a API em loop.
    try:
        raw = await redis.get(_WORKER_HEARTBEAT_KEY)
        if raw is None:
            checks["worker"] = "stale: sem heartbeat"
        else:
            age = int(time.time()) - int(raw)
            checks["worker"] = (
                "ok" if age <= _WORKER_HEARTBEAT_MAX_AGE_S else f"stale: {age}s sem processar"
            )
    except Exception as exc:
        checks["worker"] = f"error: {exc.__class__.__name__}"

    # Celery queue depth — informativo, nao bloqueia status.
    try:
        celery = await queue_depths(redis)
    except Exception:
        celery = {}

    critical_checks = {k: v for k, v in checks.items() if k in ("db", "redis", "worker")}
    critical_ok = all(v == "ok" for v in critical_checks.values())
    if not critical_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if critical_ok else "degraded",
        "checks": checks,
        "celery": celery,
    }
