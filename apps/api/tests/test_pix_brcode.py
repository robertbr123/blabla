"""F3 — Geração de BR Code (Pix EMV)."""
from __future__ import annotations

from ondeline_api.services.pix_brcode import _crc16, gerar_brcode


def test_crc16_known_vector() -> None:
    """CRC16/CCITT-FALSE vetor classico: '123456789' -> 0x29B1."""
    assert _crc16("123456789") == "29B1"


def test_brcode_minimo_termina_com_crc16() -> None:
    code = gerar_brcode(
        chave="12345678901",
        nome="Provedor",
        cidade="Sao Paulo",
        valor=99.90,
    )
    # Final tem tag "6304" + 4 hex.
    assert "6304" in code[-8:]
    assert len(code[-4:]) == 4
    assert all(c in "0123456789ABCDEF" for c in code[-4:])


def test_brcode_contem_chave_e_valor() -> None:
    code = gerar_brcode(
        chave="11999999999",
        nome="Provedor Tel",
        cidade="Curitiba",
        valor=42.50,
    )
    # Chave aparece como TLV id=01 dentro do MAI (id=26).
    assert "11999999999" in code
    # Valor formatado 2 decimais aparece como id=54.
    assert "542" in code  # "5405" or similar — len 5
    assert "42.50" in code


def test_brcode_normaliza_acentos_no_nome() -> None:
    code = gerar_brcode(
        chave="x@y.com",
        nome="João Silva ME",
        cidade="São Paulo",
        valor=10.0,
    )
    # Nao pode conter caracteres acentuados (BR Code exige ASCII).
    assert "ã" not in code
    assert "õ" not in code
    # Nome normalizado pra ASCII upper.
    assert "JOAO" in code


def test_brcode_txid_default_estatico() -> None:
    code = gerar_brcode(
        chave="x@y.com",
        nome="Provedor",
        cidade="POA",
        valor=10.0,
    )
    # Sem txid → '***' no campo 05 do additional data (id=62)
    assert "***" in code
