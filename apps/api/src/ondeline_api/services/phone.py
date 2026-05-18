"""Utilitários de telefone brasileiro.

Normalização e formatação para uso em matching (técnico/cliente por JID)
e display (lista de OS para técnico). Extraído de `services/inbound.py`
quando começou a ser usado em mais de um lugar.
"""
from __future__ import annotations

import re

_DIGITS_RE = re.compile(r"\D")


def br_local_digits(digits: str) -> str:
    """Normaliza dígitos de número BR para os 8 dígitos locais.

    Tolera: com/sem código de país (55), com/sem DDD, com/sem nono dígito.
    Ex: "559784109856" → "84109856"
        "5597984109856" → "84109856"
        "97984109856" → "84109856"
    Entrada deve ser só dígitos (caller usa _DIGITS_RE.sub se necessário).
    """
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) in (10, 11):
        digits = digits[2:]
    if len(digits) == 9 and digits[0] == "9":
        digits = digits[1:]
    return digits


def format_br_phone(raw: str | None) -> str:
    """Formata telefone BR para display: "(DD) 9 XXXX-XXXX".

    Aceita qualquer entrada com lixo (parênteses, espaços, hífens, +55).
    Se o número não tiver DDD reconhecível, devolve só o local "XXXX-XXXX".
    """
    if not raw:
        return ""
    d = _DIGITS_RE.sub("", raw)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    if len(d) == 11:
        # DDD + 9° dígito: 97 9 8410 9856
        return f"({d[0:2]}) {d[2]} {d[3:7]}-{d[7:11]}"
    if len(d) == 10:
        # DDD sem 9°: 97 8410 9856
        return f"({d[0:2]}) {d[2:6]}-{d[6:10]}"
    if len(d) == 9 and d[0] == "9":
        # 9° dígito + 8 locais, sem DDD
        return f"{d[0]} {d[1:5]}-{d[5:9]}"
    if len(d) == 8:
        return f"{d[0:4]}-{d[4:8]}"
    return raw  # fallback: devolve original
