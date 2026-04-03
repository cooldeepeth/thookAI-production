---
phase: 21-ci-strictness-httponly-cookie-auth
plan: 02
subsystem: auth-security
tags: [csrf, cookies, security, middleware, auth]
dependency_graph:
  requires: []
  provides: [csrf-middleware, csrf-cookie-on-login, csrf-cookie-on-register]
  affects: [backend/middleware/csrf.py, backend/routes/auth.py, backend/server.py]
tech_stack:
  added: []
  patterns: [double-submit-cookie-csrf, starlette-base-http-middleware]
key_files:
  created:
    - backend/middleware/csrf.py
    - backend/tests/test_csrf.py
  modified:
    - backend/routes/auth.py
    - backend/server.py
decisions:
  - "CSRF exempt paths use exact-match set + prefix tuple — easy to extend"
  - "Bearer auth bypasses CSRF entirely — non-browser API clients are not vulnerable to CSRF"
  - "No session_token cookie = no CSRF check — unauthenticated requests fall through to route auth"
  - "csrf_token cookie set httpOnly=False intentionally — JS must read it to send as header"
  - "GET /api/auth/csrf-token endpoint added for page-reload CSRF token refresh"
metrics:
  duration: 8m
  completed: "2026-04-03T20:48:50Z"
  tasks_completed: 1
  files_modified: 4
---

# Phase 21 Plan 02: CSRF Double-Submit Cookie Protection Summary

CSRF middleware with double-submit cookie pattern — cookie-auth requests require matching X-CSRF-Token header; Bearer auth bypasses CSRF; 16 tests covering all exemptions.

## What Was Built

Implemented CSRF protection using the double-submit cookie pattern (AUTH-05):

1. `backend/middleware/csrf.py` — `CSRFMiddleware` (Starlette BaseHTTPMiddleware):
   - Safe methods (GET/HEAD/OPTIONS/TRACE) always pass through
   - Exempt paths skip CSRF (login, register, Google auth, billing webhook, n8n, /health)
   - Requests without `session_token` cookie skip CSRF (Bearer auth / unauthenticated)
   - Cookie-authenticated requests must provide `X-CSRF-Token` header matching `csrf_token` cookie
   - Returns `403 {"detail": "CSRF token missing"}` when header absent
   - Returns `403 {"detail": "CSRF token invalid"}` when header does not match cookie

2. `backend/routes/auth.py`:
   - Added `set_csrf_cookie(response, csrf_value)` helper — httpOnly=False (JS-readable)
   - `register` endpoint now sets both `session_token` (httpOnly) and `csrf_token` cookies
   - `login` endpoint now sets both `session_token` (httpOnly) and `csrf_token` cookies
   - Both endpoints return `csrf_token` in the JSON response body for immediate frontend use
   - `logout` endpoint now deletes both `session_token` and `csrf_token` cookies
   - Added `GET /api/auth/csrf-token` endpoint to refresh CSRF token after page reloads

3. `backend/server.py`:
   - Imports `CSRFMiddleware` from `middleware.csrf`
   - Registers `CSRFMiddleware` after CORS, before `SecurityHeadersMiddleware`

4. `backend/tests/test_csrf.py` — 16 tests in `TestCSRFProtection`:
   - All behaviors from the plan verified (all 12 original + 4 additional)

## Decisions Made

| Decision | Rationale |
|---|---|
| CSRF exempt paths: exact set + prefix tuple | Clean, readable, easy to extend for new auth/webhook paths |
| Bearer auth bypasses CSRF | Non-browser API/mobile clients are not vulnerable to CSRF attacks |
| No `session_token` cookie = no CSRF check | Unauthenticated requests fall through to route-level auth check |
| `csrf_token` cookie `httpOnly=False` | Intentional — JS must read it to set as request header |
| CSRF token returned in JSON response body | Frontend needs the token immediately after login without needing to parse cookies |

## Requirements Fulfilled

- **AUTH-01**: Login and register set httpOnly `session_token` cookie AND JS-readable `csrf_token` cookie
- **AUTH-02**: `get_current_user` reads cookie first, falls back to Authorization header (pre-existing, verified by test suite)
- **AUTH-05**: CSRF middleware enforces double-submit cookie pattern for all state-changing cookie-authenticated requests

## Deviations from Plan

None — plan executed exactly as written.

## Tests

All 16 tests in `TestCSRFProtection` pass:

- `test_cookie_auth_no_csrf_header_returns_403` — CSRF missing → 403
- `test_cookie_auth_correct_csrf_header_returns_200` — matching header → 200
- `test_cookie_auth_wrong_csrf_header_returns_403` — wrong header → 403
- `test_bearer_auth_bypasses_csrf` — Bearer header, no cookies → 200
- `test_get_request_exempt_from_csrf` — GET with cookie, no CSRF → 200
- `test_options_request_exempt_from_csrf` — OPTIONS preflight → 200
- `test_login_endpoint_exempt_from_csrf` — POST /api/auth/login → 200
- `test_register_endpoint_exempt_from_csrf` — POST /api/auth/register → 200
- `test_webhook_endpoint_exempt_from_csrf` — POST /api/billing/webhook → 200
- `test_login_sets_both_session_and_csrf_cookies` — register sets both cookies + body token
- `test_register_sets_both_session_and_csrf_cookies` — register sets both cookies
- `test_logout_clears_csrf_cookie` — logout clears both cookies
- `test_put_with_correct_csrf_returns_200` — PUT also requires CSRF
- `test_delete_with_no_csrf_returns_403` — DELETE also requires CSRF
- `test_health_endpoint_always_exempt` — /health always passes
- `test_no_cookie_no_header_not_csrf_checked` — no cookie = CSRF skipped

## Known Stubs

None.

## Commits

| Hash | Message |
|---|---|
| 03b125f | feat(21-02): add CSRF double-submit cookie protection |

## Self-Check: PASSED
