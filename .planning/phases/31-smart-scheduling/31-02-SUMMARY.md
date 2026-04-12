---
phase: 31-smart-scheduling
plan: "02"
subsystem: backend/agents
tags: [scheduling, celery, planner, optimal-times, schd-01, schd-04]
dependency_graph:
  requires:
    - "31-01 (test scaffold — test_scheduling_phase31.py)"
  provides:
    - "schedule_content with dual-write to scheduled_posts"
    - "get_optimal_posting_times with stored engagement data preference"
  affects:
    - "backend/tasks/scheduled_tasks.py (Celery Beat — now gets populated scheduled_posts)"
    - "backend/routes/dashboard.py (schedule_content caller)"
tech_stack:
  added: []
  patterns:
    - "Stored-data-first with heuristic fallback for optimal time suggestions"
    - "Dual-write pattern — update content_jobs then insert into scheduled_posts"
key_files:
  created: []
  modified:
    - backend/agents/planner.py
decisions:
  - "Extract _compute_heuristic_suggestions as standalone helper to enable stored-data-first path without code duplication"
  - "Use data_driven=True flag + source='stored' on suggestions to satisfy test assertions without requiring specific reason text"
  - "Pad stored-slot results with heuristics when insufficient stored data (avoids returning fewer than num_suggestions)"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-12T12:57:10Z"
  tasks_completed: 3
  files_modified: 1
requirements:
  - SCHD-01
  - SCHD-04
---

# Phase 31 Plan 02: Smart Scheduling Core Bug Fixes Summary

**One-liner:** Fixed two critical bugs in planner.py — get_optimal_posting_times now reads persona engagement history (SCHD-01) and schedule_content now dual-writes into scheduled_posts enabling Celery Beat to publish (SCHD-04).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire get_optimal_posting_times to stored engagement data (SCHD-01) | 999fa69 | backend/agents/planner.py |
| 2 | Fix schedule_content to insert into scheduled_posts (SCHD-04) | 08234db | backend/agents/planner.py |
| 3 | Full test suite sanity check and post-change grep verification | (no commit — verification only) | — |

## What Changed

### backend/agents/planner.py

**Lines 50–87 (new):** Added `_compute_heuristic_suggestions(platform, num_suggestions, now)` helper.
- Extracted the existing for-loop heuristic logic from `get_optimal_posting_times`
- Returns a sorted list of time slots from PLATFORM_PEAKS static data
- Used both as primary path (new users) and padding fallback (insufficient stored slots)

**Lines 90–200 (modified):** Overhauled `get_optimal_posting_times`:
- After burnout cap section, reads `persona.get("optimal_posting_times", {})` (SCHD-01 fix)
- When stored slots exist: sorts by `avg_engagement_rate` descending, maps `day_of_week` (0=Mon) to next occurrence within 7 days, marks suggestions with `source="stored"`, `data_driven=True`
- Pads with heuristics if stored slots < `num_suggestions`
- Falls back to `_compute_heuristic_suggestions` for new users (no post history)
- Returns `data_driven: True/False` flag in response

**Lines 363–407 (new block in schedule_content):** Added dual-write to `scheduled_posts`:
- After `content_jobs.update_one` succeeds, fetches `final_content` and `media_assets` from the job
- Inserts one `scheduled_posts` document per platform with: `schedule_id` (`sch_` + 12-char uuid hex), `user_id`, `job_id`, `platform`, `final_content`, `media_assets`, `scheduled_at`, `status="scheduled"`, `created_at`
- Celery Beat (`_process_scheduled_posts` in scheduled_tasks.py) now has data to read and publish

## Test Results

```
tests/test_scheduling_phase31.py
  PASSED  TestOptimalTimesWiring::test_optimal_times_uses_stored_data           [Test 1 — was RED]
  PASSED  TestOptimalTimesWiring::test_optimal_times_falls_back_to_heuristics   [Test 2 — was GREEN]
  PASSED  TestOptimalTimesWiring::test_optimal_times_returns_correct_count      [Test 3 — was GREEN]
  PASSED  TestScheduleContentCreatesScheduledPosts::test_schedule_content_creates_scheduled_posts_doc  [Test 4 — was RED]
  PASSED  TestScheduleContentCreatesScheduledPosts::test_schedule_content_one_doc_per_platform         [Test 5 — was RED]
  FAILED  TestCalendarEndpoint::test_calendar_endpoint_exists                   [Test 6 — Plan 03 scope]
  FAILED  TestCalendarEndpoint::test_calendar_endpoint_month_filter             [Test 7 — Plan 03 scope]
  FAILED  TestRescheduleEndpoint::test_reschedule_creates_new_record            [Test 8 — Plan 04 scope]

Result: 5 passed, 3 failed (3 failures are Plan 03/04 scope — calendar + reschedule endpoints not yet built)
```

**Regression:** `test_celery_cutover.py` — 5 pre-existing failures unchanged. These reflect stale test expectations from Phase 9 (tests assert `beat_schedule == {}` but celeryconfig.py now has a non-empty schedule restored in a prior phase). Not caused by Plan 02 changes, out of scope.

## Deviations from Plan

None — plan executed exactly as written.

The plan specified adding `data_driven=True` and `source="stored"` fields to distinguish stored-data suggestions from heuristic ones. This was implemented as specified and satisfies all three assertion paths in `test_optimal_times_uses_stored_data`.

## Known Stubs

None — both fixes are fully wired with real database operations (no stubs or placeholder data).

## Self-Check: PASSED

- [x] `backend/agents/planner.py` exists and is modified
- [x] Commit `999fa69` exists — Task 1 (SCHD-01 fix)
- [x] Commit `08234db` exists — Task 2 (SCHD-04 fix)
- [x] `grep "insert_many" backend/agents/planner.py` returns 1 match (line 392)
- [x] `grep "optimal_posting_times" backend/agents/planner.py` returns 3 matches (lines 124, 127)
- [x] `grep "_compute_heuristic_suggestions" backend/agents/planner.py` returns 3 matches (def + 2 calls)
- [x] `python3 -c "import agents.planner; print('OK')"` outputs OK
- [x] Tests 1, 4, 5 turned GREEN (were RED before Plan 02)
- [x] Tests 2, 3 remain GREEN (regression guards intact)
