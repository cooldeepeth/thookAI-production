---
phase: 26-backend-endpoint-hardening
plan: "04"
subsystem: api
tags: [credits, refund, media, celery, fastapi, content-generation]

requires:
  - phase: 26-01
    provides: CSRF middleware double-submit cookie protection
  - phase: 26-02
    provides: Error format standardization and error_code envelope
  - phase: 26-03
    provides: Pydantic field constraints and input validation hardening

provides:
  - Credit refund on image generation failure (sync path, HTTP layer)
  - Credit refund on carousel generation failure (sync path, HTTP layer)
  - Credit refund on voice narration failure (sync path, HTTP layer)
  - Credit refund on video generation failure (sync path, HTTP layer)
  - Credit refund on image generation Celery task failure
  - Credit refund on video generation Celery task failure
  - Credit refund on voice generation Celery task failure

affects:
  - 26-backend-endpoint-hardening
  - billing
  - content-generation

tech-stack:
  added: []
  patterns:
    - "Atomic credit safety: try/except wraps generator call, add_credits refund on any Exception"
    - "Celery task refund: nested try/except in except block so refund failure never hides original error"
    - "Source-module patching: patch services.credits.deduct_credits/add_credits for tests with local imports"
    - "FastAPI auth bypass in tests: app.dependency_overrides[get_current_user] avoids CSRF middleware"

key-files:
  created: []
  modified:
    - backend/routes/content.py
    - backend/tasks/media_tasks.py
    - backend/tests/test_credit_refund_media.py

key-decisions:
  - "Patch services.credits.* (not routes.content.*) for tests because sync fallback paths use local function-level imports that bypass module-level patches"
  - "Use app.dependency_overrides[get_current_user] in tests instead of session cookie to bypass CSRF middleware"
  - "Refund calls in Celery tasks wrapped in nested try/except — original exception always re-raised"

patterns-established:
  - "Credit refund pattern: deduct_credits before agent call, add_credits in except block on failure"
  - "Distinct source strings per refund site enable MongoDB audit queries"

requirements-completed:
  - BACK-06

duration: 6min
completed: 2026-04-12
---

# Phase 26 Plan 04: Media Credit Refund Summary

**Try/except refund blocks added to all 4 sync HTTP media endpoint failure paths and all 3 Celery task failure paths, ensuring credits are always returned when generation fails**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-12T09:47:00Z
- **Completed:** 2026-04-12T09:53:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `add_credits` to the import chain in `routes/content.py` (top-level and 4 local imports in sync fallback paths)
- Wrapped `designer_generate()`, `designer_carousel()`, `generate_voice_narration()`, and `video_generate()` calls in try/except blocks — each refunds the correct credit amount on failure with a distinct audit source string
- Added `add_credits` refund calls to `generate_video`, `generate_image`, and `generate_voice` Celery task except blocks in `media_tasks.py` — each refund is wrapped in its own try/except so a refund failure never masks the original task error
- All 4 tests in `test_credit_refund_media.py` pass

## Task Commits

1. **Task 1: Add credit refund to sync media endpoint failure paths** - `bca0051` (feat)
2. **Task 2: Add credit refund to Celery media task failure paths** - `d2c5cc7` (feat)

## Files Created/Modified

- `backend/routes/content.py` - 4 sync generator calls wrapped in try/except with add_credits refund blocks; add_credits added to all imports
- `backend/tasks/media_tasks.py` - generate_video, generate_image, generate_voice except blocks now call add_credits with task-specific source strings
- `backend/tests/test_credit_refund_media.py` - Tests updated: switched from cookie-header CSRF auth to `app.dependency_overrides[get_current_user]`; patching at `services.credits.*` level to handle local function-scope imports

## Decisions Made

- **Source-module patching required:** The sync fallback paths in `content.py` use local `from services.credits import deduct_credits, add_credits, CreditOperation` inside the function body. These local imports create new references that bypass module-level patches on `routes.content.deduct_credits`. Patching `services.credits.deduct_credits` (the source) is the correct approach.
- **CSRF bypass via dependency_overrides:** The original test stubs used `Cookie: session_token=fakejwt` headers which triggered CSRF middleware (403 without X-CSRF-Token). Switching to `app.dependency_overrides[get_current_user]` skips cookie auth entirely — CSRF middleware only fires when a `session_token` cookie is present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test CSRF collision — pre-written tests used cookie auth without CSRF tokens**
- **Found during:** Task 1 (test execution, GREEN phase)
- **Issue:** The pre-written tests used `headers={"Cookie": "session_token=fakejwt"}` but didn't supply `csrf_token` cookie + `X-CSRF-Token` header. CSRF middleware returned 403, blocking the test from reaching the route handler.
- **Fix:** Replaced cookie-header auth pattern with `app.dependency_overrides[get_current_user]` (FastAPI dependency injection bypass). This avoids CSRF entirely since no session cookie is sent.
- **Files modified:** `backend/tests/test_credit_refund_media.py`
- **Verification:** All 4 tests return 500 (not 403) and `mock_refund.assert_called_once()` passes.
- **Committed in:** `bca0051` (Task 1 commit)

**2. [Rule 1 - Bug] Test module patching level — routes.content.deduct_credits patch ineffective**
- **Found during:** Task 1 (test execution, GREEN phase — tests returned 500 but mock_refund not called)
- **Issue:** Patching `routes.content.deduct_credits` doesn't affect the local `from services.credits import deduct_credits` inside function bodies — these create new bindings that bypass the module-level mock.
- **Fix:** Changed all credit-related patches from `routes.content.*` to `services.credits.*` (source module patching). This correctly intercepts all calls regardless of where the import happens.
- **Files modified:** `backend/tests/test_credit_refund_media.py`
- **Verification:** `mock_refund.assert_called_once()` passes for all 4 tests.
- **Committed in:** `bca0051` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs in pre-written test setup)
**Impact on plan:** Both fixes necessary for tests to correctly verify the implementation. The implementation code itself matched the plan exactly — only the test harness needed correction.

## Issues Encountered

None beyond the CSRF/patching issues documented in deviations above.

## Known Stubs

None. All 4 sync paths and all 3 Celery task paths now have real refund logic wired to `add_credits`.

## Next Phase Readiness

- BACK-06 verified: credits are now returned automatically on any media generation failure
- 7 distinct refund source strings enable future MongoDB audit queries: `image_generation_failure_refund`, `carousel_generation_failure_refund`, `voice_narration_failure_refund`, `video_generation_failure_refund`, `image_task_failure_refund`, `video_task_failure_refund`, `voice_task_failure_refund`
- Ready for Plan 05 (auth guard coverage) — no blockers

---
*Phase: 26-backend-endpoint-hardening*
*Completed: 2026-04-12*
