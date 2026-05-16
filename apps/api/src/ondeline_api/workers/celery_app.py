"""Celery application factory.

Filas:
  - default: tarefas leves (envio outbound, atualizacoes simples)
  - llm: chamadas LLM (M4)
  - sgp: integracoes SGP (M4)
  - notifications: envio agendado (M5)

Result backend tambem em Redis. Acks LATE para evitar perda em crash mid-task,
e prefetch=1 para distribuir trabalho uniformemente.
"""
from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from ondeline_api.config import get_settings
from ondeline_api.services.logging_config import configure_logging
from ondeline_api.services.otel_init import init_otel
from ondeline_api.services.sentry_init import init_sentry
from ondeline_api.workers.queues import DEFAULT_QUEUE, QUEUES


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "ondeline",
        broker=settings.effective_celery_broker(),
        backend=settings.effective_celery_result_backend(),
        include=[
            "ondeline_api.workers.inbound",
            "ondeline_api.workers.outbound",
            "ondeline_api.workers.llm_turn",
            "ondeline_api.workers.notify_jobs",
            "ondeline_api.workers.notify_sender",
            "ondeline_api.workers.partition_jobs",
            "ondeline_api.workers.followup",
        ],
    )
    app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_default_queue=DEFAULT_QUEUE,
        task_queues={q: {"exchange": q, "routing_key": q} for q in QUEUES},
        task_routes={
            "ondeline_api.workers.inbound.process_inbound_message_task": {
                "queue": "default"
            },
            "ondeline_api.workers.outbound.send_outbound_task": {"queue": "default"},
            "ondeline_api.workers.llm_turn.llm_turn_task": {"queue": "llm"},
            "ondeline_api.workers.notify_jobs.run_planner_jobs": {"queue": "notifications"},
            "ondeline_api.workers.notify_jobs.followup_os_job": {"queue": "notifications"},
            "ondeline_api.workers.notify_jobs.manutencao_job": {"queue": "notifications"},
            "ondeline_api.workers.notify_jobs.lgpd_purge_job": {"queue": "notifications"},
            "ondeline_api.workers.notify_sender.flush_pending": {"queue": "notifications"},
            "ondeline_api.workers.followup.followup_os_task": {"queue": "notifications"},
            "ondeline_api.workers.partition_jobs.ensure_future_mensagens_partitions": {
                "queue": "default"
            },
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="America/Sao_Paulo",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
    )
    from ondeline_api.workers.beat_schedule import BEAT_SCHEDULE
    app.conf.beat_schedule = BEAT_SCHEDULE
    return app


celery_app = create_celery_app()


@worker_process_init.connect
def _init_worker_logging(**_kwargs: object) -> None:
    """Reconfigure logging + Sentry + OTel inside each forked Celery worker process."""
    configure_logging()
    init_sentry(component="worker")
    init_otel(component="worker")
