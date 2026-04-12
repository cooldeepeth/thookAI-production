---
phase: 31-smart-scheduling
plan: "01"
subsystem: backend/tests
tags: [tdd, scheduling, test-scaffold, nyquist]
dependency_graph:
  requires: []
  provides:
    - test scaffold for SCHD-01 (optimal_posting_times stored data wiring)
    - test scaffold for SCHD-02 (schedule_content inserts into scheduled_posts)
    - test scaffold for SCHD-03 (calendar endpoint)
    - test scaffold for SCHD-04 (reschedule endpoint)
  affects:
    - backend/agents/planner.py (verified by tests 1, 4, 5)
    - backend/routes/dashboard.py (verified by tests 6, 7, 8)
tech_stack:
  added: []
  patterns:
    - Isolated FastAPI TestClient with dependency_overrides (Phase 20 pattern)
    - Motor async cursor mocking with MagicMock + AsyncMock
    - database.db patch for lazy imports (Phase 18-04 decision)
key_files:
  created:
    - backend/tests/test_scheduling_phase31.py
  modified: []
decisions:
  - "Tightened test_optimal_times_uses_stored_data assertion to reject generic heuristic reasons — 'peak engagement time for professionals' does not count; only explicit data-driven markers qualify"
  - "Used capture_insert_many pattern (async function replacing AsyncMock) to inspect call arguments with async context"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-12"
  tasks_completed: 1
  files_created: 1
  files_modified: 0
---

# Phase 31 Plan 01: Smart Scheduling Test Scaffold Summary

TDD test scaffold with 8 tests in RED state covering all 4 SCHD requirements before any production code changes — Nyquist compliance achieved.

## What Was Built

Created `backend/tests/test_scheduling_phase31.py` with 8 tests:

| Test | Requirement | Expected State | Actual State |
|------|-------------|---------------|--------------|
| test_optimal_times_uses_stored_data | SCHD-01 | FAIL (RED) | FAIL |
| test_optimal_times_falls_back_to_heuristics_when_no_stored_data | SCHD-01 regression | PASS (green guard) | PASS |
| test_optimal_times_returns_correct_count | SCHD-01 regression | PASS (green guard) | PASS |
| test_schedule_content_creates_scheduled_posts_doc | SCHD-02 | FAIL (RED) | FAIL |
| test_schedule_content_one_doc_per_platform | SCHD-02 | FAIL (RED) | FAIL |
| test_calendar_endpoint_exists | SCHD-03 | FAIL (RED) | FAIL |
| test_calendar_endpoint_month_filter | SCHD-03 | FAIL (RED) | FAIL |
| test_reschedule_creates_new_record | SCHD-04 | FAIL (RED) | FAIL |

**Result: 6 FAILED, 2 PASSED — RED state confirmed.**

## Verification Command

```bash
cd /Users/kuldeepsinhparmar/thookAI-production/backend && pytest tests/test_scheduling_phase31.py -v
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tightened SCHD-01 test assertion**
- **Found during:** Task 1 verification (RED state check)
- **Issue:** Original assertion checked `"engagement" in reason.lower()` — this matched the generic heuristic reason "peak engagement time for professionals" even when stored data was NOT used, causing test_optimal_times_uses_stored_data to PASS (false green)
- **Fix:** Tightened assertion to only accept explicit data-driven markers: "based on your data", "your data", "historical", "your posting history", `data_driven=True` flag, or `source` field set to "stored"/"historical"
- **Files modified:** backend/tests/test_scheduling_phase31.py
- **Commit:** 502e76b

## Unexpected Findings

- The current `get_optimal_posting_times` generates reasons like "Tuesday morning is peak engagement time for professionals (optimal day)" which contains the word "engagement" — naive string matching would cause false greens in the SCHD-01 test
- The calendar endpoint URL `/schedule/calendar` conflicts with a wildcard pattern in existing routes returning HTTP 405 (Method Not Allowed) instead of 404 — both indicate missing endpoint, RED state is confirmed regardless

## Files Created

- `/Users/kuldeepsinhparmar/thookAI-production/.claude/worktrees/agent-a7ed2d00/backend/tests/test_scheduling_phase31.py` (498 lines, 8 tests)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 502e76b | test(31-01): add failing test scaffold for SCHD-01 through SCHD-04 |

## Self-Check: PASSED

- File exists: `backend/tests/test_scheduling_phase31.py` — FOUND
- Commit 502e76b — FOUND
- 6 FAILED, 2 PASSED (meets acceptance criteria: at least 5 FAILED) — CONFIRMED
- No import errors or syntax errors — CONFIRMED
