"""ClienteRepo: upsert + get_by_cpf_hash."""
from __future__ import annotations

import pytest
from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato, EnderecoSgp
from ondeline_api.db.crypto import decrypt_pii, hash_pii
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum
from ondeline_api.repositories.cliente import ClienteRepo
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _cli() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Maria",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="Premium 100MB", status="ativo", cidade="Sao Paulo")],
        endereco=EnderecoSgp(logradouro="Rua A", numero="10", cidade="Sao Paulo", uf="SP"),
    )


async def test_insert_e_get(db_session: AsyncSession) -> None:
    repo = ClienteRepo(db_session)
    cli = await repo.upsert_from_sgp(_cli(), whatsapp="5511@s")
    assert cli.id is not None
    fetched = await repo.get_by_cpf_hash(hash_pii("11122233344"))
    assert fetched is not None
    assert fetched.nome_encrypted is not None
    assert decrypt_pii(fetched.nome_encrypted) == "Maria"
    assert fetched.cidade == "Sao Paulo"
    assert fetched.plano == "Premium 100MB"


async def test_upsert_atualiza_existente(db_session: AsyncSession) -> None:
    repo = ClienteRepo(db_session)
    a = await repo.upsert_from_sgp(_cli(), whatsapp="5511@s")
    cli2 = _cli()
    cli2 = ClienteSgp(
        provider=cli2.provider,
        sgp_id=cli2.sgp_id,
        nome="Maria S",
        cpf_cnpj=cli2.cpf_cnpj,
        contratos=cli2.contratos,
        endereco=cli2.endereco,
    )
    b = await repo.upsert_from_sgp(cli2, whatsapp="5511@s")
    assert a.id == b.id
    assert b.nome_encrypted is not None
    assert decrypt_pii(b.nome_encrypted) == "Maria S"
