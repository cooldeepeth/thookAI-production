---
report: perf-01-p95-latency
phase: 35
plan: 35-01
requirement: PERF-01
status: instrumentation_ready_measurement_pending
---

# PERF-01: API p95 Latency Results

**Generated:** 2026-04-13
**Target:** p95 < 500ms on the 10 most-used fast endpoints
**Method:** `bash backend/scripts/measure_p95.sh` — 100 iterations + 15 warmup per endpoint, reads `X-Response-Time` response header emitted by `TimingMiddleware` (`backend/middleware/performance.py`).
**Threshold:** `TimingMiddleware.slow_request_threshold_ms` is now **500** (previously 2000). Confirmed at both class default (`performance.py:258`) and instantiation (`server.py:393`).

## Instrumentation Status

| Item | Status | Evidence |
|------|--------|----------|
| `X-Response-Time` header emitted on every response | Active | `performance.py:270` — `response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"` |
| Slow-request warning threshold lowered 2000 → 500 ms | Done | `performance.py:258`, `server.py:393`, commit `cf674ab` |
| Reusable measurement script | Done | `backend/scripts/measure_p95.sh` (108 lines, executable, env-var driven, rate-limit-aware) |
| `/api/content/generate` excluded from 500ms gate | Documented | See "Exclusions" below |

## Results

Measurement is **operator-executable** — the script is ready but requires a running backend with valid auth. Populate the rows below after running `measure_p95.sh` against each endpoint.

| # | Endpoint | p95 (ms) | Mean (ms) | Max (ms) | Status |
|---|----------|----------|-----------|----------|--------|
| 1 | `GET /api/auth/me` | _pending_ | _pending_ | _pending_ | PENDING |
| 2 | `GET /api/dashboard/stats` | _pending_ | _pending_ | _pending_ | PENDING |
| 3 | `GET /api/dashboard/feed` | _pending_ | _pending_ | _pending_ | PENDING |
| 4 | `GET /api/content/` (list) | _pending_ | _pending_ | _pending_ | PENDING |
| 5 | `GET /api/persona/` | _pending_ | _pending_ | _pending_ | PENDING |
| 6 | `GET /api/billing/subscription` | _pending_ | _pending_ | _pending_ | PENDING |
| 7 | `GET /api/billing/credits/balance` | _pending_ | _pending_ | _pending_ | PENDING |
| 8 | `GET /api/analytics/overview` | _pending_ | _pending_ | _pending_ | PENDING |
| 9 | `GET /api/templates/` | _pending_ | _pending_ | _pending_ | PENDING |
| 10 | `GET /api/platforms/status` | _pending_ | _pending_ | _pending_ | PENDING |

## Exclusions

### `/api/content/generate` — LLM pipeline exemption
Content generation flows through the Commander → Scout → Thinker → Writer → QC agent pipeline backed by Claude Sonnet. Expected wall-clock latency is 5–30 seconds (dominated by upstream LLM inference, not server compute). This endpoint is **explicitly out of scope** for the 500ms gate and must not be measured against PERF-01. LLM endpoints have their own budget (tracked separately under Phase 35 load-test work, plan 35-04).

### Other long-running endpoints (informational)
- `/api/content/generate-media` — fal.ai / Luma / ElevenLabs provider latency
- `/api/onboarding/analyze` — LLM persona generation
- Any route that streams (`StreamingResponse`) — CompressionMiddleware skips, timing still recorded

These are not part of the 10 listed above and are not measured by PERF-01.

## How to run the measurement

```bash
# Production (use DELAY_MS=1000 to respect 60 req/min rate limit)
export BASE="https://api.thook.ai"
export JWT="$(curl -s -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"...","password":"..."}' | jq -r .access_token)"
export TOK="Bearer $JWT"
export DELAY_MS=1000

ENDPOINTS=(
  "$BASE/api/auth/me"
  "$BASE/api/dashboard/stats"
  "$BASE/api/dashboard/feed"
  "$BASE/api/content/"
  "$BASE/api/persona/"
  "$BASE/api/billing/subscription"
  "$BASE/api/billing/credits/balance"
  "$BASE/api/analytics/overview"
  "$BASE/api/templates/"
  "$BASE/api/platforms/status"
)

for ep in "${ENDPOINTS[@]}"; do
  ENDPOINT_URL="$ep" AUTH_TOKEN="$TOK" DELAY_MS=1000 bash backend/scripts/measure_p95.sh
  sleep 2
done
```

```bash
# Local dev server (no rate limit — set DELAY_MS=0)
export BASE="http://localhost:8001"
# ... same as above, DELAY_MS=0
```

## Slow Endpoint Investigation

This section will be populated after measurement if any endpoint fails the 500ms gate. For each FAIL:

1. Reproduce with `curl -v` against the endpoint to capture the full request trace.
2. Identify the query — grep the route file under `backend/routes/` for the collection being queried.
3. Run MongoDB `explain("executionStats")` on the query:
   ```python
   from database import db
   result = await db.<collection>.find({...}).explain("executionStats")
   # Check result["executionStats"]["executionStages"]["stage"] — if COLLSCAN, an index is missing.
   ```
4. Add the missing index to `backend/db_indexes.py` matching the existing `IndexModel` pattern.
5. Restart the app so `db_indexes.py` re-runs on startup (it auto-runs per CLAUDE.md).
6. Re-measure and document the before/after numbers.

**Current index coverage:** `backend/db_indexes.py` already defines indexes for `users.user_id`, `users.email`, `persona_engines.user_id`, `content_jobs`, `scheduled_posts`, `platform_tokens`, `workspaces`, `workspace_members`, `templates`, `media_assets`, `uploads`, `password_reset_tokens`, `persona_shares`. Most dashboard / listing queries should hit an index — if a FAIL occurs, it's likely a compound index gap (e.g., `(user_id, created_at DESC)`).

## Verdict

**PERF-01: instrumentation_ready / measurement_pending**

Blocking items to flip to `passed`:
- [ ] Operator runs `measure_p95.sh` against production (or dev server with seeded data) for all 10 endpoints
- [ ] This report's results table is populated with real numbers
- [ ] Any FAIL row has an `explain()` trace + index fix documented in the "Slow Endpoint Investigation" section
- [ ] Final verdict line updated to `PERF-01: PASS` or `PERF-01: FAIL — <list>`

Non-blocking (already satisfied):
- [x] `TimingMiddleware.slow_request_threshold_ms == 500` (class default + server.py instantiation)
- [x] `measure_p95.sh` exists, is executable, uses env-var auth, is rate-limit-aware
- [x] `/api/content/generate` excluded from the gate with rationale
- [x] Report skeleton exists at `reports/phase-35/perf-01-p95-results.md`
