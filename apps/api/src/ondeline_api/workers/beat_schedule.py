"""Celery Beat schedule config.

Jobs:
- planner_jobs (every 30min):  vencimentos + atrasos + pagamentos
- followup_os_job (every 1h):  envia CSAT 24h apos OS concluida
- manutencao_job (every 15min): broadcast manutencoes proximas
- send_notifications (every 1min): processa fila Notificacao pendente
- lgpd_purge_job (daily 03:00): deleta registros expirados (retention_until < now)
- ensure_future_mensagens_partitions (daily 02:30): cria as proximas 3 particoes mensais
"""
from __future__ import annotations

from typing import Any

from celery.schedules import crontab

BEAT_SCHEDULE: dict[str, dict[str, Any]] = {
    "vencimentos-atrasos-pagamentos": {
        "task": "ondeline_api.workers.notify_jobs.run_planner_jobs",
        "schedule": crontab(minute="*/30"),
    },
    "follow-up-os": {
        "task": "ondeline_api.workers.notify_jobs.followup_os_job",
        "schedule": crontab(minute=0),  # hourly
    },
    "manutencoes": {
        "task": "ondeline_api.workers.notify_jobs.manutencao_job",
        "schedule": crontab(minute="*/15"),
    },
    "send-pending-notifications": {
        "task": "ondeline_api.workers.notify_sender.flush_pending",
        "schedule": crontab(minute="*"),  # every minute
    },
    "lgpd-purge": {
        "task": "ondeline_api.workers.notify_jobs.lgpd_purge_job",
        "schedule": crontab(hour=3, minute=0),
    },
    "ensure-future-partitions": {
        "task": "ondeline_api.workers.partition_jobs.ensure_future_mensagens_partitions",
        "schedule": crontab(hour=2, minute=30),
    },
}
