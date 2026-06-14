# apps/api/src/ondeline_api/services/broadcast_import.py
"""Parser de CSV de destinatários de campanha.

Coluna de telefone obrigatória; colunas opcionais por variável (casadas por
label normalizado) e uma coluna 'botao'/'link'/'url' para o botão dinâmico.
"""
from __future__ import annotations

import csv
import io
import unicodedata
from typing import Any

from ondeline_api.services.phone import to_cloud_jid

_PHONE_COLS = {"telefone", "whatsapp", "phone", "celular", "fone"}
_BTN_COLS = {"botao", "link", "url"}


def _norm(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _detect_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","


def parse_csv_destinatarios(
    content: bytes, variaveis: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Retorna (rows, invalidos).

    Cada row: {whatsapp, body_params: list[str|None] | None, button_param: str|None}.
    invalidos: linhas (texto) cujo telefone não normalizou.
    """
    text = content.decode("utf-8-sig", errors="replace")
    linhas = text.splitlines()
    delim = _detect_delimiter(linhas[0] if linhas else "")
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    fieldmap = {_norm(h): h for h in (reader.fieldnames or [])}

    phone_key = next((fieldmap[k] for k in fieldmap if k in _PHONE_COLS), None)
    if phone_key is None and reader.fieldnames:
        phone_key = reader.fieldnames[0]
    btn_key = next((fieldmap[k] for k in fieldmap if k in _BTN_COLS), None)

    var_keys: dict[int, str] = {}
    for v in variaveis:
        idx = int(v["indice"])
        alvo_label = _norm(str(v.get("label") or ""))
        for nk, real in fieldmap.items():
            if nk == alvo_label or nk == f"var{idx}" or nk == f"variavel{idx}":
                var_keys[idx] = real
                break

    rows: list[dict[str, Any]] = []
    invalidos: list[str] = []
    for raw in reader:
        jid = to_cloud_jid(raw.get(phone_key) if phone_key else None)
        if jid is None:
            invalidos.append(delim.join(str(x) for x in raw.values()))
            continue
        body_params: list[str | None] | None = None
        if variaveis:
            n = max(int(v["indice"]) for v in variaveis)
            body_params = [
                (raw.get(var_keys[i]) or None) if i in var_keys else None
                for i in range(1, n + 1)
            ]
        button_param = (raw.get(btn_key) or None) if btn_key else None
        rows.append(
            {"whatsapp": jid, "body_params": body_params, "button_param": button_param}
        )
    return rows, invalidos
