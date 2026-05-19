"""F8 — Histórico de equipamentos por cliente."""
from __future__ import annotations

from typing import Any

import pytest
from ondeline_api.db.models.business import Cliente, OrdemServico, OsStatus, Tecnico
from ondeline_api.db.models.estoque import EstoqueItem
from ondeline_api.repositories.cliente_equipamento import ClienteEquipamentoRepo
from ondeline_api.services.estoque import registrar_movimento

pytestmark = pytest.mark.asyncio


async def _setup(db_session: Any) -> tuple[Any, Any, Any, Any, Any]:
    from ondeline_api.db.crypto import encrypt_pii, hash_pii
    from ondeline_api.db.models.identity import Role, User

    cli = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("João Silva"),
        whatsapp="5511f8@s.whatsapp.net",
    )
    onu = EstoqueItem(sku="ONU-F8", nome="ONU F8", categoria="onu", serializado=True)
    tec = Tecnico(nome="Téc F8", ativo=True)
    admin = User(
        email=f"admf8_{hash_pii('f8')[:8]}@x.com",
        name="Adm",
        role=Role.ADMIN,
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$xx$xx",
        is_active=True,
    )
    db_session.add_all([cli, onu, tec, admin])
    await db_session.flush()

    # Cria OS
    os_row = OrdemServico(
        codigo="OS-F8-001",
        cliente_id=cli.id,
        tecnico_id=tec.id,
        problema="instalar",
        endereco="rua x",
        status=OsStatus.EM_ANDAMENTO,
    )
    db_session.add(os_row)
    await db_session.flush()

    # Da entrada da ONU no estoque do técnico.
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="entrada",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="SN-INSTALADA",
    )
    return cli, onu, tec, admin, os_row


async def test_saida_com_os_cria_cliente_equipamento(db_session) -> None:
    cli, onu, tec, admin, os_row = await _setup(db_session)
    await registrar_movimento(
        db_session,
        item_id=onu.id,
        tipo="saida",
        quantidade=1,
        tecnico_id=tec.id,
        criado_por=admin.id,
        serial="SN-INSTALADA",
        ordem_servico_id=os_row.id,
    )

    repo = ClienteEquipamentoRepo(db_session)
    registros = await repo.list_by_cliente(cli.id)
    assert len(registros) == 1
    r = registros[0]
    assert r.serial == "SN-INSTALADA"
    assert r.item_id == onu.id
    assert r.instalado_em_os_id == os_row.id
    assert r.instalado_por_tecnico_id == tec.id
    assert r.removido_em is None


async def test_recolhido_fecha_registro_ativo(db_session) -> None:
    cli, onu, tec, admin, os_row = await _setup(db_session)
    # Instala
    await registrar_movimento(
        db_session, item_id=onu.id, tipo="saida", quantidade=1,
        tecnico_id=tec.id, criado_por=admin.id, serial="SN-X",
        ordem_servico_id=os_row.id,
    )
    # Cria 2a OS pra recolher
    os2 = OrdemServico(
        codigo="OS-F8-002",
        cliente_id=cli.id,
        tecnico_id=tec.id,
        problema="trocar",
        endereco="rua x",
        status=OsStatus.EM_ANDAMENTO,
    )
    db_session.add(os2)
    await db_session.flush()
    # Recolhe
    await registrar_movimento(
        db_session, item_id=onu.id, tipo="recolhido", quantidade=1,
        tecnico_id=tec.id, criado_por=admin.id, serial="SN-X",
        ordem_servico_id=os2.id,
    )

    repo = ClienteEquipamentoRepo(db_session)
    todos = await repo.list_by_cliente(cli.id)
    assert len(todos) == 1
    assert todos[0].removido_em is not None
    assert todos[0].removido_em_os_id == os2.id

    ativos = await repo.list_by_cliente(cli.id, ativos_only=True)
    assert ativos == []


async def test_saida_sem_os_nao_cria_registro(db_session) -> None:
    """Movimento de saída sem ordem_servico_id (ex: admin via dashboard) não
    sabe qual cliente — não cria cliente_equipamento."""
    cli, onu, tec, admin, _os = await _setup(db_session)
    await registrar_movimento(
        db_session, item_id=onu.id, tipo="saida", quantidade=1,
        tecnico_id=tec.id, criado_por=admin.id, serial="SN-X",
        ordem_servico_id=None,
    )
    repo = ClienteEquipamentoRepo(db_session)
    assert await repo.list_by_cliente(cli.id) == []


async def test_item_nao_serializado_nao_cria_registro(db_session) -> None:
    """Conector (não serializado) não vai pra cliente_equipamento."""
    from ondeline_api.repositories.cliente_equipamento import (
        ClienteEquipamentoRepo,
    )

    cli, _onu, tec, admin, os_row = await _setup(db_session)
    conector = EstoqueItem(
        sku="CONECT", nome="Conector", categoria="conector", serializado=False
    )
    db_session.add(conector)
    await db_session.flush()
    await registrar_movimento(
        db_session, item_id=conector.id, tipo="entrada", quantidade=50,
        tecnico_id=tec.id, criado_por=admin.id,
    )
    await registrar_movimento(
        db_session, item_id=conector.id, tipo="saida", quantidade=2,
        tecnico_id=tec.id, criado_por=admin.id,
        ordem_servico_id=os_row.id,
    )
    assert await ClienteEquipamentoRepo(db_session).list_by_cliente(cli.id) == []


async def test_find_ativo_por_serial(db_session) -> None:
    cli, onu, tec, admin, os_row = await _setup(db_session)
    await registrar_movimento(
        db_session, item_id=onu.id, tipo="saida", quantidade=1,
        tecnico_id=tec.id, criado_por=admin.id, serial="SN-FIND",
        ordem_servico_id=os_row.id,
    )
    repo = ClienteEquipamentoRepo(db_session)
    achado = await repo.find_ativo_por_serial(onu.id, "SN-FIND")
    assert achado is not None
    assert achado.cliente_id == cli.id

    # Serial diferente → None
    assert await repo.find_ativo_por_serial(onu.id, "SN-OUTRO") is None
