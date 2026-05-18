"""F4 — Canal: ensure_default + lookup + conversas escopadas por canal."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import Canal
from ondeline_api.repositories.canal import CanalRepo
from ondeline_api.repositories.conversa import ConversaRepo

pytestmark = pytest.mark.asyncio


async def test_ensure_default_cria_quando_inexistente(db_session) -> None:
    repo = CanalRepo(db_session)
    c = await repo.ensure_default(
        slug="suporte_test", nome="Suporte Test", evolution_instance="evt-default"
    )
    assert c.id is not None
    assert c.slug == "suporte_test"
    assert c.evolution_instance == "evt-default"
    assert c.ativo is True


async def test_ensure_default_idempotente(db_session) -> None:
    repo = CanalRepo(db_session)
    a = await repo.ensure_default(
        slug="suporte_idem", nome="Suporte", evolution_instance="evt-idem"
    )
    b = await repo.ensure_default(
        slug="suporte_idem", nome="Suporte (renomeado)", evolution_instance="evt-idem-2"
    )
    assert a.id == b.id
    # Idempotente: nao sobrescreve campos.
    assert b.nome == "Suporte"


async def test_get_by_evolution_instance(db_session) -> None:
    repo = CanalRepo(db_session)
    await repo.ensure_default(
        slug="comercial_x", nome="Comercial", evolution_instance="evt-com"
    )
    found = await repo.get_by_evolution_instance("evt-com")
    assert found is not None
    assert found.slug == "comercial_x"
    missing = await repo.get_by_evolution_instance("nao-existe")
    assert missing is None


async def test_mesma_whatsapp_em_canais_diferentes_geram_conversas_separadas(
    db_session,
) -> None:
    repo_canal = CanalRepo(db_session)
    suporte = await repo_canal.ensure_default(
        slug="supo_a", nome="Suporte", evolution_instance="inst-supo-a"
    )
    comercial = Canal(
        slug="comerc_a", nome="Comercial", evolution_instance="inst-comerc-a"
    )
    db_session.add(comercial)
    await db_session.flush()

    repo_conv = ConversaRepo(db_session)
    jid = "5511multi@s.whatsapp.net"
    c_sup = await repo_conv.get_or_create_by_whatsapp(jid, canal_id=suporte.id)
    c_com = await repo_conv.get_or_create_by_whatsapp(jid, canal_id=comercial.id)
    assert c_sup.id != c_com.id
    assert c_sup.canal_id == suporte.id
    assert c_com.canal_id == comercial.id

    # Repeticao retorna a mesma conversa (idempotente por canal)
    c_sup_again = await repo_conv.get_or_create_by_whatsapp(
        jid, canal_id=suporte.id
    )
    assert c_sup_again.id == c_sup.id


async def test_canal_id_none_nao_casa_com_canal_id_setado(db_session) -> None:
    """Conversa legada (canal_id=NULL) nao eh devolvida quando se busca por canal_id."""
    repo_canal = CanalRepo(db_session)
    canal = await repo_canal.ensure_default(
        slug="supo_b", nome="Suporte", evolution_instance="inst-supo-b"
    )

    repo_conv = ConversaRepo(db_session)
    jid = "5511legacy@s.whatsapp.net"
    # Cria conversa legada sem canal
    c_legacy = await repo_conv.get_or_create_by_whatsapp(jid, canal_id=None)
    assert c_legacy.canal_id is None
    # Busca com canal → cria nova
    c_canal = await repo_conv.get_or_create_by_whatsapp(jid, canal_id=canal.id)
    assert c_canal.id != c_legacy.id


async def test_webhook_parser_extrai_instance() -> None:
    from ondeline_api.webhook.parser import parse_messages_upsert

    payload = {
        "event": "messages.upsert",
        "instance": "comercial-wa",
        "data": {
            "key": {"id": "WAEVT_xyz", "remoteJid": "5511@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "olá"},
            "pushName": "Maria",
        },
    }
    evt = parse_messages_upsert(payload)
    assert evt.instance == "comercial-wa"


async def test_webhook_parser_instance_vazio_quando_ausente() -> None:
    from ondeline_api.webhook.parser import parse_messages_upsert

    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"id": "WAEVT_xyz", "remoteJid": "5511@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "olá"},
        },
    }
    evt = parse_messages_upsert(payload)
    assert evt.instance == ""
