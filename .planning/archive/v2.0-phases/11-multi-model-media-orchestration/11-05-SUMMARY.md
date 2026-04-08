---
phase: 11-multi-model-media-orchestration
plan: 05
subsystem: api
tags: [designer-agent, qc-agent, media-format-selection, media-validation, python, pytest]

requires:
  - phase: 11-04
    provides: carousel, talking_head, short_form_video, text_on_video handlers in media_orchestrator.py

provides:
  - PLATFORM_FORMAT_PREFERENCES dict with linkedin/instagram/x format tier tables
  - CONTENT_ANGLE_FORMAT_MAP dict with 8 content angles mapped to ranked format candidates
  - select_media_format() in designer.py: deterministic scoring, returns media_type + reason + alternatives + confidence
  - PLATFORM_MEDIA_SPECS dict with image/video dimension specs for 3 platforms
  - validate_media_output() in qc.py: 4-check validation (platform_dimensions, brand_consistency, anti_slop, file_format)
  - 23 unit tests across 2 test files covering happy paths, failure modes, edge cases

affects:
  - backend/agents/pipeline.py (can wire select_media_format before Writer step)
  - backend/services/media_orchestrator.py (select_media_format return feeds MediaBrief.media_type)
  - backend/routes/content.py (validate_media_output can be called post-render)

tech-stack:
  added: []
  patterns:
    - "Deterministic scoring table: platform-preference + angle-candidate + capability bonuses — no LLM call needed for format selection"
    - "Module-level import of anthropic_available in qc.py to enable patch() in unit tests"
    - "asyncio.run() for synchronous test helpers (not get_event_loop().run_until_complete())"

key-files:
  created:
    - backend/tests/test_designer_format_selection.py
    - backend/tests/test_qc_media.py
  modified:
    - backend/agents/designer.py
    - backend/agents/qc.py

key-decisions:
  - "select_media_format is deterministic (no LLM call) — scoring table gives stable, explainable results"
  - "anthropic_available imported at qc.py module level (not inside validate_media_output) so unit tests can patch it"
  - "anti_slop graceful pass when vision unavailable — QC does not block delivery when Anthropic key absent"
  - "validate_media_output dimension check is metadata-level only (no asset download) — pixel-level check deferred to vision path"

patterns-established:
  - "Format selection pattern: score all candidates via platform-pref + angle-map + capability tables, return ranked result with reason"
  - "Media QC pattern: always return 4 named checks with pass/detail; overall_pass = all checks pass; feedback = messages from failed checks"

requirements-completed:
  - MEDIA-12
  - MEDIA-14

duration: 7min
completed: 2026-04-01
---

# Phase 11 Plan 05: Designer Format Selection + QC Media Validation Summary

**Deterministic media format selection via scoring tables in designer.py and 4-check media validation (dimensions, brand, anti-slop, file-format) in qc.py with 23 unit tests.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-01T04:57:48Z
- **Completed:** 2026-04-01T05:04:27Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `select_media_format()` to `backend/agents/designer.py` — deterministic scoring via `PLATFORM_FORMAT_PREFERENCES` + `CONTENT_ANGLE_FORMAT_MAP` + capability bonuses (data_points, avatar, long content); returns media_type, reason, alternatives list, and 0-1 confidence score
- Added `validate_media_output()` to `backend/agents/qc.py` — 4-check validation: platform spec existence (dimensions), brand color metadata check, anti-AI-slop via Claude vision (graceful pass if unavailable), and file extension correctness
- 23 passing unit tests in 2 new files covering all acceptance criteria, edge cases, and graceful degradation paths

## Task Commits

1. **Task 1: Designer select_media_format() + QC validate_media_output()** - `29933f6` (feat)
2. **Task 2: Unit tests for format selection and media QC validation** - `e917849` (test)

## Files Created/Modified

- `backend/agents/designer.py` — added `PLATFORM_FORMAT_PREFERENCES`, `CONTENT_ANGLE_FORMAT_MAP`, `_ALL_MEDIA_TYPES`, `select_media_format()`
- `backend/agents/qc.py` — added `PLATFORM_MEDIA_SPECS`, `validate_media_output()`, module-level `anthropic_available` import, `typing` imports
- `backend/tests/test_designer_format_selection.py` — 11 tests for format selection
- `backend/tests/test_qc_media.py` — 12 tests for media QC validation

## Decisions Made

- `select_media_format` uses deterministic scoring (no LLM) — stable, explainable, no API cost
- `anthropic_available` moved to module-level import in qc.py to support `patch()` in tests
- `validate_media_output` dimension check is metadata-only (no asset download) — pixel-level check happens inside the anti_slop vision path when Anthropic key is available
- `asyncio.run()` used in test helpers instead of deprecated `get_event_loop().run_until_complete()`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved anthropic_available to module-level import in qc.py**
- **Found during:** Task 2 (unit tests)
- **Issue:** `anthropic_available` was imported inside `validate_media_output` function body; `patch("agents.qc.anthropic_available")` raised `AttributeError` because the module namespace didn't contain it
- **Fix:** Added `anthropic_available` to the module-level import line; removed local import inside function
- **Files modified:** `backend/agents/qc.py`
- **Verification:** All 23 tests pass including `test_anti_slop_passes_when_no_vision` which patches at module level
- **Committed in:** `e917849` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Minimal — necessary for tests to work correctly. No scope creep.

## Issues Encountered

None beyond the auto-fixed import issue above.

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

- `select_media_format()` ready to be wired into `backend/agents/pipeline.py` before the Writer/Designer step to auto-populate `MediaBrief.media_type`
- `validate_media_output()` ready to be called from content routes after Remotion renders complete
- Phase 11 complete — all 5 plans executed: media_orchestrator, static handlers, video handlers, carousel/talking_head handlers, format selection + QC

## Self-Check: PASSED

- FOUND: backend/agents/designer.py (select_media_format, PLATFORM_FORMAT_PREFERENCES, CONTENT_ANGLE_FORMAT_MAP)
- FOUND: backend/agents/qc.py (validate_media_output, PLATFORM_MEDIA_SPECS)
- FOUND: backend/tests/test_designer_format_selection.py (11 tests)
- FOUND: backend/tests/test_qc_media.py (12 tests)
- FOUND: .planning/phases/11-multi-model-media-orchestration/11-05-SUMMARY.md
- COMMITS: 29933f6 (feat), e917849 (test), 14de39c (docs) — all verified in git log

---
*Phase: 11-multi-model-media-orchestration*
*Completed: 2026-04-01*
