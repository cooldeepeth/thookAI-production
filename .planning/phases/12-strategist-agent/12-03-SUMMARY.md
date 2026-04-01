---
phase: 12-strategist-agent
plan: "03"
subsystem: api
tags: [n8n, strategist, notifications, workflow-bridge, hmac]

# Dependency graph
requires:
  - phase: 12-01
    provides: "StrategistConfig, N8nConfig.workflow_nightly_strategist, db.strategy_recommendations, run_strategist_for_all_users"
provides:
  - "POST /api/n8n/execute/run-nightly-strategist endpoint with HMAC auth"
  - "nightly-strategist entry in _get_workflow_map() mapped to settings.n8n.workflow_nightly_strategist"
  - "nightly-strategist entry in WORKFLOW_NOTIFICATION_MAP with user-facing title and body template"
affects: [n8n-cron-config, 12-04-strategy-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import pattern: from agents.strategist import run_strategist_for_all_users inside function body"
    - "Execute endpoint returns status/result/executed_at dict — consistent with all other n8n execute endpoints"
    - "WORKFLOW_NOTIFICATION_MAP entry enables _dispatch_workflow_notification to notify users when strategy cards are ready"

key-files:
  created: []
  modified:
    - backend/routes/n8n_bridge.py

key-decisions:
  - "nightly-strategist workflow map key (without 'run-' prefix) is consistent with other map keys; endpoint path uses /execute/run-nightly-strategist (with 'run-' prefix) matching n8n URL convention"
  - "Module docstring updated to list the new endpoint — keeps the file self-documenting and satisfies grep -c 'run-nightly-strategist' >= 2"

patterns-established:
  - "All new n8n execute endpoints follow: @router.post, async def, Depends(_verify_n8n_request), lazy import, return {status, result, executed_at}"

requirements-completed:
  - STRAT-01

# Metrics
duration: 2min
completed: "2026-04-01"
---

# Phase 12 Plan 03: n8n Bridge — Nightly Strategist Endpoint Summary

**n8n trigger path for the Strategist Agent wired in n8n_bridge.py: workflow map entry, notification map entry, and HMAC-authenticated execute endpoint calling `run_strategist_for_all_users`**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-01T06:31:06Z
- **Completed:** 2026-04-01T06:32:33Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `"nightly-strategist": settings.n8n.workflow_nightly_strategist` to `_get_workflow_map()` — workflow map grows from 7 to 8 entries
- Added `"nightly-strategist"` entry to `WORKFLOW_NOTIFICATION_MAP` with title "Your daily content strategy is ready" and body "New content recommendations are waiting for your review" — notification map grows from 4 to 5 entries
- Added `POST /api/n8n/execute/run-nightly-strategist` endpoint with `Depends(_verify_n8n_request)` HMAC auth and lazy import of `run_strategist_for_all_users` from `agents.strategist`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add nightly-strategist to workflow map and notification map** - `f01015b` (feat)
2. **Task 2: Add execute endpoint for run-nightly-strategist** - `74e7a60` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/routes/n8n_bridge.py` — Added workflow map entry (line 82), notification map entry (lines 110-113), execute endpoint (lines 817-842), and updated module docstring

## Decisions Made

- `nightly-strategist` (without `run-` prefix) used as the workflow map key to stay consistent with other map keys (`process-scheduled-posts`, `reset-daily-limits`, etc.). The endpoint path `/execute/run-nightly-strategist` uses the `run-` prefix to match n8n cron URL convention.
- Module docstring updated to list the new endpoint — keeps file self-documenting and ensures `grep -c "run-nightly-strategist" backend/routes/n8n_bridge.py` returns 2 (acceptance criteria).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The `N8N_WORKFLOW_NIGHTLY_STRATEGIST` env var is already declared in `backend/config.py` (added in Plan 01). The n8n operator must configure a cron workflow to call `POST /api/n8n/execute/run-nightly-strategist` at 03:00 UTC with the HMAC signature header.

## Next Phase Readiness

- n8n trigger path complete: workflow map + notification map + execute endpoint all wired
- n8n can now call `POST /api/n8n/execute/run-nightly-strategist` at 03:00 UTC to run the full Strategist pipeline
- Plan 04 (Strategy Dashboard frontend) can proceed — the backend API is fully ready

---
*Phase: 12-strategist-agent*
*Completed: 2026-04-01*
