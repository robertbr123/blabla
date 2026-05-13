"""Celery task: ensure next 3 monthly mensagens partitions exist.

Runs daily at 02:30. Idempotent — uses CREATE TABLE IF NOT EXISTS.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import structlog
from celery import shared_task
from sqlalchemy import create_engine, text

from ondeline_api.config import get_settings

log = structlog.get_logger(__name__)


def _month_window(d: date) -> tuple[date, date]:
    """Return (first_day_of_month, first_day_of_next_month) for the month containing d."""
    start = d.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return start, end


def _next_n_month_windows(today: date, n: int) -> list[tuple[str, date, date]]:
    """Return [(table_name, start, end), ...] for the next n months starting from `today`'s month."""
    windows: list[tuple[str, date, date]] = []
    cur = today.replace(day=1)
    for _ in range(n):
        start, end = _month_window(cur)
        table = f"mensagens_{start:%Y_%m}"
        windows.append((table, start, end))
        cur = end
    return windows


def ensure_partitions(today: date, n: int = 3) -> list[str]:
    """Create (idempotently) the next n monthly partitions. Returns list of table names."""
    settings = get_settings()
    sync_url = settings.database_url_sync or settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    created: list[str] = []
    try:
        with engine.connect() as conn:
            for table, start, end in _next_n_month_windows(today, n):
                conn.execute(text(
                    f"CREATE TABLE IF NOT EXISTS {table} "
                    f"PARTITION OF mensagens FOR VALUES FROM ('{start}') TO ('{end}')"
                ))
                created.append(table)
    finally:
        engine.dispose()
    return created


@shared_task(
    bind=True,
    name="ondeline_api.workers.partition_jobs.ensure_future_mensagens_partitions",
    queue="default",
)
def ensure_future_mensagens_partitions(self: Any) -> dict[str, Any]:
    try:
        created = ensure_partitions(today=datetime.now().date(), n=3)
        log.info("partition_job.completed", created=created)
        return {"created": created}
    except Exception as e:
        log.error("partition_job.failed", error=str(e), exc_info=True)
        raise
