"""Import de clientes do site MySQL antigo pra `clientes_cadastro` Postgres.

Estrategia:
- Dedup por cpf_hash (UPDATE se ja existe, INSERT se nao)
- Match `installer` (texto livre no MySQL) com `users.name` — se bater,
  preenche installer_user_id; senao, deixa NULL e mantem so o texto.
- Encripta PII na inserção (Fernet + hash com pepper).
- `mark_as_synced=True` (default): seta sgp_synced_at = registration_date
  porque clientes do site antigo ja estavam no SGP.
"""
from __future__ import annotations

from datetime import UTC, datetime, time as _time
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.cliente_cadastro import (
    ImportClienteRow,
    ImportResult,
)
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import ClienteCadastro
from ondeline_api.db.models.identity import User
from ondeline_api.repositories.cliente_cadastro import ClienteCadastroRepo

log = structlog.get_logger(__name__)


def _only_digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


async def _build_installer_index(session: AsyncSession) -> dict[str, Any]:
    """Mapa nome lower -> User. Pra match fuzzy na importacao."""
    rows = (await session.execute(select(User))).scalars().all()
    return {u.name.strip().lower(): u for u in rows if u.name}


async def import_rows(
    session: AsyncSession,
    rows: list[ImportClienteRow],
    *,
    dry_run: bool = False,
    mark_as_synced: bool = True,
) -> ImportResult:
    """Processa lista de rows. Dedup por cpf_hash."""
    repo = ClienteCadastroRepo(session)
    user_idx = await _build_installer_index(session)

    inserted = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for i, row in enumerate(rows):
        try:
            cpf_digits = _only_digits(row.cpf)
            if len(cpf_digits) not in (11, 14):
                errors.append(f"row {i}: CPF invalido ({row.cpf!r})")
                skipped += 1
                continue
            tel_digits = _only_digits(row.phone)
            if len(tel_digits) < 10:
                errors.append(f"row {i} cpf={cpf_digits}: telefone invalido")
                skipped += 1
                continue

            cpf_hash = hash_pii(cpf_digits)
            installer_user = user_idx.get(row.installer.strip().lower())
            installer_user_id = installer_user.id if installer_user else None
            installer_nome = row.installer.strip()

            existente = await repo.get_by_cpf_hash(cpf_hash)

            sgp_synced_at: datetime | None = None
            if mark_as_synced:
                # naive datetime no fuso local — converte pra UTC com Z
                sgp_synced_at = datetime.combine(
                    row.registration_date, _time(12, 0), tzinfo=UTC
                )

            if existente is not None:
                # UPDATE: atualiza campos editaveis, preserva cpf_hash + dob.
                existente.nome_encrypted = encrypt_pii(row.name.strip())
                existente.telefone_encrypted = encrypt_pii(tel_digits)
                existente.cep = row.cep
                existente.address = row.address.strip()
                existente.number = row.number.strip()
                existente.complement = row.complement
                existente.neighborhood = row.neighborhood
                existente.city = row.city.strip()
                existente.state = (row.state or "").upper() or None
                existente.plan_id = row.plan_id
                existente.plan_nome = row.plan.strip()
                if row.pppoe_user:
                    existente.pppoe_user_encrypted = encrypt_pii(row.pppoe_user)
                if row.pppoe_pass:
                    existente.pppoe_pass_encrypted = encrypt_pii(row.pppoe_pass)
                existente.due_date = row.due_date
                if installer_user_id and not existente.installer_user_id:
                    existente.installer_user_id = installer_user_id
                if not existente.installer_nome:
                    existente.installer_nome = installer_nome
                existente.serial = row.serial or existente.serial
                existente.contrato = row.contrato or existente.contrato
                if row.observation:
                    existente.observation = row.observation
                existente.latitude = (
                    row.latitude if row.latitude is not None else existente.latitude
                )
                existente.longitude = (
                    row.longitude if row.longitude is not None else existente.longitude
                )
                existente.location_accuracy = (
                    row.location_accuracy
                    if row.location_accuracy is not None
                    else existente.location_accuracy
                )
                if mark_as_synced and existente.sgp_synced_at is None:
                    existente.sgp_synced_at = sgp_synced_at
                if not dry_run:
                    await session.flush()
                updated += 1
                continue

            cliente = ClienteCadastro(
                cpf_hash=cpf_hash,
                cpf_encrypted=encrypt_pii(cpf_digits),
                nome_encrypted=encrypt_pii(row.name.strip()),
                dob=row.dob,
                telefone_encrypted=encrypt_pii(tel_digits),
                cep=row.cep,
                address=row.address.strip(),
                number=row.number.strip(),
                complement=row.complement,
                neighborhood=row.neighborhood,
                city=row.city.strip(),
                state=(row.state or "").upper() or None,
                plan_id=row.plan_id,
                plan_nome=row.plan.strip(),
                pppoe_user_encrypted=(
                    encrypt_pii(row.pppoe_user) if row.pppoe_user else None
                ),
                pppoe_pass_encrypted=(
                    encrypt_pii(row.pppoe_pass) if row.pppoe_pass else None
                ),
                due_date=row.due_date,
                installer_user_id=installer_user_id,
                installer_nome=installer_nome,
                serial=row.serial,
                contrato=row.contrato,
                observation=row.observation,
                latitude=row.latitude,
                longitude=row.longitude,
                location_accuracy=row.location_accuracy,
                registration_date=row.registration_date,
                sgp_synced_at=sgp_synced_at,
            )
            if not dry_run:
                await repo.create(cliente)
            inserted += 1
        except Exception as e:
            log.warning(
                "cliente_import.row_failed",
                idx=i,
                error=str(e)[:200],
            )
            errors.append(f"row {i}: {type(e).__name__}: {e}")
            skipped += 1

    if dry_run:
        # Roll back tudo que foi flushado (nao deveria ter sido, mas garante).
        await session.rollback()

    return ImportResult(
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )


def parse_csv(content: bytes) -> list[ImportClienteRow]:
    """Parse de CSV com header. Aceita os nomes de coluna do MySQL antigo:
    cpf, name, dob, phone, cep, address, number, complement, neighborhood,
    city, state, plan, pppoe_user, pppoe_pass, due_date, installer, serial,
    contrato, observation, latitude, longitude, location_accuracy,
    registration_date.

    Datas: aceita YYYY-MM-DD.
    Numericos: aceita string com . ou , decimal.
    """
    import csv as _csv
    import io
    from datetime import date as _date

    text = content.decode("utf-8-sig", errors="replace")
    reader = _csv.DictReader(io.StringIO(text))
    rows: list[ImportClienteRow] = []
    def _f_or_none(d: dict[str, Any], key: str) -> float | None:
        v = d.get(key)
        if v in (None, "", "NULL"):
            return None
        return float(str(v).replace(",", "."))

    def _to_date(d: dict[str, Any], key: str) -> _date:
        v = d.get(key)
        if not v:
            raise ValueError(f"{key} vazio")
        return _date.fromisoformat(str(v).split(" ")[0])

    for raw in reader:
        # Normaliza
        d: dict[str, Any] = {k.strip().lower(): (v.strip() if v else None) for k, v in raw.items()}

        row = ImportClienteRow(
            cpf=str(d.get("cpf", "")),
            name=str(d.get("name", "")),
            dob=_to_date(d, "dob"),
            phone=str(d.get("phone", "")),
            cep=d.get("cep") or None,
            address=str(d.get("address", "")),
            number=str(d.get("number", "")),
            complement=d.get("complement") or None,
            neighborhood=d.get("neighborhood") or None,
            city=str(d.get("city", "")),
            state=(d.get("state") or "").upper() or None,
            plan=str(d.get("plan", "")),
            plan_id=int(d["plan_id"]) if d.get("plan_id") else None,
            pppoe_user=d.get("pppoe_user") or None,
            pppoe_pass=d.get("pppoe_pass") or None,
            due_date=int(d.get("due_date", "10")),
            installer=str(d.get("installer", "")),
            serial=d.get("serial") or None,
            contrato=d.get("contrato") or None,
            observation=d.get("observation") or None,
            latitude=_f_or_none(d, "latitude"),
            longitude=_f_or_none(d, "longitude"),
            location_accuracy=_f_or_none(d, "location_accuracy"),
            registration_date=_to_date(d, "registration_date"),
        )
        rows.append(row)
    return rows


async def total_clientes_cadastro(session: AsyncSession) -> int:
    """Conta total na tabela (debug/teste)."""
    return int(
        (
            await session.execute(
                select(func.count(ClienteCadastro.id))
                .where(ClienteCadastro.deleted_at.is_(None))
            )
        ).scalar_one()
    )
