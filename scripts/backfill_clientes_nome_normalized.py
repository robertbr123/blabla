#!/usr/bin/env python3
"""Backfill `clientes.nome_normalized` decifrando nome_encrypted.

Necessario apos a migration 0052 para que a busca por nome em Conversas
encontre clientes que ja existiam antes da coluna. Novos/atualizados ja
entram preenchidos via ClienteRepo.upsert_from_sgp.

Roda dentro do container API (tem acesso ao Fernet key + DB).

IMPORTANTE: a imagem do GHCR NAO inclui a pasta scripts/, entao copie o
arquivo pro container antes de rodar (a partir do clone git na VPS):

    cd blabla   # raiz do repo, onde existe scripts/
    docker cp scripts/backfill_clientes_nome_normalized.py blabla-api:/tmp/
    docker exec -it blabla-api python /tmp/backfill_clientes_nome_normalized.py

Flags:
    --all   reprocessa todos (nao so os com nome_normalized NULL)
"""
from __future__ import annotations

import asyncio
import os
import sys

# Acesso aos módulos do app
sys.path.insert(0, "/app/src")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from ondeline_api.db.crypto import decrypt_pii  # noqa: E402
from ondeline_api.db.models.business import Cliente  # noqa: E402
from ondeline_api.repositories.cliente_cadastro import normalize_nome  # noqa: E402


async def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL não setada", file=sys.stderr)
        return 1
    # Driver asyncpg
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(url, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    updated = 0
    failed = 0
    skipped = 0

    async with SessionLocal() as session:
        force_all = "--all" in sys.argv
        stmt = select(Cliente).where(Cliente.deleted_at.is_(None))
        if not force_all:
            stmt = stmt.where(Cliente.nome_normalized.is_(None))
        rows = (await session.execute(stmt)).scalars().all()
        print(f"→ {len(rows)} clientes para processar")

        for c in rows:
            try:
                nome = decrypt_pii(c.nome_encrypted)
                norm = normalize_nome(nome)
                if norm is None:
                    skipped += 1
                    continue
                c.nome_normalized = norm
                updated += 1
                if updated % 100 == 0:
                    print(f"  ... {updated} atualizados")
            except Exception as e:
                failed += 1
                print(f"  ✗ {c.id}: {type(e).__name__}: {e}", file=sys.stderr)

        await session.commit()

    print("─" * 60)
    print(f"Resultado: updated={updated} skipped={skipped} failed={failed}")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
