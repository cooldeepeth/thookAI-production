---
phase: 14-strategy-dashboard-notifications
plan: "01"
subsystem: strategy-api
tags: [strategy, api-routes, content-generation, dash-05, dash-02]
dependency_graph:
  requires:
    - "12-strategist-agent (handle_approval, handle_dismissal)"
    - "backend/agents/strategist.py (Phase 12)"
  provides:
    - "GET /api/strategy — strategy feed endpoint"
    - "POST /api/strategy/{id}/approve — approve with generate_payload"
    - "POST /api/strategy/{id}/dismiss — dismiss with suppression info"
  affects:
    - "14-02 (frontend consumes these 3 endpoints)"
tech_stack:
  added: []
  patterns:
    - "APIRouter with prefix=/strategy, tags=[strategy]"
    - "DismissRequest BaseModel with optional reason field"
    - "_serialize_card helper for datetime ISO serialization"
    - "patch('routes.strategy.db') + patch('routes.strategy.handle_approval/handle_dismissal') for route tests"
    - "_make_cursor_mock helper: .sort().limit().to_list() chain mock"
key_files:
  created:
    - backend/routes/strategy.py
    - backend/tests/test_strategy_routes.py
  modified:
    - backend/server.py
decisions:
  - "Route does NOT call /api/content/create itself — frontend fires that call after receiving generate_payload (thin route wrapper pattern)"
  - "DismissRequest body is Optional — dismiss works with or without a reason body"
  - "_serialize_card handles 4 datetime fields: created_at, dismissed_at, expires_at, approved_at"
metrics:
  duration: "21 minutes"
  completed: "2026-04-01"
  tasks_completed: 2
  files_modified: 3
---

# Phase 14 Plan 01: Strategy API Routes Summary

**One-liner:** Three JWT-protected strategy endpoints (GET feed, POST approve, POST dismiss) wrapping Phase 12's strategist handle_approval/handle_dismissal with full 13-test coverage.

## What Was Built

Created `backend/routes/strategy.py` with three endpoints that serve as thin wrappers around Phase 12's strategist agent functions:

- `GET /api/strategy` — returns strategy recommendation cards filtered by `status` (default `pending_approval`) and `limit` (default 20); serializes datetime fields to ISO strings
- `POST /api/strategy/{id}/approve` — calls `handle_approval`, returns `generate_payload` with `platform`, `content_type`, `raw_input` for one-click content creation (DASH-02)
- `POST /api/strategy/{id}/dismiss` — calls `handle_dismissal` with optional `reason`, returns `dismissed`, `topic_suppressed_until`, `needs_calibration_prompt`

Both POST endpoints return 404 when the card is not found or has already been actioned.

Registered `strategy_router` in `backend/server.py` under the `/api` prefix.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create strategy routes and register in server.py | 85af3b8 | backend/routes/strategy.py, backend/server.py |
| 2 | Write comprehensive unit tests for strategy routes | b23825b | backend/tests/test_strategy_routes.py |

## Verification Results

```
13 passed in 1.00s
['/api/strategy', '/api/strategy/{recommendation_id}/approve', '/api/strategy/{recommendation_id}/dismiss']
```

All 13 tests pass. Full suite regression check: 397 passed (1 pre-existing failure in `test_beat_schedule_has_cleanup_stale_jobs` — unrelated Celery beat schedule issue from before this plan).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All three endpoints are fully wired to `handle_approval` and `handle_dismissal` from `agents/strategist.py`.

## Self-Check: PASSED

- [x] `backend/routes/strategy.py` exists with 3 routes
- [x] `backend/tests/test_strategy_routes.py` exists with 13 tests (min_lines 80 satisfied: 434 lines)
- [x] Commits 85af3b8 and b23825b exist
- [x] `from agents.strategist import handle_approval, handle_dismissal` present in strategy.py
- [x] `from routes.strategy import router as strategy_router` present in server.py
- [x] `api_router.include_router(strategy_router)` present in server.py
