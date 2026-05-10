"""HMAC-SHA256 signature verification for inbound webhooks.

Evolution API envia o cabecalho `X-Hub-Signature-256` no formato
`sha256=<hex>`. Validamos com `hmac.compare_digest` para evitar timing oracles.
"""
from __future__ import annotations

import hashlib
import hmac


PREFIX = "sha256="


def verify_signature(body: bytes, header_value: str | None, secret: str) -> bool:
    """Return True iff `header_value` is a valid sha256 HMAC of `body` under `secret`.

    Falha cedo (e silenciosamente) se algum dos parametros for vazio. Toda comparacao
    de bytes usa `compare_digest` para resistir a timing attacks.
    """
    if not secret or not header_value or not header_value.startswith(PREFIX):
        return False
    provided_hex = header_value[len(PREFIX):].lower()
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    # `compare_digest` em strings hex compara em tempo constante.
    return hmac.compare_digest(provided_hex, expected)
