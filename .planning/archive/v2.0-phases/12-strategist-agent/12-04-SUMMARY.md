---
phase: 12-strategist-agent
plan: "04"
subsystem: tests
tags: [strategist, tests, tdd, STRAT-01, STRAT-02, STRAT-03, STRAT-04, STRAT-05, STRAT-06, STRAT-07]

# Dependency graph
requires:
  - phase: 12-02
    provides: "run_strategist_for_user, run_strategist_for_all_users, handle_dismissal, handle_approval, _build_generate_payload"
  - phase: 12-03
    provides: "n8n execute endpoint for nightly-strategist"
provides:
  - "29 tests covering all 7 STRAT requirements in backend/tests/test_strategist.py"
  - "Verified: pending_approval status always set (STRAT-02)"
  - "Verified: why_now fallback on empty LLM response (STRAT-03)"
  - "Verified: 3-card/day atomic cap (STRAT-04)"
  - "Verified: 14-day topic suppression blocks re-recommendation (STRAT-05)"
  - "Verified: 5 dismissals triggers halved_rate + calibration prompt (STRAT-06)"
  - "Verified: generate_payload has platform/content_type/raw_input keys (STRAT-07)"
affects: [future-refactors-to-agents/strategist.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_AsyncIterator class for proper async-for compatible Motor cursor mocking (Python 3.13)"
    - "patch.dict sys.modules for lazy-import modules (lightrag_service)"
    - "side_effect list on AsyncMock to simulate multi-call return sequences"
    - "_make_mock_db() factory pattern for isolated test setup across test classes"

key-files:
  created:
    - backend/tests/test_strategist.py
  modified: []

key-decisions:
  - "_AsyncIterator custom class used instead of MagicMock.__aiter__ — Python 3.13 requires __anext__ to be a real coroutine, not MagicMock"
  - "patch.dict sys.modules used for services.lightrag_service lazy import mocking — standard import.mock.patch cannot intercept lazy imports inside function bodies"
  - "pre-existing test_n8n_workflow_status.py failure is out of scope — confirmed present before plan 04 changes"

patterns-established:
  - "All strategist tests use _make_mock_db() factory to create independent mocks per test"
  - "_AsyncIterator class should be reused across future tests that mock Motor cursor async-for loops"

requirements-completed:
  - STRAT-01
  - STRAT-02
  - STRAT-03
  - STRAT-04
  - STRAT-05
  - STRAT-06
  - STRAT-07

# Metrics
duration: 12min
completed: "2026-04-01"
---

# Phase 12 Plan 04: Strategist Agent Tests Summary

**29 tests covering all 7 STRAT requirements — card schema, cadence controls, topic suppression, consecutive dismissal threshold, and generate_payload compatibility. All pass with mocked MongoDB, LLM, and LightRAG.**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-04-01
- **Tasks:** 2 (both in same file, committed together)
- **Files created:** 1 (`backend/tests/test_strategist.py`)
- **Tests written:** 29

## Accomplishments

### Task 1: Tests for STRAT-01 through STRAT-04

Created `backend/tests/test_strategist.py` with 4 test classes:

- **TestStrategistAgent (STRAT-01):** 5 tests — entry points, multi-user processing, eligibility check (approved_count threshold), LightRAG degradation (raises exception -> returns ""), Anthropic unavailable -> empty list
- **TestRecommendationCardSchema (STRAT-02):** 3 tests — status always "pending_approval", all 10 required fields present, AST check that pipeline is never imported
- **TestWhyNowRationale (STRAT-03):** 2 tests — non-empty why_now passes through, empty why_now triggers fallback (card still written)
- **TestCadenceControls (STRAT-04):** 3 tests — 5 LLM cards capped at 3 inserts, find_one_and_update returning None means cap reached, new-day reset sets cards_today_date to today

### Task 2: Tests for STRAT-05 through STRAT-07

Added 3 more test classes to the same file:

- **TestDismissalTracking (STRAT-05):** 6 tests — dismissed status set, consecutive_dismissals incremented, suppressed_until is 14 days out (within 5s tolerance), not_found returns error dict, find_one returns doc -> True, find_one returns None -> False
- **TestConsecutiveDismissalThreshold (STRAT-06):** 5 tests — 5th dismissal sets halved_rate=True, sets needs_calibration_prompt=True, halved_rate=True reduces max_cards to 1, approval resets consecutive_dismissals/halved_rate/calibration, approval not_found
- **TestGeneratePayloadSchema (STRAT-07):** 5 tests — required fields present, platform/content_type/raw_input map correctly, defaults (linkedin/post/topic), approval returns generate_payload, keys are subset of ContentCreateRequest required fields

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 | All STRAT tests (STRAT-01 through STRAT-07) | d18d70e | backend/tests/test_strategist.py |

## Files Created

- `backend/tests/test_strategist.py` — 874 lines, 29 tests across 7 test classes

## Decisions Made

- `_AsyncIterator` custom class used instead of `MagicMock.__aiter__` — Python 3.13 strict async iteration requires `__anext__` to be a real coroutine (not just a MagicMock method).
- `patch.dict("sys.modules", {"services.lightrag_service": mock_lightrag})` used for the LightRAG degradation test — the lazy import `from services.lightrag_service import query_knowledge_graph` inside `_query_content_gaps()` requires sys.modules patching, not standard `patch("agents.strategist._query_content_gaps")`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _AsyncIterator class for Motor async cursor mocking**
- **Found during:** Task 1, first test run
- **Issue:** `iter([])` returns a sync iterator — Python 3.13 raises `TypeError: 'async for' received an object from __aiter__ that does not implement __anext__: list_iterator`
- **Fix:** Created `_AsyncIterator` class with proper `async def __anext__` method
- **Files modified:** `backend/tests/test_strategist.py`
- **Commit:** d18d70e

**2. [Rule 1 - Bug] lightrag_raises function signature in degradation test**
- **Found during:** Task 1, second test run
- **Issue:** `async def lightrag_raises(user_id, topic, mode=None)` had wrong signature — `_query_content_gaps(user_id)` only passes one argument
- **Fix:** Changed to `async def lightrag_raises(user_id)`, then moved to `patch.dict sys.modules` approach to test the inner `query_knowledge_graph` raises path through `_query_content_gaps`'s try/except
- **Files modified:** `backend/tests/test_strategist.py`
- **Commit:** d18d70e

## Known Stubs

None — test file has no stubs. All 29 tests exercise real logic paths through mocked dependencies.

## Full Test Suite Status

- `pytest tests/test_strategist.py`: **29 passed**
- `pytest -x --tb=short` (full suite): **343 passed, 1 pre-existing failure** (`test_n8n_workflow_status.py::test_map_has_exactly_four_entries` — pre-dates plan 04, confirmed by stash check)

---
*Phase: 12-strategist-agent*
*Completed: 2026-04-01*

## Self-Check: PASSED

- FOUND: `backend/tests/test_strategist.py` (874 lines, 29 tests)
- FOUND: commit `d18d70e`
