"""F6+ — Parser de materiais do CONCLUIR via WhatsApp."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.estoque import EstoqueItem
from ondeline_api.services.estoque import registrar_movimento
from ondeline_api.services.material_concluir import (
    _fuzzy_match,
    _parse_linha,
    _split_input,
    parse_e_casar_materiais,
)

pytestmark = pytest.mark.asyncio


def test_parse_linha_quantidade_simples() -> None:
    assert _parse_linha("2 conector") == (2, "conector")


def test_parse_linha_com_unidade_metros() -> None:
    assert _parse_linha("100m cabo") == (100, "cabo")
    assert _parse_linha("100 metros cabo") == (100, "cabo")


def test_parse_linha_com_x() -> None:
    assert _parse_linha("3x roteador") == (3, "roteador")


def test_parse_linha_nome_composto() -> None:
    assert _parse_linha("2 conector sc apc") == (2, "conector sc apc")


def test_parse_linha_invalida() -> None:
    assert _parse_linha("conector sem qty") is None
    assert _parse_linha("0 conector") is None  # qty 0 invalida
    assert _parse_linha("") is None


def test_split_input_virgula_e_e() -> None:
    assert _split_input("2 conector, 100m cabo") == ["2 conector", "100m cabo"]
    assert _split_input("2 conector e 100m cabo") == ["2 conector", "100m cabo"]
    assert _split_input("2 conector; 100m cabo") == ["2 conector", "100m cabo"]


def test_fuzzy_match_por_nome() -> None:
    it_a = EstoqueItem(sku="CON-SC", nome="Conector SC/APC", categoria="conector")
    it_b = EstoqueItem(sku="CABO-DROP", nome="Cabo drop óptico", categoria="cabo")
    cat = [(it_a, 10), (it_b, 50)]
    res = _fuzzy_match("conector", cat)
    assert res is not None and res[0].sku == "CON-SC"


def test_fuzzy_match_por_categoria() -> None:
    it = EstoqueItem(sku="CABO-X", nome="Cabo drop", categoria="cabo")
    cat = [(it, 100)]
    res = _fuzzy_match("cabo", cat)
    assert res is not None and res[0].sku == "CABO-X"


def test_fuzzy_match_acento_e_case_insensitive() -> None:
    it = EstoqueItem(
        sku="CABO-OPT", nome="Cabo Óptico Drop", categoria="cabo"
    )
    cat = [(it, 50)]
    assert _fuzzy_match("CABO", cat) is not None
    assert _fuzzy_match("optico", cat) is not None
    assert _fuzzy_match("Óptico", cat) is not None


def test_fuzzy_match_sem_resultado() -> None:
    it = EstoqueItem(sku="X", nome="ONU", categoria="onu")
    cat = [(it, 1)]
    assert _fuzzy_match("xyz inexistente", cat) is None


# ── Integração com DB ────────────────────────────────────


async def _setup_tecnico_com_estoque(db_session):  # type: ignore[no-untyped-def]
    from ondeline_api.db.crypto import hash_pii
    from ondeline_api.db.models.identity import Role, User

    conector = EstoqueItem(
        sku="CON-SC", nome="Conector SC/APC", categoria="conector", serializado=False
    )
    cabo = EstoqueItem(
        sku="CABO-DROP", nome="Cabo drop óptico", categoria="cabo", serializado=False
    )
    onu = EstoqueItem(
        sku="ONU-ZTE", nome="ONU XPON ZTE", categoria="onu", serializado=True
    )
    tec = Tecnico(nome="Tec Mat", ativo=True)
    admin = User(
        email=f"adm_mat_{hash_pii('y')[:8]}@x.com",
        name="Admin Mat",
        role=Role.ADMIN,
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$xx$xx",
        is_active=True,
    )
    db_session.add_all([conector, cabo, onu, tec, admin])
    await db_session.flush()
    # Da entrada nos itens não serializados.
    await registrar_movimento(
        db_session, item_id=conector.id, tipo="entrada", quantidade=20,
        tecnico_id=tec.id, criado_por=admin.id,
    )
    await registrar_movimento(
        db_session, item_id=cabo.id, tipo="entrada", quantidade=200,
        tecnico_id=tec.id, criado_por=admin.id,
    )
    # ONU também (1 unidade, serializada).
    await registrar_movimento(
        db_session, item_id=onu.id, tipo="entrada", quantidade=1,
        tecnico_id=tec.id, criado_por=admin.id, serial="SN-001",
    )
    return tec, conector, cabo, onu, admin


async def test_parse_e_casar_2_conectores_e_100_cabo(db_session) -> None:
    tec, conector, cabo, _onu, _admin = await _setup_tecnico_com_estoque(db_session)
    res = await parse_e_casar_materiais(
        db_session, tecnico_id=tec.id, texto="2 conector, 100m cabo"
    )
    assert len(res.matches) == 2
    assert any(m.item_id == conector.id and m.quantidade == 2 for m in res.matches)
    assert any(m.item_id == cabo.id and m.quantidade == 100 for m in res.matches)
    assert res.nao_encontrados == []
    assert res.invalidos == []
    assert res.sem_saldo == []


async def test_parse_marca_nao_encontrado_quando_item_fora_do_estoque(db_session) -> None:
    tec, *_ = await _setup_tecnico_com_estoque(db_session)
    res = await parse_e_casar_materiais(
        db_session, tecnico_id=tec.id, texto="2 conector, 5 parafuso"
    )
    assert len(res.matches) == 1
    assert any("parafuso" in n for n in res.nao_encontrados)


async def test_parse_marca_sem_saldo_quando_qty_maior_que_saldo(db_session) -> None:
    tec, _conector, _cabo, _onu, _admin = await _setup_tecnico_com_estoque(db_session)
    # saldo conector = 20, técnico pede 999.
    res = await parse_e_casar_materiais(
        db_session, tecnico_id=tec.id, texto="999 conector"
    )
    assert res.matches == []
    assert len(res.sem_saldo) == 1
    assert res.sem_saldo[0][1] == 999  # quantidade pedida
    assert res.sem_saldo[0][2] == 20  # saldo atual


async def test_parse_marca_invalido_quando_serializado_com_qty_acima_de_1(db_session) -> None:
    tec, *_ = await _setup_tecnico_com_estoque(db_session)
    res = await parse_e_casar_materiais(
        db_session, tecnico_id=tec.id, texto="2 onu"
    )
    assert res.matches == []
    assert len(res.invalidos) == 1
    assert "serializado" in res.invalidos[0].lower()


async def test_parse_aceita_onu_qty_1(db_session) -> None:
    tec, _c, _cabo, onu, _admin = await _setup_tecnico_com_estoque(db_session)
    res = await parse_e_casar_materiais(
        db_session, tecnico_id=tec.id, texto="1 onu"
    )
    assert len(res.matches) == 1
    assert res.matches[0].item_id == onu.id
    assert res.matches[0].quantidade == 1
    # Serializado=True precisa ser exposto pra orquestrador pedir serial.
    assert res.matches[0].serializado is True
    assert res.matches[0].serial is None


def test_render_resumo_baixa_inclui_serial() -> None:
    from uuid import uuid4

    from ondeline_api.services.material_concluir import (
        MaterialMatch,
        render_resumo_baixa,
    )

    m = MaterialMatch(
        item_id=uuid4(),
        sku="ONU-X",
        nome="ONU XPON",
        categoria="onu",
        serializado=True,
        quantidade=1,
        saldo_atual=1,
        nome_digitado="onu",
        serial="SN-001",
    )
    out = render_resumo_baixa([m])
    assert "1x ONU XPON" in out
    assert "SN-001" in out


def test_render_resumo_baixa_dict_inclui_serial() -> None:
    from ondeline_api.services.material_concluir import render_resumo_baixa_dict

    out = render_resumo_baixa_dict(
        [
            {"nome": "ONU XPON", "quantidade": 1, "serial": "SN-001"},
            {"nome": "Conector", "quantidade": 2, "serial": None},
        ]
    )
    assert "SN-001" in out
    assert "Conector" in out
