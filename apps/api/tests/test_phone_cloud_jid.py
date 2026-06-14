# apps/api/tests/test_phone_cloud_jid.py
from __future__ import annotations

from ondeline_api.services.phone import to_cloud_jid


def test_ja_normalizado_com_ddi() -> None:
    assert to_cloud_jid("5592999999999") == "5592999999999"


def test_com_pontuacao_adiciona_ddi() -> None:
    assert to_cloud_jid("(92) 99999-9999") == "5592999999999"


def test_ddd_mais_numero_sem_ddi() -> None:
    assert to_cloud_jid("92999999999") == "5592999999999"


def test_dez_digitos_fixo_like() -> None:
    assert to_cloud_jid("9233334444") == "559233334444"


def test_invalido_retorna_none() -> None:
    assert to_cloud_jid("999") is None
    assert to_cloud_jid("") is None
    assert to_cloud_jid(None) is None
    assert to_cloud_jid("abc") is None
