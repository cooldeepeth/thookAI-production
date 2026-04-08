---
phase: 17-test-foundation-billing-payments
plan: "03"
subsystem: infra
tags: [ci, github-actions, pytest, coverage, billing, testing]

requires:
  - phase: 17-test-foundation-billing-payments
    provides: "pytest infrastructure, .coveragerc with branch coverage, mongomock-motor, pytest-cov installed"

provides:
  - "CI matrix with 4 domain-specific test jobs (billing, security, pipeline, general)"
  - "Billing CI job with 95% branch coverage gate on credits.py, stripe_service.py, billing.py"
  - "Security and pipeline CI jobs with 85% branch coverage gate"
  - "General catch-all job for remaining tests without coverage gate"

affects:
  - "Phase 18 security tests must satisfy 85% coverage gate"
  - "Phase 19 pipeline tests must satisfy 85% coverage gate"
  - "Phase 17 plans 04-05 must write billing tests to satisfy 95% coverage gate"

tech-stack:
  added: []
  patterns:
    - "Domain-isolated CI jobs: each test domain has its own CI job with tailored coverage thresholds"
    - "continue-on-error on billing job until comprehensive tests exist (removed after Phase 17)"

key-files:
  created: []
  modified:
    - ".github/workflows/ci.yml"

key-decisions:
  - "Billing job uses continue-on-error=true until Phase 17 billing tests (plans 04-05) write the comprehensive suite that satisfies the 95% gate"
  - "General job ignores all domain-specific test files to avoid double-counting and conflicting coverage reports"
  - "All 4 domain jobs share identical Python 3.11 + mongo:7.0 + redis:7-alpine setup for consistency"

patterns-established:
  - "Coverage gate pattern: billing=95%, security/pipeline=85%, general=no gate"
  - "Domain isolation: each CI job specifies exact --cov=file targets matching its test scope"

requirements-completed:
  - FOUND-04

duration: 2min
completed: "2026-04-03"
---

# Phase 17 Plan 03: CI Matrix with Domain-Specific Coverage Gates Summary

**GitHub Actions CI matrix with 4 domain-specific test jobs enforcing 95% branch coverage on billing modules and 85% on security/pipeline modules**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T03:24:17Z
- **Completed:** 2026-04-03T03:26:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced single `backend-test` CI job with 4 domain-specific jobs: billing, security, pipeline, and general
- Billing job enforces 95% branch coverage on `services/credits.py`, `services/stripe_service.py`, `routes/billing.py`
- Security job enforces 85% branch coverage on `auth_utils.py`, `routes/auth.py`, `routes/auth_google.py`, `middleware/security.py`
- Pipeline job enforces 85% branch coverage on `agents/` and `services/` for all pipeline/integration tests
- General job is a catch-all for remaining tests without a coverage gate
- Billing job temporarily uses `continue-on-error: true` until plans 04-05 write the comprehensive billing test suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Configure CI matrix with domain-specific test jobs and coverage gates** - `d60e136` (feat)

**Plan metadata:** (added in final commit)

## Files Created/Modified
- `.github/workflows/ci.yml` - Replaced single backend-test job with 4 domain-specific jobs (billing/security/pipeline/general) with per-domain coverage thresholds

## Decisions Made
- Billing job set to `continue-on-error: true` to prevent blocking PRs before plans 04-05 write the comprehensive billing test suite that satisfies the 95% gate. The TODO comment marks it for removal.
- General job explicitly ignores all domain-specific test files to prevent double-counting and coverage report conflicts between parallel jobs.
- Coverage targets specified per-file (e.g., `--cov=services/credits.py`) rather than directory-wide to ensure coverage measurement is scoped to the billing domain only.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CI infrastructure is ready for Phase 17 plans 04-05 to write billing tests that satisfy the 95% coverage gate
- Security and pipeline gates (85%) are established and will gate Phase 18 and Phase 19 work respectively
- Once plans 04-05 complete billing tests, `continue-on-error: true` should be removed from `backend-test-billing` job

---
*Phase: 17-test-foundation-billing-payments*
*Completed: 2026-04-03*
