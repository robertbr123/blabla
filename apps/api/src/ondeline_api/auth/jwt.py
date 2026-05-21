"""JWT helpers for access and refresh tokens.

- access (staff): 15min, payload {sub, role, kind=staff, type=access, jti, exp, iat}
- access (cliente app): 30d, payload {sub, kind=cliente, type=access, jti, exp, iat}
- refresh: 7d, payload {sub, type=refresh, jti, exp, iat} + token_hash em DB

`kind` separa o publico (staff dashboard/tecnico vs cliente final). Deps
de cada publico exigem o kind correspondente — token nao cruza fronteira.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from uuid import UUID, uuid4

import jwt as pyjwt

from ondeline_api.config import get_settings

ALGO = "HS256"

CLIENTE_ACCESS_TTL_DAYS = 30


class InvalidToken(Exception):
    pass


class InvalidTokenType(InvalidToken):
    pass


class InvalidTokenKind(InvalidToken):
    pass


class TokenExpired(InvalidToken):
    pass


@lru_cache(maxsize=1)
def _secret() -> str:
    s = get_settings().jwt_secret.get_secret_value()
    if not s:
        raise RuntimeError("JWT_SECRET not set")
    return s


def reset_caches() -> None:
    _secret.cache_clear()
    get_settings.cache_clear()


def _now() -> datetime:
    return datetime.now(UTC)


def encode_access_token(user_id: UUID, role: str) -> str:
    settings = get_settings()
    iat = _now()
    exp = iat + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "kind": "staff",
        "type": "access",
        "jti": str(uuid4()),
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO)


def encode_refresh_token(user_id: UUID) -> tuple[str, str]:
    """Returns (token, jti) so caller can persist jti or token_hash."""
    settings = get_settings()
    iat = _now()
    exp = iat + timedelta(days=settings.refresh_token_ttl_days)
    jti = str(uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO), jti


def encode_cliente_access_token(user_id: UUID) -> str:
    iat = _now()
    exp = iat + timedelta(days=CLIENTE_ACCESS_TTL_DAYS)
    payload = {
        "sub": str(user_id),
        "kind": "cliente",
        "type": "access",
        "jti": str(uuid4()),
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO)


def _decode(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = pyjwt.decode(token, _secret(), algorithms=[ALGO])
    except pyjwt.ExpiredSignatureError as exc:
        raise TokenExpired(str(exc)) from exc
    except pyjwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenType(f"expected {expected_type}, got {payload.get('type')}")
    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode a STAFF access token.

    Backward-compat: tokens without `kind` are treated as staff (legacy
    tokens still in circulation predate the kind claim). Tokens with
    `kind != "staff"` (i.e. cliente tokens) are rejected.
    """
    payload = _decode(token, "access")
    kind = payload.get("kind", "staff")
    if kind != "staff":
        raise InvalidTokenKind(f"expected kind=staff, got {kind}")
    return payload


def decode_cliente_access_token(token: str) -> dict[str, Any]:
    """Decode a CLIENTE access token. Requires explicit `kind=cliente`."""
    payload = _decode(token, "access")
    if payload.get("kind") != "cliente":
        raise InvalidTokenKind(
            f"expected kind=cliente, got {payload.get('kind')}"
        )
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode(token, "refresh")


def hash_refresh_token(token: str) -> str:
    """SHA256 hex — used to persist refresh tokens server-side without raw value."""
    return hashlib.sha256(token.encode()).hexdigest()
