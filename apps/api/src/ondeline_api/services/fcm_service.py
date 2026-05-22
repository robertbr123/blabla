"""Wrapper Firebase Cloud Messaging (FCM) — push out-of-app pro cliente-app.

Lazy init do firebase-admin. Graceful degradation:
- Sem credenciais → `send_push` retorna False, log warning, nao quebra.
- Token invalido → marca user.push_token=None (limpa stale).
"""
from __future__ import annotations

import base64
import json
import threading

import structlog

from ondeline_api.config import get_settings

log = structlog.get_logger(__name__)

_lock = threading.Lock()
_initialized = False
_disabled = False  # true se nao tem credenciais OU init falhou


def _ensure_initialized() -> bool:
    """Inicializa firebase-admin uma vez. Retorna False se nao for possivel."""
    global _initialized, _disabled
    if _initialized:
        return True
    if _disabled:
        return False
    with _lock:
        if _initialized:
            return True
        if _disabled:
            return False
        s = get_settings()
        cred_dict = None
        if s.firebase_credentials_b64:
            try:
                cred_dict = json.loads(
                    base64.b64decode(s.firebase_credentials_b64).decode("utf-8")
                )
            except Exception as e:
                log.warning("fcm.cred_b64_invalid", error=str(e))
        if cred_dict is None and s.firebase_credentials_path:
            try:
                with open(s.firebase_credentials_path) as f:
                    cred_dict = json.load(f)
            except Exception as e:
                log.warning("fcm.cred_path_invalid", error=str(e))
        if cred_dict is None:
            log.info("fcm.disabled_no_credentials")
            _disabled = True
            return False
        try:
            import firebase_admin
            from firebase_admin import credentials

            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _initialized = True
            log.info("fcm.initialized")
            return True
        except Exception as e:
            log.error("fcm.init_failed", error=str(e))
            _disabled = True
            return False


def send_push(
    token: str,
    titulo: str,
    corpo: str,
    data: dict[str, str] | None = None,
) -> tuple[bool, bool]:
    """Envia push pro device token.

    Retorna `(enviado, token_invalido)`:
    - `enviado=True`: FCM aceitou.
    - `enviado=False, token_invalido=True`: token nao existe mais — caller
      deve limpar `user.push_token`.
    - `enviado=False, token_invalido=False`: falha transitoria, retry possivel.
    """
    if not token:
        return False, False
    if not _ensure_initialized():
        return False, False
    try:
        from firebase_admin import messaging
        from firebase_admin.exceptions import (
            FirebaseError,
            NotFoundError,
        )

        msg = messaging.Message(
            notification=messaging.Notification(title=titulo, body=corpo),
            data=data or {},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    icon="ic_notification",
                    color="#14B8B0",
                    channel_id="default",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1),
                ),
            ),
        )
        msg_id = messaging.send(msg)
        log.info("fcm.sent", msg_id=msg_id, token_prefix=token[:12])
        return True, False
    except NotFoundError:
        # Token nao registrado mais — limpar do DB.
        log.info("fcm.token_invalid", token_prefix=token[:12])
        return False, True
    except FirebaseError as e:
        # Outras falhas (UNREGISTERED, INVALID_ARGUMENT) sao consideradas
        # token invalido pra evitar retries infinitos.
        code = getattr(e, "code", "") or ""
        if code in ("UNREGISTERED", "INVALID_ARGUMENT", "SENDER_ID_MISMATCH"):
            log.info("fcm.token_invalid", code=code, token_prefix=token[:12])
            return False, True
        log.warning("fcm.firebase_error", code=code, error=str(e))
        return False, False
    except Exception as e:
        log.warning("fcm.unknown_error", error=str(e))
        return False, False
