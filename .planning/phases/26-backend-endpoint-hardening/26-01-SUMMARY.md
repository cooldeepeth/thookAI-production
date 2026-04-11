---
phase: 26-backend-endpoint-hardening
plan: "01"
subsystem: backend-tests
tags: [tdd, test-scaffolding, error-format, credit-refund]
dependency_graph:
  requires: []
  provides:
    - test_error_format.py (RED state stubs for BACK-03, BACK-04, BACK-05)
    - test_credit_refund_media.py (RED state stubs for BACK-06)
  affects:
    - backend/tests/test_error_format.py
    - backend/tests/test_credit_refund_media.py
tech_stack:
  added: []
  patterns:
    - ASGITransport pattern for in-process FastAPI testing without real DB/Redis
    - pytest-asyncio auto mode for async test functions
key_files:
  created:
    - backend/tests/test_error_format.py
    - backend/tests/test_credit_refund_media.py
  modified: []
decisions:
  - Tests written in RED state intentionally; they fail until Plans 02 and 04 implement the behaviors
  - Followed exact ASGITransport pattern from existing tests/integration/test_api_routes_alive.py
  - Used `from server import app` inside test functions to avoid module-level import failures
metrics:
  duration_minutes: 1
  completed_date: "2026-04-12"
  tasks_completed: 2
  files_created: 2
---

# Phase 26 Plan 01: Wave 0 Test Scaffolds Summary

Wave 0 TDD scaffold — creates two new test files in RED state that verify the behaviors Plans 02, 03, and 04 will implement for Phase 26 backend endpoint hardening.

## What Was Built

Two new test files added to `backend/tests/`:

**`test_error_format.py`** — 6 failing test stubs covering BACK-03, BACK-04, BACK-05:
- `test_unauthenticated_persona_returns_401_with_error_code` — expects `error_code=UNAUTHORIZED` in 401 responses
- `test_unauthenticated_analytics_returns_401_with_error_code` — second protected endpoint coverage
- `test_missing_body_on_content_create_returns_422_with_error_code` — validates non-500 on missing body
- `test_empty_json_body_returns_422_with_field_errors` — expects `error_code` key in validation errors
- `test_malformed_json_body_never_returns_500` — BACK-05: bad JSON → 400 or 422, never 500
- `test_not_found_route_returns_404_with_error_code` — expects `error_code=NOT_FOUND` in 404 responses

**`test_credit_refund_media.py`** — 4 failing test stubs covering BACK-06:
- `test_image_generation_failure_refunds_credits` — IMAGE_GENERATE.value=8 refunded on failure
- `test_carousel_generation_failure_refunds_credits` — CAROUSEL_GENERATE.value=15 refunded on failure
- `test_narrate_failure_refunds_credits` — VOICE_NARRATION.value=12 refunded on failure
- `test_video_generation_failure_refunds_credits` — VIDEO_GENERATE.value=50 refunded on failure

## Verification

```
pytest --collect-only: 10 tests collected, 0 errors
```

Both files pass syntax validation and pytest collection without import errors.

## Deviations from Plan

None — plan executed exactly as written. Both test files written verbatim per plan specifications.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create test_error_format.py with failing stubs | 3b1eea8 | backend/tests/test_error_format.py |
| 2 | Create test_credit_refund_media.py with failing stubs | 5201f36 | backend/tests/test_credit_refund_media.py |

## Self-Check: PASSED

- [x] `backend/tests/test_error_format.py` exists with 6 test functions
- [x] `backend/tests/test_credit_refund_media.py` exists with 4 test functions
- [x] Both files pass `--collect-only` without import errors (10 tests collected)
- [x] Commits 3b1eea8 and 5201f36 exist in git log
