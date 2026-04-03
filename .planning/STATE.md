---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Production Hardening — 50x Testing Sprint
status: executing
stopped_at: Completed 17-01-PLAN.md — Green CI baseline, coverage infrastructure, conftest fixtures
last_updated: "2026-04-03T03:21:49.397Z"
last_activity: 2026-04-03
progress:
  total_phases: 12
  completed_phases: 0
  total_plans: 5
  completed_plans: 1
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Zero P0 failures before public launch — every revenue path, auth flow, and content pipeline verified with automated tests.
**Current focus:** Phase 17 — test-foundation-billing-payments

## Current Position

Phase: 17 (test-foundation-billing-payments) — EXECUTING
Plan: 2 of 5
Status: Ready to execute
Last activity: 2026-04-03

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v2.1)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*
| Phase 17 P01 | 15 minutes | 2 tasks | 9 files |

## Accumulated Context

### Decisions

- v2.1 ordering is non-negotiable: Phase 17 (foundation + billing P0 fixes) must complete before Phase 18 (security) — testing an insecure system is misleading
- TDD discipline: write failing test first, observe failure, then fix production code — never fix code without a failing test driving it
- Branch coverage from day one: `--cov-branch` configured in Phase 17 so all subsequent phases are measured correctly; retroactive application requires test rewrites
- mongomock-motor (not AsyncMock) required for credit atomicity tests — AsyncMock cannot verify MongoDB filter/operation semantics
- pytest-mock for automatic mock cleanup — eliminates ordering-dependent failures at 1,000-test scale
- Playwright deferred to Phase 20: E2E against broken auth/billing (pre-Phase 17 fixes) would produce green results for wrong reasons
- Phase 17 baseline first: delete/update 3 broken CI tests and fix 6 unawaited coroutine warnings before writing any new tests
- [Phase 17]: Skip beat_schedule tests (n8n owns scheduling since Phase 8) — beat_schedule is intentionally empty
- [Phase 17]: asyncio.create_task mocks must consume coroutines via side_effect=lambda coro: coro.close() to prevent RuntimeWarning
- [Phase 17]: filterwarnings = error::RuntimeWarning in pytest.ini enforces no unawaited coroutines on every run including local

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 17]: Stripe Test Clock method signatures need verification against `stripe==8.0.0` SDK before implementing Test Clock tests — HIGH complexity per research
- [Phase 19]: LangGraph `asyncio_mode = auto` interaction with LangGraph internal task group needs investigation before writing node isolation tests
- [Phase 20]: Playwright + CRA dev server startup time may exceed 120s CI timeout — validate before committing to `webServer` config
- [Phase 20]: Playwright recommends Node 20+, CI uses Node 18 — add separate Node 20 setup step for playwright-e2e CI job only

## Session Continuity

Last session: 2026-04-03T03:21:49.394Z
Stopped at: Completed 17-01-PLAN.md — Green CI baseline, coverage infrastructure, conftest fixtures
Resume file: None
