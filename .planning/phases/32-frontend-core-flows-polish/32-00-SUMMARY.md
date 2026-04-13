---
phase: 32-frontend-core-flows-polish
plan: "00"
subsystem: frontend-tests
tags: [tdd, stub-tests, wave-0, jest]
dependency_graph:
  requires: []
  provides:
    - frontend/src/__tests__/pages/AuthPage.test.jsx
    - frontend/src/__tests__/pages/DashboardHome.test.jsx
    - frontend/src/__tests__/pages/Settings.test.jsx
  affects:
    - Plan 32-06 (fills in real assertions)
tech_stack:
  added: []
  patterns:
    - Jest test.todo() stubs for TDD ordering enforcement
key_files:
  created:
    - frontend/src/__tests__/pages/AuthPage.test.jsx
    - frontend/src/__tests__/pages/DashboardHome.test.jsx
    - frontend/src/__tests__/pages/Settings.test.jsx
  modified: []
decisions:
  - No imports in stub files — keeps stubs free of breakage risk from changing component structure during wave 1
  - test.todo() used over test.skip() — cleaner output, shows as "todo" not "skip" so intent is explicit
metrics:
  duration_minutes: 5
  completed_date: "2026-04-12"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
---

# Phase 32 Plan 00: Wave-0 TDD Stub Tests Summary

Three wave-0 stub test files created for AuthPage, DashboardHome, and Settings using Jest test.todo() placeholders — satisfying TDD ordering so test files exist before wave 1 implementation runs.

## Objective

Create minimal stub test files for AuthPage, DashboardHome, and Settings before any implementation plans run. These stubs satisfy TDD ordering: tests exist (RED/skip state) before implementation (Plans 32-01 through 32-05), and Plan 32-06 fills them with real assertions afterward.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | AuthPage stub test | 8e3d1cf | frontend/src/__tests__/pages/AuthPage.test.jsx |
| 2 | DashboardHome + Settings stubs | 8d0160e | frontend/src/__tests__/pages/DashboardHome.test.jsx, Settings.test.jsx |

## Files Created

| File | Lines | test.todo count |
|------|-------|-----------------|
| frontend/src/__tests__/pages/AuthPage.test.jsx | 9 | 4 |
| frontend/src/__tests__/pages/DashboardHome.test.jsx | 8 | 3 |
| frontend/src/__tests__/pages/Settings.test.jsx | 9 | 4 |

**Total:** 3 files, 26 lines, 11 test.todo entries

## Stub Behaviors Registered

**AuthPage (4 stubs):**
- `renders_without_crash` — page renders login form
- `error_alert_aria` — error element has role=alert when login fails
- `google_auth_button` — Google auth button is present and focusable
- `password_rules_register` — password rules list appears after focus in register mode

**DashboardHome (3 stubs):**
- `skeleton_during_load` — skeleton or loading state appears while fetching
- `error_state_with_retry` — retry button visible when stats fetch fails
- `empty_content_cta` — CTA visible when no content jobs exist

**Settings (4 stubs):**
- `four_tabs_present` — all four tab triggers render (Billing, Connections, Profile, Notifications)
- `billing_skeleton_during_load` — skeleton renders while billing data is fetching
- `billing_error_retry` — error state with retry button renders on billing fetch failure
- `tabs_keyboard_accessible` — tab triggers are keyboard-accessible via role=tab

## Verification Output

```
PASS src/__tests__/pages/AuthPage.test.jsx
PASS src/__tests__/pages/DashboardHome.test.jsx
PASS src/__tests__/pages/Settings.test.jsx
Tests: 11 todo, 11 total
```

No FAIL lines. No imports in any stub file — zero breakage risk.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

All test entries are intentional stubs (test.todo). These are not data stubs but TDD-ordering placeholders — Plan 32-06 will replace them with real assertions after wave 1 implementation completes.

## Self-Check: PASSED

- [x] frontend/src/__tests__/pages/AuthPage.test.jsx — FOUND (4 test.todo)
- [x] frontend/src/__tests__/pages/DashboardHome.test.jsx — FOUND (3 test.todo)
- [x] frontend/src/__tests__/pages/Settings.test.jsx — FOUND (4 test.todo)
- [x] Commit 8e3d1cf — FOUND (AuthPage stub)
- [x] Commit 8d0160e — FOUND (DashboardHome + Settings stubs)
- [x] npm test: 11 todo, 0 FAIL
