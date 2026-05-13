#!/usr/bin/env bash
# Snapshot the v1 bot data + code into a dated zip under
# /root/BLABLA/ondeline-archive/v1-snapshot-YYYYMMDD.zip
# Run at T-1d of cutover. Idempotent in the sense that re-running the same day
# is refused (won't overwrite); re-running with a different date is OK.
set -euo pipefail

V1_DIR="${V1_DIR:-/root/BLABLA/ondeline-bot}"
ARCHIVE_DIR="${ARCHIVE_DIR:-/root/BLABLA/ondeline-archive}"
DATE_TAG="$(date +%Y%m%d)"
OUT="${ARCHIVE_DIR}/v1-snapshot-${DATE_TAG}.zip"

if [ ! -d "$V1_DIR" ]; then
    echo "ERROR: v1 source dir not found: $V1_DIR" >&2
    exit 2
fi

mkdir -p "$ARCHIVE_DIR"

if [ -e "$OUT" ]; then
    echo "ERROR: archive already exists: $OUT" >&2
    echo "Delete it manually if you really want to re-snapshot today." >&2
    exit 3
fi

# Required artifacts per spec §12; bot.log/dashboard.log included as best-effort
INCLUDES=(
    "bot.py"
    "dashboard.py"
    "config.json"
    "tecnicos.json"
    "conversas"
    "ordens_servico"
    "notificacoes"
    "bot.log"
    "dashboard.log"
)

cd "$V1_DIR"

PRESENT=()
for item in "${INCLUDES[@]}"; do
    if [ -e "$item" ]; then
        PRESENT+=("$item")
    else
        echo "warn: missing $V1_DIR/$item — skipping" >&2
    fi
done

if [ "${#PRESENT[@]}" -eq 0 ]; then
    echo "ERROR: nothing to archive" >&2
    exit 4
fi

zip -r -q "$OUT" "${PRESENT[@]}"

SIZE=$(stat -c %s "$OUT")
SHA=$(sha256sum "$OUT" | awk '{print $1}')

echo "Archive created: $OUT"
echo "Size: $SIZE bytes"
echo "SHA-256: $SHA"
echo "Items archived: ${PRESENT[*]}"
