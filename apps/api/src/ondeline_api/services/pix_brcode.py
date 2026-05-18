"""F3 — Gerador de BR Code (Pix EMV).

Usado quando o SGP nao entrega `codigo_pix` na fatura. Gera Pix estatico com
valor pre-preenchido a partir da chave Pix configurada pelo admin.

Referencia: Manual BR Code do BCB v01 — campos EMV TLV (id + len + value).
Final tem CRC16-CCITT/FALSE (polinomio 0x1021, init 0xFFFF, no reflect, no XOR).
"""
from __future__ import annotations

import re
import unicodedata

# CRC16-CCITT/FALSE
_CRC_POLY = 0x1021
_CRC_INIT = 0xFFFF


def _crc16(data: str) -> str:
    crc = _CRC_INIT
    for b in data.encode("ascii", errors="replace"):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _tlv(tag: str, value: str) -> str:
    """Field EMV: 2-digit ID + 2-digit length + value."""
    return f"{tag}{len(value):02d}{value}"


def _ascii_safe(s: str, max_len: int) -> str:
    """ASCII-only + trim. BR Code so aceita ASCII basico em nome/cidade."""
    nfkd = unicodedata.normalize("NFKD", s)
    asc = "".join(c for c in nfkd if ord(c) < 128)
    asc = re.sub(r"[^A-Za-z0-9 ]", "", asc).strip().upper()
    return asc[:max_len] or "PIX"


def _fmt_valor(valor: float) -> str:
    """Valor com ponto decimal, 2 casas, sem milhar."""
    return f"{valor:.2f}"


def _fmt_txid(txid: str | None) -> str:
    """TXID Pix: alfanumerico 1-25 chars. Sem TXID = '***' (estatico)."""
    if not txid:
        return "***"
    clean = re.sub(r"[^A-Za-z0-9]", "", txid).upper()
    return clean[:25] or "***"


def gerar_brcode(
    *,
    chave: str,
    nome: str,
    cidade: str,
    valor: float,
    txid: str | None = None,
    descricao: str | None = None,
) -> str:
    """Gera BR Code (Pix EMV) para pagamento.

    Args:
      chave: chave Pix do recebedor (CPF/CNPJ digits, email, telefone +5511..., ou aleatoria UUID).
      nome: nome do beneficiario (max 25 chars, ASCII).
      cidade: cidade do beneficiario (max 15 chars, ASCII).
      valor: valor em BRL (R$).
      txid: identificador externo da cobranca (max 25 alfanumericos). None = Pix estatico.
      descricao: descricao opcional (max 50 chars).
    """
    # Merchant Account Information (id 26) — GUI + chave + descricao
    mai_inner = _tlv("00", "br.gov.bcb.pix") + _tlv("01", chave.strip())
    if descricao:
        desc_clean = _ascii_safe(descricao, 50)
        if desc_clean:
            mai_inner += _tlv("02", desc_clean)
    mai = _tlv("26", mai_inner)

    payload_format = _tlv("00", "01")
    merchant_category = _tlv("52", "0000")
    transaction_currency = _tlv("53", "986")
    transaction_amount = _tlv("54", _fmt_valor(valor))
    country = _tlv("58", "BR")
    name_field = _tlv("59", _ascii_safe(nome, 25))
    city_field = _tlv("60", _ascii_safe(cidade, 15))

    # Additional Data Field (id 62) — TXID em 05
    add_data = _tlv("62", _tlv("05", _fmt_txid(txid)))

    body = (
        payload_format
        + mai
        + merchant_category
        + transaction_currency
        + transaction_amount
        + country
        + name_field
        + city_field
        + add_data
    )
    # CRC tag = "6304" + valor 4 hex
    to_crc = body + "6304"
    crc = _crc16(to_crc)
    return to_crc + crc
