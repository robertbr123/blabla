"""Pagination cursor encode/decode + clamp."""
from __future__ import annotations

from datetime import UTC, datetime

from ondeline_api.api.schemas.pagination import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    CursorPage,
    clamp_limit,
    decode_cursor,
    encode_cursor,
)


def test_encode_decode_roundtrip() -> None:
    ts = datetime(2026, 5, 10, 12, 34, 56, tzinfo=UTC)
    enc = encode_cursor(ts)
    assert isinstance(enc, str)
    assert "=" not in enc
    dec = decode_cursor(enc)
    assert dec == ts


def test_decode_none_returns_none() -> None:
    assert decode_cursor(None) is None
    assert decode_cursor("") is None


def test_decode_invalid_returns_none() -> None:
    assert decode_cursor("not-base64!!!") is None
    assert decode_cursor("dGVzdA") is None


def test_clamp_limit_default() -> None:
    assert clamp_limit(None) == DEFAULT_LIMIT
    assert clamp_limit(0) == DEFAULT_LIMIT
    assert clamp_limit(-5) == DEFAULT_LIMIT


def test_clamp_limit_caps_at_max() -> None:
    assert clamp_limit(10) == 10
    assert clamp_limit(MAX_LIMIT) == MAX_LIMIT
    assert clamp_limit(MAX_LIMIT + 1) == MAX_LIMIT


def test_cursor_page_empty() -> None:
    page: CursorPage[str] = CursorPage()
    assert page.items == []
    assert page.next_cursor is None


def test_cursor_page_with_items() -> None:
    page: CursorPage[str] = CursorPage(items=["a", "b"], next_cursor="abc")
    assert page.items == ["a", "b"]
    assert page.next_cursor == "abc"
