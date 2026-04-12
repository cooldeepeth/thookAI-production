---
report: perf-07-load-test
phase: 35
plan: 35-04
requirement: PERF-07
status: script_ready_run_pending
---

# PERF-07: Load Test Results

**Generated:** 2026-04-13
**Target:** `p95 < 2000ms` on fast endpoints under 50 concurrent users, zero 5xx errors for the full 5-minute run
**Tool:** `locust >= 2.43.4, < 3.0` (Python)
**Load profile:** 50 users, spawn rate 5/s, run time 5m

## Instrumentation Status

| Item | Status | Evidence |
|------|--------|----------|
| `locust` declared in `backend/requirements.txt` | Done | `backend/requirements.txt:58 — locust>=2.43.4,<3.0` |
| Threshold documentation in locustfile header | Done | `backend/tests/load/locustfile.py` — LOAD TEST THRESHOLDS block after imports |
| Fast vs LLM endpoint distinction | Done | Fast (2s gate): `/api/dashboard/stats`, `/api/billing/credits`, `/api/auth/me`. LLM (excluded): `/api/content/generate` |
| `--host` CLI override documented | Done | Run command block shows `--host https://api.thook.ai` syntax |
| Unique email pattern for test users | Done | `locustfile.py:61 — email = f"loadtest-{uuid4()}@test.io"` (already in place) |
| Credit atomicity check | Done | `on_test_stop` listener detects negative balances (pre-existing) |

## Run Status

**Not yet executed against production.** `locust` is declared but was not installed into the local Python environment during this plan run because:
1. Adding a 200+ MB Python package to a shared dev venv has broad side effects
2. There is no running backend at `https://api.thook.ai` or `http://localhost:8001` in the current environment to load-test against
3. The 50-user × 5-minute run creates ~1500–3000 real user accounts on the target — this must be operator-confirmed and directed at a known target (staging or production), not run opportunistically

The plan's "fallback to localhost" path was available, but with no backend running locally and no seeded MongoDB/Redis, a localhost run would produce no meaningful data.

## Results

| Endpoint | Requests | p50 (ms) | p95 (ms) | p99 (ms) | Failures | Status |
|----------|----------|----------|----------|----------|----------|--------|
| `GET /api/auth/me` | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | PENDING |
| `GET /api/dashboard/stats` | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | PENDING |
| `GET /api/billing/credits` | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | PENDING |

## LLM Pipeline (excluded from 2s gate — expected > 5000 ms)

| Endpoint | Requests | p50 (ms) | p95 (ms) | Failures | Note |
|----------|----------|----------|----------|----------|------|
| `POST /api/content/generate` | _pending_ | _pending_ | _pending_ | _pending_ | LLM wall-clock — excluded from 2s gate |

## 5xx Error Summary

Total 5xx errors across all endpoints during the full run: **_pending_**
Gate: zero 5xx errors.

## How to run

```bash
# 0. Install locust (dev machine — NOT the production container)
cd /Users/kuldeepsinhparmar/thookAI-production/backend
pip install "locust>=2.43.4,<3.0"

# 1. Point at the target. Three valid targets:
#    a) production Railway  — LOAD_HOST=https://api.thook.ai
#    b) staging             — LOAD_HOST=https://staging.api.thook.ai
#    c) local dev server    — LOAD_HOST=http://localhost:8001 (start the backend first)
export LOAD_HOST="https://api.thook.ai"

# 2. Run the 50-user / 5-minute test (headless, CSV + HTML output)
cd /Users/kuldeepsinhparmar/thookAI-production/backend
locust \
  -f tests/load/locustfile.py \
  --headless \
  -u 50 -r 5 --run-time 5m \
  --host "$LOAD_HOST" \
  --csv=load-results \
  --html=load-results.html 2>&1 | tee /tmp/locust-output.txt

echo "Exit code: $?"
```

## How to parse results into this report

```bash
# load-results_stats.csv has columns: Type, Name, Request Count, Failure Count,
# Median Response Time, Average Response Time, Min, Max, 50%, 66%, 75%, 80%,
# 90%, 95%, 98%, 99%, 99.9%, 99.99%, 99.999%, 100%
column -t -s, load-results_stats.csv | awk 'NR==1 || /api\// {print}'

# Extract just the 95% column for the fast endpoints
awk -F, 'NR>1 && $2 ~ /dashboard\/stats|billing\/credits|auth\/me/ {
  gsub(/"/,""); printf "%-40s p95=%sms fails=%s\n", $2, $14, $4
}' load-results_stats.csv

# 5xx count
awk -F, 'NR>1 {fails+=$4} END {print "total failures:", fails}' load-results_stats.csv
```

Paste the numbers from the `awk` outputs into the Results and LLM Pipeline tables above, update the Status column, and flip the frontmatter `status: script_ready_run_pending` → `status: passed` (or `failed`).

## Pre-run checklist

Before running against production — even staging — confirm:

- [ ] Owner has confirmed the target host is OK to receive ~1500–3000 synthetic registrations and ~2500 LLM calls (Anthropic quota impact — each `generate_content` call is a real Claude API hit)
- [ ] Off-peak hours (to avoid trampling real users)
- [ ] The target has `RATE_LIMIT_PER_MINUTE` tuned for load tests or the test IP is allowlisted (the 60 req/min default will kick in at 50 users after a few seconds and throw 429s — these are real production behaviour but they mask the p95 measurement)
- [ ] A cleanup plan for the `loadtest-*@test.io` accounts post-run: `db.users.deleteMany({email: /^loadtest-.*@test\.io$/})` via mongosh, or the admin `/api/admin/bulk-delete-users?prefix=loadtest-` route if one exists
- [ ] `ANTHROPIC_API_KEY` budget is not near exhaustion — ~2500 LLM calls at claude-sonnet-4 rates is ~$5–15 depending on token count

## Exclusions (documented)

The `/api/content/generate` endpoint is **explicitly excluded** from the 2 s PERF-07 gate. LLM inference wall-clock is 5–30 seconds and is an inherent characteristic of the Commander → Scout → Thinker → Writer → QC pipeline, not a server performance regression. This exclusion is documented in three places for redundancy:
1. The report (here, this section)
2. The locustfile header threshold block
3. The plan 35-04 frontmatter must_haves

## Verdict

**PERF-07: script_ready / run_pending**

Open items to flip to PASS:
- [ ] Operator runs `locust` per the "How to run" section above against a confirmed target
- [ ] Results table populated from `load-results_stats.csv`
- [ ] 5xx error count populated
- [ ] Fast endpoints all show p95 < 2000 ms
- [ ] 0 failures total (or documented rate-limit reasoning if the 60 req/min cap fires)
- [ ] Frontmatter flipped to `status: passed`

Non-blocking (already satisfied):
- [x] `locust` declared in requirements.txt
- [x] locustfile.py documents the fast-vs-LLM threshold distinction
- [x] Report skeleton with runbook exists
- [x] LLM endpoint excluded from 2s gate with written rationale
