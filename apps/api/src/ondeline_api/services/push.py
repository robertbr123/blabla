"""FCM push notifications via firebase-admin.

`send_push_to_user(user_id, title, body, data)` busca todos os tokens ativos
do user e envia pra cada. Tokens invalidados pelo FCM (UNREGISTERED/INVALID
sao auto-revogados em DB.

Configuracao via env:
- FIREBASE_CREDENTIALS_B64: service account JSON em base64 (recomendado)
- FIREBASE_CREDENTIALS_PATH: caminho absoluto pro JSON (alternativa local)

Se nenhum dos dois, push fica desligado — `send_push_to_user` vira no-op.
Util pra dev local sem Firebase configurado.
"""
from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.config import get_settings

log = structlog.get_logger(__name__)

_app = None  # firebase_admin.App nomeado "tecnico" (projeto blabla-mobile)
_disabled = False

# Nome do app firebase_admin do tecnico. Projeto Firebase proprio (blabla-mobile),
# separado do cliente (fcm_service.py / ondeline-clients) — por isso app nomeado.
_APP_NAME = "tecnico"


def _ensure_app():
    """Inicializa o app firebase nomeado 'tecnico' uma vez. Retorna o App ou None.

    Credencial: firebase_credentials_tecnico_b64 (projeto blabla-mobile). SEM
    fallback pro b64 legado — esse aponta pro projeto do cliente e enviaria pro
    projeto errado. Vazio = push do tecnico desligado (no-op gracioso).
    """
    global _app, _disabled
    if _app is not None:
        return _app
    if _disabled:
        return None

    s = get_settings()
    cred_json: dict[str, Any] | None = None
    if s.firebase_credentials_tecnico_b64:
        try:
            cred_json = json.loads(
                base64.b64decode(s.firebase_credentials_tecnico_b64)
            )
        except Exception as e:
            log.error("push.config.invalid_b64", error=str(e))
            _disabled = True
            return None

    if cred_json is None:
        log.info("push.disabled.no_credentials")
        _disabled = True
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(cred_json)
        try:
            _app = firebase_admin.get_app(_APP_NAME)
        except ValueError:
            _app = firebase_admin.initialize_app(cred, name=_APP_NAME)
        log.info("push.initialized", app=_APP_NAME)
        return _app
    except Exception as e:
        log.error("push.init.failed", error=str(e))
        _disabled = True
        return None


async def send_push_to_user(
    session: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Envia push pra todos os tokens nao revogados de um user.

    Retorna a quantidade de pushes bem-sucedidos. Falhas individuais
    (token invalido) sao logadas e o token e auto-revogado em DB. Falhas
    de transporte sao silenciadas — push e best-effort.

    NAO levanta excecao. Falha de FCM nunca deve quebrar o fluxo de OS.
    """
    app = _ensure_app()
    if app is None:
        return 0

    from firebase_admin import messaging

    from ondeline_api.db.models.identity import DeviceToken

    tokens_rows = (
        await session.execute(
            select(DeviceToken).where(
                DeviceToken.user_id == user_id,
                DeviceToken.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    tokens_list = list(tokens_rows)
    if not tokens_list:
        return 0

    sent = 0
    for row in tokens_list:
        try:
            msg = messaging.Message(
                token=row.token,
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        channel_id="ondeline_default",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1),
                    ),
                ),
            )
            messaging.send(msg, app=app)  # sync — firebase-admin nao tem async API
            sent += 1
        except Exception as e:
            err = str(e).lower()
            # Tokens invalidos: revoga em DB pra parar de tentar.
            if "unregistered" in err or "invalid" in err or "not-found" in err:
                row.revoked_at = datetime.now(tz=UTC)
                log.info(
                    "push.token.auto_revoked",
                    user_id=str(user_id),
                    reason=str(e)[:120],
                )
            else:
                log.warning(
                    "push.send.failed",
                    user_id=str(user_id),
                    error=str(e)[:240],
                )
    if sent > 0:
        log.info("push.sent", user_id=str(user_id), count=sent)
    return sent


async def send_push_to_tecnico(
    session: AsyncSession,
    tecnico_id: UUID,
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Resolve tecnico_id -> user_id e envia."""
    from ondeline_api.db.models.business import Tecnico

    tec = (
        await session.execute(select(Tecnico).where(Tecnico.id == tecnico_id))
    ).scalar_one_or_none()
    if tec is None or tec.user_id is None:
        return 0
    return await send_push_to_user(
        session, tec.user_id, title=title, body=body, data=data
    )
