"""Tests for PII encryption helpers."""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken
from ondeline_api.db import crypto


@pytest.fixture(autouse=True)
def _crypto_env(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PII_ENCRYPTION_KEY", key)
    monkeypatch.setenv("PII_HASH_PEPPER", "test-pepper-32-bytes-of-randomness!")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://x:x@localhost:5432/x"
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    crypto.reset_caches()


def test_encrypt_decrypt_roundtrip() -> None:
    cipher = crypto.encrypt_pii("12345678900")

    assert cipher != "12345678900"
    assert crypto.decrypt_pii(cipher) == "12345678900"


def test_encrypt_returns_str_not_bytes() -> None:
    cipher = crypto.encrypt_pii("Robério")
    assert isinstance(cipher, str)


def test_encrypt_empty_string_roundtrips() -> None:
    cipher = crypto.encrypt_pii("")
    assert crypto.decrypt_pii(cipher) == ""


def test_decrypt_invalid_ciphertext_raises() -> None:
    with pytest.raises(InvalidToken):
        crypto.decrypt_pii("not-a-fernet-token")


def test_hash_pii_is_deterministic() -> None:
    h1 = crypto.hash_pii("12345678900")
    h2 = crypto.hash_pii("12345678900")
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_hash_pii_differs_for_different_inputs() -> None:
    assert crypto.hash_pii("11111111111") != crypto.hash_pii("22222222222")


def test_missing_encryption_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_ENCRYPTION_KEY", "")
    crypto.reset_caches()
    with pytest.raises(RuntimeError, match="PII_ENCRYPTION_KEY"):
        crypto.encrypt_pii("x")


def test_missing_pepper_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_HASH_PEPPER", "")
    crypto.reset_caches()
    with pytest.raises(RuntimeError, match="PII_HASH_PEPPER"):
        crypto.hash_pii("x")
