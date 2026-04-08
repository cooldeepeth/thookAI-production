---
phase: 06-media-generation-analytics
plan: 02
subsystem: media-storage
tags: [testing, r2, uploads, media-storage, tdd]
dependency_graph:
  requires: []
  provides: [MEDIA-04-verified, MEDIA-05-verified]
  affects: [backend/tests, backend/routes/uploads.py, backend/services/media_storage.py]
tech_stack:
  added: []
  patterns: [FastAPI dependency_overrides for auth mocking, patch() for R2/settings isolation]
key_files:
  created:
    - backend/tests/test_uploads_media_storage.py
  modified: []
decisions:
  - Use app.dependency_overrides[get_current_user] (not patch) for auth bypass in FastAPI tests
  - Build minimal FastAPI app per-test (not full server import) to avoid lifespan/DB side effects
  - patch routes.uploads._r2_client as callable (mock_r2_fn.return_value) not as value
metrics:
  duration: 5 minutes
  completed: 2026-03-31
  tasks_completed: 2
  files_modified: 1
  tests_added: 17
---

# Phase 06 Plan 02: Uploads and Media Storage Tests Summary

**One-liner:** 17 TDD tests proving R2 upload path, production 503 guard, /tmp dev fallback, presigned URL generation, and media asset R2 URL storage.

## Objective

Verify MEDIA-04 and MEDIA-05 requirements via automated tests. Both `uploads.py` and `media_storage.py` already had the correct code paths; this plan adds tests that prove them.

## Tasks Completed

### Task 1: R2 Upload Path and Production 503 Guard (TDD)

**7 tests added covering:**
1. R2 upload success — file goes to R2, URL starts with R2 public base, `put_object` called with correct bucket
2. Production 503 guard — when R2 is not configured and `is_production=True`, HTTP 503 with `media_storage_unavailable` detail returned
3. Dev /tmp fallback — when R2 not configured and `is_production=False`, HTTP 200 with local path URL
4. Invalid `context_type` rejected with HTTP 400
5. File exceeding 100MB MAX_BYTES rejected with HTTP 400 "too large"
6. MIME type mismatch (video file for image context) rejected with HTTP 400
7. URL upload stores document with `context_type='link'` in `db.uploads`

**Implementation note:** FastAPI `dependency_overrides[get_current_user]` used (not `patch`) to properly bypass auth in isolated test apps.

### Task 2: Media Storage Service Tests (TDD)

**10 tests added covering:**
1. `generate_upload_url` returns `upload_url`, `storage_key`, `expires_in` when R2 configured
2. `generate_upload_url` raises HTTP 503 without R2
3. `generate_upload_url` raises HTTP 400 for invalid `file_type`
4. `generate_upload_url` raises HTTP 400 for wrong MIME for `file_type`
5. `confirm_upload` saves asset with `media_id`, `user_id`, `status='uploaded'` to `db.media_assets`
6. `confirm_upload` `public_url` uses `settings.r2.r2_public_url` as base
7. `get_user_assets` filters by `user_id` and `status='uploaded'`
8. `delete_asset` calls both R2 `delete_object` and MongoDB `delete_one`
9. `delete_asset` raises HTTP 404 for non-existent asset
10. `upload_bytes_to_r2` calls `put_object` and returns public URL

## Verification

All 17 new tests pass:
```
17 passed, 0 failed
```

No regressions in full test suite:
```
294 passed, 36 skipped, 8 warnings
```

## Acceptance Criteria Confirmed

- [x] `backend/tests/test_uploads_media_storage.py` exists with 17 test functions (>= 7 required)
- [x] `grep "503" backend/routes/uploads.py` matches (line 159: `status_code=503`)
- [x] `grep "is_production" backend/routes/uploads.py` matches (line 158: `if settings.app.is_production:`)
- [x] `grep "media_storage_unavailable" backend/routes/uploads.py` matches (line 161: `"error": "media_storage_unavailable"`)
- [x] `grep "confirm_upload" backend/services/media_storage.py` matches (line 222)
- [x] `grep "get_user_assets" backend/services/media_storage.py` matches (line 310)
- [x] `grep "delete_asset" backend/services/media_storage.py` matches (line 350)
- [x] `grep "upload_bytes_to_r2" backend/services/media_storage.py` matches (line 273)
- [x] All tests pass (exit code 0)

## Requirements Confirmed

**MEDIA-04:** Tests prove production returns 503 without R2, dev allows /tmp fallback, R2 path works when configured.

**MEDIA-05:** Tests prove media assets in DB have valid R2 public URLs (constructed from `settings.r2.r2_public_url + "/" + storage_key`), presigned URL flow works end-to-end.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed router prefix causing 404 in TestClient**
- **Found during:** Task 1 RED phase
- **Issue:** Router has `prefix="/uploads"`, mounting at `/api/uploads` created `/api/uploads/uploads/media` path
- **Fix:** Mount router at root `"/"` via `app.include_router(router)` so natural path `/uploads/media` is used
- **Files modified:** `backend/tests/test_uploads_media_storage.py`
- **Commit:** 2915a8a

**2. [Rule 1 - Bug] Fixed auth patch not working (401 responses)**
- **Found during:** Task 1 RED phase after routing fix
- **Issue:** `patch("routes.uploads.get_current_user", return_value=FAKE_USER)` doesn't work with FastAPI's dependency injection system — the framework calls the dependency function through its own resolution chain, not the patched module attribute
- **Fix:** Used `app.dependency_overrides[get_current_user] = lambda: FAKE_USER` pattern (correct FastAPI idiom)
- **Files modified:** `backend/tests/test_uploads_media_storage.py`
- **Commit:** 2915a8a

## Known Stubs

None — all test assertions verify real behavior in existing production code.

## Self-Check: PASSED

- File `backend/tests/test_uploads_media_storage.py` exists: FOUND
- Commit `2915a8a` exists: FOUND
- 17 tests in file: FOUND (grep -c "def test_" = 17)
- No stubs in new test file: CONFIRMED
