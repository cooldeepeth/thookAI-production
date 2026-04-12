---
phase: 31-smart-scheduling
verified: 2026-04-12T00:00:00Z
status: human_needed
score: 4/4 must-haves verified (automated); 1/4 success criteria needs human
human_verification:
  - test: "Open http://localhost:3000/dashboard/calendar and verify calendar grid loads from the new /schedule/calendar endpoint (check Network tab for the new request), month ChevronLeft/ChevronRight triggers a new API call, and a scheduled post card shows the 'Edit' (Clock icon) button"
    expected: "Calendar grid renders, month navigation fires new GET /api/dashboard/schedule/calendar?year=...&month=... requests, and post cards with status=scheduled show three buttons: Now, Edit, Trash"
    why_human: "Visual/interactive behavior — automated tests mock the DB, but the full browser stack (auth cookie, real backend, React rendering) requires human eyes to confirm the calendar grid is populated and the reschedule modal opens"
  - test: "Schedule a piece of content from ContentStudio, then verify in MongoDB that db.scheduled_posts now has a document for that job_id"
    expected: "db.scheduled_posts collection has one document per platform with schedule_id starting with 'sch_', status='scheduled', and correct user_id/job_id"
    why_human: "Requires a live MongoDB connection and a real authenticated session — automated tests mock the DB"
  - test: "With Celery Beat running (celery -A celery_app:celery_app beat), schedule a post for a time 5-10 minutes from now and wait for it to auto-publish"
    expected: "After Celery Beat fires process_scheduled_posts, the scheduled_posts document status changes to 'published' and published_at is within 2 minutes of the scheduled_at time"
    why_human: "SCHD-04 real-world reliability (Success Criterion 3) requires an actual running Celery Beat worker, a real Redis broker, and real social platform tokens — cannot be tested without the live infrastructure"
  - test: "Open a scheduled post card in the calendar, click 'Edit', change the date/time in the reschedule modal, and click 'Reschedule'"
    expected: "PATCH /api/dashboard/schedule/{schedule_id}/reschedule is called, toast 'Rescheduled' appears, modal closes, calendar refreshes showing the post at the new time"
    why_human: "Full modal interaction flow requires browser UI — automated tests verify the API contract but not the React state machine or modal UX"
---

# Phase 31: Smart Scheduling Verification Report

**Phase Goal:** The platform suggests AI-optimized posting times per platform based on user's engagement history, user can view all scheduled posts in a calendar view, and Celery Beat reliably publishes posts at their scheduled times.

**Verified:** 2026-04-12
**Status:** human_needed — all automated checks pass; 4 human verification items needed for real-world Celery/UI confirmation
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (derived from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | AI suggests optimal times from stored engagement data (or sensible default) | VERIFIED | `get_optimal_posting_times` reads `persona.optimal_posting_times`, returns `source="stored"`, `data_driven=True` flags; heuristic fallback verified for new users |
| 2 | Calendar view shows scheduled posts for a given month across platforms | VERIFIED | `GET /api/dashboard/schedule/calendar` endpoint exists in `dashboard.py` lines 602-673; reads `db.scheduled_posts` with month filter; ContentCalendar.jsx fetches from this endpoint with `currentMonth` dependency |
| 3 | schedule_content() populates scheduled_posts so Celery Beat can publish | VERIFIED | `schedule_content()` in `planner.py` lines 366-406 inserts one doc per platform into `db.scheduled_posts`; Celery Beat configured in `celeryconfig.py` with `process-scheduled-posts` running every 5 minutes |
| 4 | Rescheduling cancels old record and creates new scheduled_posts doc | VERIFIED | `PATCH /schedule/{schedule_id}/reschedule` in `dashboard.py` lines 676-772 atomically sets old doc status=cancelled and inserts new doc with new schedule_id; ownership verified |

**Score:** 4/4 automated truths verified

---

## Required Artifacts

| Artifact | Provides | Exists | Substantive | Wired | Status |
|----------|---------|--------|-------------|-------|--------|
| `backend/tests/test_scheduling_phase31.py` | TDD scaffold covering all 4 SCHD requirements | Yes (498 lines) | Yes (8 test functions) | Yes (imports agents.planner, routes.dashboard) | VERIFIED |
| `backend/agents/planner.py` | `schedule_content` dual-write + `get_optimal_posting_times` with stored data preference | Yes | Yes — `insert_many` at line 392, `optimal_posting_times` at line 127 | Yes — called by dashboard.py schedule endpoint | VERIFIED |
| `backend/routes/dashboard.py` | Calendar endpoint + reschedule endpoint | Yes | Yes — calendar at line 602, reschedule at line 676, `RescheduleRequest` at line 496 | Yes — mounted in server.py under /api/dashboard | VERIFIED |
| `frontend/src/pages/Dashboard/ContentCalendar.jsx` | Calendar grid using /schedule/calendar + reschedule modal | Yes | Yes — `fetchCalendarData` at line 60, `reschedulePost` at line 128, `rescheduleModal` state at line 49 | Yes — `useEffect` depends on `currentMonth`, Dialog modal wired to state | VERIFIED |

---

## Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `ContentCalendar.jsx::fetchCalendarData` | `GET /api/dashboard/schedule/calendar` | `apiFetch` with year/month params | WIRED | Line 66: `` `/api/dashboard/schedule/calendar?year=${year}&month=${month}` `` |
| `ContentCalendar.jsx::reschedulePost` | `PATCH /api/dashboard/schedule/{schedule_id}/reschedule` | PATCH `apiFetch` with `new_scheduled_at` | WIRED | Line 133: `` `/api/dashboard/schedule/${rescheduleModal.schedule_id}/reschedule` `` |
| `useEffect` | `fetchCalendarData` | `[currentMonth]` dependency | WIRED | Line 56-58: `useEffect(() => { fetchCalendarData(); }, [currentMonth])` |
| `dashboard.py::get_calendar_data` | `db.scheduled_posts` | `find` with year/month range filter | WIRED | Lines 624-642: lazy `_db = _db_module.db`, `_db.scheduled_posts.find(...)` |
| `dashboard.py::reschedule_post` | `db.scheduled_posts` | `update_one` (cancel) + `insert_one` (new) | WIRED | Lines 725-750: `_db.scheduled_posts.update_one(... status=cancelled ...)` then `_db.scheduled_posts.insert_one(new_doc)` |
| `dashboard.py::reschedule_post` | `db.content_jobs` | `update_one` (scheduled_at) | WIRED | Lines 755-758: `_db.content_jobs.update_one(...)` |
| `planner.py::schedule_content` | `db.scheduled_posts` | `insert_many` | WIRED | Lines 391-398: `await db.scheduled_posts.insert_many(scheduled_posts_docs)` |
| `planner.py::get_optimal_posting_times` | `db.persona_engines.optimal_posting_times` | `find_one` + `get("optimal_posting_times")` | WIRED | Lines 112, 127-128: `persona = await db.persona_engines.find_one(...)` then `stored_times = (persona or {}).get("optimal_posting_times", {})` |
| `celeryconfig.py::beat_schedule` | `tasks.scheduled_tasks.process_scheduled_posts` | Celery Beat crontab every 5 minutes | WIRED | Lines 41-46: `"process-scheduled-posts"` task configured with `crontab(minute="*/5")` |
| `scheduled_tasks.py::_process_scheduled_posts` | `db.scheduled_posts` | `find` query for due posts | WIRED | Line 266: `await _db.scheduled_posts.find({"scheduled_at": {"$lte": now}, "status": {"$in": ["pending", "scheduled"]}})` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `ContentCalendar.jsx` | `scheduledContent` | `GET /api/dashboard/schedule/calendar` → `db.scheduled_posts` | Yes — live MongoDB query filtered by user_id, year/month, status | FLOWING |
| `ContentCalendar.jsx` | `rescheduleModal.schedule_id` | `item.schedule_id` from calendar API response | Yes — schedule_id generated as `sch_{uuid}` by `planner.schedule_content` | FLOWING |
| `dashboard.py::get_calendar_data` | `posts` enriched | `db.scheduled_posts.find()` + `db.content_jobs.find()` batch enrichment | Yes — real DB queries, not hardcoded | FLOWING |
| `planner.py::get_optimal_posting_times` | `best_times` | `persona.optimal_posting_times` or `PLATFORM_PEAKS` heuristics | Yes — DB read path wired; `data_driven=True` flag distinguishes stored vs. heuristic | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 8 phase31 tests pass | `cd backend && pytest tests/test_scheduling_phase31.py -v` | 8 passed, 0 failed, 3 warnings (pymongo compression, multipart deprecation) | PASS |
| planner.py syntax valid | `cd backend && python3 -c "import agents.planner; print('OK')"` | Verified by test runner importing module successfully | PASS |
| dashboard.py syntax valid | `cd backend && python3 -c "from routes.dashboard import router; print('OK')"` | Verified by test runner successfully mounting the router via FastAPI TestClient | PASS |
| Celery Beat schedule configured | `grep beat_schedule backend/celeryconfig.py` | `process-scheduled-posts` task present, runs every 5 minutes | PASS |
| `insert_many` in planner.py | `grep insert_many backend/agents/planner.py` | Line 392: `await db.scheduled_posts.insert_many(scheduled_posts_docs)` | PASS |
| `optimal_posting_times` read in planner.py | `grep optimal_posting_times backend/agents/planner.py` | Lines 123, 124, 127, 128 — stored data path wired | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| SCHD-01 | 31-01, 31-02 | AI suggests optimal posting times per platform based on engagement patterns | SATISFIED | `get_optimal_posting_times` reads `persona.optimal_posting_times`, sorts by `avg_engagement_rate`, sets `source="stored"` and `data_driven=True`; falls back to `PLATFORM_PEAKS` for new users |
| SCHD-02 | 31-01, 31-03 | User can approve/modify suggested schedule | SATISFIED | `PATCH /api/dashboard/schedule/{schedule_id}/reschedule` atomically cancels old + creates new record; `ContentCalendar.jsx` reschedule modal with datetime-local input wired to PATCH call |
| SCHD-03 | 31-01, 31-03, 31-04 | Calendar view shows all scheduled posts across platforms | SATISFIED | `GET /api/dashboard/schedule/calendar` queries `db.scheduled_posts` by month, enriches with content preview; `ContentCalendar.jsx` fetches from this endpoint with `currentMonth` dependency |
| SCHD-04 | 31-01, 31-02 | Scheduled posts publish automatically at scheduled time via Celery Beat | SATISFIED (code) / NEEDS HUMAN (live verification) | `schedule_content()` inserts into `db.scheduled_posts`; Celery Beat configured with 5-minute `process_scheduled_posts` task that reads `scheduled_posts` and calls publisher; actual publish timing requires live Celery + Redis + social tokens |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ContentCalendar.jsx` | 72, 98, 120, 155, 185 | `console.error(...)` in catch blocks | Info | Expected in error handling paths; not a stub — these log real errors to the browser console. Per project conventions (no formal frontend logging library), acceptable but worth noting |
| `planner.py::_get_ai_reasoning` | 228-259 | Falls back silently if `openai_available()` returns False | Info | Not a stub — the fallback returns a sensible default string. LLM reasoning enhancement requires an OpenAI key which is optional |
| `ContentCalendar.jsx` | 58 | `useEffect` with `[currentMonth]` dependency but `fetchCalendarData` is not in the dependency array | Warning | ESLint react-hooks/exhaustive-deps would flag this. Does not break functionality (function is stable via closure) but is a minor React best-practice gap |

No blocker anti-patterns found. No TODOs, FIXMEs, placeholder returns, or hardcoded empty data arrays in the critical data paths.

---

## Human Verification Required

### 1. Calendar Grid Browser Visual Check

**Test:** Start backend (`uvicorn server:app --reload --port 8000`) and frontend (`npm start`), open `http://localhost:3000/dashboard/calendar`, open browser Network tab, and observe page load.
**Expected:** Calendar grid renders without blank screen or JS error. Network tab shows `GET /api/dashboard/schedule/calendar?year=YYYY&month=MM` returning 200. Month nav (ChevronLeft/ChevronRight) fires a new calendar request for the adjacent month.
**Why human:** Visual rendering, React state machine, auth cookie flow — cannot test programmatically without a running browser stack.

### 2. Scheduled Posts Appear in MongoDB After Scheduling

**Test:** Log in to the app, generate content in ContentStudio, approve it, and schedule it for any future time. Then connect to MongoDB and run `db.scheduled_posts.find({user_id: "<your_user_id>"}).pretty()`.
**Expected:** At least one document exists with `schedule_id` starting with `sch_`, `status: "scheduled"`, and the correct `job_id` and `platform` values.
**Why human:** Requires a live authenticated session writing to a real MongoDB instance.

### 3. Celery Beat Auto-Publish (SCHD-04 Live Verification)

**Test:** With Redis and Celery Beat running (`celery -A celery_app:celery_app beat -l info`), schedule a post for 5 minutes from now. Wait 5-7 minutes. Check `db.scheduled_posts` for `status: "published"` and `published_at` timestamp.
**Expected:** `published_at` is within 2 minutes of the original `scheduled_at`. Content job status changes to `published`.
**Why human:** SCHD-04 Success Criterion 3 requires live Celery Beat + Redis + social platform OAuth tokens. The code path is wired but real-world timing reliability cannot be asserted without the live infrastructure.

### 4. Reschedule Modal UX Flow

**Test:** Find a post with `status: "scheduled"` in the calendar. Click the "Edit" (Clock icon, blue) button. Verify the modal opens with the datetime-local input pre-filled with the current scheduled time. Change the date to tomorrow at the same time and click "Reschedule".
**Expected:** PATCH request fires to `/api/dashboard/schedule/{schedule_id}/reschedule`, toast "Rescheduled" appears, modal closes, calendar grid refreshes showing the post at the new time.
**Why human:** Modal open/close state, datetime-local input interaction, and toast rendering require browser UI verification.

---

## Gaps Summary

No gaps blocking goal achievement for the automated/code aspects of the phase. All 4 SCHD requirements have implementation evidence:

- **SCHD-01**: `get_optimal_posting_times` reads stored engagement data with explicit `data_driven=True` flag — test passes GREEN.
- **SCHD-02**: `PATCH /schedule/{schedule_id}/reschedule` endpoint atomically cancels + creates new record — test passes GREEN. Frontend modal is wired.
- **SCHD-03**: `GET /schedule/calendar` endpoint queries `scheduled_posts` by month with enrichment — test passes GREEN. `ContentCalendar.jsx` uses this endpoint.
- **SCHD-04**: `schedule_content()` writes to `scheduled_posts`; Celery Beat configured with 5-minute task — tests pass GREEN.

The remaining human_needed items are:
1. Visual browser confirmation that the calendar renders correctly end-to-end
2. Live MongoDB verification that scheduling populates `scheduled_posts`
3. Live Celery Beat auto-publish timing verification (Success Criterion 3 is infrastructure-dependent)
4. Reschedule modal UX interaction

ROADMAP.md note: Plan 31-04 is marked `[ ]` (unchecked) despite the SUMMARY reporting completion and commits f5046ac + d9f0dcb. The code is on disk and verified. The ROADMAP checkbox may need manual update after human verification approves.

---

_Verified: 2026-04-12_
_Verifier: Claude (gsd-verifier)_
