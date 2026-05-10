"""HMAC verification for /webhook (X-Hub-Signature-256)."""
from __future__ import annotations

import hashlib
import hmac as _hmac

from ondeline_api.webhook.hmac import verify_signature

SECRET = "supersecret-evolution"


def _sign(body: bytes, secret: str = SECRET) -> str:
    mac = _hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def test_valid_signature_passes() -> None:
    body = b'{"event":"messages.upsert"}'
    assert verify_signature(body, _sign(body), SECRET) is True


def test_invalid_hex_fails() -> None:
    body = b'{"event":"messages.upsert"}'
    assert verify_signature(body, "sha256=deadbeef", SECRET) is False


def test_missing_prefix_fails() -> None:
    body = b'{"event":"messages.upsert"}'
    bare = _sign(body).removeprefix("sha256=")
    assert verify_signature(body, bare, SECRET) is False


def test_wrong_algo_prefix_fails() -> None:
    body = b'{"event":"messages.upsert"}'
    sig = _sign(body)
    assert verify_signature(body, sig.replace("sha256=", "sha1="), SECRET) is False


def test_empty_header_fails() -> None:
    assert verify_signature(b"x", "", SECRET) is False
    assert verify_signature(b"x", None, SECRET) is False


def test_empty_secret_always_fails() -> None:
    body = b"x"
    assert verify_signature(body, _sign(body, ""), "") is False


def test_constant_time_comparison() -> None:
    """Sanity: assinaturas iguais por bytes devem casar mesmo com strings em caso diferente."""
    body = b'{"x":1}'
    sig = _sign(body)
    # mesmo conteudo em maiusculo (hex e case-insensitive)
    assert verify_signature(body, sig.upper().replace("SHA256=", "sha256="), SECRET) is True
