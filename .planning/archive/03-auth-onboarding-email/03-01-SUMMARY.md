---
phase: 03-auth-onboarding-email
plan: 01
subsystem: auth
tags: [auth, jwt, google-oauth, testing, bug-fix]
dependency_graph:
  requires: []
  provides: [AUTH-01, AUTH-02, AUTH-03]
  affects: [backend/routes/auth.py, backend/routes/auth_google.py, backend/auth_utils.py]
tech_stack:
  added: []
  patterns: [ASGITransport httpx testing, JWT fallback secret, dev-safe cookie flags]
key_files:
  created:
    - backend/tests/test_auth_core.py
  modified:
    - backend/routes/auth.py
    - backend/auth_utils.py
decisions:
  - JWT secret fallback 'thook-dev-secret' applied consistently in both create and decode paths
  - Cookie secure/samesite flags vary by environment (development=lax/http-safe, production=none/https)
  - EXPIRE_DAYS replaced with settings.security.jwt_expire_days for config-driven expiry
metrics:
  duration: 4 minutes
  completed: "2026-03-31T04:27:00Z"
  tasks: 2
  files_created: 1
  files_modified: 2
---

# Phase 03 Plan 01: Auth Core Verification & Hardening Summary

17 async unit tests covering registration, login, session persistence, and Google OAuth flows — all passing. Fixed a critical JWT secret mismatch that caused every /auth/me call to return 401 for tokens issued by /auth/register and /auth/login.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write unit tests for auth core | 5578a9a | backend/tests/test_auth_core.py |
| 2 | Fix auth issues found by tests | 3a6ce6a | backend/routes/auth.py, backend/auth_utils.py |

## What Was Built

### Task 1: Unit Tests (`test_auth_core.py`)

17 async tests using `httpx.AsyncClient` with `ASGITransport` — runs without a live server or MongoDB. Classes:

- **TestRegistration** (6 tests): 200 response with token, credits=200, no hashed_password/_id, onboarding_completed=False, 400 on duplicate email, session_token cookie set
- **TestLogin** (4 tests): valid credentials 200+token, wrong password 401, nonexistent email 401, Google-auth user blocked 401
- **TestSessionPersistence** (4 tests): valid Bearer token returns user, no token returns 401, expired token returns 401, logout returns message
- **TestGoogleOAuth** (3 tests): 503 with error=google_auth_unavailable when not configured, callback creates new user with credits=200, callback links existing user without duplicate

### Task 2: Auth Route Fixes

Three issues fixed:

1. **JWT secret mismatch** (critical bug): `auth_utils.decode_token()` used `settings.security.jwt_secret_key` (empty in dev), while `auth.py`'s `create_jwt_token()` fell back to `"thook-dev-secret"`. Every `/auth/me` call returned 401 for tokens issued by login/register. Fixed by applying the same `or "thook-dev-secret"` fallback in `decode_token`.

2. **Hardcoded EXPIRE_DAYS=7**: Replaced with `settings.security.jwt_expire_days` throughout `auth.py`. Cookie `max_age` also now uses the config value.

3. **Cookie secure settings**: Added `is_dev = settings.app.is_development` check. Development: `secure=False, samesite="lax"` (works over HTTP). Production: `secure=True, samesite="none"` (requires HTTPS, cross-origin).

## Verification

```
pytest tests/test_auth_core.py -v
17 passed, 0 failed

pytest tests/ (full suite)
67 passed, 36 skipped, 0 failed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JWT secret mismatch between create and decode paths**
- **Found during:** Task 1 test execution (test_me_with_valid_bearer_token_returns_user_data failing with 401)
- **Issue:** `auth.py` `create_jwt_token()` used `settings.security.jwt_secret_key or "thook-dev-secret"` but `auth_utils.decode_token()` used only `settings.security.jwt_secret_key` (empty when JWT_SECRET_KEY env var not set). All tokens issued by login/register were unverifiable.
- **Fix:** Added `or "thook-dev-secret"` fallback in `decode_token()` in `auth_utils.py`
- **Files modified:** `backend/auth_utils.py`
- **Commit:** 3a6ce6a

**2. [Rule 1 - Bug] httpx `app=` parameter removed in newer versions**
- **Found during:** Task 1 first run
- **Issue:** `httpx.AsyncClient(app=app, ...)` raises `TypeError` in httpx 0.28+. Must use `ASGITransport`.
- **Fix:** Changed fixture to `ASGITransport(app=app)` pattern
- **Files modified:** `backend/tests/test_auth_core.py`
- **Commit:** 5578a9a

## Known Stubs

None — all test mocks return realistic data and all auth routes work end-to-end with the fixed JWT secret.

## Self-Check: PASSED
