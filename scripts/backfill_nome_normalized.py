#!/usr/bin/env python3
"""Backfill `clientes_cadastro.nome_normalized` decifrando nome_encrypted.

Roda dentro do container API (tem acesso ao Fernet key + DB).

Uso:
    docker exec -it blabla-api python /app/scripts/backfill_nome_normalized.py

Ou copia o script pro container e roda:
    docker cp scripts/backfill_nome_normalized.py blabla-api:/tmp/
    docker exec -it blabla-api python /tmp/backfill_nome_normalized.py
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
from ondeline_api.db.models.business import ClienteCadastro  # noqa: E402
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
        # Pega todos os que estão sem normalized (ou força refill com --all)
        force_all = "--all" in sys.argv
        stmt = select(ClienteCadastro).where(ClienteCadastro.deleted_at.is_(None))
        if not force_all:
            stmt = stmt.where(ClienteCadastro.nome_normalized.is_(None))
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
