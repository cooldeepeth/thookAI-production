---
phase: 11-multi-model-media-orchestration
plan: "04"
subsystem: media-orchestrator
tags: [media, orchestrator, carousel, talking_head, short_form_video, text_on_video, heygen, elevenlabs, luma, remotion, r2, credit-ledger, asyncio-gather]
dependency_graph:
  requires: [11-01, 11-02, 11-03]
  provides: [carousel handler, talking_head handler, short_form_video handler, text_on_video handler]
  affects: [backend/services/media_orchestrator.py, backend/tests/test_media_orchestrator.py]
tech_stack:
  added: []
  patterns:
    - "asyncio.gather for parallel multi-asset generation (carousel slides, SFV voice+avatar+broll)"
    - "Immediate R2 staging pattern for ephemeral CDN URLs (HeyGen video URLs expire ~1h)"
    - "_generate_voice_for_video wrapper for pcm_48000 intent isolation"
    - "Partial failure tolerance: asyncio.gather(return_exceptions=True) + skip failed slides/assets"
key_files:
  created: []
  modified:
    - backend/services/media_orchestrator.py
    - backend/tests/test_media_orchestrator.py
key-decisions:
  - "Carousel truncates to max 10 slides via brief.slides[:10] before any ledger entry"
  - "HeyGen video URL staged to R2 immediately after avatar generation — before returning to prevent CDN URL expiry"
  - "_generate_voice_for_video wrapper isolates pcm_48000 intent without modifying shared generate_voice_narration function"
  - "short_form_video credits_consumed calculated dynamically — only counts stages that successfully completed"
  - "text_on_video uses single remotion_render ledger stage — user provides the video, no generation cost"
patterns-established:
  - "Parallel asset generation via asyncio.gather(return_exceptions=True) with per-key ledger IDs"
  - "Immediate R2 staging of ephemeral provider URLs before any further pipeline steps"
  - "Fallback segment pattern: text-only segment if all video asset generation fails"
requirements-completed:
  - MEDIA-07
  - MEDIA-09
  - MEDIA-10
  - MEDIA-11
metrics:
  duration: 5min
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_modified: 2
---

# Phase 11 Plan 04: Complex Media Format Handlers Summary

**Carousel, talking_head, short_form_video, and text_on_video handlers wired through MediaOrchestrator with asyncio.gather parallel generation — all 8 media types now fully orchestrated.**

## Performance

- **Duration:** ~5 min (implementation was pre-built in prior session)
- **Started:** 2026-04-01T04:36:32Z
- **Completed:** 2026-04-01T04:41:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `_handle_carousel`: generates up to 10 slide images in parallel via `asyncio.gather`, stages all to R2, calls `ImageCarousel` Remotion composition
- `_handle_talking_head`: calls HeyGen avatar generation, stages video to R2 immediately (before any further steps), calls `TalkingHeadOverlay` composition
- `_handle_short_form_video`: orchestrates voice (ElevenLabs), avatar (HeyGen, optional), and B-roll (Luma) in parallel, stages all to R2, calls `ShortFormVideo` composition
- `_handle_text_on_video`: validates user-provided `video_url`, stages to R2, calls `ShortFormVideo` with text overlay segment
- 8 unit tests covering all 4 handlers — all 34 total tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement carousel, talking_head, short_form_video, text_on_video handlers** - `57aaeb7` (feat)
2. **Task 2: Unit tests for carousel and video format handlers** - `f0aa36a` (test)

## Files Created/Modified
- `backend/services/media_orchestrator.py` - Added `_generate_voice_for_video` wrapper plus 4 handlers: `_handle_carousel`, `_handle_talking_head`, `_handle_short_form_video`, `_handle_text_on_video`; `_MEDIA_TYPE_HANDLERS` now contains all 8 entries
- `backend/tests/test_media_orchestrator.py` - Added `TestCarouselHandler`, `TestTalkingHeadHandler`, `TestShortFormVideoHandler`, `TestTextOnVideoHandler` with 8 tests covering parallel generation, truncation, validation errors, and R2 staging patterns

## Decisions Made

- **Carousel max-10 truncation early**: `brief.slides[:10]` applied before ledger entry — no orphaned ledger records for truncated slides
- **Immediate HeyGen R2 staging**: HeyGen video URL staged inside the `try` block before `_ledger_update` — ensures staging always happens before the ledger is marked consumed
- **pcm_48000 isolation**: `_generate_voice_for_video` wrapper added to isolate the pcm_48000 intent comment without touching shared `generate_voice_narration` — future iteration can add `output_format` param to voice agent without changing the orchestrator call site
- **Dynamic credits_consumed for SFV**: Credits calculated as sum of stages that completed successfully — partial asset generation failures don't charge for failed stages

## Deviations from Plan

None — plan executed exactly as written. The implementation was already committed by a prior parallel agent in the same wave; this agent verified the verification criteria and test results, confirmed all 34 tests pass, and produced this SUMMARY.

## Known Stubs

None. All handlers call real provider interfaces (via lazy imports to `agents/voice.py`, `agents/video.py`, `agents/designer.py`) with correct parameters. Test mocking is test-only and does not affect production code paths.

## Self-Check: PASSED

Files exist:
- FOUND: backend/services/media_orchestrator.py
- FOUND: backend/tests/test_media_orchestrator.py

Commits exist:
- FOUND: 57aaeb7 (feat(11-04): implement carousel, talking_head, short_form_video, text_on_video handlers)
- FOUND: f0aa36a (test(11-04): add unit tests for carousel and video format handlers)

Tests: 34 passed, 0 failed
