---
phase: 25-e2e-verification-production-ship
plan: "03"
subsystem: e2e/playwright
tags: [e2e, playwright, export, download, redirect, SHIP-01]
dependency_graph:
  requires: [Phase 24 ExportActionsBar]
  provides: [export-actions-spec, full-playwright-suite-green]
  affects: [e2e/export.spec.ts, e2e/helpers/mock-api.ts, e2e/critical-path.spec.ts]
tech_stack:
  added: []
  patterns: [playwright-route-mock, promise-all-race-prevention, context-waitForEvent, browser-download-assertion]
key_files:
  created:
    - e2e/export.spec.ts
  modified:
    - e2e/helpers/mock-api.ts
    - e2e/critical-path.spec.ts
decisions:
  - "Export spec uses inline auth+mock helpers instead of mockExportContent (more reliable, avoids abstraction layer)"
  - "LinkedIn URL assertion accepts login redirect (linkedin.com/uas/login?session_redirect=...shareArticle) as correct behavior"
  - "X URL assertion accepts x.com/intent/tweet due to Twitter→X rebrand redirect"
  - "Instagram negative popup test uses .catch() on waitForEvent instead of Promise.race timeout"
  - "auth expiry test uses goto(waitUntil:commit) to avoid goto hanging on mid-navigation 401 redirect"
  - "API failure test uses waitForSelector+textContent fallback to handle apiFetch 1s retry backoff"
metrics:
  duration_minutes: 66
  completed_date: "2026-04-04"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 3
requirements: [SHIP-01]
---

# Phase 25 Plan 03: Export E2E Spec and Full Playwright Suite Summary

**One-liner:** E2E coverage for Phase 24 download/redirect features — 5-test export.spec.ts verifying .txt download, LinkedIn popup, X popup, Instagram tooltip, and export bar visibility — full 31-test Playwright suite green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add mockExportContent helper to mock-api.ts | a217569 | e2e/helpers/mock-api.ts |
| 2 | Write export.spec.ts and fix critical-path error tests | 494b948 | e2e/export.spec.ts, e2e/critical-path.spec.ts |

## What Was Built

### mockExportContent helper (`e2e/helpers/mock-api.ts`)

New exported function appended to mock-api.ts. Mocks:
- `GET /api/auth/me` → authenticated user (pro tier, onboarding complete)
- `GET /api/content/${jobId}` → approved content job with `final_content` set
- `GET /api/dashboard/stats` → minimal dashboard stats

Options: `jobId`, `platform`, `finalContent` with sensible defaults.

### export.spec.ts (`e2e/export.spec.ts`)

5-test suite covering all ExportActionsBar behaviors:

1. **Export bar visible** — Navigates to studio, generates content via mocked API, waits for `[data-testid="export-actions-bar"]` to become visible.

2. **Download .txt** — `Promise.all([page.waitForEvent("download"), click])` — asserts filename matches `linkedin-YYYY-MM-DD.txt`.

3. **Open in LinkedIn** — `context.waitForEvent("page")` captures popup — asserts URL matches `linkedin.com` with `shareArticle` in decoded URL (handles login redirect).

4. **Open in X** — Same popup pattern — asserts URL matches `(twitter|x).com/intent/tweet` (handles Twitter→X rebrand).

5. **Instagram tooltip** — Clicks "Post to Instagram" button, verifies no popup via `.catch()` on `context.waitForEvent("page", { timeout: 500 })`, asserts "Instagram has no web compose URL" tooltip visible.

Zero actual `waitForTimeout` calls in the test body.

### critical-path.spec.ts fixes

Two Error Resilience tests updated for Phase 21-22 changes:

**API failure test (Test 8):** `apiFetch` retries 5xx responses with 1s backoff. Changed error assertion to use `waitForSelector` (up to 5s) + `page.textContent("body")` fallback — handles the retry delay before `setError` fires.

**Auth expiry test (Test 9):** `apiFetch` 401 handler does `window.location.href = '/auth?expired=1'` mid-navigation, which caused `page.goto()` to hang. Changed to `{ waitUntil: "commit" }` + `waitForURL(/\/auth/)` + `notOnDashboard` assertion.

## Success Criteria Met

- [x] SHIP-01: E2E coverage of Phase 24 download/redirect features
- [x] export.spec.ts has 5 passing tests
- [x] Full Playwright suite exits 0: smoke (6) + critical-path (13) + billing (5) + agency (4) + export (5) = **31 tests, 31 passed**
- [x] Zero `waitForTimeout` calls in export.spec.ts
- [x] `mockExportContent` exported from e2e/helpers/mock-api.ts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Phase 24 ExportActionsBar missing from worktree branch**
- **Found during:** Task 2 execution
- **Issue:** Worktree branched from `dev` before Phase 23+24 merge. `ExportActionsBar.jsx`, `contentExport.js`, and `jszip` dependency were not present — frontend compiled with "Module not found: jszip" error.
- **Fix:** Merged `dev` into worktree branch (`git merge dev --no-edit`). Installed `jszip` npm package in worktree frontend. Restarted webpack dev server.
- **Commit:** 82fea7f (merge commit)

**2. [Rule 1 - Bug] Test race condition in waitForResponse placement**
- **Found during:** Task 2 — first test run
- **Issue:** `waitForResponse` was registered AFTER click, causing it to miss fast mock responses.
- **Fix:** Wrapped `[waitForResponse, click()]` in `Promise.all` to register listener before click.
- **Files modified:** e2e/export.spec.ts

**3. [Rule 1 - Bug] LinkedIn popup URL assertion too strict**
- **Found during:** Task 2 test run
- **Issue:** LinkedIn redirects unauthenticated browsers from `/shareArticle` to `/uas/login?session_redirect=...shareArticle`. Test failed on `toMatch(/linkedin.com\/shareArticle/)`.
- **Fix:** Changed assertion to check `linkedin.com` domain AND `shareArticle` in `decodeURIComponent(url)`.
- **Files modified:** e2e/export.spec.ts

**4. [Rule 1 - Bug] X/Twitter URL assertion outdated**
- **Found during:** Task 2 test run
- **Issue:** `buildXUrl()` produces `twitter.com/intent/tweet` but browser follows redirect to `x.com/intent/tweet` (Twitter→X rebrand).
- **Fix:** Changed assertion to `/(twitter|x)\.com\/intent\/tweet/`.
- **Files modified:** e2e/export.spec.ts

**5. [Rule 1 - Bug] Instagram negative popup assertion throws**
- **Found during:** Task 2 test run
- **Issue:** `context.waitForEvent("page", { timeout: 500 })` throws `TimeoutError` when used in `Promise.race` — the throw propagated instead of resolving to `false`.
- **Fix:** Changed to `.then(() => { popupOpened = true }).catch(() => {})` pattern.
- **Files modified:** e2e/export.spec.ts

**6. [Rule 1 - Bug] critical-path error tests broken by Phase 22 apiFetch migration**
- **Found during:** Task 2 full suite run
- **Issue:** `apiFetch` retries 5xx with 1s backoff — error check started before retry+setError completed. Auth 401 handler does `window.location.href` mid-navigation causing `page.goto()` to hang.
- **Fix:** API failure: `waitForSelector` + `textContent` fallback with adequate timeout. Auth expiry: `waitUntil:"commit"` + relaxed assertion.
- **Files modified:** e2e/critical-path.spec.ts

## Known Stubs

None. All tests perform real browser interactions against the mocked API. No hardcoded empty values or placeholders.

## Self-Check: PASSED

Files created:
- e2e/export.spec.ts — FOUND ✓

Files modified:
- e2e/helpers/mock-api.ts — mockExportContent found at line 693 ✓
- e2e/critical-path.spec.ts — error resilience tests fixed ✓

Commits:
- a217569 — FOUND ✓
- 494b948 — FOUND ✓

Playwright suite: 31 passed, 0 failed ✓
waitForTimeout count in export.spec.ts: 1 (comment only, zero actual calls) ✓
