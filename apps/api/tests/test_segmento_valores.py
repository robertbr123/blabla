# apps/api/tests/test_segmento_valores.py
from __future__ import annotations

import pytest

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.services.segmento import valores_distintos


async def _mk(session, *, cidade=None, status=None, plano=None, deleted=False):
    from uuid import uuid4

    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("0"),
        cpf_hash=hash_pii(uuid4().hex),
        nome_encrypted=encrypt_pii("x"),
        whatsapp="5592" + uuid4().hex[:8],
        cidade=cidade,
        status=status,
        plano=plano,
    )
    if deleted:
        from datetime import UTC, datetime

        c.deleted_at = datetime.now(tz=UTC)
    session.add(c)
    await session.flush()


@pytest.mark.asyncio
async def test_valores_distintos_ignora_nulos_e_deletados(db_session) -> None:
    import uuid

    marca = "ZZ" + uuid.uuid4().hex[:6]
    await _mk(db_session, cidade=f"Manaus{marca}", status=f"Ativo{marca}", plano=f"100MB{marca}")
    await _mk(db_session, cidade=f"Manaus{marca}", status=None, plano=None)
    await _mk(db_session, cidade=f"Del{marca}", status=f"X{marca}", deleted=True)

    out = await valores_distintos(db_session)

    assert f"Manaus{marca}" in out["cidades"]
    assert f"Del{marca}" not in out["cidades"]
    assert f"Ativo{marca}" in out["status"]
    assert f"100MB{marca}" in out["planos"]
    assert out["cidades"].count(f"Manaus{marca}") == 1
