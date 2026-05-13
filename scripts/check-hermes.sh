#!/usr/bin/env bash
# Confirm the Hermes-3 LLM gateway is reachable and serving the right model.
# Run during pre-cutover checks (and any time the gateway might have changed).
#
# Usage:
#   scripts/check-hermes.sh
#   HERMES_URL=http://127.0.0.1:8642/v1 scripts/check-hermes.sh
set -euo pipefail

HERMES_URL="${HERMES_URL:-http://127.0.0.1:8642/v1}"
EXPECTED_MODEL_SUBSTRING="${EXPECTED_MODEL_SUBSTRING:-Hermes}"

echo "Checking $HERMES_URL/models ..."
RESP=$(curl -s --max-time 5 "$HERMES_URL/models" || true)
if [ -z "$RESP" ]; then
    echo "FAIL: empty response (gateway not reachable?)" >&2
    exit 1
fi
echo "$RESP" | python3 -m json.tool 2>/dev/null || { echo "FAIL: not JSON: $RESP" >&2; exit 1; }
if echo "$RESP" | grep -qi -- "$EXPECTED_MODEL_SUBSTRING"; then
    echo
    echo "OK: gateway responding with a model whose id contains '$EXPECTED_MODEL_SUBSTRING'"
    exit 0
else
    echo "FAIL: gateway response does not mention '$EXPECTED_MODEL_SUBSTRING'" >&2
    exit 1
fi
