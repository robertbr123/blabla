#!/usr/bin/env bash
# Production smoke for Ondeline v2. Runs at T-0 and post-deploy.
# Hits /livez, /healthz, /metrics and reports any failure.
#
# Usage:
#   scripts/smoke-prod.sh              # checks localhost:8000
#   API_BASE=https://api.example.com scripts/smoke-prod.sh
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
FAIL=0

check() {
    local label="$1"
    local url="$2"
    local expect_status="$3"
    local body_match="${4:-}"

    echo -n "[$label] $url ... "
    local resp status body
    resp=$(curl -s -o /tmp/_smoke_body -w "%{http_code}" --max-time 10 "$url" || echo "000")
    status="$resp"
    body=$(cat /tmp/_smoke_body 2>/dev/null || true)
    rm -f /tmp/_smoke_body

    if [ "$status" != "$expect_status" ]; then
        echo "FAIL (got HTTP $status, expected $expect_status)"
        FAIL=1
        return
    fi
    if [ -n "$body_match" ] && ! grep -q -- "$body_match" <<<"$body"; then
        echo "FAIL (body missing '$body_match')"
        FAIL=1
        return
    fi
    echo "OK"
}

check "livez"    "$API_BASE/livez"    200 '"alive"'
check "healthz"  "$API_BASE/healthz"  200 '"checks"'
check "metrics"  "$API_BASE/metrics"  200 'ondeline_webhook_received_total'

# Webhook smoke: POST with bad HMAC must 401 (proving the route + signature check are active)
echo -n "[webhook hmac-reject] POST /webhook with bad signature ... "
WSTATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -X POST "$API_BASE/webhook" \
    -H "Content-Type: application/json" \
    -H "X-Signature: sha256=deadbeef" \
    -d '{"event":"test"}' || echo "000")
if [ "$WSTATUS" = "401" ] || [ "$WSTATUS" = "403" ]; then
    echo "OK (HTTP $WSTATUS as expected)"
else
    echo "FAIL (got HTTP $WSTATUS, expected 401 or 403)"
    FAIL=1
fi

# /healthz must report db=ok and redis=ok
echo -n "[healthz body] checks.db=ok && checks.redis=ok ... "
HBODY=$(curl -s "$API_BASE/healthz")
if echo "$HBODY" | grep -q '"db":"ok"' && echo "$HBODY" | grep -q '"redis":"ok"'; then
    echo "OK"
else
    echo "FAIL (body: $HBODY)"
    FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
    echo
    echo "SMOKE FAILED — DO NOT proceed with cutover. Investigate above failures."
    exit 1
fi
echo
echo "SMOKE OK"
