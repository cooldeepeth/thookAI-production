---
phase: "09"
plan: "03"
subsystem: backend/n8n-bridge
tags: [n8n, notifications, workflow-status, n8n-workflows, cron, scheduling]
dependency_graph:
  requires: [09-01, 09-02]
  provides: [workflow-status-notifications, n8n-workflow-json-files, n8n-import-documentation]
  affects: [backend/routes/n8n_bridge.py, backend/n8n_workflows/]
tech_stack:
  added: []
  patterns:
    - WORKFLOW_NOTIFICATION_MAP dict for user-facing workflow types
    - _dispatch_workflow_notification for per-user SSE notification dispatch
    - n8n workflow JSON template: Cron Trigger -> Execute Task -> Callback
key_files:
  created:
    - backend/n8n_workflows/cleanup-stale-jobs.json
    - backend/n8n_workflows/cleanup-old-jobs.json
    - backend/n8n_workflows/cleanup-expired-shares.json
    - backend/n8n_workflows/reset-daily-limits.json
    - backend/n8n_workflows/refresh-monthly-credits.json
    - backend/n8n_workflows/aggregate-daily-analytics.json
    - backend/n8n_workflows/process-scheduled-posts.json
    - backend/n8n_workflows/README.md
    - backend/tests/test_n8n_workflow_status.py
  modified:
    - backend/routes/n8n_bridge.py
decisions:
  - "WORKFLOW_NOTIFICATION_MAP excludes cleanup tasks — they are infrastructure ops, not user-visible events"
  - "process-scheduled-posts callback includes affected_user_ids from result.published_user_ids to close notification loop"
  - "Per-user notifications added in both execute endpoint (immediate) and callback handler (from n8n) to handle both direct and n8n-mediated calls"
  - "_dispatch_workflow_notification uses lazy import pattern (from services.notification_service import create_notification) consistent with other execute endpoints in n8n_bridge.py"
metrics:
  duration: "~22 minutes"
  completed_date: "2026-04-01"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 10
---

# Phase 09 Plan 03: Workflow Status Notifications + n8n Workflow JSON Files Summary

**One-liner:** Callback handler extended with WORKFLOW_NOTIFICATION_MAP + _dispatch_workflow_notification for user-facing SSE notifications, 7 importable n8n workflow JSON files with cron schedules matching original Celery beat, and 17-test suite verifying notification dispatch logic.

## What Was Built

### Task 1: Extend callback handler with workflow_status notifications (commit: be6daa1)

Added 3 modifications to `backend/routes/n8n_bridge.py`:

**1. WORKFLOW_NOTIFICATION_MAP dict**
- Maps 4 user-facing workflow types to notification title and body_template
- `process-scheduled-posts`, `reset-daily-limits`, `refresh-monthly-credits`, `aggregate-daily-analytics`
- Cleanup tasks excluded intentionally — they are infrastructure ops

**2. `_dispatch_workflow_notification` async function**
- Reads `workflow_type`, `status`, `result`, `affected_user_ids` from callback payload
- Skips silently if workflow not in map or no user IDs
- Prefixes title with `[Failed]` when status is "failed"
- Uses `body_template.format(**result)` for dynamic bodies
- Catches all exceptions per-user (logs warning, never raises)
- Lazy imports `create_notification` from `services.notification_service`

**3. Updated `n8n_callback` endpoint**
- Calls `_dispatch_workflow_notification(payload)` after signature verification
- Returns `{"status": "accepted", "workflow_type": workflow_type}` (added `workflow_type` field)
- Wraps dispatch in try/except so failures never block the callback response

**4. Updated `execute_process_scheduled_posts` endpoint**
- After publishing loop completes, notifies each user in `published_user_ids`
- Each notification: type=`workflow_status`, title="Scheduled posts processed"
- Exception per-user is caught and logged as warning

**Created `backend/tests/test_n8n_workflow_status.py`**
- 17 tests across 3 test classes, all passing
- `TestWorkflowStatusNotifications` — callback endpoint integration (3 tests)
- `TestDispatchWorkflowNotification` — unit tests for _dispatch_workflow_notification (7 tests)
- `TestWorkflowNotificationMap` — structural map validation (7 tests)
- Patching strategy: `services.notification_service.create_notification` at module level

### Task 2: Create n8n workflow JSON files for all 7 migrated tasks (commit: feeb59f)

**Created `backend/n8n_workflows/` directory with 7 workflow JSON files:**

| File | Cron | Task |
|------|------|------|
| cleanup-stale-jobs.json | `*/10 * * * *` | Mark stale running jobs as errored |
| cleanup-old-jobs.json | `0 2 * * *` | Delete 30-day-old failed jobs/sessions |
| cleanup-expired-shares.json | `30 2 * * *` | Deactivate expired persona shares |
| reset-daily-limits.json | `0 0 * * *` | Reset daily_content_count to 0 for all users |
| refresh-monthly-credits.json | `5 0 1 * *` | Refresh monthly credits per tier config |
| aggregate-daily-analytics.json | `0 1 * * *` | Upsert daily stats to db.daily_stats |
| process-scheduled-posts.json | `*/5 * * * *` | Publish due scheduled posts + notify users |

**Each workflow JSON contains:**
- Cron Trigger node with `n8n-nodes-base.scheduleTrigger` typeVersion 1.2
- Execute Task node: POST to `/api/n8n/execute/{task-name}` with HMAC-SHA256 header
- Callback node: POST to `/api/n8n/callback` with HMAC signature and result body
- `connections` mapping Cron Trigger → Execute Task → Callback

**Special case: process-scheduled-posts.json**
- Callback body includes `affected_user_ids` from `result.published_user_ids`
- Closes the notification loop: execute endpoint sends immediate per-user notification,
  callback handler sends another via _dispatch_workflow_notification

**Created `backend/n8n_workflows/README.md` (142 lines)**
- Import instructions: n8n UI step-by-step and REST API bash commands
- Workflow schedule map table with all 7 workflows, cron, frequency, original task
- HMAC signing explanation with Code node fallback for older n8n versions
- Cutover verification checklist
- Notification visibility documentation

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | be6daa1 | feat(09-03): extend callback handler with workflow_status notifications |
| 2 | feeb59f | feat(09-03): create 7 n8n workflow JSON files with cron schedules and HMAC signing |

## Deviations from Plan

None — plan executed exactly as written.

The plan specified testing using `HMAC signing test pattern from test_n8n_bridge.py`. The test file uses direct patching of `services.notification_service.create_notification` at module level (matching how the lazy import works), which is correct for the implementation pattern. Test approach matches behavior rather than copying patterns verbatim.

## Known Stubs

None. All notification dispatch logic calls real `create_notification` from `notification_service`. All 7 workflow JSON files contain real cron schedules and real endpoint URLs (parameterized via n8n env vars).

## Self-Check: PASSED

- FOUND: backend/routes/n8n_bridge.py (809 lines with WORKFLOW_NOTIFICATION_MAP and _dispatch_workflow_notification)
- FOUND: backend/tests/test_n8n_workflow_status.py (17 tests, all passing)
- FOUND: backend/n8n_workflows/ (7 JSON files + README.md)
- FOUND: commit be6daa1 (Task 1)
- FOUND: commit feeb59f (Task 2)
- VERIFIED: grep "workflow_status" backend/routes/n8n_bridge.py -- FOUND
- VERIFIED: grep "create_notification" backend/routes/n8n_bridge.py -- FOUND
- VERIFIED: ls n8n_workflows/*.json | wc -l == 7
- VERIFIED: all 7 JSON files parseable by json.load
- VERIFIED: all cron expressions correct
