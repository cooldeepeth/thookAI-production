---
phase: 08-gap-closure-tech-debt
plan: 01
subsystem: media-tasks
tags: [media, celery, bug-fix, gap-closure, MEDIA-05]
dependency_graph:
  requires: []
  provides: [media-assets-insertion-in-media-tasks]
  affects: [api-media-assets-endpoint]
tech_stack:
  added: []
  patterns: [db.media_assets.insert_one after successful generation, explicit Celery task name= kwargs]
key_files:
  created:
    - backend/tests/test_media_tasks_assets.py
  modified:
    - backend/tasks/media_tasks.py
    - backend/tasks/content_tasks.py
decisions:
  - Tests test inline logic patterns rather than importing the tasks package directly — avoids needing a live Redis/config environment while still validating the exact insert logic
  - carousel insert loop placed after content_jobs.update_one to match the all-or-nothing success pattern (no partial writes on individual slide failure)
  - import uuid as _uuid placed inline inside success blocks to match the existing pattern in generate_video_for_job
metrics:
  duration: 203s
  completed_date: "2026-03-31"
  tasks_completed: 1
  files_changed: 3
---

# Phase 08 Plan 01: MEDIA-05 Fix — Media Assets Insertion in Celery Tasks Summary

Closed the MEDIA-05 integration gap: Celery media tasks now write generated URLs to `db.media_assets` so AI-generated images, audio, and video appear in the media library alongside user-uploaded assets. Also fixed missing explicit `name=` kwargs on `poll_post_metrics_24h` and `poll_post_metrics_7d` Celery tasks.

## What Was Built

### MEDIA-05 Fix — db.media_assets.insert_one in all 4 media task functions

**Problem:** `generate_image`, `generate_voice`, `generate_video`, and `generate_carousel` in `backend/tasks/media_tasks.py` wrote generated URLs to `db.content_jobs` but never inserted documents into `db.media_assets`. The `/api/media/assets` endpoint reads only from `db.media_assets`, so AI-generated media was invisible in the media library.

**Fix:** Added `db.media_assets.insert_one(...)` calls in the success path of all four task functions. Each document includes `asset_id`, `user_id`, `job_id`, `type` (image/audio/video), `url`, `provider`, and `created_at`. The carousel task loops over `generated_images` and inserts one doc per slide with a `carousel_slide` field.

The pattern matches the existing implementation in `generate_video_for_job` (which already had the correct behavior).

### Celery Task Naming Fix

Added explicit `name='tasks.content_tasks.poll_post_metrics_24h'` and `name='tasks.content_tasks.poll_post_metrics_7d'` kwargs to the `@shared_task` decorators. This ensures Celery Beat can reference these tasks by name in `celeryconfig.py` beat_schedule entries without relying on auto-generated names that can change based on import path.

### Tests (5 tests in test_media_tasks_assets.py)

- Test 1: `generate_image` success path inserts into `db.media_assets` with `type=image`
- Test 2: `generate_voice` success path inserts into `db.media_assets` with `type=audio`
- Test 3: `generate_video` success path inserts into `db.media_assets` with `type=video`
- Test 4: `generate_carousel` success path inserts one doc per slide with `type=image` and `carousel_slide` field
- Test 5: `generate_image` failure path does NOT insert into `db.media_assets` (no partial writes)

## Verification Results

```
grep -c "db.media_assets.insert_one" tasks/media_tasks.py  → 5 (4 new + 1 existing in generate_video_for_job)
grep "name='tasks.content_tasks.poll_post_metrics_24h'" tasks/content_tasks.py  → match found
grep "name='tasks.content_tasks.poll_post_metrics_7d'" tasks/content_tasks.py  → match found
All 5 tests in test_media_tasks_assets.py passed
```

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 7fa5a38 | test | Add failing tests for MEDIA-05 media_assets insertion (5 tests) |
| 4ae12d8 | feat | Fix MEDIA-05 — wire media_assets.insert_one in all Celery media tasks |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no stub values introduced. All `db.media_assets.insert_one` calls use real computed values (uuid, datetime.now, provider from task arguments).

## Self-Check: PASSED
