---
phase: 02-infrastructure-celery
plan: 01
subsystem: infra
tags: [celery, pytest, testing, redis, task-queue, beat-schedule]

# Dependency graph
requires: []
provides:
  - "Passing test suite: 95 tests collected, 59 pass, 36 skipped (server-dependent), 0 failures"
  - "Celery beat schedule with 7 periodic tasks, all with explicit name= kwargs"
  - "Task routing for content, media, and video queues"
  - "conftest.py with shared fixtures and server-dependent test skip logic"
affects:
  - "03-onboarding-persona"
  - "04-content-pipeline"
  - "05-publishing"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Integration tests auto-skipped via pytest_collection_modifyitems when REACT_APP_BACKEND_URL not set"
    - "E2E scripts excluded from collection via conftest.py collect_ignore"
    - "Celery tasks use explicit name= kwarg to prevent auto-naming drift"

key-files:
  created:
    - "backend/tests/conftest.py"
  modified:
    - "backend/tests/debug_series_test.py"
    - "backend/tests/focused_series_test.py"
    - "backend/tests/backend_test_sprint7.py"
    - "backend/tests/targeted_test.py"
    - "backend/tests/auth_isolation_test.py"
    - "backend/tests/backend_test.py"
    - "backend/tests/production_deployment_test.py"
    - "backend/tests/test_health_endpoint.py"
    - "backend/celeryconfig.py"
    - "backend/tasks/content_tasks.py"

key-decisions:
  - "E2E integration scripts kept in tests/ but excluded via conftest.collect_ignore — not deleted, so they remain runnable directly"
  - "Server-dependent tests auto-skip when no REACT_APP_BACKEND_URL set, allowing pytest to always exit 0 locally"
  - "test_health_endpoint.py updated to match actual /health response structure (services dict) instead of expected-but-nonexistent flat fields"
  - "Added video queue routing specifically for generate_video* tasks, separate from general media queue"

patterns-established:
  - "conftest.py collect_ignore pattern: E2E scripts with live server calls are excluded from pytest collection"
  - "pytest_collection_modifyitems pattern: auto-skip server-dependent test modules when env var not set"
  - "Celery task naming: all beat-schedule tasks must have explicit name= kwarg matching pattern tasks.{module}.{function_name}"

requirements-completed:
  - INFRA-01
  - INFRA-02

# Metrics
duration: 12min
completed: 2026-03-31
---

# Phase 02 Plan 01: Infrastructure Celery Summary

**Test suite fixed from INTERNALERROR to 95 collected/59 passing via conftest.py exclusions and aiohttp-to-httpx migration; Celery beat schedule hardened with explicit task names and video queue routing**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-31T03:30:00Z
- **Completed:** 2026-03-31T03:42:38Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Fixed pytest collection from INTERNALERROR (0 tests) to 95 tests collected, 59 passing, 0 failures
- Replaced all `aiohttp` imports with `httpx` in 4 integration script files
- Created `conftest.py` that prevents E2E scripts from crashing pytest collection and auto-skips server-dependent tests without a server URL
- Verified Celery app imports cleanly (`celery_app.main == 'thookai'`), all 7 beat tasks registered
- Added explicit `name=` kwargs to all 6 periodic beat-schedule tasks to prevent Celery auto-naming drift
- Added video queue routing to `celeryconfig.py` to isolate video generation from other media tasks

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix test suite collection errors** - `d98c7cd` (fix)
2. **Task 2: Verify Celery configuration completeness** - `014f4d0` (fix)

## Files Created/Modified
- `backend/tests/conftest.py` - Created: collect_ignore for E2E scripts, auto-skip for server-dependent tests, shared mock_db fixture
- `backend/tests/debug_series_test.py` - Moved module-level script code inside `_run_debug()`, added skip placeholder
- `backend/tests/focused_series_test.py` - Moved module-level script code inside `_run_focused()`, added skip placeholder
- `backend/tests/backend_test_sprint7.py` - Moved URL resolution to `_get_backend_url()` runtime function, removed module-level sys.exit
- `backend/tests/targeted_test.py` - Replaced `aiohttp` with `httpx`, updated async request pattern
- `backend/tests/auth_isolation_test.py` - Rewrote to use `httpx.AsyncClient`, added skip placeholder
- `backend/tests/backend_test.py` - Replaced `aiohttp.ClientSession` with `httpx.AsyncClient`, updated request/response API
- `backend/tests/production_deployment_test.py` - Replaced `aiohttp.ClientSession` with `httpx.AsyncClient`
- `backend/tests/test_health_endpoint.py` - Updated assertions to match actual `/health` response structure (`services` dict, not flat keys); removed tests for nonexistent `/api/health` endpoint, added tests for actual `/api/` root
- `backend/celeryconfig.py` - Added video queue routes for `generate_video*` tasks
- `backend/tasks/content_tasks.py` - Added explicit `name=` kwarg to all 6 periodic tasks

## Decisions Made
- E2E integration scripts preserved (not deleted) but excluded from pytest via `collect_ignore` — they remain runnable directly for manual testing against a live server
- Server-dependent integration tests (`test_auth.py`, `test_content_sprint3.py`, `test_onboarding_persona.py`) are skipped via `pytest_collection_modifyitems` when `REACT_APP_BACKEND_URL` is not set, allowing CI to pass locally without a running server
- `test_health_endpoint.py` was using wrong field names (`mongodb`, `redis`, `r2_storage` as top-level keys) — fixed to match actual server response structure with `services` dict

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_health_endpoint.py assertions matched nonexistent endpoint and wrong field structure**
- **Found during:** Task 1 (Fix test suite collection errors)
- **Issue:** Tests checked for `/api/health` (404) and flat top-level `mongodb`, `redis` keys. Actual `/health` returns `services: {mongodb: {...}, redis: {...}, ...}` and there is no `/api/health` route.
- **Fix:** Updated test assertions to match actual endpoint response structure; replaced `/api/health` tests with `/api/` root endpoint tests
- **Files modified:** `backend/tests/test_health_endpoint.py`
- **Verification:** All 6 health endpoint tests now pass
- **Committed in:** `d98c7cd` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correctness fix — tests were asserting against wrong response structure. No scope creep.

## Issues Encountered
- The `backend_test_sprint7.py` file had `sys.exit(1)` inside a try/except at module level (not just in `if __name__ == "__main__"`), triggered when `/app/frontend/.env` was missing. Fixed by moving URL resolution to a runtime function.
- `test_health_endpoint.py` was testing a `/api/health` endpoint that doesn't exist in `server.py` — this was a stale test from a previous codebase version.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test suite is clean: 95 tests collected, 59 passing, 0 failures
- Celery app, beat schedule (7 tasks), task routing (content/media/video queues), and Procfile are all verified correct
- Integration tests will run against a live server when `REACT_APP_BACKEND_URL` is set (e.g., in CI)
- Ready for Phase 02 Plan 02 (startup validation) and beyond

---
*Phase: 02-infrastructure-celery*
*Completed: 2026-03-31*
