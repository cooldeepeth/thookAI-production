---
phase: 23-frontend-unit-test-suite
plan: "02"
subsystem: testing
tags: [react, jest, testing-library, msw, unit-testing, apiFetch, AuthContext, useStrategyFeed, useNotifications]

# Dependency graph
requires:
  - 23-01 (MSW server, setupTests.js, @/ moduleNameMapper, jest-polyfills.js)
provides:
  - 22 apiFetch tests: timeout, retry, 401-redirect, 403-toast, 5xx-toast, CSRF, credentials, content-type, response
  - 10 AuthContext tests: cookie-based auth lifecycle, login/logout, Google OAuth, useAuth guard
  - 8 useStrategyFeed tests: active cards, approveCard, dismissCard, error handling
  - 8 useNotifications tests: REST fetch, markRead, markAllRead, SSE mock

affects:
  - 23-03-PLAN (page/component tests can reuse same infrastructure)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stub global.fetch with jest.fn().mockRejectedValue(abortError) to test AbortError path when MSW Node interceptor does not propagate abort"
    - "Re-assign global.EventSource in beforeEach (not module level) to survive resetMocks: true auto-reset between tests"
    - "waitFor timeout override for 5xx retry tests: retries add 1s backoff per call, set { timeout: 6000 } to accommodate"
    - "renderHook from @testing-library/react for hook isolation; act() wrapping for async mutations"

key-files:
  created:
    - frontend/src/__tests__/lib/apiFetch.test.js
    - frontend/src/__tests__/context/AuthContext.test.jsx
    - frontend/src/__tests__/hooks/useStrategyFeed.test.js
    - frontend/src/__tests__/hooks/useNotifications.test.js
    - frontend/src/jest-polyfills.js
  modified: []

key-decisions:
  - "AbortError timeout test uses fetch stub (not MSW never-resolving handler) because MSW v2 Node mode does not propagate AbortError from intercepted handler back to caller"
  - "EventSource mock re-assigned in beforeEach because CRA default resetMocks: true auto-resets jest.fn() implementations before every test"
  - "5xx error_does_not_crash waitFor timeout set to 6000ms to account for apiFetch 1s retry backoff across 3 strategy API calls"

requirements-completed: [TEST-03, TEST-05]

# Metrics
duration: 92min
completed: 2026-04-04
---

# Phase 23 Plan 02: API Client + Auth + Hook Unit Tests Summary

**48 unit tests across 4 files verifying apiFetch behaviors, cookie-based AuthContext lifecycle, and strategy/notification hook interactions via MSW — no real network calls**

## Performance

- **Duration:** 92 min
- **Started:** 2026-04-03T22:33:11Z
- **Completed:** 2026-04-04T00:05:18Z
- **Tasks:** 2
- **Files created:** 5

## Accomplishments

### Task 1: apiFetch unit tests (22 tests)

Created `frontend/src/__tests__/lib/apiFetch.test.js` with 22 tests:
- Timeout enforcement (AbortError via fetch stub), custom timeout override, caller signal passthrough
- 5xx retry: exactly 2 fetch calls on 503 then 200; no retry on 4xx or 200
- 401 redirect to `/auth?expired=1`; 403 permission-denied toast; 5xx server-error toast
- CSRF header injected on POST/PUT/PATCH/DELETE when cookie present; excluded on GET; excluded with no cookie
- `credentials: 'include'` on every request
- `Content-Type: application/json` on JSON body; no Content-Type on FormData
- Response object returned with `.json()` callable; base URL prepend behavior

Created `frontend/src/jest-polyfills.js` (missing from Plan 23-01 commit):
- `TextEncoder`/`TextDecoder` polyfills for MSW v2 in jsdom
- Web Streams API (`ReadableStream`, `WritableStream`, `TransformStream`) for `@mswjs/interceptors`
- `BroadcastChannel` stub
- `REACT_APP_BACKEND_URL=http://localhost` so apiFetch constructs valid absolute URLs in Jest

### Task 2: AuthContext, useStrategyFeed, useNotifications tests (26 tests)

**AuthContext.test.jsx** (10 tests):
- Initial loading state: `loading=true` → `false` after `/api/auth/me`
- Authenticated user state from cookie-based `/api/auth/me` response
- `user=null` on 401 and network errors; no localStorage reads/writes
- `login(userData)` sets user; `logout()` POSTs to `/api/auth/logout` then clears user
- Google OAuth: `?token=` param causes Bearer header on `/api/auth/me` call
- `window.history.replaceState` called with `/dashboard` after OAuth
- `useAuth` outside `AuthProvider` throws

**useStrategyFeed.test.js** (8 tests):
- Empty initial state; active cards from API loaded correctly
- `approveCard()`: POST to correct endpoint, returns `generate_payload`, refreshes active list
- `dismissCard()`: POST with reason body, refreshes both active and history lists
- 500 API response → empty arrays, no crash

**useNotifications.test.js** (8 tests):
- Initial `loading=true`; notifications and unreadCount populated from API
- `markRead(id)`: POST to `/api/notifications/:id/read`
- `markAllRead()`: POST to `/api/notifications/read-all`
- Error fallback to empty array; EventSource mocked so SSE doesn't crash jsdom

## Task Commits

1. **Task 1: apiFetch tests + polyfills** - `a4e9720` (test)
2. **Task 2: AuthContext + hook tests** - `9940770` (test)

## Files Created

- `frontend/src/__tests__/lib/apiFetch.test.js` — 22 tests, 270 lines
- `frontend/src/__tests__/context/AuthContext.test.jsx` — 10 tests, 295 lines
- `frontend/src/__tests__/hooks/useStrategyFeed.test.js` — 8 tests, 262 lines
- `frontend/src/__tests__/hooks/useNotifications.test.js` — 8 tests, 200 lines
- `frontend/src/jest-polyfills.js` — MSW v2 polyfills, 45 lines

## Decisions Made

- **AbortError timeout test uses fetch stub**: MSW v2 Node interceptor does not propagate `AbortError` back to the caller when the handler is pending and the signal fires. The fetch never settles in this scenario. Solution: stub `global.fetch` to immediately reject with a `DOMException('AbortError')` to directly test `fetchWithTimeout`'s catch block.

- **EventSource re-assigned in `beforeEach`**: CRA's default `resetMocks: true` calls `jest.resetAllMocks()` before each test, clearing `jest.fn()` implementations. A module-level `global.EventSource = jest.fn(...)` loses its factory after the first test. Re-assigning in `beforeEach` survives the reset.

- **5xx error test waitFor timeout 6000ms**: `apiFetch` retries on 5xx with 1s backoff. `useStrategyFeed` makes 3 parallel fetch calls on mount (active + dismissed + approved). With all returning 500, total wait is ~3s for retries. Default 1000ms `waitFor` timeout fails.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] MSW v2 AbortError not propagated in Node mode**
- **Found during:** Task 1 — timeout test
- **Issue:** MSW v2 Node server does not propagate `AbortError` from the never-resolving handler back to the `fetch()` caller when the abort signal fires. The `fetch()` never resolves or rejects.
- **Fix:** Stub `global.fetch` with `jest.fn().mockRejectedValue(new DOMException(..., 'AbortError'))` to directly test the abort catch-block in `fetchWithTimeout`.
- **Files modified:** `frontend/src/__tests__/lib/apiFetch.test.js`
- **Commit:** `a4e9720`

**2. [Rule 3 - Blocking] `jest-polyfills.js` not in git from Plan 23-01**
- **Found during:** Task 1 — MSW v2 fails without TextEncoder polyfill
- **Issue:** The `jest-polyfills.js` referenced in `craco.config.js` from Plan 23-01 was not committed.
- **Fix:** Created `frontend/src/jest-polyfills.js` with full Web APIs polyfill set.
- **Files modified:** `frontend/src/jest-polyfills.js`
- **Commit:** `a4e9720`

**3. [Rule 3 - Blocking] resetMocks: true clears EventSource mock implementation**
- **Found during:** Task 2 — all useNotifications tests fail
- **Issue:** `resetMocks: true` (CRA default) calls `jest.resetAllMocks()` before each test, clearing the `jest.fn()` factory. Calling `new EventSource()` after reset returns `undefined`, causing `close()` to throw.
- **Fix:** Re-assign `global.EventSource = jest.fn(() => ({ close: jest.fn(), ... }))` inside `beforeEach` so each test gets a fresh implementation.
- **Files modified:** `frontend/src/__tests__/hooks/useNotifications.test.js`
- **Commit:** `9940770`

## Known Stubs

None — all test assertions verify real behavior from actual source files.

## Self-Check: PASSED

- FOUND: `frontend/src/__tests__/lib/apiFetch.test.js`
- FOUND: `frontend/src/__tests__/context/AuthContext.test.jsx`
- FOUND: `frontend/src/__tests__/hooks/useStrategyFeed.test.js`
- FOUND: `frontend/src/__tests__/hooks/useNotifications.test.js`
- FOUND: `frontend/src/jest-polyfills.js`
- FOUND commit: `a4e9720` (test(23-02): apiFetch unit tests)
- FOUND commit: `9940770` (test(23-02): AuthContext + hook tests)

Final verification: "Test Suites: 4 passed, 4 total" and "Tests: 48 passed, 48 total"

---
*Phase: 23-frontend-unit-test-suite*
*Completed: 2026-04-04*
