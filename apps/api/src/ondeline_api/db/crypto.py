"""PII field helpers — passthrough when keys are not configured."""
from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptography.fernet import Fernet

from ondeline_api.config import get_settings


@lru_cache(maxsize=1)
def _fernet_or_none() -> Fernet | None:
    key = get_settings().pii_encryption_key.get_secret_value()
    if not key:
        return None
    from cryptography.fernet import Fernet as _Fernet
    return _Fernet(key.encode())


@lru_cache(maxsize=1)
def _pepper_or_none() -> bytes | None:
    pepper = get_settings().pii_hash_pepper.get_secret_value()
    return pepper.encode() if pepper else None


def encrypt_pii(value: str) -> str:
    f = _fernet_or_none()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_pii(token: str) -> str:
    f = _fernet_or_none()
    if f is None:
        return token
    return f.decrypt(token.encode()).decode()


def hash_pii(value: str) -> str:
    pepper = _pepper_or_none()
    if pepper is None:
        return hashlib.sha256(value.encode()).hexdigest()
    return hmac.new(pepper, value.encode(), hashlib.sha256).hexdigest()


def reset_caches() -> None:
    _fernet_or_none.cache_clear()
    _pepper_or_none.cache_clear()
    get_settings.cache_clear()
