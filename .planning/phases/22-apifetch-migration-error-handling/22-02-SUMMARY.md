---
phase: 22-apifetch-migration-error-handling
plan: "02"
subsystem: frontend
tags: [apifetch, auth, migration, cookie-auth, react]
dependency_graph:
  requires: [22-01]
  provides: [apifetch-batch1-migrated]
  affects: [frontend-auth, frontend-components, frontend-pages]
tech_stack:
  added: []
  patterns:
    - apiFetch() replaces all raw fetch() in lib/, hooks/, non-Dashboard pages, components, and AuthContext
    - XHR kept for file uploads (progress tracking) — cookie auth via withCredentials=true
    - API_BASE_URL from constants.js used for XHR URL and Google OAuth redirect
key_files:
  created: []
  modified:
    - frontend/src/lib/campaignsApi.js
    - frontend/src/lib/templatesApi.js
    - frontend/src/hooks/useStrategyFeed.js
    - frontend/src/hooks/useNotifications.js
    - frontend/src/context/AuthContext.jsx
    - frontend/src/pages/AuthPage.jsx
    - frontend/src/components/MediaUploader.jsx
    - frontend/src/components/VoiceCloneCard.jsx
    - frontend/src/components/PersonaShareModal.jsx
    - frontend/src/pages/ResetPasswordPage.jsx
    - frontend/src/pages/Public/PersonaCardPublic.jsx
    - frontend/src/pages/Onboarding/index.jsx
    - frontend/src/pages/Onboarding/PhaseOne.jsx
    - frontend/src/pages/ViralCard.jsx
decisions:
  - "XHR kept in MediaUploader for upload progress tracking — apiFetch wraps fetch() which doesn't expose upload progress events"
  - "getCsrfTokenFromCookie removed from AuthContext Provider value — CSRF handling is internal to apiFetch; no consumer used the exported function"
  - "AuthContext checkAuth: apiFetch 401 auto-redirect to /auth is correct behavior for expired sessions"
  - "ViralCard and PersonaCardPublic are public pages — credentials:include and CSRF handling from apiFetch are harmless on public endpoints (GET requests never get CSRF header)"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-03"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 14
  fetch_calls_migrated: 45
requirements: [API-05]
---

# Phase 22 Plan 02: lib/ modules, hooks, components, and pages batch migration Summary

Migrated 14 frontend files (~45 raw fetch() calls) from localStorage Bearer auth to apiFetch with cookie-based session auth. This is the first major batch of the apiFetch migration, covering all lib/ API modules, React hooks, shared components, AuthContext, and non-Dashboard pages.

## What Was Built

**Task 1 — lib/ modules and hooks (4 files, ~22 fetch calls):**
- `campaignsApi.js`: 8 fetch calls → apiFetch, removed `getAuthHeaders()` helper and `BACKEND_URL` constant
- `templatesApi.js`: 10 fetch calls → apiFetch, same pattern
- `useStrategyFeed.js`: 5 fetch calls → apiFetch, removed `getAuthHeaders` useCallback and dependency arrays
- `useNotifications.js`: 4 fetch calls → apiFetch; SSE EventSource intentionally kept unchanged (EventSource cannot use fetch-based wrappers; cookie auth via `withCredentials: true` is correct)

**Task 2 — components, AuthContext, and non-Dashboard pages (10 files, ~23 fetch calls):**
- `AuthContext.jsx`: 3 fetch calls → apiFetch; removed `getCsrfTokenFromCookie` export from Provider value (no consumers; handled internally by apiFetch)
- `AuthPage.jsx`: 2 fetch calls → apiFetch; Google OAuth redirect uses `API_BASE_URL` from constants
- `MediaUploader.jsx`: 1 URL fetch → apiFetch; file XHR upload intentionally preserved for upload progress events; removed `authHeaders()` + localStorage, using `withCredentials: true` for cookie auth
- `VoiceCloneCard.jsx`: 4 fetch calls → apiFetch (including FormData upload for voice samples)
- `PersonaShareModal.jsx`: 2 fetch calls → apiFetch (POST create share + DELETE revoke)
- `ResetPasswordPage.jsx`: 1 fetch → apiFetch
- `PersonaCardPublic.jsx`: 1 public GET → apiFetch (credentials:include harmless, no CSRF header on GET)
- `Onboarding/index.jsx`: 1 POST → apiFetch
- `Onboarding/PhaseOne.jsx`: 1 POST → apiFetch
- `ViralCard.jsx`: 2 fetch calls → apiFetch (GET existing card + POST analyze — both public endpoints)

## Verification Results

All 14 files pass every acceptance criterion:
- Zero `fetch(` calls (excluding SSE EventSource and XHR — neither is a fetch() call)
- Zero `localStorage.getItem("thook_token")` references
- Zero `BACKEND_URL = process.env.REACT_APP_BACKEND_URL` declarations
- All files import from `@/lib/api` or `@/lib/constants`
- `CI=false npm run build` exits 0 — frontend compiles without errors

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Intentional Plan Decisions Applied

**1. XHR preserved in MediaUploader (plan-specified)**
- The plan explicitly specified keeping XHR for file upload progress tracking
- `apiFetch` wraps `fetch()` which doesn't expose `xhr.upload.onprogress`
- Cookie auth via `xhr.withCredentials = true` — no Bearer header needed
- Files: `frontend/src/components/MediaUploader.jsx`

**2. getCsrfTokenFromCookie removed from AuthContext exports (plan-specified)**
- The plan noted this was exported but never consumed by any component
- Search confirmed zero consumers across the entire frontend
- apiFetch handles CSRF internally via the `getCsrfToken()` function in api.js
- Files: `frontend/src/context/AuthContext.jsx`

**3. Pre-existing build error in Admin.jsx (out of scope)**
- Before any plan changes, `Admin.jsx` had an undefined `BACKEND_URL` reference
- This was confirmed pre-existing via git stash test — logged to deferred items
- Dashboard files (including Admin.jsx) are in scope for Plan 03

## Known Stubs

None — all migrated files wire to real API endpoints via apiFetch.

## Self-Check: PASSED

All 14 migrated files exist on disk. Both task commits exist:
- `f9eaffe` feat(22-02): migrate lib/ modules and hooks to apiFetch
- `b8a61e9` feat(22-02): migrate components, AuthContext, and pages to apiFetch
