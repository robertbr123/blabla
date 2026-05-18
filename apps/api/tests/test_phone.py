"""Testes de normalização e formatação de telefone BR."""
from __future__ import annotations

import pytest
from ondeline_api.services.phone import br_local_digits, format_br_phone


def test_br_local_digits_strips_country_code() -> None:
    assert br_local_digits("559784109856") == "84109856"


def test_br_local_digits_strips_country_and_ninth_digit() -> None:
    assert br_local_digits("5597984109856") == "84109856"


def test_br_local_digits_strips_ddd_only() -> None:
    assert br_local_digits("97984109856") == "84109856"


def test_br_local_digits_already_local() -> None:
    assert br_local_digits("84109856") == "84109856"


def test_br_local_digits_handles_non_digit_input() -> None:
    # Caller é responsável por strip; função aceita só dígitos
    assert br_local_digits("") == ""


def test_format_br_phone_full_with_ninth_digit() -> None:
    assert format_br_phone("5597984109856") == "(97) 9 8410-9856"


def test_format_br_phone_without_country_code() -> None:
    assert format_br_phone("97984109856") == "(97) 9 8410-9856"


def test_format_br_phone_eight_digit_local() -> None:
    # Sem DDD/9° dígito conhecidos — devolve "como está" formatado
    assert format_br_phone("84109856") == "8410-9856"


def test_format_br_phone_with_punctuation_input() -> None:
    assert format_br_phone("(97) 9 8410-9856") == "(97) 9 8410-9856"


def test_format_br_phone_empty_returns_empty() -> None:
    assert format_br_phone("") == ""
    assert format_br_phone(None) == ""
