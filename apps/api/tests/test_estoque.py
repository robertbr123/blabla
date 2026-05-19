"""F6 — Estoque: itens, movimentos, saldo."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.estoque import EstoqueItem
from ondeline_api.repositories.estoque import ItemRepo, MovimentoRepo
from ondeline_api.services.estoque import (
    EstoqueError,
    SaldoInsuficiente,
    SerialDuplicado,
    calcular_saldo_tecnico,
    registrar_movimento,
)

pytestmark = pytest.mark.asyncio


async def _setup_basics(db_session):  # type: ignore[no-untyped-def]
    from ondeline_api.db.crypto import hash_pii
    from ondeline_api.db.models.identity import Role, User

    onu = EstoqueItem(
        sku="ONU-XPON-ZTE", nome="ONU XPON ZTE", categoria="onu", serializado=True
    )
    conector = EstoqueItem(
        sku="CONECT-SC", nome="Conector SC/APC", categoria="conector", serializado=False
    )
    db_session.add(onu)
    db_session.add(conector)

    tec = Tecnico(nome="Pedro Estoque", ativo=True)
    db_session.add(tec)

    admin = User(
        email=f"adm_est_{hash_pii('x')[:8]}@x.com",
        name="Adm",
        role=Role.ADMIN,
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$xx$xx",
        is_active=True,
    )
    db_session.add(admin)

    await db_session.flush()
    return onu, conector, tec, admin


async def test_entrada_simples_aumenta_saldo_conector(db_session) -> None:
    _onu, conector, tec, admin = await _setup_basics(db_session)
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="entrada",
        quantidade=20,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    saldo = await MovimentoRepo(db_session).saldo_por_tecnico_item(tec.id, conector.id)
    assert saldo == 20


async def test_saida_diminui_saldo(db_session) -> None:
    _onu, conector, tec, admin = await _setup_basics(db_session)
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="entrada",
        quantidade=10,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="saida",
        quantidade=3,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    saldo = await MovimentoRepo(db_session).saldo_por_tecnico_item(tec.id, conector.id)
    assert saldo == 7


async def test_saida_sem_saldo_falha(db_session) -> None:
    _onu, conector, tec, admin = await _setup_basics(db_session)
    with pytest.raises(SaldoInsuficiente):
        await registrar_movimento(
            db_session,
            item_id=conector.id,
            tipo="saida",
            quantidade=1,
            tecnico_id=tec.id,
            criado_por=admin.id,
        )


async def test_serializado_exige_serial(db_session) -> None:
    onu, _c, tec, admin = await _setup_basics(db_session)
    with pytest.raises(EstoqueError):
        await registrar_movimento(
            db_session,
            item_id=onu.id,
            tipo="entrada",
            quantidade=1,
            tecnico_id=tec.id,
            criado_por=admin.id,
            serial=None,
        )


async def test_serializado_quantidade_1(db_session) -> None:
    onu, _c, tec, admin = await _setup_basics(db_session)
    with pytest.raises(EstoqueError):
        await registrar_movimento(
            db_session,
            item_id=onu.id,
            tipo="entrada",
            quantidade=2,
            tecnico_id=tec.id,
            criado_por=admin.id,
            serial="X12345",
        )


async def test_serial_duplicado_falha(db_session) -> None:
    onu, _c, tec, admin = await _setup_basics(db_session)
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="entrada",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="SN-001",
    )
    with pytest.raises(SerialDuplicado):
        await registrar_movimento(
            db_session,
            item_id=onu.id,
            tipo="entrada",
            quantidade=1,
            tecnico_id=tec.id,
            criado_por=admin.id,
            serial="SN-001",
        )


async def test_serial_baixado_pode_voltar_a_entrar(db_session) -> None:
    """Após saida do serial, ele pode ser dado entrada novamente (retornou)."""
    onu, _c, tec, admin = await _setup_basics(db_session)
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="entrada",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="SN-RETURN",
    )
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="saida",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="SN-RETURN",
    )
    # Agora pode entrar de novo
    mov = await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="entrada",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="SN-RETURN",
    )
    assert mov.id is not None


async def test_devolucao_diminui_saldo_do_tecnico(db_session) -> None:
    _onu, conector, tec, admin = await _setup_basics(db_session)
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="entrada",
        quantidade=15,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="devolucao",
        quantidade=5,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    saldo = await MovimentoRepo(db_session).saldo_por_tecnico_item(tec.id, conector.id)
    assert saldo == 10


async def test_ajustes_positivo_e_negativo(db_session) -> None:
    _onu, conector, tec, admin = await _setup_basics(db_session)
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="ajuste_positivo",
        quantidade=5,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="ajuste_negativo",
        quantidade=2,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    saldo = await MovimentoRepo(db_session).saldo_por_tecnico_item(tec.id, conector.id)
    assert saldo == 3


async def test_calcular_saldo_tecnico_lista_todos_itens(db_session) -> None:
    _onu, conector, tec, admin = await _setup_basics(db_session)
    await registrar_movimento(
        db_session,
        item_id=conector.id,
        tipo="entrada",
        quantidade=12,
        tecnico_id=tec.id,
        criado_por=admin.id,
    )
    linhas = await calcular_saldo_tecnico(db_session, tec.id)
    # 2 itens ativos cadastrados; conector tem saldo 12, ONU tem 0.
    skus = {ln["sku"]: ln["saldo"] for ln in linhas}
    assert skus.get("CONECT-SC") == 12
    assert skus.get("ONU-XPON-ZTE") == 0


async def test_tipo_negativo_exige_tecnico_id(db_session) -> None:
    _onu, conector, _tec, admin = await _setup_basics(db_session)
    with pytest.raises(EstoqueError):
        await registrar_movimento(
            db_session,
            item_id=conector.id,
            tipo="perda",
            quantidade=1,
            tecnico_id=None,
            criado_por=admin.id,
        )


async def test_item_repo_get_by_sku(db_session) -> None:
    _onu, _c, _tec, _admin = await _setup_basics(db_session)
    found = await ItemRepo(db_session).get_by_sku("ONU-XPON-ZTE")
    assert found is not None
    assert found.nome == "ONU XPON ZTE"


async def test_recolhido_aumenta_saldo_do_tecnico(db_session) -> None:
    """F6+: tipo `recolhido` (cliente → técnico) é positivo e não exige saldo prévio."""
    onu, _c, tec, admin = await _setup_basics(db_session)
    # Tecnico recolhe ONU velha do cliente — saldo era 0, vai pra 1.
    mov = await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="recolhido",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="OLD-SN-999",
    )
    assert mov.tipo == "recolhido"
    saldo = await MovimentoRepo(db_session).saldo_por_tecnico_item(tec.id, onu.id)
    assert saldo == 1


async def test_fluxo_troca_de_equipamento(db_session) -> None:
    """F6+: cenário troca — técnico instala ONU nova (saida) e recolhe velha (recolhido).

    Saldo final: ONU=0 (vendeu uma, ganhou outra de volta).
    """
    onu, _c, tec, admin = await _setup_basics(db_session)
    # Entrada: técnico recebe 1 ONU nova do almoxarifado
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="entrada",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="NEW-SN-001",
    )
    assert await MovimentoRepo(db_session).saldo_por_tecnico_item(tec.id, onu.id) == 1

    # Instala a nova no cliente (saida) + recolhe a velha (recolhido)
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="saida",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="NEW-SN-001",
    )
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="recolhido",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="OLD-SN-999",
    )
    # Saldo final: -1 (saida) + 1 (recolhido) + 1 (entrada inicial) = 1, mas
    # subtraindo saida = 1 - 1 + 1 = 1. Wait let me redo: começo 0, +1 entrada,
    # -1 saida, +1 recolhido = 1.
    final = await MovimentoRepo(db_session).saldo_por_tecnico_item(tec.id, onu.id)
    assert final == 1
