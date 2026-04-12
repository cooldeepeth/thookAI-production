---
phase: 29-media-generation-pipeline
plan: 03
subsystem: backend/routes
tags: [bug-fix, r2-upload, sentry, voice-narration, media-generation, wave2]

# Dependency graph
requires:
  - 29-01 (Wave 0 regression tests for Bug 2)
provides:
  - Bug 2 fixed: voice narration uploads audio bytes to R2 and stores public URL
  - Bug 5 fixed: Sentry capture_exception wired in all three media except blocks
affects:
  - 29-02 (BUG-1 fix — media_tasks.py CreativeProvidersService)
  - 29-04 (BUG-4 fix — carousel Remotion wiring)
  - 29-05 (MDIA-08 — R2 presigned upload endpoints)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy sentry_sdk import inside 'if settings.app.sentry_dsn:' guard — matches server.py pattern, avoids ModuleNotFoundError in test environments"
    - "R2 bytes upload in sync voice path: decode audio_base64 → upload_bytes_to_r2() → store public URL; graceful fallback to data: URI when R2 unconfigured"
    - "add_credits() for refunds in except blocks — not deduct_credits(), which would double-charge"

key-files:
  created: []
  modified:
    - backend/routes/content.py
    - backend/tests/test_media_generation.py

key-decisions:
  - "Lazy sentry_sdk import (inside guard block) instead of top-level — sentry_sdk is in requirements.txt but not in test venvs; lazy import follows server.py precedent and avoids test-breaking ModuleNotFoundError"
  - "Use add_credits() for refunds in except blocks — deduct_credits() would subtract more credits, not refund them"
  - "R2 fallback: catch all exceptions from upload_bytes_to_r2, log warning, use data: URI only as last resort — no 503 raised, no double credit charge"
  - "Ported test_voice_narration_uploads_to_r2_not_data_uri from dev branch to worktree — Plan 29-01 commits only landed on dev branch, worktree is on separate branch"

# Metrics
duration: 4min
completed: 2026-04-12
---

# Phase 29 Plan 03: Voice Narration R2 Upload + Sentry Media Observability Summary

**Bug 2 fixed (voice narration stores R2 public URL not data: URI) and Bug 5 fixed (Sentry capture_exception wired in all three media endpoint except blocks) — regression test GREEN, 29/29 tests pass**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-12T07:31:02Z
- **Completed:** 2026-04-12T07:35:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Fixed Bug 2: `narrate_content()` sync path now decodes `audio_base64`, uploads bytes to R2 via `upload_bytes_to_r2()`, and stores the public URL in `content_jobs.audio_url` — MongoDB documents no longer bloated with base64 strings
- Fixed Bug 5: All three media except blocks (`generate_image`, `generate_carousel`, `narrate_content`) now call `sentry_sdk.capture_exception(exc)` guarded by `if settings.app.sentry_dsn:`
- Graceful R2 fallback: if upload fails (R2 not configured), logs a warning and falls back to data: URI — no 503 raised, no credits double-charged
- Returns modified result with stable R2 URL (strips `audio_base64` from response to avoid large payloads)
- Credit refund via `add_credits()` on all three media generation failures
- Bug 2 regression test `test_voice_narration_uploads_to_r2_not_data_uri` is GREEN
- Full test suite: 29/29 pass, 0 regressions

## Task Commits

1. **Task 1: Fix narrate_content() R2 upload + Sentry in all except blocks** - `1073cee` (fix)
2. **Task 2: Lazy sentry import + Bug 2 regression test GREEN** - `6010e69` (fix)

## Files Created/Modified

- `backend/routes/content.py` — Added `from config import settings`, lazy `import sentry_sdk` inside guards, R2 upload in narrate sync path, try/except with Sentry+credit-refund in all three media endpoints
- `backend/tests/test_media_generation.py` — Added `test_voice_narration_uploads_to_r2_not_data_uri` (ported from Plan 29-01 dev branch commits)

## Decisions Made

- **Lazy sentry_sdk import:** `sentry_sdk` is in `requirements.txt` but not installed in test venvs. Top-level `import sentry_sdk` caused `ModuleNotFoundError` when tests imported `routes.content`. Changed to lazy import inside each `if settings.app.sentry_dsn:` block — consistent with `server.py` pattern.
- **add_credits() for refunds:** Original plan template used `add_credits()`. `deduct_credits()` would deduct more credits (wrong direction). Fixed to `add_credits(user_id, amount, source, description)`.
- **R2 fallback strategy:** `upload_bytes_to_r2()` raises `HTTPException(503)` when R2 is unconfigured. Wrapped in try/except to catch all exceptions, log warning, and fall back to data: URI — plan requirement says no 503 propagated and no double-charge.
- **Worktree test porting:** Plan 29-01 added `test_voice_narration_uploads_to_r2_not_data_uri` to dev branch. This worktree is on a separate branch without those commits. Added the test directly to this worktree's test file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed sentry_sdk top-level import causing ModuleNotFoundError**
- **Found during:** Task 2 (running regression test)
- **Issue:** `import sentry_sdk` at module top level raised `ModuleNotFoundError` in test environment — package is in requirements.txt but not installed in test venv
- **Fix:** Removed top-level `import sentry_sdk`; added lazy `import sentry_sdk` inside each `if settings.app.sentry_dsn:` guard block, matching `server.py` pattern
- **Files modified:** `backend/routes/content.py`
- **Commit:** `6010e69`

**2. [Rule 1 - Bug] Fixed wrong function used for credit refund in except blocks**
- **Found during:** Task 1 (implementing except blocks)
- **Issue:** Used `deduct_credits(user_id, CreditOperation.X, source=..., description=...)` which has wrong signature (no `source` param) and wrong semantic (deducts more credits instead of refunding)
- **Fix:** Changed to `add_credits(user_id, CreditOperation.X.value, source=..., description=...)` which matches the `add_credits` signature and correctly refunds credits
- **Files modified:** `backend/routes/content.py`
- **Commit:** `1073cee` (updated in `6010e69`)

**3. [Rule 3 - Blocking] Ported Bug 2 regression test from dev branch to worktree**
- **Found during:** Task 2 (attempting to run test)
- **Issue:** `test_voice_narration_uploads_to_r2_not_data_uri` exists in dev branch (added by Plan 29-01 commits) but not in this worktree's branch
- **Fix:** Added the test directly to `backend/tests/test_media_generation.py` in the worktree
- **Files modified:** `backend/tests/test_media_generation.py`
- **Commit:** `6010e69`

## Known Stubs

None — all production fixes are complete. The R2 fallback to data: URI is intentional behavior when R2 is not configured, not a stub.

## Self-Check: PASSED

- FOUND: `backend/routes/content.py` — modified with R2 upload + Sentry
- FOUND: `backend/tests/test_media_generation.py` — Bug 2 regression test added
- FOUND: commit `1073cee` (Task 1)
- FOUND: commit `6010e69` (Task 2)
- Regression test: 1/1 PASSED
- Full test suite: 29/29 PASSED
