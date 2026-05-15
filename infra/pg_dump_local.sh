#!/usr/bin/env bash
# Local daily Postgres backup for Ondeline v2 prod.
# Writes /root/BLABLA/ondeline-backups/ondeline-YYYYMMDD-HHMM.sql.gz and prunes
# files older than ${RETENTION_DAYS:-30} days.
#
# Wire into cron via: 0 3 * * * /root/BLABLA/ondeline-v2/infra/pg_dump_local.sh
#
# Remote upload (S3/MinIO) is out of scope for M9; add later by piping the gz to
# `mc cp -` / `aws s3 cp -` after this script writes locally.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/root/BLABLA/ondeline-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
CONTAINER="${CONTAINER:-blabla-postgres}"
DB="${DB:-ondeline}"
USER="${PG_USER:-ondeline}"

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d-%H%M)"
OUT="$BACKUP_DIR/ondeline-$TS.sql.gz"

docker exec -i "$CONTAINER" pg_dump -U "$USER" -d "$DB" --no-owner --clean --if-exists \
    | gzip -9 > "$OUT"

SIZE=$(stat -c %s "$OUT")
echo "backup ok: $OUT ($SIZE bytes)"

# Prune
find "$BACKUP_DIR" -name 'ondeline-*.sql.gz' -mtime "+$RETENTION_DAYS" -print -delete || true
