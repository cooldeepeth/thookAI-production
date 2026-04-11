---
phase: 26-backend-endpoint-hardening
plan: "02"
subsystem: backend-middleware-error-handling
tags: [error-format, rate-limiting, exception-handler, tdd, BACK-03, BACK-04, BACK-05, BACK-07]
dependency_graph:
  requires:
    - 26-01 (test_error_format.py RED stubs)
  provides:
    - STATUS_TO_ERROR_CODE dict with 11 status codes
    - "@app.exception_handler(HTTPException) — standardized error_code in all 4xx responses"
    - "@app.exception_handler(StarletteHTTPException) — standardized 404 from route-not-found"
    - "@app.exception_handler(RequestValidationError) — field-level errors with error_code"
    - "RateLimitMiddleware 429 response with error_code=RATE_LIMITED"
    - "InputValidationMiddleware 413 response with error_code=PAYLOAD_TOO_LARGE"
    - "CSRFMiddleware 403 responses with error_code=CSRF_INVALID"
    - test_rate_limit_threshold.py (3 passing tests covering BACK-07)
  affects:
    - backend/server.py
    - backend/middleware/security.py
    - backend/middleware/csrf.py
    - backend/tests/test_error_format.py
    - backend/tests/test_rate_limit_threshold.py
tech_stack:
  added: []
  patterns:
    - FastAPI exception_handler decorator for both FastAPI and Starlette HTTPException variants
    - STATUS_TO_ERROR_CODE lookup table for consistent error code mapping
    - inspect.signature for testing constructor parameter defaults without instantiation side effects
key_files:
  created:
    - backend/tests/test_rate_limit_threshold.py
  modified:
    - backend/server.py
    - backend/middleware/security.py
    - backend/middleware/csrf.py
    - backend/tests/test_error_format.py
decisions:
  - Registered handler for both FastAPI HTTPException AND StarletteHTTPException — FastAPI route-not-found 404 uses Starlette's exception class, requiring separate handler registration
  - test_error_format.py unauthenticated POST test fixed to omit session_token cookie — sending a cookie triggers CSRF middleware before auth, returning 403 instead of 401/422
  - Added third test to test_rate_limit_threshold.py using inspect.signature to verify constructor defaults without relying on instantiation attributes alone
metrics:
  duration_minutes: 12
  completed_date: "2026-04-12"
  tasks_completed: 3
  files_created: 1
  files_modified: 4
---

# Phase 26 Plan 02: Standardized Error Codes Summary

Standardized error format for all FastAPI/Starlette HTTP error responses by adding `error_code` field to exception handlers and middleware — enabling type-safe frontend error handling without string-matching on `detail` messages.

## What Was Built

### Task 1: Exception Handlers in server.py

Added to `backend/server.py`:

- `STATUS_TO_ERROR_CODE` dict mapping 11 HTTP status codes to machine-readable error strings
- `@app.exception_handler(HTTPException)` — merges `error_code` into all FastAPI HTTPException responses (handles both string and dict `detail`)
- `@app.exception_handler(StarletteHTTPException)` — covers route-not-found 404 which uses Starlette's exception class
- `@app.exception_handler(RequestValidationError)` — returns `error_code=VALIDATION_ERROR` plus field-level `errors` list with path and message
- Updated global `Exception` handler to include `error_code=INTERNAL_ERROR` in 500 responses

All handlers registered BEFORE the generic `Exception` handler.

### Task 2: Middleware error_code Fields

Added `error_code` to direct JSONResponse returns that bypass the exception handler mechanism:

- `RateLimitMiddleware` 429 response: `"error_code": "RATE_LIMITED"` added
- `InputValidationMiddleware` 413 response: `"error_code": "PAYLOAD_TOO_LARGE"` added
- `CSRFMiddleware` 403 responses (missing and invalid): `"error_code": "CSRF_INVALID"` added

### Task 3: Rate Limit Threshold Test

Created `backend/tests/test_rate_limit_threshold.py` with 3 passing tests:

1. `test_auth_route_rate_limit_is_at_most_10_per_minute` — reads `endpoint_limits` dict, verifies auth paths have numeric limit <= 10 (BACK-07 numeric assertion)
2. `test_default_rate_limit_is_reasonable` — confirms `default_limit` attribute is > 10
3. `test_auth_limit_constructor_parameter_is_10` — uses `inspect.signature` to verify the `auth_limit` constructor default is <= 10

## Test Results

All 9 tests across the two test files pass:

```
tests/test_error_format.py::test_missing_body_on_content_create_returns_422_with_error_code PASSED
tests/test_error_format.py::test_not_found_route_returns_404_with_error_code PASSED
tests/test_error_format.py::test_malformed_json_body_never_returns_500 PASSED
tests/test_error_format.py::test_unauthenticated_persona_returns_401_with_error_code PASSED
tests/test_error_format.py::test_empty_json_body_returns_422_with_field_errors PASSED
tests/test_error_format.py::test_unauthenticated_analytics_returns_401_with_error_code PASSED
tests/test_rate_limit_threshold.py::test_auth_limit_constructor_parameter_is_10 PASSED
tests/test_rate_limit_threshold.py::test_auth_route_rate_limit_is_at_most_10_per_minute PASSED
tests/test_rate_limit_threshold.py::test_default_rate_limit_is_reasonable PASSED
9 passed, 3 warnings
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Bug] Fixed StarletteHTTPException not covered by FastAPI HTTPException handler**
- **Found during:** Task 1 verification
- **Issue:** FastAPI route-not-found returns Starlette's `HTTPException`, not FastAPI's. The `@app.exception_handler(HTTPException)` only catches FastAPI's variant, leaving 404 responses without `error_code`.
- **Fix:** Added `from starlette.exceptions import HTTPException as StarletteHTTPException` and registered a second `@app.exception_handler(StarletteHTTPException)` handler.
- **Files modified:** `backend/server.py`
- **Commit:** 62cfa7c

**2. [Rule 1 - Bug] Fixed CSRF collision in test_error_format.py unauthenticated test**
- **Found during:** Task 1 RED→GREEN transition
- **Issue:** `test_missing_body_on_content_create_returns_422_with_error_code` sent `Cookie: session_token=fakejwt` which triggered CSRF middleware returning 403 before auth could return 401 or validation could return 422.
- **Fix:** Removed the `Cookie` header from the test — unauthenticated requests don't need a cookie to test the 401/422 path.
- **Files modified:** `backend/tests/test_error_format.py`
- **Commit:** 62cfa7c

## Known Stubs

None — all error_code fields are wired to actual response content. No placeholder values.

## Self-Check: PASSED
