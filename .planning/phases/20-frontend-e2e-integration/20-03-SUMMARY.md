---
phase: 20-frontend-e2e-integration
plan: "03"
subsystem: e2e-testing
tags: [playwright, e2e, critical-path, mocking, error-resilience]
dependency_graph:
  requires: [20-01]
  provides: [E2E-02]
  affects: [e2e/critical-path.spec.ts, e2e/helpers/test-data.ts]
tech_stack:
  added: []
  patterns:
    - "Serial test groups (test.describe.serial) for stateful E2E flows"
    - "page.route() with route.fulfill() for deterministic API mocking"
    - "Per-element visibility iteration instead of comma-separated CSS selectors"
    - "afterEach screenshot-on-failure hook for CI debugging"
key_files:
  created:
    - e2e/critical-path.spec.ts
    - e2e/helpers/test-data.ts
  modified: []
decisions:
  - "Used test.describe.serial() for the 7 happy-path steps — each step depends on the previous (shared mock state)"
  - "Error resilience tests run independently (not serial) — they set up their own auth mocks"
  - "Fixed CSS selector issue: Playwright's page.locator() cannot combine comma-separated selectors that use text= — split into per-element loops"
  - "route.continue() replaced with route.fulfill() for the auth 401 test to satisfy plan's all-mocks-use-fulfill requirement"
  - "setTimeout inside route handler (LLM timeout test) is acceptable — it's inside the mock, not a test-level delay"
metrics:
  duration: "8 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  files_changed: 2
requirements: [E2E-02]
---

# Phase 20 Plan 03: Critical Path E2E Test Summary

Critical path E2E test suite covering the complete ThookAI user journey — signup through one-click strategy approve — with deterministic mocks, zero waitForTimeout, and error resilience.

## What Was Built

### `e2e/helpers/test-data.ts` (186 lines)

Deterministic test data constants for the critical path suite:

- `TEST_USER` — unique email via `Date.now()` to avoid parallel run collisions
- `MOCK_PERSONA` — minimal valid persona engine matching CLAUDE.md Section 5 schema
- `MOCK_CONTENT_JOB` — content job in "reviewing" state with draft text
- `MOCK_SCHEDULE_RESULT` — schedule confirmation with tomorrow's ISO timestamp
- `MOCK_STRATEGY_CARD` — strategy recommendation with `recommendation_id`, `topic`, `why_now`, `generate_payload`

All objects are `Object.freeze()`'d for immutability.

### `e2e/critical-path.spec.ts` (1,005 lines)

**Happy Path (serial, 7 steps):**

| Step | Test Name | Key Assertion |
|------|-----------|---------------|
| 1 | signup creates account and redirects | URL matches `/dashboard\|onboarding` after register |
| 2 | onboarding wizard generates persona | Persona API responds < 400, phase 3 visible or redirect |
| 3 | content generation produces draft | `/api/content/create` returns 200, draft visible or no error |
| 4 | content can be scheduled | `/api/content/job/{id}/schedule` responds, no error shown |
| 5 | analytics page loads with data | At least one element (h1, .card-thook, "Analytics", "LinkedIn") visible |
| 6 | strategy dashboard shows recommendations | "AI content trends" and "AI content creation is trending" visible |
| 7 | one-click approve triggers generation | `/approve` returns 200, navigates to `/dashboard/studio` |

**Error Resilience (independent, 3 tests):**

| Test | Scenario | Assertion |
|------|----------|-----------|
| 8 | Generation API 500 | Error element visible, body not white-screened |
| 9 | Auth 401 (token expiry) | Redirect to `/auth` or landing page |
| 10 | LLM timeout (4s delay) | Loading state visible or graceful outcome, body intact |

**Infrastructure patterns:**

- `test.afterEach` hook captures `test-results/failure-{title}.png` on failure
- All 39 `page.route()` handlers use `route.fulfill()` — zero `route.continue()`
- All waits use `waitForSelector`, `waitForURL`, or `waitForResponse`
- Zero `.waitForTimeout()` function calls in the entire file

## Test Results

```
Running 10 tests using 1 worker

✓  1  signup creates account and redirects (2.1s)
✓  2  onboarding wizard generates persona (16.8s)
✓  3  content generation produces draft (4.0s)
✓  4  content can be scheduled (4.0s)
✓  5  analytics page loads with data (1.8s)
✓  6  strategy dashboard shows recommendations (1.8s)
✓  7  one-click approve triggers generation (1.9s)
✓  8  shows error on generation API failure (2.1s)
✓  9  handles auth token expiry gracefully (2.0s)
✓ 10  onboarding handles LLM timeout gracefully (1.8s)

10 passed (45.2s)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comma-separated CSS selector incompatibility**
- **Found during:** Task 1 execution (test run)
- **Issue:** Playwright's `page.locator()` does not support `text=` tokens combined with CSS commas — produces "Unexpected token" CSS parse error
- **Fix:** Replaced multi-selector strings with per-element visibility loops (`for (const el of [...]) { isVisible() }`)
- **Files modified:** `e2e/critical-path.spec.ts`
- **Commit:** 8cb23c3

**2. [Rule 1 - Bug] route.continue() in auth 401 test**
- **Found during:** Task 2 review
- **Issue:** Plan requires all route mocks use `route.fulfill()`. The catch-all `/api/**` handler used `route.continue()` to defer to the specific `/api/auth/me` handler
- **Fix:** Changed to `route.fulfill(401)` directly in the catch-all, matching the specific handler's response
- **Files modified:** `e2e/critical-path.spec.ts`
- **Commit:** 8cb23c3

## Known Stubs

None — all mock data is fully wired. The `MOCK_PERSONA` object is returned by the mocked `/api/onboarding/generate-persona` endpoint. The `MOCK_STRATEGY_CARD` is returned by the mocked `/api/strategy` endpoint. No placeholders or hardcoded empty values reach UI rendering assertions.

## Self-Check: PASSED
