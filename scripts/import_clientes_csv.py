#!/usr/bin/env python3
"""Importa clientes de um CSV (exportado do phpMyAdmin) pra BlaBla via API.

Uso:
    pip install httpx

    # Dry-run (não grava — só reporta)
    python scripts/import_clientes_csv.py \\
        --csv scripts/clients.csv \\
        --api-url https://apiblabla.robertbr.dev \\
        --email seuadmin@exemplo.com \\
        --password 'suasenha' \\
        --dry-run --limit 5

    # Pra valer
    python scripts/import_clientes_csv.py \\
        --csv scripts/clients.csv \\
        --api-url https://apiblabla.robertbr.dev \\
        --email seuadmin@exemplo.com \\
        --password 'suasenha'

CSV esperado: o exportado do phpMyAdmin com colunas (em qualquer ordem):
    cpf, name, address, number, complement, city, state, neighborhood,
    dueDay, phone, phone_number, cep, birthDate, observation,
    latitude, longitude, location_accuracy, planId, installer,
    pppoe, password, serial, contrato, created_at, active

O script:
  - Loga via /auth/login (não precisa pegar token do DevTools)
  - Trata "NULL" literal e "" como null
  - Manda em batches via /api/v1/clientes-campo/import
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from typing import Any


def _clean(v: Any) -> str | None:
    """Trata 'NULL' literal do phpMyAdmin e strings vazias como None."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.upper() == "NULL":
        return None
    return s


def _opt_int(v: Any) -> int | None:
    s = _clean(v)
    if s is None:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _opt_float(v: Any) -> float | None:
    s = _clean(v)
    if s is None:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _date_part(v: Any) -> str | None:
    """Pega 'YYYY-MM-DD' de um datetime tipo '2026-03-30 15:33:19'.

    Trata '0000-00-00' (null-fake do MySQL) e datas com mês/dia inválidos
    como None — a API rejeitaria.
    """
    s = _clean(v)
    if s is None:
        return None
    part = s.split(" ")[0]
    # MySQL null-fake e variantes
    if part.startswith("0000") or part == "":
        return None
    # Valida estrutura YYYY-MM-DD com mês 1-12 e dia 1-31
    try:
        y, m, d = part.split("-")
        mi = int(m)
        di = int(d)
        if not (1 <= mi <= 12 and 1 <= di <= 31 and len(y) == 4):
            return None
    except (ValueError, AttributeError):
        return None
    return part


def _digits(v: Any) -> str | None:
    """Extrai só dígitos de uma string (útil pra phone formatado)."""
    s = _clean(v)
    if s is None:
        return None
    out = "".join(ch for ch in s if ch.isdigit())
    return out or None


def _normalize_state(v: Any) -> str | None:
    """State precisa ter exatamente 2 chars (UF). Aceita 'AM' ou retorna None."""
    s = _clean(v)
    if s is None or len(s) != 2:
        return None
    return s.upper()


def _normalize_phone(v: Any, fallback: Any = None) -> str:
    """Telefone: min 10, max 15 dígitos. Usa fallback se principal falhar."""
    for cand in (v, fallback):
        d = _digits(cand)
        if d and 10 <= len(d) <= 15:
            return d
    return "0000000000"  # sentinela — vai entrar como "sem telefone real"


def _clamp(v: int | None, lo: int, hi: int, default: int) -> int:
    if v is None:
        return default
    return max(lo, min(hi, v))


def _truncate(v: str | None, max_len: int) -> str | None:
    if v is None:
        return None
    return v[:max_len]


def _row_to_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Converte uma row do CSV pra payload da API.

    Campos obrigatórios recebem fallback (sentinelas) quando faltam — a API
    rejeitaria a linha caso contrário. Marcadores típicos:
      - phone "0000000000" → sem telefone real
      - dob "1900-01-01" → data desconhecida
      - number "S/N", name "Sem nome", etc.
    Corrija no dashboard depois.
    """
    plan_id = _opt_int(row.get("planId"))
    plan_name = f"Plano {plan_id}" if plan_id is not None else "Sem plano"
    return {
        "cpf": _clean(row.get("cpf")) or "",  # vazio API rejeita
        "name": _truncate(_clean(row.get("name")) or "Sem nome", 255),
        "dob": _date_part(row.get("birthDate")) or "1900-01-01",
        "phone": _normalize_phone(row.get("phone"), row.get("phone_number")),
        "cep": _truncate(_digits(row.get("cep")), 10),
        "address": _truncate(_clean(row.get("address")) or "Sem endereço", 255),
        "number": _truncate(_clean(row.get("number")) or "S/N", 10),
        "complement": _truncate(_clean(row.get("complement")), 255),
        "neighborhood": _truncate(_clean(row.get("neighborhood")), 100),
        "city": _truncate(_clean(row.get("city")) or "Não informada", 100),
        "state": _normalize_state(row.get("state")),
        "plan": _truncate(plan_name, 255),
        "plan_id": plan_id,
        "pppoe_user": _truncate(_clean(row.get("pppoe")), 100),
        "pppoe_pass": _truncate(_clean(row.get("password")), 100),
        "due_date": _clamp(_opt_int(row.get("dueDay")), 10, 30, 10),
        "installer": _truncate(_clean(row.get("installer")) or "Sem instalador", 255),
        "serial": _truncate(_clean(row.get("serial")), 100),
        "contrato": _truncate(_clean(row.get("contrato")), 20),
        "observation": _clean(row.get("observation")),
        "latitude": _opt_float(row.get("latitude")),
        "longitude": _opt_float(row.get("longitude")),
        "location_accuracy": _opt_float(row.get("location_accuracy")),
        "registration_date": _date_part(row.get("created_at")) or str(date.today()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="caminho do CSV (ex: scripts/clients.csv)")
    ap.add_argument("--api-url", required=True, help="ex: https://apiblabla.robertbr.dev")
    ap.add_argument("--email", required=True, help="email de um user admin")
    ap.add_argument("--password", required=True, help="senha do user admin")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument(
        "--mark-as-synced",
        action="store_true",
        default=True,
        help="marca como sincronizado com SGP (default true)",
    )
    ap.add_argument(
        "--no-mark-as-synced",
        dest="mark_as_synced",
        action="store_false",
    )
    ap.add_argument(
        "--only-active",
        action="store_true",
        help="importa só linhas com active='1' (default: importa todas)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        help="limite max de rows pra teste (default: tudo)",
    )
    args = ap.parse_args()

    try:
        import httpx
    except ImportError:
        print("✗ Instale primeiro: pip install httpx", file=sys.stderr)
        return 1

    # 1) Ler CSV
    print(f"→ Lendo {args.csv}…")
    try:
        with open(args.csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"✗ CSV não encontrado: {args.csv}", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        # Tenta latin-1 como fallback (phpMyAdmin antigo)
        with open(args.csv, newline="", encoding="latin-1") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    if args.only_active:
        before = len(rows)
        rows = [r for r in rows if _clean(r.get("active")) == "1"]
        print(f"  filtrado: {len(rows)}/{before} active=1")

    if args.limit:
        rows = rows[: args.limit]

    print(f"  {len(rows)} linhas a importar")
    if not rows:
        return 0

    payloads = [_row_to_payload(r) for r in rows]

    # 2) Login
    print(f"→ Login em {args.api_url}…")
    api = httpx.Client(base_url=args.api_url.rstrip("/"), timeout=60.0)
    try:
        r = api.post(
            "/auth/login",
            json={"email": args.email, "password": args.password},
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        print("  ✓ autenticado")
    except httpx.HTTPStatusError as e:
        print(f"  ✗ login falhou ({e.response.status_code}): {e.response.text[:200]}", file=sys.stderr)
        return 2

    api.headers["Authorization"] = f"Bearer {token}"

    # 3) Importar em batches
    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    all_errors: list[str] = []

    n_batches = (len(payloads) + args.batch_size - 1) // args.batch_size
    for i in range(0, len(payloads), args.batch_size):
        chunk = payloads[i : i + args.batch_size]
        print(f"→ Batch {i // args.batch_size + 1}/{n_batches} ({len(chunk)} rows)…")
        try:
            r = api.post(
                "/api/v1/clientes-campo/import",
                json={
                    "rows": chunk,
                    "dry_run": args.dry_run,
                    "mark_as_synced": args.mark_as_synced,
                },
            )
            r.raise_for_status()
            result = r.json()
            total_inserted += result["inserted"]
            total_updated += result["updated"]
            total_skipped += result["skipped"]
            all_errors.extend(result["errors"])
            print(
                f"  ✓ inserted={result['inserted']} "
                f"updated={result['updated']} "
                f"skipped={result['skipped']} "
                f"errors={len(result['errors'])}"
            )
        except httpx.HTTPStatusError as e:
            body = e.response.text[:300]
            print(f"  ✗ HTTP {e.response.status_code}: {body}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"  ✗ {type(e).__name__}: {e}", file=sys.stderr)
            return 2

    print("─" * 60)
    print(
        "Resultado final: "
        f"inserted={total_inserted} updated={total_updated} "
        f"skipped={total_skipped} errors={len(all_errors)}"
    )
    if all_errors:
        print("\nPrimeiros 10 erros:")
        for e in all_errors[:10]:
            print(f"  · {e}")
    if args.dry_run:
        print("\n⚠ DRY RUN — nenhum dado foi gravado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
