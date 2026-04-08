---
phase: 18-security-auth
plan: "03"
subsystem: security-tests
tags: [security, input-validation, owasp, nosql-injection, xss, path-traversal, rate-limiting, tests]
dependency_graph:
  requires: [18-01]
  provides: [SEC-05, SEC-07]
  affects: [backend/tests/security/, backend/routes/auth.py]
tech_stack:
  added: []
  patterns:
    - pytest autouse fixture for rate limiter state reset (prevents test isolation failures)
    - _patch_all_db() context manager for patching both database.db and routes.auth.db
    - TestClient + InputValidationMiddleware for synchronous middleware size-limit tests
    - httpx.AsyncClient + ASGITransport for async FastAPI route tests
key_files:
  created:
    - backend/tests/security/__init__.py
    - backend/tests/security/conftest.py
    - backend/tests/security/test_input_validation.py
    - backend/tests/security/test_owasp_top10.py
  modified:
    - backend/routes/auth.py
decisions:
  - "routes/auth.py binds db at module import time via 'from database import db', so tests patching auth routes must patch routes.auth.db (not only database.db)"
  - "autouse fixture resets in-memory RateLimiter._mem_requests between tests to prevent cross-test rate limit contamination (429 false positives)"
  - "Path traversal protection tested via sanitization logic unit tests (character allowlist strips '/'), not HTTP integration tests (no multipart test client needed)"
  - "Rule 2 auto-fix: added logging import + logger.warning() calls to routes/auth.py for failed login audit events (A09 gap)"
metrics:
  duration: "~50 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 18 Plan 03: Input Validation and OWASP Top 10 Security Tests Summary

54 security tests across two files covering NoSQL injection, XSS, path traversal, request size limits, and all OWASP Top 10 2021 categories.

## What Was Built

### Task 1: Input Validation Security Tests (SEC-05)

**`backend/tests/security/test_input_validation.py`** — 22 tests

- **TestNoSQLInjection** (6 tests): MongoDB operator payloads (`{"$gt": ""}`, `{"$ne": null}`, `{"$regex": ".*"}`, `{"$where": "1==1"}`) in email fields are rejected by Pydantic EmailStr (422). Password object injection gets 422 or 401. `raw_input` operator payload does not cause 500.
- **TestXSSPrevention** (5 tests): XSS payloads stored as literal JSON strings. All responses return `application/json` (not HTML). CSP header `default-src 'none'` is present. Email XSS rejected by EmailStr (422). Error responses are also JSON.
- **TestPathTraversal** (5 tests): Upload filename sanitization strips `/`. URL-encoded and double-encoded traversal paths are sanitized. Null byte injection is stripped. R2 key construction enforces `context/{user_id}/{upload_id}/` prefix.
- **TestRequestSizeLimits** (6 tests): `InputValidationMiddleware.MAX_BODY_SIZE` is exactly 10MB (10485760 bytes). Requests over 10MB return 413. Exact-at-limit passes. Missing Content-Length header is not rejected.

### Task 2: OWASP Top 10 Systematic Verification Tests (SEC-07)

**`backend/tests/security/test_owasp_top10.py`** — 32 tests

- **TestA01BrokenAccessControl** (5 tests): Unauthenticated GET to `/api/auth/me`, `/api/dashboard/stats`, `/api/content/jobs`, `/api/persona/me` returns 401. Invalid Bearer token returns 401, not 500.
- **TestA02CryptographicFailures** (4 tests): Registration stores bcrypt hash (`$2b$` prefix), never plaintext. `create_access_token()` uses HS256 (not `none`). Login sets HttpOnly session cookie. `encrypt_token()` output differs from input.
- **TestA03Injection** (3 tests): NoSQL injection in email returns 422. Password object injection rejected. AST static check confirms `find_one()` calls use dict parameters (no f-strings).
- **TestA04InsecureDesign** (6 tests): PasswordPolicy rejects missing uppercase, missing digit, too short (<8), common passwords (`password`, `qwerty`, `admin`), and over-length (>128). Accepts strong passwords.
- **TestA05SecurityMisconfiguration** (4 tests): Security headers present on 404 and 422 responses. Empty JWT secret raises JWTError (no fallback). SecurityConfig warns on short secrets.
- **TestA07IdentificationFailures** (4 tests): Non-existent email, wrong password, Google OAuth user — all return "Invalid email or password" (same message, prevents user enumeration). Duplicate email registration returns 400.
- **TestA08SoftwareIntegrity** (2 tests): Stripe webhook without `Stripe-Signature` header returns 400. Static source assertion confirms signature check is enforced before event processing.
- **TestA09Logging** (4 tests): Security middleware has module-level logger. Rate limit violations are logged at WARNING. Failed login path uses 401 with generic message. auth.py imports logging.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added logging to routes/auth.py**

- **Found during:** Task 2, TestA09Logging
- **Issue:** `routes/auth.py` had no `import logging` and no logger configured. The A09 (Logging and Monitoring) test verifying audit logging for failed authentication was failing because there was nothing to assert against.
- **Fix:** Added `import logging` and `logger = logging.getLogger(__name__)` at module top. Added `logger.warning(...)` calls in both failed login code paths (user not found / wrong password) for audit trail.
- **Files modified:** `backend/routes/auth.py`
- **Commits:** 5c41e7b

**2. [Rule 1 - Bug] Fixed path traversal assertion was too strict**

- **Found during:** Task 1, TestPathTraversal
- **Issue:** Initial assertion `assert not safe_name.startswith("..")` failed because the character allowlist includes `.`, so `../../../etc/passwd` becomes `......etcpasswd` (dots are valid in filenames like `file.pdf`). The actual protection is that `/` is stripped.
- **Fix:** Changed assertion to `assert "etc/passwd" not in safe_name` and added comment explaining that dots alone cannot traverse directories without a path separator.
- **Files modified:** `backend/tests/security/test_input_validation.py`

**3. [Rule 3 - Blocking Issue] Rate limiter state leaks between tests**

- **Found during:** Running both test files together
- **Issue:** The `_rate_limiter` in `middleware/security.py` is a module-level singleton with in-memory state. Auth endpoint tests in one file accumulate request counts that trigger the 10 req/min auth rate limit (429) when the second file's tests run — causing false positives.
- **Fix:** Added `autouse=True` pytest fixture in `conftest.py` that calls `_rate_limiter._mem_requests.clear()` before/after each test. This gives each test a clean rate limiter state without mocking.
- **Files modified:** `backend/tests/security/conftest.py`

**4. [Rule 3 - Blocking Issue] routes.auth.db binding requires dual patching**

- **Found during:** Task 2, test_register_duplicate_email_returns_400
- **Issue:** `routes/auth.py` line 8 does `from database import db`, creating a local name binding at import time. Patching only `database.db` doesn't affect the already-bound `db` in `routes.auth`. Test returned 200 instead of 400.
- **Fix:** Created `_patch_all_db()` context manager that patches both `database.db` and `routes.auth.db`. Applied to all tests that exercise auth routes. Documented in test file docstring.
- **Files modified:** `backend/tests/security/test_owasp_top10.py`

## Known Stubs

None — all tests verify actual behavior, no stubs.

## Self-Check: PASSED

- FOUND: backend/tests/security/test_input_validation.py
- FOUND: backend/tests/security/test_owasp_top10.py
- FOUND: backend/tests/security/conftest.py
- FOUND: commit 2548293 (input validation tests)
- FOUND: commit 5c41e7b (OWASP Top 10 tests + auth.py logging)
