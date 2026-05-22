"""Celery task que envia push FCM out-of-app pro cliente.

Disparada por `cliente_app_notif.notify_user` quando user tem push_token.
Fire-and-forget — falha aqui nao deve travar criacao da notif no DB.

Se token for invalido, limpa `cliente_app_users.push_token` pra parar
de tentar.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import update

from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.services.fcm_service import send_push
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _enviar(
    user_id: str,
    token: str,
    titulo: str,
    corpo: str,
    data: dict[str, str] | None,
) -> None:
    sent, invalid = send_push(token, titulo, corpo, data or {})
    if invalid:
        async with task_session() as session:
            await session.execute(
                update(ClienteAppUser)
                .where(ClienteAppUser.id == UUID(user_id))
                .values(push_token=None)
            )
            await session.commit()
        log.info("fcm.token_cleared", user_id=user_id)
    elif sent:
        log.info("fcm.delivered", user_id=user_id)


@celery_app.task(
    name="ondeline_api.workers.fcm_push.send_user_push",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def send_user_push(
    self: object,
    user_id: str,
    token: str,
    titulo: str,
    corpo: str,
    data: dict[str, str] | None = None,
) -> None:
    """Envia push individual. Roda na fila default (rapido)."""
    try:
        run_task(lambda: _enviar(user_id, token, titulo, corpo, data))
    except Exception as e:
        log.warning("fcm.task_error", user_id=user_id, error=str(e))
        # Soft fail — push nao e critico, melhor nao retry agressivo.
