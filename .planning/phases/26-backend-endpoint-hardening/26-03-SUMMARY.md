---
phase: 26-backend-endpoint-hardening
plan: "03"
subsystem: backend-validation
tags: [pydantic, field-constraints, input-validation, tdd]
dependency_graph:
  requires:
    - 26-01 (test scaffold for error format tests)
  provides:
    - Pydantic Field() constraints on all major POST endpoint request models
    - field_validator for platform normalization in ContentCreateRequest
    - 422 responses instead of 400 for validation failures on constrained fields
  affects:
    - backend/routes/auth.py
    - backend/routes/content.py
    - backend/routes/onboarding.py
    - backend/routes/persona.py
    - backend/routes/uploads.py
    - backend/tests/test_platform_features.py
tech_stack:
  added: []
  patterns:
    - Pydantic v2 Field() constraints (min_length, max_length, ge, le, pattern)
    - Pydantic v2 field_validator for normalization + validation
    - List[T] with min_length/max_length for batch endpoint validation
key_files:
  created: []
  modified:
    - backend/routes/auth.py
    - backend/routes/content.py
    - backend/routes/onboarding.py
    - backend/routes/persona.py
    - backend/routes/uploads.py
    - backend/tests/test_platform_features.py
decisions:
  - "Applied Field() constraints to actual existing field names (answers, expiry_days) not plan aliases (interview_answers, expires_days)"
  - "Changed UrlUploadRequest.url from HttpUrl to str+Field(min_length=10) since handler validates URL format via urlparse anyway"
  - "test_platform_features.py test updated: empty-posts import now returns 422 (Pydantic) not 400 (manual check)"
metrics:
  duration_minutes: 7
  completed_date: "2026-04-12"
  tasks_completed: 2
  files_created: 0
  files_modified: 6
---

# Phase 26 Plan 03: Pydantic Field Constraints for POST Endpoints Summary

Pydantic Field() constraints and field_validators added to all 5 major POST endpoint request models, replacing manual if-check validation with declarative schema-level validation that produces standardized 422 responses.

## What Was Built

### Task 1: auth.py and content.py

**`backend/routes/auth.py`:**
- `RegisterRequest`: `password = Field(min_length=1, max_length=200)`, `name = Field(min_length=1, max_length=100)`
- `DeleteAccountRequest`: `confirm = Field(min_length=1)`
- Import updated: `from pydantic import BaseModel, EmailStr, Field`

**`backend/routes/content.py`:**
- `ContentCreateRequest`: `raw_input = Field(min_length=5, max_length=50000)` + `@field_validator("platform")` that lowercases and validates against `{"linkedin", "x", "instagram"}`
- `ContentStatusUpdate`: `status = Field(pattern="^(approved|rejected)$")`
- `VoiceGenerateRequest`: `job_id = Field(min_length=1)`, `stability = Field(default=0.5, ge=0.0, le=1.0)`, `similarity_boost = Field(default=0.75, ge=0.0, le=1.0)`
- `VideoGenerateRequest`: `job_id = Field(min_length=1)`, `duration = Field(default=5, ge=1, le=300)`
- `ImageGenerateRequest`: `job_id = Field(min_length=1)`
- Removed manual if-checks in `create_content` handler for `raw_input` length (lines 100-103)
- Import updated: `from pydantic import BaseModel, Field, field_validator`

### Task 2: onboarding.py, persona.py, uploads.py

**`backend/routes/onboarding.py`:**
- `ImportHistoryRequest`: `posts = Field(min_length=1, max_length=50)` — limits batch to 1-50 items
- `AnalyzePostsRequest`: `posts_text = Field(min_length=1)`
- `GeneratePersonaRequest`: `answers = Field(min_length=1)` — at least one answer required
- Import updated: `from pydantic import BaseModel, Field`

**`backend/routes/persona.py`:**
- `SharePersonaRequest`: `expiry_days = Field(default=7, ge=1, le=30)` — validates 1-30 day range; changed from `Optional[int]` to `int` with explicit constraints
- Import updated: `from pydantic import BaseModel, Field`

**`backend/routes/uploads.py`:**
- `UrlUploadRequest`: `url` changed from `HttpUrl` to `str = Field(min_length=10, max_length=2048)` — handler still validates URL format via `urlparse`
- Import updated: `from pydantic import BaseModel, Field` (removed HttpUrl)

### Test Fix: test_platform_features.py

- `test_import_history_empty_posts_returns_400` updated to expect 422 (Pydantic Field constraint) instead of 400 (old manual check)

## Verification

```
python3 -c "from routes.content import ContentCreateRequest, VoiceGenerateRequest, VideoGenerateRequest; from routes.auth import RegisterRequest; print('imports OK')"
# → imports OK

python3 -c "from routes.onboarding import GeneratePersonaRequest; from routes.persona import SharePersonaRequest; from routes.uploads import UrlUploadRequest; print('all imports OK')"
# → all imports OK

pytest tests/test_auth.py tests/test_onboarding_core.py -q
# → 35 passed, 11 skipped

pytest tests/test_uploads_media_storage.py -q
# → 17 passed

pytest tests/test_platform_features.py::TestPostHistoryImport -q
# → 3 passed
```

Spot-check constraint behavior:
- `ContentCreateRequest(platform='bad', ...)` → ValidationError (platform validator)
- `ContentCreateRequest(platform='linkedin', ..., raw_input='hi')` → ValidationError (min_length=5)
- `ContentCreateRequest(platform='LinkedIn', ..., raw_input='hello world')` → normalizes to `linkedin`
- `GeneratePersonaRequest(answers=[])` → ValidationError (min_length=1)
- `SharePersonaRequest(expiry_days=0)` → ValidationError (ge=1)
- `UrlUploadRequest(url='hi')` → ValidationError (min_length=10)

## Deviations from Plan

**1. [Rule 1 - Bug] Field name mismatch — `answers` vs `interview_answers`**
- Found during: Task 2 read phase
- Issue: Plan used `interview_answers` but actual field in GeneratePersonaRequest is `answers`
- Fix: Applied Field(min_length=1) to actual field name `answers`
- Files modified: backend/routes/onboarding.py

**2. [Rule 1 - Bug] Field name mismatch — `expiry_days` vs `expires_days`**
- Found during: Task 2 read phase
- Issue: Plan used `expires_days` but actual field in SharePersonaRequest is `expiry_days`
- Fix: Applied Field(default=7, ge=1, le=30) to actual field name `expiry_days`
- Files modified: backend/routes/persona.py

**3. [Rule 2 - Auto-fix] Test expected old 400 status for empty posts**
- Found during: Task 2 verification
- Issue: `test_import_history_empty_posts_returns_400` expected 400 from old manual check, now gets 422 from Pydantic
- Fix: Updated test to expect 422 (correct behavior)
- Files modified: backend/tests/test_platform_features.py
- Commit: 4b7666e

**4. HttpUrl → str for UrlUploadRequest**
- Found during: Task 2 implementation
- Issue: HttpUrl type is more restrictive than needed; handler already validates URL format via urlparse
- Fix: Changed to `str = Field(min_length=10, max_length=2048)` per plan action section
- No functional regression — urlparse validation in handler still validates URL scheme

**5. Merge from dev to get Plan 01 test files**
- Found during: Task 1 start
- Issue: Plan 01 test files (test_error_format.py) were on dev branch, not in this worktree branch
- Fix: Fast-forward merged dev into worktree branch to get test scaffold files

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Pydantic Field constraints to auth.py and content.py | f2f361a | backend/routes/auth.py, backend/routes/content.py |
| 2 | Add Pydantic Field constraints to onboarding.py, persona.py, uploads.py | 381c914 | backend/routes/onboarding.py, backend/routes/persona.py, backend/routes/uploads.py |
| 2 (fix) | Update test to expect 422 for empty posts import | 4b7666e | backend/tests/test_platform_features.py |

## Known Stubs

None — all request model constraints are wired directly to Pydantic validation, no stub behavior.

## Self-Check: PASSED

- [x] `backend/routes/auth.py` — `grep "Field(min_length" routes/auth.py` returns 3 matches
- [x] `backend/routes/content.py` — `grep "field_validator" routes/content.py` returns 2 matches, `grep "Field.*ge=0" routes/content.py` returns 2 matches
- [x] `backend/routes/onboarding.py` — `grep "Field(min_length" routes/onboarding.py` returns 2+ matches
- [x] `backend/routes/persona.py` — `grep "Field" routes/persona.py` returns matches
- [x] `backend/routes/uploads.py` — `grep "Field(min_length" routes/uploads.py` returns 1 match
- [x] Manual raw_input checks removed: `grep "len(data.raw_input)" routes/content.py` returns 0
- [x] Commits f2f361a, 381c914, 4b7666e exist in git log
- [x] 35 tests pass in test_onboarding_core.py, 17 pass in test_uploads_media_storage.py, 3 pass in test_platform_features.py::TestPostHistoryImport
