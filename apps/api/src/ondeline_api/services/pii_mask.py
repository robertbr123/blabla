"""Mascaramento de PII em strings (logs, prompts).

Reduz CPF/CNPJ, telefone BR e email a placeholders. Aplicado em qualquer
log relacionado a LLM (prompts crus tem CPFs).
"""
from __future__ import annotations

import re

_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_PHONE = re.compile(r"\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b")
_EMAIL = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+")


def mask_pii(text: str) -> str:
    if not text:
        return text
    text = _CNPJ.sub("[CNPJ]", text)
    text = _CPF.sub("[CPF]", text)
    text = _PHONE.sub("[PHONE]", text)
    text = _EMAIL.sub("[EMAIL]", text)
    return text
