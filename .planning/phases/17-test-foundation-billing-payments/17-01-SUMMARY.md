---
phase: 17-test-foundation-billing-payments
plan: 01
subsystem: test-infrastructure
tags: [testing, ci, coverage, fixtures, coroutine-fixes, pytest]
dependency_graph:
  requires: []
  provides:
    - green-ci-baseline
    - branch-coverage-measurement
    - standardized-conftest-fixtures
    - test-infrastructure-packages
  affects:
    - backend/tests/
    - backend/pytest.ini
    - backend/.coveragerc
    - backend/tests/conftest.py
tech_stack:
  added:
    - pytest-cov>=7.1.0
    - pytest-mock>=3.15.1
    - pytest-randomly>=3.15.0
    - mongomock-motor>=0.0.36
    - respx>=0.22.0
    - Faker>=40.12.0
    - greenlet (transitive, for coverage concurrency)
  patterns:
    - pytest filterwarnings = error::RuntimeWarning enforces no unawaited coroutines
    - mongomock-motor for real MongoDB query semantics without a live DB
    - respx for transport-level httpx mocking
    - Faker for deterministic test data generation
key_files:
  created:
    - backend/.coveragerc
    - backend/tests/billing/__init__.py
  modified:
    - backend/requirements.txt
    - backend/pytest.ini
    - backend/tests/conftest.py
    - backend/tests/test_pipeline_e2e.py
    - backend/tests/test_sharing_notifications_webhooks.py
    - backend/tests/test_media_generation.py
    - backend/tests/test_media_orchestrator.py
    - backend/services/media_orchestrator.py
decisions:
  - "Skip beat_schedule tests rather than repopulate them — n8n owns scheduling since Phase 8"
  - "asyncio.create_task mocks must consume coroutines with side_effect=lambda coro: coro.close() not return_value=None"
  - "validate_media_output in media_orchestrator.py was missing await — fixed as Rule 1 deviation"
  - "TestViralCard required routes.viral_card.db patch in addition to database.db to prevent event-loop-closed ordering failure"
  - "filterwarnings = error::RuntimeWarning added to pytest.ini (not just -W flag) so it enforces on every local run"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  files_modified: 9
  files_created: 2
---

# Phase 17 Plan 01: Test Foundation Summary

Clean CI baseline and test infrastructure for Phase 17.

**One-liner:** Green pytest baseline with zero RuntimeWarning emissions, branch coverage via .coveragerc, and 5 standardized fixtures (mongomock-motor/respx/Faker) for all downstream billing test plans.

## Tasks Completed

### Task 1: Fix 3 broken tests, fix 6 unawaited coroutines, install 6 packages

**Commit:** `377bd61`

Fixed 3 failing tests:
1. `TestBeatScheduleHasCleanupStaleJobs::test_beat_schedule_has_cleanup_stale_jobs` — added `@pytest.mark.skip(reason="n8n handles scheduling since Phase 8 -- beat_schedule intentionally empty")`
2. `TestBeatScheduleHasCleanupStaleJobs::test_all_six_periodic_tasks_are_scheduled` — same skip
3. `TestViralCard::test_analyze_returns_card_with_id_and_share_url` — ordering-dependent failure caused by `asyncio.run()` closing the event loop in other tests; fixed by patching `routes.viral_card.db` (module-level reference) in addition to `database.db`

Fixed 6 unawaited coroutine RuntimeWarnings:
1. `fire_webhook` in `test_pipeline_e2e.py` — changed `asyncio.create_task` mock from `return_value=None` to `side_effect=lambda coro: coro.close()`
2. `fire_webhook` in `test_pipeline_e2e.py` (second occurrence) — same fix
3. `_cleanup` in `test_pipeline_e2e.py` — changed `run_async` mock to consume coroutine before returning
4. `_cleanup` in `test_pipeline_e2e.py` (second occurrence) — same fix
5. `_do_render` in `test_media_orchestrator.py` — changed `asyncio.wait_for` mock to async function that closes coroutine before raising `TimeoutError`
6. `AsyncMockMixin._execute_mock_call` in `test_media_generation.py` — same wait_for fix pattern

Installed 6 packages in requirements.txt (new `# Test infrastructure` section):
- pytest-cov>=7.1.0
- pytest-mock>=3.15.1
- pytest-randomly>=3.15.0
- mongomock-motor>=0.0.36
- respx>=0.22.0
- Faker>=40.12.0

**Result:** 741 passed, 40 skipped, 0 failures, 0 RuntimeWarning emissions

### Task 2: Configure coverage infrastructure + standardize conftest.py fixtures

**Commit:** `93b4227`

Updated `backend/pytest.ini`:
- Added `addopts = -p randomly` for random test ordering
- Added `filterwarnings = error::RuntimeWarning` to enforce no unawaited coroutines on every run

Created `backend/.coveragerc`:
- `branch = true` — branch coverage enabled
- `concurrency = greenlet,thread` — correct for async FastAPI code
- Omits tests/, scripts/, venv/, .venv/
- `show_missing = true` with 2 decimal precision

Updated `backend/tests/conftest.py` with 5 new fixtures:
- `make_user` — factory for user documents with Faker
- `mongomock_db` — in-memory Motor DB with real query semantics
- `mock_db_atomic` — patches `database.db` with mongomock
- `respx_mock` — transport-level httpx mock
- `mock_current_user` — pre-built test user for auth dependency override

Created `backend/tests/billing/__init__.py` — empty init for billing test subdirectory

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing `await` on `validate_media_output` in media_orchestrator.py**
- **Found during:** Task 1 (while fixing coroutine warnings)
- **Issue:** `validate_media_output` is `async def` in `agents/qc.py` but called without `await` in `services/media_orchestrator.py` line 1166, producing a unawaited coroutine RuntimeWarning
- **Fix:** Added `await` to the call: `qc_result = await validate_media_output(...)`
- **Files modified:** `backend/services/media_orchestrator.py`
- **Commit:** `377bd61`

**2. [Rule 1 - Bug] TestViralCard event-loop-closed ordering failure**
- **Found during:** Task 1 investigation
- **Issue:** `test_pipeline_e2e.py` sync Celery tests call `run_async()` which creates a new event loop, sets it globally, then closes it. Subsequent async tests using Motor MongoDB driver fail with "Event loop is closed" because Motor tries to use the now-closed global event loop.
- **Fix:** Added `routes.viral_card.db` to the mock patch context so Motor is never invoked in the viral card analyze test.
- **Files modified:** `backend/tests/test_sharing_notifications_webhooks.py`
- **Commit:** `377bd61`

## Verification Results

```
$ pytest tests/ -q -W error::RuntimeWarning
741 passed, 40 skipped, 3 warnings in 26.92s

$ pytest tests/test_health_endpoint.py --cov=. --cov-branch -q
6 passed, 3 warnings in 2.86s
(branch coverage output: TOTAL 11310 statements, 21 branches covered)
```

## Self-Check: PASSED

Files created/verified:
- backend/.coveragerc: EXISTS
- backend/tests/billing/__init__.py: EXISTS
- backend/tests/conftest.py: HAS mongomock_db, make_user, respx_mock, mock_db_atomic, mock_current_user

Commits verified:
- 377bd61: EXISTS (fix: broken tests, coroutine warnings, 6 packages)
- 93b4227: EXISTS (feat: coverage + conftest fixtures)
