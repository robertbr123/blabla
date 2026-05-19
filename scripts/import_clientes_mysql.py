#!/usr/bin/env python3
"""Importa clientes do MySQL antigo pra Postgres do BlaBla via API.

Uso:
    pip install pymysql httpx
    python scripts/import_clientes_mysql.py \\
        --mysql-host localhost \\
        --mysql-user root \\
        --mysql-pass senha \\
        --mysql-db meudb \\
        --api-url https://apiblabla.robertbr.dev \\
        --token <ACCESS_TOKEN_ADMIN> \\
        --dry-run                  # opcional: nao grava, so reporta
        --batch-size 100           # default 100
        --since 2024-01-01         # opcional: importa so a partir dessa data

Autenticacao: passa o access token de um user admin no header. Pega ele
fazendo login no dashboard e copiando do localStorage (chave `access_token`).

Credenciais MySQL nao saem da sua maquina — o script faz a leitura local
e envia pra API ja em formato JSON.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Any


def _row_to_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Converte uma row do mysqldump pra payload da API."""
    def _s(v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    return {
        "cpf": _s(row.get("cpf")) or "",
        "name": _s(row.get("name")) or "",
        "dob": str(row["dob"]) if row.get("dob") else None,
        "phone": _s(row.get("phone")) or "",
        "cep": _s(row.get("cep")),
        "address": _s(row.get("address")) or "",
        "number": _s(row.get("number")) or "",
        "complement": _s(row.get("complement")),
        "neighborhood": _s(row.get("neighborhood")),
        "city": _s(row.get("city")) or "",
        "state": _s(row.get("state")),
        "plan": _s(row.get("plan")) or "",
        "plan_id": int(row["plan_id"]) if row.get("plan_id") else None,
        "pppoe_user": _s(row.get("pppoe_user")),
        "pppoe_pass": _s(row.get("pppoe_pass")),
        "due_date": int(row.get("due_date") or 10),
        "installer": _s(row.get("installer")) or "",
        "serial": _s(row.get("serial")),
        "contrato": _s(row.get("contrato")),
        "observation": _s(row.get("observation")),
        "latitude": float(row["latitude"]) if row.get("latitude") is not None else None,
        "longitude": float(row["longitude"]) if row.get("longitude") is not None else None,
        "location_accuracy": (
            float(row["location_accuracy"])
            if row.get("location_accuracy") is not None
            else None
        ),
        "registration_date": (
            str(row["registration_date"])
            if row.get("registration_date")
            else str(date.today())
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mysql-host", default="localhost")
    ap.add_argument("--mysql-port", type=int, default=3306)
    ap.add_argument("--mysql-user", required=True)
    ap.add_argument("--mysql-pass", required=True)
    ap.add_argument("--mysql-db", required=True)
    ap.add_argument("--mysql-table", default="clients")
    ap.add_argument("--api-url", required=True, help="ex: https://apiblabla.robertbr.dev")
    ap.add_argument("--token", required=True, help="access token de um user admin")
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
        "--since",
        type=str,
        help="filtra registration_date >= YYYY-MM-DD",
    )
    ap.add_argument(
        "--limit",
        type=int,
        help="limite max de rows pra teste (default: tudo)",
    )
    args = ap.parse_args()

    try:
        import pymysql  # type: ignore[import-untyped]
    except ImportError:
        print("✗ Instale primeiro: pip install pymysql", file=sys.stderr)
        return 1

    try:
        import httpx
    except ImportError:
        print("✗ Instale primeiro: pip install httpx", file=sys.stderr)
        return 1

    print(f"→ Conectando no MySQL {args.mysql_host}:{args.mysql_port}/{args.mysql_db}…")
    conn = pymysql.connect(
        host=args.mysql_host,
        port=args.mysql_port,
        user=args.mysql_user,
        password=args.mysql_pass,
        database=args.mysql_db,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
    )

    sql = f"SELECT * FROM `{args.mysql_table}`"  # noqa: S608 (tabela vem do user)
    where = []
    sql_args: list[Any] = []
    if args.since:
        where.append("registration_date >= %s")
        sql_args.append(args.since)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY registration_date ASC"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    with conn.cursor() as cur:
        print(f"→ Lendo MySQL: {sql}")
        cur.execute(sql, sql_args)
        rows = cur.fetchall()
    conn.close()
    print(f"  {len(rows)} rows encontradas")
    if not rows:
        return 0

    payloads = [_row_to_payload(r) for r in rows]

    api = httpx.Client(
        base_url=args.api_url.rstrip("/"),
        headers={"Authorization": f"Bearer {args.token}"},
        timeout=60.0,
    )

    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    all_errors: list[str] = []

    for i in range(0, len(payloads), args.batch_size):
        chunk = payloads[i : i + args.batch_size]
        print(
            f"→ Batch {i // args.batch_size + 1}/"
            f"{(len(payloads) + args.batch_size - 1) // args.batch_size} "
            f"({len(chunk)} rows)…"
        )
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
