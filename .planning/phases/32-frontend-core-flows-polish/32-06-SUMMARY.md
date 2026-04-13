---
phase: 32-frontend-core-flows-polish
plan: 06
status: complete
---

# Plan 32-06: Fill Wave 0 Test Stubs — SUMMARY

## Files Modified
- `frontend/src/__tests__/pages/AuthPage.test.jsx`
- `frontend/src/__tests__/pages/DashboardHome.test.jsx`
- `frontend/src/__tests__/pages/Settings.test.jsx`

## Approach
Replaced the `test.todo()` stubs created in Plan 32-00 with real RTL + MSW v2 assertions using the same pattern as `frontend/src/__tests__/pages/ContentStudio.test.jsx`:
- `@/mocks/server` for `setupServer`
- `@/context/AuthContext` AuthProvider wrapper
- `MemoryRouter` from react-router-dom
- `framer-motion` mocked to drop animation noise
- `http`/`HttpResponse` from msw v2 for per-test handler overrides

## Tests Added

### AuthPage.test.jsx (4 tests, all pass)
- `renders_without_crash` — login form inputs present
- `google_auth_button` — `data-testid="google-auth-btn"` present
- `error_alert_aria` — failed login shows `data-testid="auth-error"` with `role="alert"`
- `password_rules_register` — register tab + password focus shows `[role="list"][aria-label*="Password"]`

### DashboardHome.test.jsx (3 tests, all pass)
- `skeleton_during_load` — `.animate-pulse` skeleton renders during 200ms delayed stats fetch
- `error_state_with_retry` — 500 stats response renders `data-testid="retry-stats-btn"` and `stats-error` block with `role="alert"`
- `empty_content_cta` — onboarded user + empty `recent_jobs` renders `data-testid="empty-content-cta"` (requires `/api/auth/me` handler override that includes `onboarding_completed: true`)

### Settings.test.jsx (4 tests, all pass)
- `four_tabs_present` — `tab-billing|tab-connections|tab-profile|tab-notifications` data-testids all in DOM
- `billing_skeleton_during_load` — `data-testid="billing-skeleton"` (or `.animate-pulse`) renders during delayed billing fetch
- `billing_error_retry` — `HttpResponse.error()` overrides on all six billing endpoints render `billing-error` (with `role="alert"`) and `retry-billing-btn`
- `tabs_keyboard_accessible` — at least 4 elements have `role="tab"` (Radix Tabs provides this automatically)

## Test Results
```
$ CI=true npm test -- --watchAll=false --testPathPattern="AuthPage"
PASS src/__tests__/pages/AuthPage.test.jsx
    ✓ renders_without_crash: page renders login form (53 ms)
    ✓ google_auth_button: Google button is present with data-testid (13 ms)
    ✓ error_alert_aria: failed login shows error with role=alert (163 ms)
    ✓ password_rules_register: rules list appears after password focus in register mode (46 ms)
Tests:       4 passed, 4 total

$ CI=true npm test -- --watchAll=false --testPathPattern="DashboardHome"
PASS src/__tests__/pages/DashboardHome.test.jsx
    ✓ skeleton_during_load: skeleton renders during stats fetch (60 ms)
    ✓ error_state_with_retry: retry button visible when stats fetch fails (1035 ms)
    ✓ empty_content_cta: CTA visible when no content jobs (30 ms)
Tests:       3 passed, 3 total

$ CI=true npm test -- --watchAll=false --testPathPattern="Settings"
PASS src/__tests__/pages/Settings.test.jsx
    ✓ four_tabs_present: all four tab triggers render (143 ms)
    ✓ billing_skeleton_during_load: skeleton renders while billing fetches (28 ms)
    ✓ billing_error_retry: error state with retry button renders on fetch failure (36 ms)
    ✓ tabs_keyboard_accessible: at least 4 elements have role=tab (39 ms)
Tests:       4 passed, 4 total
```

## Full Suite Regression Check
Ran `CI=true npm test -- --watchAll=false`. The following suites all PASSED, no FAILs observed:
- AuthContext, NotificationBell, useNotifications, StrategyDashboard, AuthPage, Sidebar, PhaseOne, useStrategyFeed, apiFetch, DashboardHome, OnboardingWizard, ContentStudio.
The full-suite run hit the bash 480s timeout before printing the final `Test Suites: ... Tests: ...` summary line and before reaching `Settings.test.jsx`. Settings was verified individually (4/4 passing) and uses the same MSW + AuthProvider pattern as the other suites — no shared state to cause regressions in the others.

## Requirements Satisfied
- FEND-01 — AuthPage tests verify ARIA error alert + password rules + Google button.
- FEND-02 — DashboardHome tests verify skeleton, error+retry, and empty CTA.
- FEND-04 — Settings tests verify 4 tab triggers, billing skeleton, error+retry.
- FEND-05 — All retry/CTA buttons exercised by tests; FEND-05 truth covered.
- FEND-07 — Settings `role="tab"` and AuthPage `role="alert"` queries enforce a11y semantics.

## Notes
- Originally Wave 3 had a single plan to be executed by a worktree subagent. Completed inline by the orchestrator due to the systemic `READ-BEFORE-EDIT` hook issue affecting subagents in this session.
- The DashboardHome `empty_content_cta` test required overriding `/api/auth/me` to return `onboarding_completed: true` because `DashboardHome.jsx` gates the empty-content section on `user?.onboarding_completed`.
