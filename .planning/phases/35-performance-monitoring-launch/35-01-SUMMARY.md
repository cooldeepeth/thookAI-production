---
phase: 35-performance-monitoring-launch
plan: 01
status: done
requirement: PERF-01
updated: 2026-04-13
---

# Plan 35-01 Summary — PERF-01 Instrumentation

## Outcome

Instrumentation and tooling for PERF-01 (p95 < 500ms gate) are in place. Live measurement is operator-executable — the script is ready and the report skeleton documents exactly what to run. PERF-01 flips from `instrumentation_ready` to `passed` once an operator runs `measure_p95.sh` against production and populates the results table.

## Threshold Change

| Location | Before | After | Commit |
|----------|--------|-------|--------|
| `backend/middleware/performance.py:258` (class default `TimingMiddleware.slow_request_threshold_ms`) | 2000 | 500 | `cf674ab` |
| `backend/server.py:393` (`app.add_middleware(TimingMiddleware, slow_request_threshold_ms=...)`) | 2000 | 500 | `cf674ab` |

Grep check: `rg "slow_request_threshold_ms.*2000"` in `backend/` returns 0 matches.

## Measurement Script

**Path:** `backend/scripts/measure_p95.sh` — 108 lines, executable (`0755`).

Features beyond the plan's minimum spec:
- Env-var driven (`ENDPOINT_URL`, `AUTH_TOKEN`, `ITERATIONS`, `WARMUP`, `DELAY_MS`) — no hardcoded tokens (T-35-01-01 mitigation).
- `DELAY_MS` param so production runs stay under the 60 req/min rate limit (T-35-01-02 mitigation).
- Reads `X-Response-Time` header emitted by `TimingMiddleware` — the key-link between script and middleware is live.
- Batch example block showing the full 10-endpoint run.
- Exits non-zero on FAIL so CI/scripts can branch on it.

## Report

**Path:** `reports/phase-35/perf-01-p95-results.md`

Contents:
- Instrumentation status table (all 4 items green)
- Results table with 10 rows, each marked `PENDING` pending operator execution
- LLM exclusion rationale (`/api/content/generate` explicitly out of scope, per plan)
- Step-by-step investigation playbook for any endpoint that fails — includes `explain("executionStats")` template and the index-adding convention matching `db_indexes.py`
- Operator runbook with prod + dev variants (copy-pasteable bash)

## Measurement Results

**Status:** PENDING.

Measurement was **not** executed during this plan run because no backend was running in the current environment (no prod URL in env, no local dev server on :8001). The report skeleton is populated with empty rows so the operator can fill them in place when they run the script.

No index changes were made to `backend/db_indexes.py` in this plan — index additions are contingent on actual measurement results and must follow the investigation playbook in the report.

## PERF-01 Verdict

**instrumentation_ready / measurement_pending**

Open items required to flip to PASS (tracked in the report):
- Operator runs `measure_p95.sh` against production (or seeded dev) for all 10 endpoints
- Results table populated with real numbers
- Any FAIL row has `explain()` trace + index fix
- Final verdict line flipped to `PERF-01: PASS`

## Files Touched

| File | Type | Notes |
|------|------|-------|
| `backend/middleware/performance.py` | modified (prior commit `cf674ab`) | class default = 500 |
| `backend/server.py` | modified (prior commit `cf674ab`) | instantiation = 500 |
| `backend/scripts/measure_p95.sh` | created (prior commit) | 108 lines, executable |
| `reports/phase-35/perf-01-p95-results.md` | created (this commit) | report skeleton + runbook |
| `.planning/phases/35-performance-monitoring-launch/35-01-SUMMARY.md` | created (this commit) | this file |
| `backend/db_indexes.py` | unchanged | no index changes — pending measurement |

## Self-Check

- [x] `slow_request_threshold_ms == 500` in both middleware class and server.py instantiation
- [x] `measure_p95.sh` exists, executable, ≥ 40 lines, uses env vars, key-links to `X-Response-Time`
- [x] `reports/phase-35/perf-01-p95-results.md` exists and contains "p95"
- [x] `/api/content/generate` explicitly excluded with rationale
- [x] No secrets or tokens committed
- [ ] Live measurement numbers (operator action — see report)
