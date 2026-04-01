---
phase: 11
plan: 02
subsystem: media-orchestration
tags: [media, orchestration, celery, r2, remotion, credits, ledger]
dependency_graph:
  requires:
    - backend/config.py (Settings, R2Config)
    - backend/services/media_storage.py (get_r2_client)
    - backend/services/credits.py (CreditOperation)
    - backend/database.py (db)
  provides:
    - MediaBrief dataclass (all 8 media types)
    - pipeline credit ledger (write-before-call guarantee)
    - R2 pre-staging (base64 + HTTP URL download)
    - Remotion client (POST + poll with timeout)
    - orchestrate() dispatch function
    - POST /api/media/orchestrate endpoint
    - orchestrate_media_job Celery task
    - media_pipeline_ledger indexes
  affects:
    - backend/routes/media.py (new endpoint)
    - backend/tasks/media_tasks.py (new task)
    - backend/db_indexes.py (new collection)
tech_stack:
  added:
    - httpx (AsyncClient for R2 staging downloads + Remotion polling)
    - asyncio.wait_for (Remotion 300s timeout)
    - asyncio.gather (parallel R2 staging)
  patterns:
    - lazy import pattern (agents.designer, agents.voice, agents.video via _get_* functions)
    - register_media_handler decorator (Plans 03-04 extend the dispatch table)
    - write-before-call ledger guarantee (pending entry before every provider call)
    - dev fallback pattern (/tmp staging with warning when R2 not configured)
key_files:
  created:
    - backend/services/media_orchestrator.py
    - backend/tests/test_media_orchestrator.py
    - backend/tests/test_media_pipeline_ledger.py
  modified:
    - backend/config.py (RemotionConfig + settings.remotion)
    - backend/services/credits.py (MEDIA_ORCHESTRATION = 25)
    - backend/routes/media.py (OrchestrateRequest + POST /orchestrate)
    - backend/tasks/media_tasks.py (orchestrate_media_job)
    - backend/db_indexes.py (media_pipeline_ledger indexes)
decisions:
  - get_r2_client imported at module-level in media_orchestrator.py (not inside function) so tests can patch services.media_orchestrator.get_r2_client
  - register_media_handler decorator pattern chosen for dispatch table extensibility — Plans 03-04 register handlers without touching orchestrate()
  - /tmp fallback in _stage_asset_to_r2 logs WARNING (not raises) to support dev environments without R2 — production should always have R2 configured
  - orchestrate_media_job max_retries=1 (vs 2-3 for other tasks) — media orchestration jobs are expensive and long-running, one retry is sufficient
metrics:
  duration: 328s
  completed: "2026-04-01T00:10:24Z"
  tasks: 2
  files: 8
  tests_added: 28
---

# Phase 11 Plan 02: MediaOrchestrator Foundation Summary

MediaOrchestrator service foundation built: MediaBrief dataclass, pipeline credit ledger with write-before-call guarantee, R2 pre-staging (base64 decode + HTTP download), Remotion sidecar client (POST + 5s poll + 300s timeout), and orchestrate() skeleton with extensible handler dispatch.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RemotionConfig + MediaBrief + pipeline credit ledger + MediaOrchestrator core | a465375 | config.py, credits.py, media_orchestrator.py, db_indexes.py |
| 2 | Orchestrate route + Celery task + unit tests | 7f090c4 | routes/media.py, tasks/media_tasks.py, 2 test files, media_orchestrator.py (import fix) |

## What Was Built

**MediaBrief dataclass** (`backend/services/media_orchestrator.py`):
- 14 fields covering all 8 media types (static_image, quote_card, meme, carousel, infographic, talking_head, short_form_video, text_on_video)
- MEDIA_TYPE_COST_CAPS dict: per-type credit limits (10-100 credits)
- STAGE_COSTS dict: per-stage credit costs (image 8, voice 12, avatar 50, broll 20, remotion_render 5)

**Pipeline Credit Ledger** (4 functions):
- `_ledger_stage`: writes pending entry to `media_pipeline_ledger` before any provider call — the write-before-call guarantee
- `_ledger_update`: transitions status to consumed/failed/skipped with completed_at timestamp
- `_ledger_check_cap`: MongoDB aggregation sum of consumed credits vs cost_cap
- `_ledger_skip_remaining`: update_many pending→skipped with reason on pipeline failure

**R2 Pre-staging** (2 functions):
- `_stage_asset_to_r2`: handles `data:` URL base64 decode and `http(s)://` URL download via httpx, uploads to R2 key `media/orchestrated/{job_id}/{asset_key}.{ext}`, falls back to /tmp with warning in dev
- `_stage_assets_to_r2`: parallel staging via asyncio.gather

**Remotion Service Client**:
- `_call_remotion`: POST to `/render` → poll `/render/{id}/status` every 5s → asyncio.wait_for(300s) → RuntimeError on failure/timeout

**orchestrate() function**:
- Validates media_type against MEDIA_TYPE_COST_CAPS (ValueError if unknown)
- Dispatches to registered handler (NotImplementedError if no handler — Plans 03-04 add them)
- Returns: {url, render_id, media_type, job_id, credits_consumed}

**POST /api/media/orchestrate**:
- OrchestrateRequest with field_validator on media_type and platform
- Loads persona_card from db.persona_engines, extracts brand_color
- Submits orchestrate_media_job.delay(brief.__dict__)
- Returns 202 with {job_id, status: "queued"}

**orchestrate_media_job Celery task**:
- max_retries=1, retry_delay=120s
- Reconstructs MediaBrief from dict
- Stores result in media_assets on success
- Updates content_jobs with error status on failure

**MongoDB Indexes** (`media_pipeline_ledger`):
- idx_job_id (for ledger queries per job)
- idx_user_created (user_id + created_at for history)
- idx_status_created (status + created_at for cleanup queries)

## Test Coverage (28 tests)

**test_media_pipeline_ledger.py** (12 tests):
- `_ledger_stage`: document shape, unique IDs, write-before-call order
- `_ledger_update`: consumed, failed with reason, skipped transitions
- `_ledger_check_cap`: under/at/over cap, empty aggregate
- `_ledger_skip_remaining`: pending-only filter, no-consumed-touch guarantee

**test_media_orchestrator.py** (16 tests):
- MediaBrief: required fields + defaults, optional fields, MEDIA_TYPE_COST_CAPS completeness/positivity
- `_stage_asset_to_r2`: HTTP URL (download + R2 upload + URL), base64 data: URL (decode + upload), unsupported scheme
- `_stage_assets_to_r2`: parallel staging, empty dict
- `_call_remotion`: success (queued→rendering→done), failed status, timeout
- `orchestrate()`: invalid type ValueError, unimplemented NotImplementedError, dispatch, coroutine check

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] get_r2_client import moved to module-level for testability**
- **Found during:** Task 2 test execution
- **Issue:** `_stage_asset_to_r2` used a local `from services.media_storage import get_r2_client` inside the function body; `patch("services.media_orchestrator.get_r2_client")` failed with AttributeError because the name wasn't on the module
- **Fix:** Added `from services.media_storage import get_r2_client` at module-level imports; removed local import inside function
- **Files modified:** backend/services/media_orchestrator.py
- **Commit:** 7f090c4

## Known Stubs

None — all functions are fully implemented. The dispatch table `_MEDIA_TYPE_HANDLERS` is intentionally empty (Plans 03-04 register handlers). `orchestrate()` raises `NotImplementedError` for unimplemented types — this is correct behavior, not a stub.

## Self-Check: PASSED

All files exist on disk and all commits are present in git history.
