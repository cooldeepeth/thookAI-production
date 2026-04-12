---
phase: 30-social-publishing-end-to-end
plan: "04"
subsystem: publishing
tags: [publisher, linkedin, x-twitter, instagram, media-upload, tdd]
dependency_graph:
  requires: [30-01, 30-02]
  provides: [linkedin-image-upload, x-image-upload, instagram-media-wiring-verified]
  affects: [backend/agents/publisher.py, backend/tests/test_publishing.py]
tech_stack:
  added: []
  patterns: [linkedin-register-upload, x-v1-media-upload, tdd-red-green]
key_files:
  created:
    - .planning/phases/30-social-publishing-end-to-end/VALIDATION.md
  modified:
    - backend/agents/publisher.py
    - backend/tests/test_publishing.py
decisions:
  - "LinkedIn registerUpload fallback: non-200 register response falls back to text-only rather than failing — ensures publishing always succeeds"
  - "X media upload uses v1.1 multipart upload (files= kwarg) then attaches media_id_string to first tweet body only"
  - "Instagram: no code change needed — publish_to_platform dispatcher already extracts image_url from media_assets; verified via TestPublishInstagramMediaWiring"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-12"
  tasks_completed: 2
  files_modified: 3
requirements:
  - PUBL-01
  - PUBL-02
  - PUBL-03
---

# Phase 30 Plan 04: Media Attachment for LinkedIn and X Publishers Summary

LinkedIn and X publishers now upload images from public R2 URLs and attach them to posts; Instagram wiring confirmed end-to-end via existing publish_to_platform dispatcher.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | LinkedIn image upload via registerUpload flow (TDD) | f4f9e49 | publisher.py, test_publishing.py |
| 2 | X media upload via v1.1 + Instagram wiring verification + VALIDATION.md | 9b25365 | publisher.py, test_publishing.py, VALIDATION.md |

## What Was Built

### Task 1: LinkedIn Image Upload (publisher.py)

Added `media_assets` media upload block to `publish_to_linkedin()` implementing the full LinkedIn UGC API image flow:

1. Fetch image bytes from `media_assets[0]["image_url"]` (public R2 URL) via `GET`
2. Call `POST https://api.linkedin.com/v2/assets?action=registerUpload` with recipe + owner URN
3. Extract `asset_urn` and `uploadUrl` from the response
4. `PUT` image bytes to `uploadUrl` with Bearer authorization
5. Set `shareMediaCategory = "IMAGE"` and populate `media` array in UGC post body

If `registerUpload` returns non-200: logs warning and falls back to `shareMediaCategory = "NONE"` (text-only). Text-only path fully preserved when `media_assets` is None or empty.

### Task 2: X Image Upload (publisher.py)

Added `media_assets` parameter to `publish_to_x()` implementing X v1.1 media upload:

1. Fetch image bytes from `media_assets[0]["image_url"]` via `GET`
2. `POST https://upload.twitter.com/1.1/media/upload.json` with `files={"media": image_bytes}`
3. Extract `media_id_string` from response
4. Add `"media": {"media_ids": [media_id]}` to first tweet payload only

Falls back to text-only if upload fails. Also updated `publish_to_platform` dispatcher and `publish_content` unified publisher to pass `media_assets` through to `publish_to_x`.

### Task 2: Instagram Wiring Verification

Confirmed `publish_to_platform` dispatcher already correctly extracts `image_url` from `media_assets` and passes it to `publish_to_instagram`. No code change required. `TestPublishInstagramMediaWiring` verifies the existing path end-to-end.

### Task 2: VALIDATION.md

Created `.planning/phases/30-social-publishing-end-to-end/VALIDATION.md` with all 8 per-task test command rows for Phase 30 plans (30-01 through 30-04) and the full phase gate command.

## Test Results

```
7 new tests added, all green:
- TestPublishLinkedInMedia (4 tests)
- TestPublishXMedia (2 tests)
- TestPublishInstagramMediaWiring (1 test)

Full suite: 71 passed, 0 failures
(tests/test_publishing.py + tests/test_platform_oauth.py + tests/test_analytics_social.py)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Tests adapted to actual function signatures**
- **Found during:** Task 1 RED phase
- **Issue:** Plan's test code used keyword arguments (`content=`, `access_token=`, `media_assets=`) that don't match the actual `publish_to_linkedin(user_id, content, media_assets, token)` signature
- **Fix:** Tests written to use correct positional/keyword args and pass `token="valid_token"` to bypass DB token lookup
- **Files modified:** backend/tests/test_publishing.py

**2. [Rule 2 - Missing functionality] publish_content unified publisher also needed media_assets wiring**
- **Found during:** Task 2 implementation
- **Issue:** `publish_content()` called `publish_to_x(user_id, content, is_thread)` without passing `media_assets`
- **Fix:** Updated to `publish_to_x(user_id, content, is_thread, media_assets=media_assets)`
- **Files modified:** backend/agents/publisher.py
- **Commit:** 9b25365

## Known Stubs

None — all media flows are wired to real API calls. Text-only fallback is intentional for resilience, not a stub.

## Self-Check: PASSED

Files verified:
- `backend/agents/publisher.py` — exists, contains registerUpload and media/upload
- `backend/tests/test_publishing.py` — exists, 1061 lines (min 520 required)
- `.planning/phases/30-social-publishing-end-to-end/VALIDATION.md` — exists, contains 30-01 through 30-04 rows

Commits verified:
- `f4f9e49` — Task 1 LinkedIn media upload
- `9b25365` — Task 2 X media + Instagram wiring + VALIDATION.md
