#!/usr/bin/env bash
# measure_p95.sh — Measure p95 latency for a single API endpoint
#
# Usage:
#   ENDPOINT_URL=https://api.thook.ai/api/dashboard/stats \
#   AUTH_TOKEN="Bearer eyJ..." \
#   bash backend/scripts/measure_p95.sh
#
# Environment variables:
#   ENDPOINT_URL  — Full URL of the endpoint to measure (required)
#   AUTH_TOKEN    — Authorization header value, e.g. "Bearer eyJ..." (required)
#   ITERATIONS    — Number of measurement iterations (default: 100)
#   WARMUP        — Warmup requests to discard (default: 15)
#   DELAY_MS      — Milliseconds to sleep between requests (default: 0)
#                   Set to 1000 to stay under the 60 req/min rate limit in production.
#
# Security note (T-35-01-01):
#   AUTH_TOKEN is read from the environment — NEVER hardcode it in this file.
#   Rotate the token after measurement runs if you are concerned about log exposure.
#
# Rate-limit note (T-35-01-02):
#   With default settings: 115 requests × 10 endpoints = 1150 total requests.
#   ThookAI rate limit is 60 req/min. Use DELAY_MS=1000 for production runs,
#   or point at the dev server (no rate limiting) for faster measurement.
#
# Reads:
#   X-Response-Time response header emitted by TimingMiddleware
#   (backend/middleware/performance.py). The header value is in "NNNms" format.
#
# Output:
#   Prints p95, mean, and max to stdout.
#   Exits 0 if p95 < 500ms (PASS), exits 1 if p95 >= 500ms (FAIL).
#
# Example (batch all 10 endpoints):
#   BASE="https://api.thook.ai"
#   TOK="Bearer $JWT"
#   ENDPOINTS=(
#     "$BASE/api/auth/me"
#     "$BASE/api/dashboard/stats"
#     "$BASE/api/dashboard/feed"
#     "$BASE/api/content/jobs"
#     "$BASE/api/persona/me"
#     "$BASE/api/billing/subscription"
#     "$BASE/api/billing/credits"
#     "$BASE/api/analytics/overview"
#     "$BASE/api/templates"
#     "$BASE/api/platforms/status"
#   )
#   for ep in "${ENDPOINTS[@]}"; do
#     ENDPOINT_URL="$ep" AUTH_TOKEN="$TOK" DELAY_MS=1000 bash backend/scripts/measure_p95.sh
#     sleep 2
#   done

set -euo pipefail

ENDPOINT="${ENDPOINT_URL:?Must set ENDPOINT_URL}"
TOKEN="${AUTH_TOKEN:?Must set AUTH_TOKEN}"
ITERATIONS="${ITERATIONS:-100}"
WARMUP="${WARMUP:-15}"
DELAY_MS="${DELAY_MS:-0}"
TIMES_FILE=$(mktemp)

echo "[measure_p95] Warming up ($WARMUP requests, discarded)..."
for i in $(seq 1 $WARMUP); do
  curl -s -o /dev/null -H "Authorization: $TOKEN" "$ENDPOINT"
  if [ "$DELAY_MS" -gt 0 ]; then
    sleep "$(echo "scale=3; $DELAY_MS/1000" | bc)"
  fi
done

echo "[measure_p95] Measuring ($ITERATIONS requests)..."
for i in $(seq 1 $ITERATIONS); do
  TIME=$(curl -s -o /dev/null -D - \
    -H "Authorization: $TOKEN" \
    -H "Accept-Encoding: gzip" \
    "$ENDPOINT" \
    | grep -i "x-response-time:" \
    | awk '{print $2}' \
    | tr -d 'ms\r\n')
  [ -n "$TIME" ] && echo "$TIME" >> "$TIMES_FILE"
  if [ "$DELAY_MS" -gt 0 ]; then
    sleep "$(echo "scale=3; $DELAY_MS/1000" | bc)"
  fi
done

COUNT=$(wc -l < "$TIMES_FILE" | tr -d ' ')
if [ "$COUNT" -lt 10 ]; then
  echo "ERROR: Only $COUNT timing headers received. Is the server running and X-Response-Time emitting?"
  echo "  Verify TimingMiddleware is registered in backend/server.py"
  echo "  Verify the endpoint path is correct: $ENDPOINT"
  rm "$TIMES_FILE"
  exit 1
fi

P95=$(sort -n "$TIMES_FILE" | awk "NR==int($COUNT*0.95+0.5){print \$1}")
MEAN=$(awk '{sum+=$1} END{printf "%.1f", sum/NR}' "$TIMES_FILE")
MAX=$(sort -n "$TIMES_FILE" | tail -1)

echo ""
echo "Endpoint: $ENDPOINT"
echo "  p95:  ${P95}ms  (target: <500ms)"
echo "  mean: ${MEAN}ms"
echo "  max:  ${MAX}ms"
STATUS=$([ "${P95%.*}" -lt 500 ] && echo "PASS" || echo "FAIL")
echo "  status: $STATUS"
rm "$TIMES_FILE"
exit $([ "$STATUS" = "PASS" ] && echo 0 || echo 1)
