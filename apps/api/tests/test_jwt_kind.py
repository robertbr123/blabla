"""JWT — claim `kind` separa staff de cliente."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.auth import jwt as jwt_mod


def test_staff_token_default_kind_staff() -> None:
    uid = uuid4()
    tok = jwt_mod.encode_access_token(uid, role="admin")
    payload = jwt_mod.decode_access_token(tok)
    assert payload["kind"] == "staff"
    assert payload["sub"] == str(uid)


def test_cliente_token_has_kind_cliente() -> None:
    uid = uuid4()
    tok = jwt_mod.encode_cliente_access_token(uid)
    payload = jwt_mod.decode_cliente_access_token(tok)
    assert payload["kind"] == "cliente"


def test_decode_cliente_rejects_staff_token() -> None:
    uid = uuid4()
    staff_tok = jwt_mod.encode_access_token(uid, role="admin")
    with pytest.raises(jwt_mod.InvalidTokenKind):
        jwt_mod.decode_cliente_access_token(staff_tok)


def test_decode_staff_rejects_cliente_token() -> None:
    uid = uuid4()
    cliente_tok = jwt_mod.encode_cliente_access_token(uid)
    with pytest.raises(jwt_mod.InvalidTokenKind):
        jwt_mod.decode_access_token(cliente_tok)


def test_decode_staff_accepts_legacy_token_without_kind() -> None:
    """Tokens emitidos antes da claim `kind` (sem o campo) ainda valem como staff."""
    import jwt as pyjwt

    from ondeline_api.auth.jwt import ALGO, _secret

    payload = {
        "sub": str(uuid4()),
        "role": "admin",
        "type": "access",
        "jti": str(uuid4()),
        "iat": 1_700_000_000,
        "exp": 9_999_999_999,
    }
    legacy = pyjwt.encode(payload, _secret(), algorithm=ALGO)
    decoded = jwt_mod.decode_access_token(legacy)
    assert decoded["sub"] == payload["sub"]
