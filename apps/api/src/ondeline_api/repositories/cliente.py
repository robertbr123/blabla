"""ClienteRepo — get_by_cpf_hash + upsert_from_sgp."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


def _primary_cidade(c: ClienteSgp) -> str:
    if c.contratos:
        for ct in c.contratos:
            if ct.cidade:
                return ct.cidade
    return c.endereco.cidade or ""


def _format_endereco(c: ClienteSgp) -> str:
    e = c.endereco
    parts = [e.logradouro, e.numero, e.bairro, e.cidade, e.uf, e.cep]
    return ", ".join(p for p in parts if p)


class ClienteRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_cpf_hash(self, cpf_hash: str) -> Cliente | None:
        stmt = (
            select(Cliente)
            .where(Cliente.cpf_hash == cpf_hash, Cliente.deleted_at.is_(None))
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert_from_sgp(self, c: ClienteSgp, *, whatsapp: str) -> Cliente:
        cpf_hash = hash_pii(c.cpf_cnpj)
        existing = await self.get_by_cpf_hash(cpf_hash)
        plano = c.contratos[0].plano if c.contratos else None
        status = c.contratos[0].status if c.contratos else None
        cidade = _primary_cidade(c)
        endereco = _format_endereco(c)
        provider = (
            SgpProviderEnum.ONDELINE
            if c.provider is SgpProviderEnum.ONDELINE
            else SgpProviderEnum.LINKNETAM
        )
        if existing is not None:
            existing.nome_encrypted = encrypt_pii(c.nome)
            existing.whatsapp = whatsapp or existing.whatsapp
            existing.plano = plano
            existing.status = status
            existing.endereco_encrypted = encrypt_pii(endereco) if endereco else None
            existing.cidade = cidade
            existing.sgp_provider = provider
            existing.sgp_id = c.sgp_id
            await self._session.flush()
            return existing

        novo = Cliente(
            cpf_cnpj_encrypted=encrypt_pii(c.cpf_cnpj),
            cpf_hash=cpf_hash,
            nome_encrypted=encrypt_pii(c.nome),
            whatsapp=whatsapp,
            plano=plano,
            status=status,
            endereco_encrypted=encrypt_pii(endereco) if endereco else None,
            cidade=cidade,
            sgp_provider=provider,
            sgp_id=c.sgp_id,
        )
        self._session.add(novo)
        await self._session.flush()
        return novo
