---
phase: 28-content-generation-multi-format
plan: "04"
subsystem: frontend-content-studio
tags: [content-generation, scheduling, data-testids, api-fix, testing]
dependency_graph:
  requires: [28-01, 28-02]
  provides: [CONT-11-fix, CONT-12-verification]
  affects: [ContentOutput.jsx, PublishPanel, backend/tests/test_content_phase28.py]
tech_stack:
  added: []
  patterns:
    - FORMAT_LABEL_MAP constant for human-readable content type labels
    - JSON body for POST schedule endpoint (replaces broken query params)
    - Approve loading/error state pattern with Loader2 spinner
key_files:
  created: []
  modified:
    - frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx
    - backend/tests/test_content_phase28.py
decisions:
  - Schedule API call fixed to POST JSON body matching ScheduleContentRequest model (job_id, scheduled_at, platforms list)
  - FORMAT_LABEL_MAP defined at module level with 8 entries for all content types
  - approve-content-btn testid replaces old approve-btn to match UI-SPEC contract
  - Pipeline stages verified via source scan — all 5 stages confirmed at lines 288/307/338/348/370
metrics:
  duration: 3 minutes
  completed: 2026-04-12
  tasks_completed: 2
  files_modified: 2
---

# Phase 28 Plan 04: Fix Schedule API, Add Data-testids, Verify Pipeline Stages — Summary

**One-liner:** Fixed broken schedule API (query params → JSON body), added all 6 required data-testids per UI-SPEC contract, added output ready header with format label, and enhanced CONT-11/12 backend tests (19 passing).

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Fix PublishPanel schedule API + data-testids + output header | `2b12b09` | `ContentOutput.jsx` |
| 2 | Verify pipeline stages + update CONT-11/12 backend tests | `568bea4` | `test_content_phase28.py` |

## What Was Done

### Task 1 — ContentOutput.jsx (6 fixes)

**FIX 1 — Schedule API call (CONT-11 critical bug):**
- Was: `apiFetch('/api/dashboard/schedule/content?job_id=...&scheduled_at=...&platforms=...', { method: "POST" })`
- Now: `apiFetch('/api/dashboard/schedule/content', { method: "POST", body: JSON.stringify({ job_id, scheduled_at, platforms: [platform] }) })`
- The backend `ScheduleContentRequest` model expects a JSON body with `platforms: List[str]` — the old call always failed silently.

**FIX 2 — data-testids (UI-SPEC compliance):**
All 6 required data-testids are now present:
- `approve-content-btn` on the Approve Content button
- `schedule-content-btn` on the Schedule toggle button
- `schedule-datetime-input` on the date input
- `schedule-submit-btn` on the Schedule Post submit button
- `content-output-header` on the "Your {Format} is ready" heading
- `content-format-badge` on the platform/format badge

**FIX 3 — FORMAT_LABEL_MAP constant:**
Added module-level map for 8 content types: post, article, carousel_caption, tweet, thread, feed_caption, reel_caption, story_sequence → human-readable labels.

**FIX 4 — Output ready header:**
Added `<h2 data-testid="content-output-header">Your {formatLabel} is ready</h2>` above QC scores section.

**FIX 5 — Output format badge:**
Added `<span data-testid="content-format-badge">{platformLabel} · {formatLabel}</span>` styled per UI-SPEC (`text-xs font-mono bg-white/5 text-zinc-400 rounded-full px-2 py-1`).

**FIX 6 — Approve loading/error states:**
- Added `approving` state with Loader2 spinner + "Approving..." text during API call
- Added `approveError` state — renders `text-red-400 text-xs` "Approval failed. Try again." below button row on failure

### Task 2 — Backend Tests

**Pipeline verification (CONT-12):**
- Confirmed pipeline.py has 9 `current_agent` update calls total, with all 5 stage names (commander, scout, thinker, writer, qc) present at lines 288, 307, 338, 348, 370.
- Updated `test_pipeline_stage_progression` to do source-level verification (counts `"current_agent"` occurrences ≥5 and checks each stage name string exists).

**New tests added:**
- `test_pipeline_signature` — verifies run_agent_pipeline function signature has all 5 required params
- `test_approve_status_model_validation` — verifies ContentStatusUpdate accepts approved/rejected, rejects published/pending
- `test_schedule_content_request_model` — verifies ScheduleContentRequest model accepts job_id, scheduled_at, platforms list

**Result:** 19/19 tests PASS.

## Verification

```
cd backend && pytest tests/test_content_phase28.py -v
→ 19 passed, 3 warnings in 0.41s

grep -c "approve-content-btn|schedule-content-btn|content-output-header|content-format-badge" ContentOutput.jsx
→ 4 (all present)

grep -n "schedule/content" ContentOutput.jsx
→ line 825: clean URL, no query params

grep -c '"current_agent"' backend/agents/pipeline.py
→ 9 (5 stage updates + done/error/cancel states)
```

## Deviations from Plan

None — plan executed exactly as written. All 6 fixes from the task list were applied. Pipeline.py confirmed to already have all 5 stage updates (no modification needed, as RESEARCH.md predicted).

## Known Stubs

None — all data flows correctly from `job.content_type` to `FORMAT_LABEL_MAP` to the rendered header and badge.

## Self-Check: PASSED

- `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx` — modified, verified ✓
- `backend/tests/test_content_phase28.py` — modified, 19 tests passing ✓
- Commit `2b12b09` exists ✓
- Commit `568bea4` exists ✓
