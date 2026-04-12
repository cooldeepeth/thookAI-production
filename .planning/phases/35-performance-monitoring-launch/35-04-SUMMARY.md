---
phase: 35-performance-monitoring-launch
plan: 04
status: done
requirement: PERF-07
updated: 2026-04-13
---

# Plan 35-04 Summary — 50-User Load Test (PERF-07)

## Outcome

Load-test instrumentation is in place. `locust` is declared in `backend/requirements.txt`, the existing `backend/tests/load/locustfile.py` now carries an explicit threshold block that distinguishes fast endpoints (2 s gate) from the LLM pipeline (excluded), and the report skeleton at `reports/phase-35/perf-07-load-test-results.md` documents the full run command and result-parsing workflow. The actual 50-user × 5-minute run is operator-executable and must run against a confirmed target (production Railway, staging, or a seeded local dev server) — PERF-07 flips to PASS once the report's Results table is populated.

## Changes

| File | Change |
|------|--------|
| `backend/requirements.txt` | Added `locust>=2.43.4,<3.0` under a new `# Load testing (dev/CI only — do not install in production containers)` section, directly after the `# Test infrastructure` block |
| `backend/tests/load/locustfile.py` | Inserted a 35-line `LOAD TEST THRESHOLDS — PERF-07` comment block immediately after imports and `logger = ...`. No task logic, weights, or auth flow modified. Block documents fast-vs-LLM threshold split, `--host` CLI override, and the deliberate retention of the `>0.5s` slow-log (now a breadcrumb, no longer a gate) |
| `reports/phase-35/perf-07-load-test-results.md` | Created. Instrumentation status, results skeleton with PENDING rows, pre-run checklist (owner confirmation, off-peak, rate-limit, cleanup, Anthropic budget), `how to run` + `how to parse CSV` runbook, exclusions section |
| `.planning/phases/35-performance-monitoring-launch/35-04-SUMMARY.md` | this file |

## Why the run did not execute inline

The plan explicitly allows falling back to a local run against `http://localhost:8001` if no production URL is available. Even the localhost fallback was not viable in the current environment:

1. No backend process is running on `:8001`, and the plan's task logic is a full register → generate → dashboard → credits loop that needs a live FastAPI + MongoDB + Redis + Anthropic stack
2. Installing `locust` (200+ MB with deps including `geventhttpclient` and `pyzmq`) into a shared venv has broad side effects that should be an operator decision, not an inline orchestration decision
3. A 50-user run against any target creates ~1500–3000 real user accounts and ~2500 real Anthropic API calls — this is owner-confirmation work, not autonomous work

## PERF-07 Verdict

**script_ready / run_pending**

Open items (operator action, tracked in the report):
- [ ] Operator runs `locust` per the runbook against a confirmed target
- [ ] Results table populated from `load-results_stats.csv`
- [ ] 5xx error count populated
- [ ] Fast endpoints p95 < 2000 ms confirmed
- [ ] Report frontmatter flipped `script_ready_run_pending` → `passed`

Non-blocking (already green):
- [x] `locust` in requirements.txt
- [x] Threshold block in locustfile.py (fast vs LLM, documented)
- [x] LLM endpoint excluded from 2 s gate with rationale
- [x] Report with full runbook and pre-run checklist
- [x] Email pattern (`loadtest-{uuid4()}@test.io`) is unique per run — safe for production targets

## Self-Check

- [x] `grep ^locust backend/requirements.txt` returns `locust>=2.43.4,<3.0`
- [x] `grep -c "PERF-07\|EXCLUDED\|LOAD TEST THRESHOLDS" backend/tests/load/locustfile.py` returns 3
- [x] `locustfile.py` task logic unchanged — only the header block is new
- [x] Report exists at `reports/phase-35/perf-07-load-test-results.md` and contains `p95`
- [x] Report documents fast-vs-LLM distinction in three places for redundancy
- [x] No secrets committed, no real auth tokens in any file
