"""Tests for argon2id password hashing."""
from __future__ import annotations

import pytest
from ondeline_api.auth import passwords


def test_hash_and_verify_correct_password() -> None:
    h = passwords.hash_password("s3cret-Pa$$word")
    assert passwords.verify_password("s3cret-Pa$$word", h) is True


def test_verify_wrong_password() -> None:
    h = passwords.hash_password("s3cret-Pa$$word")
    assert passwords.verify_password("wrong", h) is False


def test_hash_uses_argon2id_format() -> None:
    h = passwords.hash_password("anything")
    assert h.startswith("$argon2id$")


def test_verify_invalid_hash_returns_false() -> None:
    assert passwords.verify_password("x", "not-a-hash") is False


def test_two_hashes_differ_due_to_salt() -> None:
    h1 = passwords.hash_password("same")
    h2 = passwords.hash_password("same")
    assert h1 != h2
    assert passwords.verify_password("same", h1)
    assert passwords.verify_password("same", h2)


def test_empty_password_raises() -> None:
    with pytest.raises(ValueError):
        passwords.hash_password("")
