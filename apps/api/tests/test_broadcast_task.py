# apps/api/tests/test_broadcast_task.py
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Campanha,
    CampanhaDestinatario,
    Canal,
    Cliente,
)
from ondeline_api.workers.broadcast import _send_campanha
from sqlalchemy import func, select


class _FakeAdapter:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_template(self, jid, *, name, language="pt_BR",
                            body_params=None, header_media_url=None, **_):
        self.sent.append(jid)
        return {"messages": [{"id": f"wamid.{jid}"}]}

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_send_campanha_materializa_e_envia(db_session, monkeypatch):
    canal = Canal(slug=f"com-{uuid4().hex[:8]}", nome="Comercial", provider="cloud",
                  cloud_phone_id="123", cloud_waba_id="456")
    db_session.add(canal)
    for i in range(3):
        db_session.add(Cliente(
            cpf_cnpj_encrypted=encrypt_pii("0"), cpf_hash=hash_pii(f"c{i}"),
            nome_encrypted=encrypt_pii(f"Cli {i}"), whatsapp=f"55920000{i}",
            cidade="Manaus", status="Ativo",
        ))
    await db_session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="comunicado_geral",
                    body_params=["oi"], segmentacao={"cidade": "Manaus"}, status="rascunho")
    db_session.add(camp)
    await db_session.flush()

    fake = _FakeAdapter()
    monkeypatch.setattr("ondeline_api.workers.broadcast.build_for_canal", lambda c, s: fake)

    result = await _send_campanha(db_session, camp.id)

    assert result["enviadas"] == 3
    assert result["falhas"] == 0
    assert len(fake.sent) == 3
    await db_session.refresh(camp)
    assert camp.status == "concluida"
    assert camp.total_destinatarios == 3
    n_dest = (await db_session.execute(
        select(func.count()).select_from(CampanhaDestinatario)
        .where(CampanhaDestinatario.campanha_id == camp.id)
    )).scalar_one()
    assert n_dest == 3


@pytest.mark.asyncio
async def test_send_campanha_idempotente(db_session, monkeypatch):
    canal = Canal(slug=f"c2-{uuid4().hex[:8]}", nome="C2", provider="cloud", cloud_phone_id="1", cloud_waba_id="2")
    db_session.add(canal)
    db_session.add(Cliente(
        cpf_cnpj_encrypted=encrypt_pii("0"), cpf_hash=hash_pii("u1"),
        nome_encrypted=encrypt_pii("U"), whatsapp="5592123", cidade="Manaus",
    ))
    await db_session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="comunicado_geral",
                    body_params=["oi"], segmentacao={"cidade": "Manaus"}, status="rascunho")
    db_session.add(camp)
    await db_session.flush()

    fake = _FakeAdapter()
    monkeypatch.setattr("ondeline_api.workers.broadcast.build_for_canal", lambda c, s: fake)

    await _send_campanha(db_session, camp.id)
    await _send_campanha(db_session, camp.id)  # re-rodar não redispara

    assert len(fake.sent) == 1
