---
phase: 31-smart-scheduling
plan: "04"
subsystem: frontend
tags: [calendar, scheduling, reschedule, frontend, react]
dependency_graph:
  requires: ["31-02", "31-03"]
  provides: ["calendar-ui", "reschedule-modal"]
  affects: ["frontend/src/pages/Dashboard/ContentCalendar.jsx"]
tech_stack:
  added: []
  patterns: ["Dialog modal", "datetime-local input", "PATCH reschedule API"]
key_files:
  modified:
    - frontend/src/pages/Dashboard/ContentCalendar.jsx
decisions:
  - "Used datetime-local input (no new library) — pre-fills with current scheduled_at in local time offset"
  - "fetchCalendarData depends on currentMonth so month navigation auto-triggers re-fetch"
  - "rescheduleModal state stores schedule_id, platform, current_time — all needed for modal display and API call"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-12"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 1
---

# Phase 31 Plan 04: ContentCalendar Smart Scheduling Frontend Summary

**One-liner:** ContentCalendar.jsx wired to month-scoped /schedule/calendar endpoint with reschedule modal using PATCH /schedule/{schedule_id}/reschedule.

## What Was Built

Updated `frontend/src/pages/Dashboard/ContentCalendar.jsx` to complete the smart scheduling frontend:

### Change 1 — Replace data source (Task 1)
Replaced `fetchScheduledContent` (calling `/schedule/upcoming?limit=20`) with `fetchCalendarData` that calls:
```
GET /api/dashboard/schedule/calendar?year={year}&month={month}
```
The new endpoint returns `posts[]` (each with `schedule_id`, `job_id`, `platform`, `status`, `scheduled_at`, `preview`, `content_type`) sourced from `scheduled_posts` collection — the authoritative publishing state.

### Change 2 — Month-reactive useEffect (Task 1)
Changed `useEffect(() => { ... }, [])` to `useEffect(() => { ... }, [currentMonth])`. Clicking ChevronLeft/ChevronRight now triggers a new calendar API call for the navigated month.

### Change 3 — Refresh callbacks (Task 1)
Updated both `cancelScheduled` and `publishNow` to call `fetchCalendarData()` after success (previously called the removed `fetchScheduledContent`).

### Change 4 — Dialog import (Task 2)
Added `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogFooter` imports from `@/components/ui/dialog`. No new npm packages.

### Change 5 — Reschedule state (Task 2)
Added three state variables:
- `rescheduleModal` — null or `{schedule_id, platform, current_time}`
- `newScheduledAt` — string in datetime-local format
- `rescheduling` — boolean loading flag

### Change 6 — reschedulePost handler (Task 2)
New async function that:
1. Calls `PATCH /api/dashboard/schedule/{schedule_id}/reschedule` with `new_scheduled_at` ISO string
2. Shows success toast with new datetime
3. Clears modal state and re-fetches calendar

### Change 7 — "Edit" button on post cards (Task 2)
Added a blue Clock-icon "Edit" button between "Now" and the trash button for `status === "scheduled"` cards. Clicking pre-fills `newScheduledAt` from `item.scheduled_at` (converted to local datetime-local format) and opens the modal with `item.schedule_id`.

### Change 8 — Reschedule Dialog modal (Task 2)
Added modal at bottom of component return with:
- Platform name display
- `datetime-local` input pre-filled with current scheduled time
- Cancel and Reschedule buttons (Reschedule disabled until input has value)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | f5046ac | feat(31-04): replace calendar data source with /schedule/calendar endpoint |
| Task 2 | d9f0dcb | feat(31-04): add reschedule modal and wire schedule_id to post cards |

## Checkpoint Status

Task 3 is `checkpoint:human-verify` — awaiting visual verification of:
- Calendar grid loads from new endpoint
- Month navigation triggers new API call
- AI suggestion reason text displays
- Reschedule "Edit" button appears on scheduled post cards
- Reschedule modal opens, accepts new datetime, and submits PATCH request

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All data flows from live API endpoints (backend Plans 02 and 03).

## Self-Check: PASSED

- Modified file exists: `/Users/kuldeepsinhparmar/thookAI-production/.claude/worktrees/agent-af7b6f30/frontend/src/pages/Dashboard/ContentCalendar.jsx` ✓
- Commit f5046ac exists ✓
- Commit d9f0dcb exists ✓
- grep "schedule/calendar" returns 1 match ✓
- grep "fetchCalendarData" returns 4 matches ✓
- grep "fetchScheduledContent" returns 0 matches ✓
- grep "rescheduleModal" returns 5+ matches ✓
- grep "schedule_id" returns 2+ matches ✓
