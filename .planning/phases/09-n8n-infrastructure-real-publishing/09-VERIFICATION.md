---
phase: 09-n8n-infrastructure-real-publishing
verified: 2026-04-01T00:00:00Z
status: human_needed
score: 4/5 success criteria verified
re_verification: false
human_verification:
  - test: "Trigger process-scheduled-posts with a real OAuth-connected account and a post due for publishing"
    expected: "Post status transitions scheduled -> processing -> published in MongoDB; LinkedIn/X/Instagram shows the post; n8n execution log shows publish node completing"
    why_human: "Requires live OAuth tokens for a social platform, a running n8n instance, and an external API call — cannot simulate programmatically"
  - test: "Navigate to Dashboard while a post is being published by n8n (status = processing) and observe the UI"
    expected: "User sees a live countdown or polling indicator showing the publish is in progress, NOT just a static status badge"
    why_human: "Success Criterion 1 requires 'countdown/polling state visible in UI' — no dedicated live-status UI component was found; only the notification bell delivers workflow_status notifications after completion. Needs a human to confirm whether the notification-on-completion pattern satisfies the intent or if a real-time indicator is required."
---

# Phase 9: n8n Infrastructure + Real Publishing Verification Report

**Phase Goal:** All scheduled operations run through observable n8n workflows with verified webhook contracts and a clean Celery cutover
**Verified:** 2026-04-01
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can see live workflow status for any in-progress publishing or analytics operation (countdown/polling state visible in UI) | ? UNCERTAIN | NotificationBell + SSE stream delivers workflow_status notifications after completion. No dedicated countdown/polling indicator found in frontend. ContentCalendar has no "processing" status style. Needs human to confirm intent coverage. |
| 2 | A scheduled post reaches LinkedIn/X/Instagram via n8n workflow — n8n execution log shows publish node completing | ? UNCERTAIN | Code path is complete: n8n workflow JSON -> /api/n8n/execute/process-scheduled-posts -> agents.publisher.publish_to_platform -> real LinkedIn/X/Instagram API. Cannot verify end-to-end without live OAuth tokens and running n8n. |
| 3 | All previously Celery-beat tasks run on schedule via n8n and not Celery beat | ✓ VERIFIED | beat_schedule = {} confirmed. 7 n8n workflow JSONs with correct cron schedules. No celery-beat service in docker-compose. |
| 4 | Submitting the same publish operation twice within 2 minutes produces exactly one social post | ✓ VERIFIED | find_one_and_update atomic claim + 2-minute published_at check in /execute/process-scheduled-posts. 4 idempotency tests pass. |
| 5 | Image/video generation tasks still run via Celery (Motor-coupled) — no regression on media generation | ✓ VERIFIED | media_tasks.py has 5 @shared_task decorators unchanged. task_routes in celeryconfig.py preserved: media/video/content queues. Celery worker still in Procfile. |

**Score:** 3/5 truths automatically verified, 2/5 need human confirmation

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/config.py` | N8nConfig dataclass with 7 workflow ID fields + is_configured() | ✓ VERIFIED | N8nConfig at line 218 with n8n_url, webhook_secret, api_key, backend_callback_url, 7 workflow_* fields, is_configured() method. Settings.n8n field at line 274. |
| `backend/routes/n8n_bridge.py` | 9 endpoints: callback, trigger, 7 execute | ✓ VERIFIED | 810 lines. All 9 routes confirmed: /n8n/callback, /n8n/trigger/{workflow_name}, /n8n/execute/cleanup-stale-jobs, /n8n/execute/cleanup-old-jobs, /n8n/execute/cleanup-expired-shares, /n8n/execute/reset-daily-limits, /n8n/execute/refresh-monthly-credits, /n8n/execute/aggregate-daily-analytics, /n8n/execute/process-scheduled-posts. |
| `backend/celeryconfig.py` | beat_schedule = {} + task_routes preserved | ✓ VERIFIED | beat_schedule confirmed empty {}. task_routes preserves media/video/content queue routing for 4 task patterns. |
| `backend/Procfile` | Exactly 2 processes (web + worker, no beat) | ✓ VERIFIED | 2 lines: web: uvicorn server:app, worker: celery -A celery_app:celery_app worker. No beat line. |
| `docker-compose.yml` | n8n + postgres-n8n + n8n-worker services, no celery-beat | ✓ VERIFIED | n8n (n8nio/n8n:stable), n8n-worker (N8N_PROCESS_TYPE=worker), postgres-n8n (postgres:15-alpine) with n8n_postgres_data volume. No celery-beat service. |
| `backend/n8n_workflows/process-scheduled-posts.json` | n8n workflow with correct cron + HMAC | ✓ VERIFIED | Cron */5 * * * *, /api/n8n/execute/process-scheduled-posts URL, X-ThookAI-Signature header, /api/n8n/callback node present. |
| `backend/n8n_workflows/README.md` | Import instructions + 7-row schedule map | ✓ VERIFIED | 142 lines. Contains import via UI and REST API, 7-row schedule table, HMAC signing documentation, verification checklist. |
| `backend/tests/test_n8n_bridge.py` | HMAC + callback + trigger unit tests | ✓ VERIFIED | 288 lines. 12 tests across TestHmacVerification, TestN8nCallback, TestN8nTrigger. All 12 pass. |
| `backend/tests/test_celery_cutover.py` | Beat removal + Procfile + Docker + idempotency tests | ✓ VERIFIED | 373 lines. 22 tests across TestCeleryBeatRemoval, TestProcfile, TestDockerCompose, TestIdempotency. 21 pass, 1 skipped (PyYAML absent, covered by string-based alternatives). |
| `backend/tests/test_n8n_workflow_status.py` | Workflow status notification tests | ✓ VERIFIED | 351 lines. 17 tests across TestWorkflowStatusNotifications, TestDispatchWorkflowNotification, TestWorkflowNotificationMap. All 17 pass. |
| `backend/.env.example` | N8N_* env vars documented | ✓ VERIFIED | N8N_URL, N8N_WEBHOOK_SECRET, N8N_API_KEY, N8N_BACKEND_CALLBACK_URL, 7 N8N_WORKFLOW_* vars, plus N8N_POSTGRES_PASSWORD, N8N_ENCRYPTION_KEY, N8N_WEBHOOK_URL for Docker. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/routes/n8n_bridge.py` | `backend/config.py` | `from config import settings; settings.n8n.*` | ✓ WIRED | Line 36: `from config import settings`. Line 54: `settings.n8n.webhook_secret`. No os.environ.get() in route file. |
| `backend/server.py` | `backend/routes/n8n_bridge.py` | `api_router.include_router(n8n_bridge_router)` | ✓ WIRED | Line 51: `from routes.n8n_bridge import router as n8n_bridge_router`. Line 300: `api_router.include_router(n8n_bridge_router)`. |
| `backend/routes/n8n_bridge.py` | `backend/agents/publisher.py` | `from agents.publisher import publish_to_platform as real_publish_to_platform` | ✓ WIRED | Line 34: module-level import. Line 735: called in execute_process_scheduled_posts. D-09 compliance confirmed. |
| `backend/routes/n8n_bridge.py` | `backend/database.py` | `from database import db` (lazy imports in each execute endpoint) | ✓ WIRED | Each execute endpoint imports `from database import db` at function entry. Pattern consistent with CLAUDE.md convention. |
| `backend/routes/n8n_bridge.py` | `backend/services/notification_service.py` | `create_notification(user_id, type='workflow_status', ...)` | ✓ WIRED | Line 130: lazy import inside `_dispatch_workflow_notification`. Line 787: lazy import in `execute_process_scheduled_posts`. Two call sites for workflow_status notifications. |
| `backend/n8n_workflows/*.json` | `backend/routes/n8n_bridge.py` | HTTP Request node POSTs to `/api/n8n/execute/{task_name}` | ✓ WIRED | All 7 JSON files contain `/api/n8n/execute/` in Execute Task node URL and `/api/n8n/callback` in Callback node URL. X-ThookAI-Signature header present in all. |
| `backend/celeryconfig.py` | `backend/tasks/media_tasks.py` | task_routes routes media tasks to media/video queues | ✓ WIRED | task_routes contains `tasks.media_tasks.generate_video*` -> video, `tasks.media_tasks.*` -> media. Content tasks still routed. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `execute_process_scheduled_posts` | `due_posts` | `db.scheduled_posts.find({"status":"scheduled","scheduled_at":{"$lte":now}})` | Yes — real MongoDB query | ✓ FLOWING |
| `execute_process_scheduled_posts` | `token` | `db.platform_tokens.find_one({"user_id":..., "platform":...})` | Yes — real OAuth token lookup | ✓ FLOWING |
| `execute_process_scheduled_posts` | `result` (publish result) | `real_publish_to_platform()` -> LinkedIn/X/Instagram API | Yes — real API call (cannot test without OAuth) | ? FLOWING (human needed) |
| `_dispatch_workflow_notification` | `affected_user_ids` | Callback payload from n8n | Depends on n8n sending `affected_user_ids` in callback body | ? FLOWING (human needed) |
| `NotificationBell` | `notifications` | `GET /api/notifications?limit=N` then SSE stream | Yes — real DB query in notification_service | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| N8nConfig accessible via settings.n8n with correct defaults | `python3 -c "from config import settings; assert settings.n8n.n8n_url == 'http://n8n:5678'; assert not settings.n8n.is_configured()"` | Passed | ✓ PASS |
| All 9 n8n_bridge routes registered | `python3 -c "from routes.n8n_bridge import router; print(len(router.routes))"` | 9 routes | ✓ PASS |
| beat_schedule is empty | `python3 -c "import celeryconfig; assert celeryconfig.beat_schedule == {}"` | Passed | ✓ PASS |
| Procfile has exactly 2 processes, no beat | `cat Procfile` line count = 2, no "beat" substring | Passed | ✓ PASS |
| 7 n8n workflow JSON files exist and are valid JSON | `python3 -c "import json,glob; files=glob.glob('.../*.json'); assert len(files)==7"` | 7 files, all parse | ✓ PASS |
| All cron schedules match original Celery beat | Script checking each file for its expected cron expression | All 7 correct | ✓ PASS |
| test_n8n_bridge.py: 12 tests | `python3 -m pytest tests/test_n8n_bridge.py -x` | 12 passed | ✓ PASS |
| test_celery_cutover.py: 22 tests | `python3 -m pytest tests/test_celery_cutover.py -x` | 21 passed, 1 skipped (PyYAML) | ✓ PASS |
| test_n8n_workflow_status.py: 17 tests | `python3 -m pytest tests/test_n8n_workflow_status.py -x` | 17 passed | ✓ PASS |
| End-to-end publish via n8n workflow | Requires live n8n + OAuth | Not runnable | ? SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| N8N-01 | 09-01, 09-02, 09-03 | n8n self-hosted deployment with Docker (stable tag) + PostgreSQL 15 queue mode | ✓ SATISFIED | docker-compose.yml has n8nio/n8n:stable with DB_TYPE=postgresdb and EXECUTIONS_MODE=queue. postgres-n8n service with postgres:15-alpine. |
| N8N-02 | 09-01 | n8n webhook bridge — FastAPI triggers n8n workflows via POST, n8n calls back via HMAC-SHA256 authenticated endpoint | ✓ SATISFIED | /api/n8n/trigger/{workflow_name} (auth-protected httpx POST to n8n) and /api/n8n/callback (HMAC-SHA256 verified, hmac.compare_digest timing-safe) both implemented and tested. |
| N8N-03 | 09-02, 09-03 | Celery beat tasks migrated to n8n workflows — publishing, analytics polling, credit resets, cleanup jobs, strategist trigger, monthly credits | ✓ SATISFIED | 7 execute endpoints in n8n_bridge.py inline the DB logic from all 7 original Celery beat tasks. 7 matching n8n workflow JSON files. beat_schedule = {}. Note: "strategist trigger" was not a separate Celery beat task in the codebase — the 7 tasks cover all actual beat entries. |
| N8N-04 | 09-02 | Hard Celery→n8n cutover protocol with idempotency keys on all publish operations | ✓ SATISFIED | beat_schedule = {} in celeryconfig.py. Procfile has no beat line. process-scheduled-posts uses find_one_and_update (atomic claim) + 2-minute published_at check. |
| N8N-05 | 09-02 | Celery retained only for Motor-coupled media generation tasks | ✓ SATISFIED | task_routes preserved for media/video/content queues. media_tasks.py has 5 @shared_task decorators intact. Celery worker still in Procfile. |
| N8N-06 | 09-03 | User can see workflow status for in-progress operations | ? NEEDS HUMAN | WORKFLOW_NOTIFICATION_MAP + _dispatch_workflow_notification + NotificationBell SSE deliver post-completion notifications. No dedicated countdown/polling indicator for "in-progress" state. Human must confirm if notification-on-completion satisfies the "live status" intent. |

**Orphaned requirements check:** All 6 requirements (N8N-01 through N8N-06) are claimed by the three plans and accounted for above. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/NotificationBell.jsx` | 5-10 | `TYPE_ICONS` dict lacks `workflow_status` key — falls through to `TYPE_ICONS.system` (bell icon) | ℹ️ Info | workflow_status notifications display with a generic bell icon instead of a dedicated workflow icon. Functional but visually unspecific. |
| `frontend/src/pages/Dashboard/ContentCalendar.jsx` | 28-33 | `STATUS_STYLES` lacks `processing` entry — posts claimed by n8n's atomic claim fall through to default scheduled style | ⚠️ Warning | During the brief window when a post is in `processing` status, the calendar shows it as "Scheduled" (lime badge) rather than indicating in-progress. This is the closest observable gap for Success Criterion 1. |

No stubs, placeholders, or hardcoded empty data sources found in the phase's primary backend artifacts.

### Human Verification Required

#### 1. End-to-End n8n Publish Flow (Success Criterion 2)

**Test:** Start the Docker Compose stack (`docker-compose up`), import `backend/n8n_workflows/process-scheduled-posts.json` into n8n, create a scheduled post in the DB with `scheduled_at <= now` and a valid OAuth token in `platform_tokens`, manually trigger the workflow or wait for the 5-minute cron.

**Expected:** MongoDB shows the post transitioning `scheduled -> processing -> published`; the connected LinkedIn/X/Instagram account shows the published post; the n8n execution log shows the Execute Task node returning `{"status":"completed","result":{"published":1,...}}` and the Callback node responding 200.

**Why human:** Requires a running n8n instance, live OAuth tokens for a social platform, and external API calls. Cannot be verified programmatically in the local codebase.

#### 2. Live Workflow Status UI (Success Criterion 1)

**Test:** Observe the Dashboard UI while a post is being published by n8n (i.e., while the post has `status: "processing"` in MongoDB). Then check the notification bell after the workflow completes.

**Expected (per ROADMAP):** "countdown/polling state visible in UI" — a real-time indicator showing the publish is in progress, not just a completion notification.

**Actual implementation:** The notification bell shows `workflow_status` notifications after publish completion. The ContentCalendar shows `scheduled` badge (not `processing`) during the brief in-progress window because `STATUS_STYLES` has no `processing` entry.

**Why human:** The gap between "completion notification" and "live countdown/polling state" is a UX judgment call. The human must confirm whether N8N-06 / Success Criterion 1 is satisfied by the notification-bell pattern, or if a dedicated live-state indicator (e.g., animated spinner on the scheduled post card during processing) needs to be added.

---

## Gaps Summary

No hard gaps in the infrastructure implementation — all backend artifacts are substantive, wired, and tested (51 total tests, 50 pass, 1 skipped for PyYAML absence).

Two items require human judgment rather than code fixes:

1. **Success Criterion 1 / N8N-06** — The notification-based pattern delivers post-completion awareness. It does not deliver a real-time in-progress indicator. Whether this closes the criterion is a product decision. If a live indicator is required, the fix is: add a `processing` style to `STATUS_STYLES` in `ContentCalendar.jsx` and an auto-refresh (poll every 10 seconds) on the calendar when any post is in `processing` status.

2. **Success Criterion 2** — The code path is complete and real (no simulation stubs). Verification requires running the full stack with valid OAuth credentials.

---

_Verified: 2026-04-01_
_Verifier: Claude (gsd-verifier)_
