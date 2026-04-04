---
phase: 21-ci-strictness-httponly-cookie-auth
plan: "01"
subsystem: infra
tags: [ci, github-actions, playwright, pytest, continue-on-error]

requires: []
provides:
  - "CI workflows with no continue-on-error — all 4 backend test jobs and Playwright job now hard-fail on test failure"
affects:
  - phase-22-cookie-auth
  - any CI run on dev/main

tech-stack:
  added: []
  patterns:
    - "CI strictness: every test job propagates its exit code — no silent pass on failure"

key-files:
  created: []
  modified:
    - .github/workflows/ci.yml
    - .github/workflows/e2e.yml

key-decisions:
  - "Removed all 4 continue-on-error directives without any other workflow changes — minimal, surgical edit"
  - "Pre-existing test failure in test_api_routes_alive.py (event loop closed) documented but not fixed in this plan — CI will correctly surface it as red"

patterns-established:
  - "No CI job may use continue-on-error: true — deliberate failures must be visible"

requirements-completed: [CI-01, CI-02, CI-03]

duration: 8min
completed: "2026-04-03"
---

# Phase 21 Plan 01: CI Strictness — Remove All continue-on-error Summary

**Deleted all 4 `continue-on-error: true` directives from ci.yml and e2e.yml so that any test failure now produces a hard red CI status instead of a silent green**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-03T20:37:00Z
- **Completed:** 2026-04-03T20:45:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed step-level `continue-on-error: true` from `backend-test-security` job in ci.yml (was at line 152)
- Removed step-level `continue-on-error: true` from `backend-test-pipeline` job in ci.yml (was at line 224)
- Removed job-level `continue-on-error: true` from `backend-test-general` job in ci.yml (was at line 229)
- Removed job-level `continue-on-error: true` from `playwright` job in e2e.yml (was at line 12)
- Validated both workflow files parse as valid YAML after edits
- Ran full local test suite to document pre-existing test status: 543 passed, 1 failed

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove all continue-on-error from CI workflows** - `5082351` (fix)
2. **Task 2: Verify CI workflows are syntactically valid** - (verification-only, no file changes, included in Task 1 commit)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `.github/workflows/ci.yml` — Removed 3 `continue-on-error: true` instances (lines 152, 224, 229)
- `.github/workflows/e2e.yml` — Removed 1 `continue-on-error: true` instance (line 12)

## Decisions Made

- Removed directives without any other workflow changes — no step reordering, no new jobs, no flag changes.
- Pre-existing test failure in `tests/integration/test_api_routes_alive.py::TestAllRoutesRespond::test_route_responds[GET-/api/media/assets-...]` documented but not fixed here. The failure is caused by an event loop closure issue (`RuntimeError: Event loop is closed`) in a Motor async cursor operation unrelated to these CI changes. CI will now correctly surface this as red — which is the desired outcome per CI-03. The failure was previously masked by `continue-on-error: true` on the `backend-test-general` job.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- **Pre-existing test failure surfaced:** `tests/integration/test_api_routes_alive.py::TestAllRoutesRespond::test_route_responds[GET-/api/media/assets-...]` fails locally with `RuntimeError: Event loop is closed`. This failure was masked by the now-removed `continue-on-error: true` on `backend-test-general`. Per plan Task 2 instructions, this was documented but not fixed here — it will correctly block CI, which is the desired behavior. Fix should be scheduled as a follow-up.

## Known Stubs

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CI strictness is now enforced: any broken test causes a hard red CI status
- Phase 22 (httpOnly cookie auth migration) can proceed — broken tests will now surface immediately rather than being masked
- Recommend fixing the pre-existing `test_api_routes_alive.py` event loop failure before or alongside Phase 22, as it will now block CI runs

## Self-Check: PASSED

- FOUND: `.planning/phases/21-ci-strictness-httponly-cookie-auth/21-01-SUMMARY.md`
- FOUND: `.github/workflows/ci.yml`
- FOUND: `.github/workflows/e2e.yml`
- FOUND: commit `5082351` (fix(21-01): remove all continue-on-error from CI workflows)

---
*Phase: 21-ci-strictness-httponly-cookie-auth*
*Completed: 2026-04-03*
