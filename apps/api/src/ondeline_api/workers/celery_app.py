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

from ondeline_api.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "ondeline",
        broker=settings.effective_celery_broker(),
        backend=settings.effective_celery_result_backend(),
        include=[
            "ondeline_api.workers.inbound",
            "ondeline_api.workers.outbound",
        ],
    )
    app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_default_queue="default",
        task_queues={
            "default": {"exchange": "default", "routing_key": "default"},
            "llm": {"exchange": "llm", "routing_key": "llm"},
            "sgp": {"exchange": "sgp", "routing_key": "sgp"},
            "notifications": {
                "exchange": "notifications",
                "routing_key": "notifications",
            },
        },
        task_routes={
            "ondeline_api.workers.inbound.process_inbound_message_task": {
                "queue": "default"
            },
            "ondeline_api.workers.outbound.send_outbound_task": {"queue": "default"},
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="America/Sao_Paulo",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = create_celery_app()
