"""TecnicoRepo.get_by_jid — lookup por número WhatsApp normalizado."""
from __future__ import annotations

import pytest
from ondeline_api.repositories.tecnico import TecnicoRepo

pytestmark = pytest.mark.asyncio


async def test_get_by_jid_matches_with_country_code(db_session) -> None:
    repo = TecnicoRepo(db_session)
    await repo.create(nome="João", whatsapp="5597984109856", ativo=True)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is not None
    assert found.nome == "João"


async def test_get_by_jid_matches_with_local_digits(db_session) -> None:
    repo = TecnicoRepo(db_session)
    # Técnico cadastrado SEM código de país
    await repo.create(nome="Maria", whatsapp="97984109856", ativo=True)
    # JID chega com código de país (formato Evolution)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is not None
    assert found.nome == "Maria"


async def test_get_by_jid_ignores_inactive(db_session) -> None:
    repo = TecnicoRepo(db_session)
    await repo.create(nome="Inativo", whatsapp="5597984109856", ativo=False)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is None


async def test_get_by_jid_returns_none_when_not_found(db_session) -> None:
    repo = TecnicoRepo(db_session)
    found = await repo.get_by_jid("5597999999999@s.whatsapp.net")
    assert found is None


async def test_get_by_jid_returns_none_for_tecnico_without_whatsapp(db_session) -> None:
    repo = TecnicoRepo(db_session)
    await repo.create(nome="SemTel", whatsapp=None, ativo=True)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is None
