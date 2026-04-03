---
phase: 20-frontend-e2e-integration
plan: "05"
subsystem: testing
tags: [dead-links, e2e, static-analysis, route-liveness, E2E-07]
dependency_graph:
  requires: []
  provides: [E2E-07-dead-link-detection]
  affects: [ci-test-suite]
tech_stack:
  added: []
  patterns:
    - _AsyncCursor class for mocking Motor async cursors in tests
    - _MockDB class with __getattr__ for dynamic collection access
    - patch("database.db") for lazy imports + patch("routes.X.db") for module-level imports
    - ASGITransport + AsyncClient for isolated FastAPI app testing
key_files:
  created:
    - backend/tests/test_dead_links_v2.py
    - backend/tests/integration/test_api_routes_alive.py
  modified: []
decisions:
  - "Used ASGITransport with isolated FastAPI app (no lifespan) instead of importing server.py app to avoid real DB/Redis connections at test time"
  - "Allowed 404 in expected_statuses for resource-404 routes (persona/me) rather than flagging as dead links"
  - "Patched both database.db (lazy imports) and routes.<mod>.db (module-level imports) plus services.notification_service.db for full coverage"
metrics:
  duration_minutes: 8
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  tests_added: 34
  completed_date: "2026-04-03"
---

# Phase 20 Plan 05: Dead Link Detection & API Route Liveness Summary

**One-liner:** Static AST-based frontend-to-backend dead link analysis plus dynamic parametrized route liveness tests covering 21 API endpoints with fully mocked DB and no external dependencies.

## What Was Built

### Task 1: Enhanced Static Dead Link Analysis (`backend/tests/test_dead_links_v2.py`)

Nine static analysis tests across three classes, extending the original `test_dead_links.py` with:

**TestFrontendApiReferencesV2:**
- `test_all_frontend_api_paths_have_backend_routes` — Scans all frontend JS/JSX files (excluding test files) for `/api/*` URL strings using regex, normalizes dynamic segments (`:id`, `{param}`, hex IDs), and verifies each maps to a registered backend route prefix
- `test_no_hardcoded_localhost_in_frontend_production_code` — Detects hardcoded `http://localhost` or `127.0.0.1` in production frontend code; excludes test files and environment-driven fallbacks (`process.env.REACT_APP_*`)
- `test_no_bare_tmp_paths_in_media_url_construction` — Detects `/tmp/` paths returned from `return` statements in `media_storage.py` and `uploads.py`

**TestRouteRegistrationCompleteness:**
- `test_all_route_files_registered_in_server` — Verifies every `.py` in `backend/routes/` appears as an import in `server.py`
- `test_no_duplicate_route_prefixes` — Parses explicit `prefix=` arguments in `include_router()` calls; asserts no two routers share the same prefix

**TestMediaUrlIntegrity:**
- `test_media_storage_uses_r2_public_url` — Confirms `media_storage.py` references `settings.r2` for URL construction
- `test_no_hardcoded_s3_endpoints_in_media_storage` — Detects hardcoded full bucket domain strings
- `test_uploads_route_rejects_when_r2_unavailable` — Verifies HTTP 503 guard is present before `/tmp` fallback (BUG-7 protection)
- `test_get_public_url_references_r2_public_url` — Confirms `get_public_url()` helper uses `settings.r2.r2_public_url`

### Task 2: Dynamic API Route Liveness Tests (`backend/tests/integration/test_api_routes_alive.py`)

Twenty-five dynamic tests across two classes:

**TestAllRoutesRespond (21 parametrized probes):**

Routes covered: `/health`, `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`, `/api/auth/forgot-password`, `/api/onboarding/questions`, `/api/persona/me`, `/api/content/jobs`, `/api/content/create`, `/api/content/platform-types`, `/api/dashboard/stats`, `/api/analytics/overview`, `/api/billing/credits`, `/api/billing/config`, `/api/templates`, `/api/agency/workspaces`, `/api/strategy`, `/api/campaigns`, `/api/media/assets`, `/api/notifications`

Each probe asserts: status NOT 500 (crash) AND status IN expected_statuses (which may include 404 only for resource-not-found routes).

**TestNoUnexpectedServerErrors (4 tests):**
- `test_health_returns_valid_json` — GET /health returns 200 with JSON `{status: ...}`
- `test_unknown_route_returns_404_not_500` — Unknown paths return 404, not 500
- `test_options_request_does_not_crash` — OPTIONS request does not crash server
- `test_malformed_json_body_returns_422_not_500` — Malformed JSON body triggers 422, not 500

**Key implementation decisions:**

1. Isolated FastAPI app (no lifespan) — prevents real MongoDB/Redis connections at test time
2. `_AsyncCursor` class implements `__aiter__`/`__anext__` for routes that use `async for` on query results
3. `_MockDB` class provides collection mocks via `__getattr__` for lazy `from database import db` imports
4. Dual patching: `database.db` (lazy imports in media, n8n_bridge, notifications) + `routes.<mod>.db` (module-level imports) + `services.notification_service.db`
5. Auth bypassed via `dependency_overrides[get_current_user]`

## Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Enhanced static dead link analysis | 9637a44 | `backend/tests/test_dead_links_v2.py` |
| 2 | Dynamic API route liveness tests | f4d0c72 | `backend/tests/integration/test_api_routes_alive.py` |

## Verification

```
pytest tests/test_dead_links_v2.py tests/integration/test_api_routes_alive.py -x -v
# 34 passed, 3 warnings in 2.33s
```

Test counts:
- `test_dead_links_v2.py`: 9 test methods (6+ required)
- `test_api_routes_alive.py`: 21 route probes (13+ required) + 4 error handling tests = 25 total
- Combined: 34 dead link detection tests

## Deviations from Plan

**1. [Rule 1 - Bug] Corrected route probe paths to match actual registered endpoints**
- Found during: Task 2 iteration
- Issue: Plan probes used `/api/reset-password/request`, `/api/persona`, `/api/content` — these return 404 because actual routes are `/api/auth/forgot-password`, `/api/persona/me`, `/api/content/jobs`
- Fix: Updated probe paths to match actual endpoint definitions discovered from route files
- Files modified: `backend/tests/integration/test_api_routes_alive.py`
- Commit: f4d0c72

**2. [Rule 1 - Bug] Fixed _mock_db() to use _MockDB class instead of MagicMock.__getattr__**
- Found during: Task 2 execution
- Issue: `MagicMock.__setattr__("__getattr__", ...)` raises `AttributeError: Attempting to set unsupported magic method '__getattr__'`
- Fix: Created `_MockDB` class (not MagicMock subclass) that implements `__getattr__` directly
- Files modified: `backend/tests/integration/test_api_routes_alive.py`
- Commit: f4d0c72

**3. [Rule 1 - Bug] Added _AsyncCursor for proper async iteration support**
- Found during: Task 2 execution
- Issue: `MagicMock().__aiter__` returns a non-async iterator, causing `TypeError: 'async for' received an object from __aiter__ that does not implement __anext__`
- Fix: Implemented `_AsyncCursor` class with proper `__aiter__`/`__anext__` async protocol
- Files modified: `backend/tests/integration/test_api_routes_alive.py`
- Commit: f4d0c72

## Known Stubs

None — both test files are complete implementations with no placeholders or hardcoded empty values.

## Self-Check: PASSED

Files exist:
- `backend/tests/test_dead_links_v2.py` — FOUND
- `backend/tests/integration/test_api_routes_alive.py` — FOUND

Commits exist:
- 9637a44 — FOUND (feat(20-05): enhanced static dead link analysis)
- f4d0c72 — FOUND (feat(20-05): dynamic API route liveness tests)
