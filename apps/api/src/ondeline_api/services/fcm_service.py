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
_app = None  # firebase_admin.App nomeado "cliente" (projeto ondeline-clients)
_disabled = False  # true se nao tem credenciais OU init falhou

# Nome do app firebase_admin do cliente. Isolado do app do tecnico (push.py),
# que usa outro projeto Firebase — por isso apps nomeados, nao o default.
_APP_NAME = "cliente"


def _ensure_app():
    """Inicializa o app firebase nomeado 'cliente' uma vez. Retorna o App ou None.

    Credencial: firebase_credentials_cliente_b64 (projeto ondeline-clients) com
    fallback pro firebase_credentials_b64/_path antigos, mantendo compat com
    deploys que so setaram a env legada.
    """
    global _app, _disabled
    if _app is not None:
        return _app
    if _disabled:
        return None
    with _lock:
        if _app is not None:
            return _app
        if _disabled:
            return None
        s = get_settings()
        cred_dict = None
        cred_b64 = s.firebase_credentials_cliente_b64 or s.firebase_credentials_b64
        if cred_b64:
            try:
                cred_dict = json.loads(base64.b64decode(cred_b64).decode("utf-8"))
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
            return None
        try:
            import firebase_admin
            from firebase_admin import credentials

            cred = credentials.Certificate(cred_dict)
            try:
                _app = firebase_admin.get_app(_APP_NAME)
            except ValueError:
                _app = firebase_admin.initialize_app(cred, name=_APP_NAME)
            log.info("fcm.initialized", app=_APP_NAME)
            return _app
        except Exception as e:
            log.error("fcm.init_failed", error=str(e))
            _disabled = True
            return None


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
    app = _ensure_app()
    if app is None:
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
        msg_id = messaging.send(msg, app=app)
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
