# apps/api/tests/test_broadcast_import.py
from __future__ import annotations

from ondeline_api.services.broadcast_import import parse_csv_destinatarios

VARIAVEIS = [
    {"indice": 1, "label": "Nome", "tipo": "texto"},
    {"indice": 2, "label": "Link", "tipo": "url"},
]


def test_virgula_com_colunas_de_variaveis() -> None:
    csv_bytes = b"telefone,nome,link\n(92) 99999-9999,Joao,https://a\n"
    rows, invalidos = parse_csv_destinatarios(csv_bytes, VARIAVEIS)
    assert invalidos == []
    assert rows[0]["whatsapp"] == "5592999999999"
    assert rows[0]["body_params"] == ["Joao", "https://a"]


def test_ponto_e_virgula_e_coluna_faltando() -> None:
    csv_bytes = b"telefone;nome\n5592888888888;Maria\n"
    rows, _invalidos = parse_csv_destinatarios(csv_bytes, VARIAVEIS)
    assert rows[0]["whatsapp"] == "5592888888888"
    assert rows[0]["body_params"] == ["Maria", None]


def test_telefone_invalido_vai_pra_invalidos() -> None:
    csv_bytes = b"telefone,nome\n999,Bad\n5592777777777,Ok\n"
    rows, invalidos = parse_csv_destinatarios(csv_bytes, VARIAVEIS)
    assert len(rows) == 1
    assert rows[0]["whatsapp"] == "5592777777777"
    assert len(invalidos) == 1


def test_coluna_botao() -> None:
    csv_bytes = b"telefone,botao\n5592111111111,https://btn\n"
    rows, _ = parse_csv_destinatarios(csv_bytes, [])
    assert rows[0]["button_param"] == "https://btn"
