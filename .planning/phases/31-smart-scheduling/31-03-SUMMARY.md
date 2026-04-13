---
phase: 31-smart-scheduling
plan: "03"
subsystem: api
tags: [fastapi, mongodb, motor, scheduled-posts, calendar, reschedule]

requires:
  - phase: 31-02
    provides: schedule_content inserts into scheduled_posts + optimal times stored data wiring

provides:
  - GET /api/dashboard/schedule/calendar — month-scoped scheduled_posts query with content_jobs enrichment (SCHD-03)
  - PATCH /api/dashboard/schedule/{schedule_id}/reschedule — atomic cancel + new record insert with ownership check (SCHD-02)
  - RescheduleRequest Pydantic model

affects:
  - 31-04
  - frontend ContentCalendar.jsx

tech-stack:
  added: []
  patterns:
    - "Lazy database module import: `import database as _db_module; _db = _db_module.db` inside function body so `patch('database.db', mock)` works correctly in tests regardless of module import ordering"
    - "Motor find() with sort= keyword arg instead of .sort() method chaining — preserves mock cursor's to_list AsyncMock through the chain"

key-files:
  created: []
  modified:
    - backend/routes/dashboard.py

key-decisions:
  - "Lazy database import pattern (import database as _db_module) instead of module-level `from database import db` binding — required so patch('database.db', mock) affects the endpoint at call time, not module load time"
  - "Motor sort as keyword argument in find() not method chaining — test mock sets to_list as AsyncMock on the cursor returned by find(); chaining .sort() returns a new MagicMock that loses the AsyncMock setup"

patterns-established:
  - "Lazy DB import: In dashboard.py endpoints that need mock-testable DB access, do `import database as _db_module; _db = _db_module.db` at the top of the function"

requirements-completed:
  - SCHD-02
  - SCHD-03

duration: 25min
completed: 2026-04-12
---

# Phase 31 Plan 03: Smart Scheduling Calendar + Reschedule Endpoints Summary

**Calendar endpoint queries scheduled_posts by month with content_jobs enrichment; reschedule endpoint atomically cancels old record and inserts new one — all 8 phase31 tests GREEN**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-12T00:00:00Z
- **Completed:** 2026-04-12T00:25:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- GET /api/dashboard/schedule/calendar returns posts from scheduled_posts for a given month, enriched with content preview from content_jobs (SCHD-03)
- PATCH /api/dashboard/schedule/{schedule_id}/reschedule atomically cancels old record, inserts new one with fresh schedule_id, updates content_jobs.scheduled_at (SCHD-02)
- All 8 tests in test_scheduling_phase31.py GREEN with any random seed ordering

## Task Commits

1. **Task 1+2: Add calendar and reschedule endpoints** - `c2110ee` (feat)
2. **Task 3: Verification** - included in same commit (all 8 tests green)

## Files Created/Modified

- `/Users/kuldeepsinhparmar/thookAI-production/backend/routes/dashboard.py` — Added RescheduleRequest model (line 496), GET /schedule/calendar (line 602-669), PATCH /schedule/{schedule_id}/reschedule (line 672-776)

## New Endpoint Signatures

### GET /api/dashboard/schedule/calendar

**Query params:** `year: int (2024-2030)`, `month: int (1-12)`

**Response:**
```json
{
  "posts": [
    {
      "schedule_id": "sch_abc123",
      "job_id": "j1",
      "platform": "linkedin",
      "status": "scheduled",
      "scheduled_at": "2026-04-15T09:00:00+00:00",
      "published_at": null,
      "preview": "First 100 chars of content...",
      "content_type": "post"
    }
  ],
  "year": 2026,
  "month": 4
}
```

### PATCH /api/dashboard/schedule/{schedule_id}/reschedule

**Body:** `{ "new_scheduled_at": "2026-04-16T10:00:00Z" }`

**Response:**
```json
{
  "rescheduled": true,
  "old_schedule_id": "sch_abc123",
  "new_schedule_id": "sch_xyz789",
  "new_scheduled_at": "2026-04-16T10:00:00+00:00",
  "platform": "linkedin",
  "job_id": "j1"
}
```

**Error cases:**
- 400 — New time is not in the future
- 404 — schedule_id not found or belongs to different user
- 400 — Post status is not "scheduled" or "pending"
- 409 — Race condition (post already processed by another worker)

## Test Results

```
8 passed — test_scheduling_phase31.py (all seeds)

Tests 6, 7 (SCHD-03 calendar): GREEN
  - test_calendar_endpoint_exists
  - test_calendar_endpoint_month_filter

Test 8 (SCHD-02 reschedule): GREEN
  - test_reschedule_creates_new_record

Tests 1-5 (from Plans 01-02): Unchanged GREEN
```

## Decisions Made

1. **Lazy database module import** — `import database as _db_module; _db = _db_module.db` inside each function body. The test file uses `patch("database.db", mock_db)` which replaces the module attribute. A module-level `from database import db` creates a local name binding at import time; the patch does not update it. The lazy pattern reads `database.db` at call time, after the patch is active.

2. **Motor sort keyword arg** — Used `find(..., sort=[("scheduled_at", 1)])` instead of `.sort("scheduled_at", 1)` method chaining. The test mock returns a `MagicMock` with `to_list = AsyncMock(return_value=[])` directly on the cursor. Calling `.sort()` on a `MagicMock` returns a new auto-created `MagicMock` that loses the `to_list` AsyncMock setup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Motor cursor sort chaining breaking test mock**
- **Found during:** Task 1 (calendar endpoint implementation)
- **Issue:** `.sort("scheduled_at", 1)` method chaining on the Motor cursor returns a new MagicMock in tests, losing the `to_list = AsyncMock` setup from `make_mock_db()`
- **Fix:** Changed to `find(..., sort=[("scheduled_at", 1)])` keyword argument form — the mock cursor returned by `find()` retains its `to_list` AsyncMock
- **Files modified:** `backend/routes/dashboard.py`
- **Committed in:** c2110ee (Task 1+2 commit)

**2. [Rule 1 - Bug] Fixed test isolation failure — lazy db import for mock compatibility**
- **Found during:** Task 2 (reschedule endpoint + Task 3 full suite run)
- **Issue:** `patch("database.db", mock_db)` does not update the local `db` name binding created by module-level `from database import db`. When `routes.dashboard` is imported before the reschedule test's patch context (due to earlier tests in the session), `db` in the endpoint refers to the real Motor object — `find_one()` queries MongoDB, finds nothing (no test doc), returns 404.
- **Fix:** Added `import database as _db_module; _db = _db_module.db` inside both new endpoint functions — reads `database.db` at call time when the patch is active
- **Files modified:** `backend/routes/dashboard.py`
- **Verification:** All 8 tests pass with random seeds 12345, 99999, 42, and default
- **Committed in:** c2110ee (Task 1+2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes were necessary for the tests to pass correctly in any import ordering. No scope creep.

## Issues Encountered

- Test ordering dependency: `test_reschedule_creates_new_record` failed when run after `TestScheduleContentCreatesScheduledPosts` because the planner import caused `routes.dashboard` to be cached with the real `db` binding before the patch context activated. Solved with lazy db import pattern.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 03 complete: calendar (SCHD-03) and reschedule (SCHD-02) endpoints in place
- Ready for Plan 04: frontend ContentCalendar.jsx integration and any remaining SCHD-04 work
- All 8 phase31 backend tests GREEN

---
*Phase: 31-smart-scheduling*
*Completed: 2026-04-12*
