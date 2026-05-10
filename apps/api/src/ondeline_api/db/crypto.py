"""PII encryption (Fernet) + deterministic hashing (HMAC-SHA256 with pepper).

Used by ORM models to store sensitive fields encrypted at rest while
preserving the ability to look up by hash (e.g. CPF).
"""
from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet

from ondeline_api.config import get_settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = get_settings().pii_encryption_key.get_secret_value()
    if not key:
        raise RuntimeError(
            "PII_ENCRYPTION_KEY not set. Generate with: "
            "python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode())


@lru_cache(maxsize=1)
def _pepper() -> bytes:
    pepper = get_settings().pii_hash_pepper.get_secret_value()
    if not pepper:
        raise RuntimeError("PII_HASH_PEPPER not set")
    return pepper.encode()


def encrypt_pii(value: str) -> str:
    """Encrypt a UTF-8 string. Returns Fernet token as str (URL-safe base64)."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_pii(token: str) -> str:
    """Decrypt a Fernet token back to UTF-8 string. Raises InvalidToken on tamper."""
    return _fernet().decrypt(token.encode()).decode()


def hash_pii(value: str) -> str:
    """Deterministic HMAC-SHA256 hex digest. Use for indexable fields like cpf_hash."""
    return hmac.new(_pepper(), value.encode(), hashlib.sha256).hexdigest()


def reset_caches() -> None:
    """Test helper: clear cached Fernet and pepper so env reload takes effect."""
    _fernet.cache_clear()
    _pepper.cache_clear()
    # get_settings is lru_cached — clear it too so env vars are re-read
    get_settings.cache_clear()
