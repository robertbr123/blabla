"""Health and liveness endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from ondeline_api.deps import DBLike, RedisLike, get_db, get_redis

router = APIRouter(tags=["health"])


@router.get("/livez")
async def livez() -> dict[str, str]:
    """Liveness — process is up."""
    return {"status": "alive"}


@router.get("/healthz")
async def healthz(
    response: Response,
    db: DBLike = Depends(get_db),  # noqa: B008
    redis: RedisLike = Depends(get_redis),  # noqa: B008
) -> dict[str, Any]:
    """Readiness — process can serve traffic (DB and Redis reachable)."""
    checks: dict[str, str] = {}

    try:
        await db.fetchval("SELECT 1")
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc.__class__.__name__}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    all_ok = all(v == "ok" for v in checks.values())
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }
