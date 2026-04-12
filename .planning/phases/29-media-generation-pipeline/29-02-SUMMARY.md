---
phase: 29-media-generation-pipeline
plan: 02
subsystem: backend/tasks
tags: [celery, media, bug-fix, agents, image, video, voice, carousel]

# Dependency graph
requires:
  - 29-01
provides:
  - Fixed Celery media generation tasks calling agent functions directly
  - No CreativeProvidersService references in media_tasks.py
  - Credit refund on failure for all 4 tasks
affects:
  - backend/tasks/media_tasks.py
  - All media generation when Redis/Celery is active

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy agent imports inside _generate() inner function (matching generate_video_for_job pattern)"
    - "result.get('generated') key check (not 'success') for agent return values"
    - "add_credits refund on exception — call in except block with separate try/except to avoid swallowing original error"

key-files:
  created: []
  modified:
    - backend/tasks/media_tasks.py
    - backend/tests/test_media_tasks_assets.py

key-decisions:
  - "Use result.get('generated') not result.get('success') — agent functions return 'generated' key per their documented interface"
  - "generate_carousel uses single designer_generate_carousel call instead of per-slide generate_image — cleaner and matches agent contract"
  - "Ported BUG-1 regression tests from dev branch 29-01 into worktree test file — worktree was at older commit before 29-01 tests were added"

# Metrics
duration: 3min
completed: 2026-04-12
---

# Phase 29 Plan 02: Fix CreativeProvidersService ImportError in Celery Media Tasks Summary

**Replaced 8 `CreativeProvidersService` references across 4 broken Celery tasks with direct agent function calls — matching the already-working `generate_video_for_job` pattern**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-12T07:29:22Z
- **Completed:** 2026-04-12T07:32:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed all `from services.creative_providers import CreativeProvidersService` and `service = CreativeProvidersService()` calls from 4 broken tasks
- `generate_video`: now calls `agents.video.generate_video` directly, checks `result.get("generated")`, adds credit refund on failure
- `generate_image`: now calls `agents.designer.generate_image` directly, checks `result.get("generated")`, adds credit refund on failure
- `generate_voice`: now calls `agents.voice.generate_voice_narration` directly, checks `result.get("generated")`, adds credit refund on failure
- `generate_carousel`: now calls `agents.designer.generate_carousel` with single call (not per-slide loop), adds credit refund on failure
- All 4 tasks preserve: retry decorators, `run_async(_generate())` wrapper, credit deduction, `db.media_assets.insert_one` persistence
- Both BUG-1 regression tests PASS: `test_celery_tasks_import_without_CreativeProvidersService` and `test_creative_providers_has_no_class`
- Full test suite (35 tests across `test_media_tasks_assets.py` + `test_media_generation.py`) passes with 0 failures

## Task Commits

1. **Task 1: Audit (no files modified)** — mental map of all CreativeProvidersService usages built before editing
2. **Task 2: Rewrite 4 broken Celery tasks** - `c1ea7e4` (fix)

## Files Created/Modified

- `backend/tasks/media_tasks.py` — 4 tasks rewritten to call agent functions directly; 8 CreativeProvidersService references removed
- `backend/tests/test_media_tasks_assets.py` — BUG-1 regression tests ported from dev branch (worktree was at pre-29-01 commit)

## Decisions Made

- **result.get("generated") not result.get("success"):** Agent functions (`generate_image`, `generate_video`, `generate_voice_narration`, `generate_carousel`) all return `"generated"` key per their documented interface. The old code incorrectly checked `"success"` which would always return `None`/falsy.
- **Single generate_carousel call:** Old code looped over slides calling `service.generate_image()` per slide. New code calls `designer_generate_carousel(topic, key_points, ...)` once — cleaner, matches agent contract, handles slide assembly internally.
- **Ported regression tests from dev branch:** The worktree was initialized at commit `1f4f6ef` (before plan 29-01's `89059cb` which added the regression tests to dev). Tests were ported into the worktree so the verification commands in the plan could run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added credit refund to generate_voice and generate_carousel**
- **Found during:** Task 2
- **Issue:** The worktree version of `generate_voice` and `generate_carousel` had no `add_credits` refund on failure (unlike `generate_video` which had it in the main repo, and `generate_video_for_job` which is the reference pattern)
- **Fix:** Added `add_credits` refund block in the `except` handler for all 4 tasks to match the `generate_video_for_job` pattern
- **Files modified:** `backend/tasks/media_tasks.py`
- **Commit:** `c1ea7e4`

**2. [Rule 3 - Blocking] Ported BUG-1 regression tests into worktree**
- **Found during:** Task 2 verification
- **Issue:** The regression tests `test_celery_tasks_import_without_CreativeProvidersService` and `test_creative_providers_has_no_class` were added by plan 29-01 to the dev branch (`89059cb`) but this worktree was created from an older commit (`1f4f6ef`) and didn't have them
- **Fix:** Appended the two test functions from the dev branch test file into the worktree's `test_media_tasks_assets.py`
- **Files modified:** `backend/tests/test_media_tasks_assets.py`
- **Commit:** `c1ea7e4`

## Known Stubs

None — all agent calls are wired to real agent functions. Agents themselves may fall back to mock responses if provider API keys are not configured (e.g., no `FAL_KEY`), but that is the agents' documented behavior, not a stub in this plan's code.

## Self-Check

Checking created files exist and commits are present.
