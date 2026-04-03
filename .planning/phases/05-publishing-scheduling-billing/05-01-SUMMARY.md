---
phase: 05-publishing-scheduling-billing
plan: "01"
subsystem: publishing-dispatch
tags:
  - publishing
  - oauth
  - testing
  - httpx
  - linkedin
  - twitter
  - instagram
dependency_graph:
  requires:
    - backend/agents/publisher.py
    - backend/tasks/content_tasks.py
    - backend/routes/platforms.py
  provides:
    - test coverage for publishing HTTP dispatch
    - test coverage for platform OAuth flows
    - _run_scheduled_posts_inner extracted for testability
  affects:
    - backend/tasks/content_tasks.py
tech_stack:
  added: []
  patterns:
    - httpx.AsyncClient patching for real code path testing
    - FastAPI TestClient with dependency_overrides for auth mocking
    - AsyncMock for async coroutine stubs
    - pytest.mark.asyncio for async test functions
key_files:
  created:
    - backend/tests/test_publishing.py
    - backend/tests/test_platform_oauth.py
  modified:
    - backend/tasks/content_tasks.py
    - backend/tests/test_e2e_ship.py
decisions:
  - "Test httpx.AsyncClient (not publisher function) to verify real HTTP dispatch code path runs end-to-end"
  - "Extract _run_scheduled_posts_inner to module level for unit-testable scheduled post processing"
  - "Added media_assets param to _publish_to_platform to support Instagram media (previously missing)"
  - "Simplified process_scheduled_posts Celery task to delegate to _run_scheduled_posts_inner"
metrics:
  duration: "6 minutes"
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 05 Plan 01: Publishing Dispatch and Platform OAuth Tests Summary

Two test files covering the full publishing and OAuth surface area — 23 tests total verifying real HTTP dispatch to LinkedIn/X/Instagram API endpoints, OAuth connect/disconnect/status flows, and token encryption/decryption.

## Tasks Completed

| Task | Status | Commit | Files |
|------|--------|--------|-------|
| 1: Publishing dispatch and scheduled post tests | Done | a97cb02 | backend/tests/test_publishing.py, backend/tasks/content_tasks.py |
| 2: Platform OAuth connect/disconnect/status tests | Done | 2c9f2b7 | backend/tests/test_platform_oauth.py, backend/tests/test_e2e_ship.py |

## Test Coverage Delivered

### test_publishing.py (9 tests)

- `TestPublishLinkedIn::test_publish_to_platform_linkedin_sends_correct_request` — mocks httpx.AsyncClient, asserts POST to `api.linkedin.com/v2/ugcPosts` with `Authorization: Bearer` header
- `TestPublishLinkedIn::test_publish_to_linkedin_no_simulation` — production mode: confirms no `[SIMULATED]` log line appears
- `TestPublishX::test_publish_to_platform_x_sends_correct_request` — asserts POST to `api.twitter.com/2/tweets` with Bearer auth
- `TestPublishInstagram::test_publish_to_platform_instagram_sends_correct_request` — calls `agents.publisher.publish_to_platform` directly, asserts `graph.facebook.com` is called with `access_token` param
- `TestPublishErrorHandling::test_publish_http_failure_returns_false` — HTTP 500 from platform API returns False
- `TestPublishErrorHandling::test_publish_network_error_returns_false` — `httpx.ConnectError` returns False
- `TestPublishErrorHandling::test_publish_expired_token_returns_false` — expired token dict caught before any HTTP call
- `TestProcessScheduledPosts::test_process_scheduled_posts_publishes_due_posts` — due post → status updated to `published`
- `TestProcessScheduledPosts::test_process_scheduled_posts_fails_without_token` — no token → status updated to `failed` with "Platform not connected"

### test_platform_oauth.py (14 tests)

- Status endpoint: all 3 platforms returned with `connected` and `configured` fields; connected token reflected correctly
- LinkedIn connect: returns URL containing `linkedin.com/oauth/v2/authorization`; returns 400 when client_id empty
- X connect: returns URL containing `twitter.com/i/oauth2/authorize` with PKCE `code_challenge` and `S256` method; returns 400 when API key empty
- Instagram connect: returns URL containing `facebook.com/dialog/oauth`; returns 400 when META_APP_ID empty
- Disconnect: deletes token and returns 200; returns 404 when platform not connected
- `get_platform_token`: decrypts stored token correctly via `_encrypt_token` round-trip; expired token with no refresh returns None; expired token with refresh_token makes HTTP refresh call and returns new token; missing token doc returns None

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_publish_to_platform` missing `media_assets` parameter**
- **Found during:** Task 1 (Instagram test)
- **Issue:** `_publish_to_platform(platform, content, token)` in `content_tasks.py` did not pass `media_assets` to `publish_to_platform()` in `publisher.py`. Instagram publishing always fails without `image_url` derived from `media_assets`, making Instagram scheduling broken.
- **Fix:** Added `media_assets: Optional[List[Dict[str, Any]]] = None` to `_publish_to_platform` and passed it through to `publish_to_platform()`.
- **Files modified:** `backend/tasks/content_tasks.py`
- **Commit:** a97cb02

**2. [Rule 1 - Bug] `process_scheduled_posts` had duplicated logic vs testability**
- **Found during:** Task 1 (process_scheduled_posts tests needed inner async function)
- **Issue:** The entire scheduling logic was inside an unexported `_process()` inner function inside the Celery task, making it impossible to unit-test without running via Celery.
- **Fix:** Extracted logic to module-level `_run_scheduled_posts_inner(db_handle=None)` function; `process_scheduled_posts` now calls `run_async(_run_scheduled_posts_inner())`. No behavior change — same logic, just testable.
- **Files modified:** `backend/tasks/content_tasks.py`
- **Commit:** a97cb02

**3. [Rule 1 - Bug] `test_e2e_ship.py` assertion broken by new `media_assets` param**
- **Found during:** Task 2 (full test suite run)
- **Issue:** Existing test `test_publish_to_platform_calls_publisher_in_production` asserted `publish_to_platform` was called without `media_assets` — now fails because `_publish_to_platform` passes `media_assets=None`.
- **Fix:** Updated assertion to include `media_assets=None`.
- **Files modified:** `backend/tests/test_e2e_ship.py`
- **Commit:** 2c9f2b7

## Success Criteria Verification

- 23 tests across 2 files — all pass (exceeds 15+ target)
- Publishing dispatch verified at HTTP level — tests mock `httpx.AsyncClient` and assert correct API endpoint URLs
- LinkedIn: `api.linkedin.com/v2/ugcPosts` with `Authorization: Bearer` header confirmed
- X/Twitter: `api.twitter.com/2/tweets` with Bearer auth confirmed
- Instagram: `graph.facebook.com` with `access_token` param confirmed
- Scheduled post processing verified — `process_scheduled_posts` picks up due posts and publishes
- OAuth flows verified — connect returns correct auth URLs, disconnect removes tokens, token encryption/decryption round-trip works
- Expired token handling verified in `get_platform_token` — returns None when expired, attempts refresh when refresh_token present
- No simulation in production path — confirmed by `test_publish_to_linkedin_no_simulation`

## Known Stubs

None — all tests verify real integration code paths.

## Self-Check: PASSED

- `backend/tests/test_publishing.py` — FOUND
- `backend/tests/test_platform_oauth.py` — FOUND
- Commit a97cb02 — FOUND
- Commit 2c9f2b7 — FOUND
- 23 tests pass — VERIFIED (206 total tests in suite pass, no regressions)
