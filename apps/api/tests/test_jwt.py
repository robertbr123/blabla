"""Tests for JWT encode/decode (access + refresh tokens)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from freezegun import freeze_time
from ondeline_api.auth import jwt as jwt_mod


@pytest.fixture(autouse=True)
def _jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-bytes-minimum-please")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost:5432/x")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_mod.reset_caches()


def test_encode_decode_access_roundtrip() -> None:
    user_id = uuid4()
    token = jwt_mod.encode_access_token(user_id, role="admin")

    payload = jwt_mod.decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


def test_encode_decode_refresh_roundtrip() -> None:
    user_id = uuid4()
    token, jti = jwt_mod.encode_refresh_token(user_id)

    payload = jwt_mod.decode_refresh_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_decode_access_rejects_refresh_token() -> None:
    user_id = uuid4()
    refresh, _ = jwt_mod.encode_refresh_token(user_id)

    with pytest.raises(jwt_mod.InvalidTokenType):
        jwt_mod.decode_access_token(refresh)


def test_decode_refresh_rejects_access_token() -> None:
    user_id = uuid4()
    access = jwt_mod.encode_access_token(user_id, role="admin")

    with pytest.raises(jwt_mod.InvalidTokenType):
        jwt_mod.decode_refresh_token(access)


def test_decode_expired_token_raises() -> None:
    user_id = uuid4()
    with freeze_time("2026-01-01 12:00:00"):
        token = jwt_mod.encode_access_token(user_id, role="admin")
    with freeze_time("2026-01-01 13:30:00"):
        with pytest.raises(jwt_mod.TokenExpired):
            jwt_mod.decode_access_token(token)


def test_decode_tampered_token_raises() -> None:
    user_id = uuid4()
    token = jwt_mod.encode_access_token(user_id, role="admin")
    tampered = token[:-4] + "AAAA"

    with pytest.raises(jwt_mod.InvalidToken):
        jwt_mod.decode_access_token(tampered)


def test_hash_refresh_token_deterministic() -> None:
    h1 = jwt_mod.hash_refresh_token("abc")
    h2 = jwt_mod.hash_refresh_token("abc")
    assert h1 == h2
    assert len(h1) == 64
