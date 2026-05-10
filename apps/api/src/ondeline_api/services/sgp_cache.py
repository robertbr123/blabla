"""SgpCacheService — Redis primario + DB fallback + write-through + negative.

Chaves Redis:
  sgp:cliente:<cpf_hash>   -> JSON do ClienteSgp
  sgp:not_found:<cpf_hash> -> b"1" (TTL menor, evita marteladas)

DB fallback: tabela `sgp_cache` (PK = cpf_hash + provider). Sobrevive a flush
do Redis. Atualizada no mesmo write-through; lida quando Redis dispara excecao.

Hash do cpf usa o `hash_pii` do projeto (HMAC-SHA256 com pepper) por
consistencia com `clientes.cpf_hash`.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, Protocol

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import hash_pii
from ondeline_api.db.models.business import SgpCache
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


class _RedisProto(Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, ex: int | None = None) -> Any: ...
    async def delete(self, *keys: str) -> int: ...


def _serialize_cliente(c: ClienteSgp) -> dict[str, Any]:
    return {
        "provider": c.provider.value,
        "sgp_id": c.sgp_id,
        "nome": c.nome,
        "cpf_cnpj": c.cpf_cnpj,
        "whatsapp": c.whatsapp,
        "contratos": [asdict(ct) for ct in c.contratos],
        "endereco": asdict(c.endereco),
        "titulos": [asdict(t) for t in c.titulos],
    }


def _deserialize_cliente(d: dict[str, Any]) -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum(d["provider"]),
        sgp_id=d["sgp_id"],
        nome=d["nome"],
        cpf_cnpj=d["cpf_cnpj"],
        whatsapp=d.get("whatsapp", ""),
        contratos=[Contrato(**c) for c in d.get("contratos", [])],
        endereco=EnderecoSgp(**d.get("endereco", {})),
        titulos=[Fatura(**t) for t in d.get("titulos", [])],
    )


class SgpCacheService:
    def __init__(
        self,
        *,
        redis: _RedisProto,
        session: AsyncSession,
        router: SgpRouter,
        ttl_cliente: int,
        ttl_negativo: int,
        cpf_hasher: Callable[[str], str] | None = None,
    ) -> None:
        self._redis = redis
        self._session = session
        self._router = router
        self._ttl = ttl_cliente
        self._ttl_neg = ttl_negativo
        self._hasher = cpf_hasher or hash_pii

    # ── public ────────────────────────────────────────────────

    async def get_cliente(self, cpf: str) -> ClienteSgp | None:
        clean = "".join(ch for ch in (cpf or "") if ch.isdigit())
        if not clean:
            return None
        cpf_hash = self._hasher(clean)

        # 1) Redis hit
        try:
            raw = await self._redis.get(f"sgp:cliente:{cpf_hash}")
            if raw:
                return _deserialize_cliente(json.loads(raw))
            neg = await self._redis.get(f"sgp:not_found:{cpf_hash}")
            if neg:
                return None
        except Exception:
            # Redis dead — fallback no DB
            db = await self._read_db(cpf_hash)
            if db is not None:
                return db

        # 2) Miss → router
        cli = await self._router.buscar_por_cpf(clean)
        await self._write(cpf_hash, cli)
        return cli

    async def invalidate(self, cpf: str) -> None:
        clean = "".join(ch for ch in (cpf or "") if ch.isdigit())
        if not clean:
            return
        cpf_hash = self._hasher(clean)
        try:
            await self._redis.delete(f"sgp:cliente:{cpf_hash}", f"sgp:not_found:{cpf_hash}")
        except Exception:
            pass
        # nao apagamos do DB — o write-through proximo sobrescreve

    # ── internal ──────────────────────────────────────────────

    async def _read_db(self, cpf_hash: str) -> ClienteSgp | None:
        stmt = (
            select(SgpCache)
            .where(SgpCache.cpf_hash == cpf_hash)
            .order_by(SgpCache.fetched_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _deserialize_cliente(row.payload)

    async def _write(self, cpf_hash: str, cli: ClienteSgp | None) -> None:
        if cli is None:
            try:
                await self._redis.set(f"sgp:not_found:{cpf_hash}", b"1", ex=self._ttl_neg)
            except Exception:
                pass
            return
        payload = _serialize_cliente(cli)
        try:
            await self._redis.set(
                f"sgp:cliente:{cpf_hash}",
                json.dumps(payload).encode("utf-8"),
                ex=self._ttl,
            )
        except Exception:
            pass

        # write-through DB
        stmt = pg_insert(SgpCache).values(
            cpf_hash=cpf_hash,
            provider=cli.provider,
            payload=payload,
            ttl=self._ttl,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["cpf_hash", "provider"],
            set_={"payload": payload, "ttl": self._ttl, "fetched_at": sa.func.now()},
        )
        await self._session.execute(stmt)
