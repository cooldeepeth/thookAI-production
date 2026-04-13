---
phase: 30-social-publishing-end-to-end
plan: "02"
subsystem: platform-oauth
tags: [token-refresh, instagram, proactive-refresh, oauth, tdd]
dependency_graph:
  requires: [30-01]
  provides: [proactive-token-refresh, instagram-token-renewal]
  affects: [backend/routes/platforms.py, backend/agents/publisher.py]
tech_stack:
  added: []
  patterns: [proactive-refresh-window, fb-exchange-token, graceful-fallback]
key_files:
  created: []
  modified:
    - /Users/kuldeepsinhparmar/thookAI-production/backend/routes/platforms.py
    - /Users/kuldeepsinhparmar/thookAI-production/backend/tests/test_platform_oauth.py
decisions:
  - "Proactive 24h window: refresh token before expiry rather than after, preventing silent publish failures"
  - "Instagram fallback in get_platform_token: passes access_token as the refresh input since Instagram has no separate refresh_token"
  - "Graceful fallback: if proactive refresh fails but token still valid, return current decrypted token rather than None"
  - "Shared response-handling block in _refresh_token: Instagram skips storing refresh_token field (long-lived token renewal pattern)"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-12"
  tasks_completed: 2
  files_modified: 2
requirements_satisfied: [PUBL-04]
---

# Phase 30 Plan 02: Platform Token Proactive Refresh + Instagram Renewal Summary

**One-liner:** Proactive 24-hour token refresh window in `get_platform_token` plus a working Instagram `fb_exchange_token` renewal branch in `_refresh_token`, preventing silent publish failures from stale credentials.

## What Was Built

### Task 1 — Proactive 24h refresh in `get_platform_token`

**Problem:** `get_platform_token()` only refreshed tokens AFTER expiry. Platform APIs receiving an expired token return 401, causing silent publish failures.

**Fix:** Replaced the post-expiry-only check with a proactive 24-hour window. If `expires_at - now < timedelta(hours=24)`, the function attempts refresh immediately. Fallback behavior:
- Refresh succeeds → return new token
- Refresh fails but token still technically valid → return current decrypted token (graceful fallback)
- Refresh fails and token already expired → return `None`

Instagram edge case handled: Instagram has no `refresh_token` field, so `get_platform_token` passes the `access_token` as the refresh input when `platform == "instagram"`.

### Task 2 — Instagram branch in `_refresh_token`

**Problem:** `_refresh_token()` had no Instagram branch — fell through to `return None`, making Instagram token renewal impossible.

**Fix:** Added `elif platform == "instagram":` branch that calls:
```
GET https://graph.facebook.com/v18.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={META_APP_ID}
  &client_secret={META_APP_SECRET}
  &fb_exchange_token={current_access_token}
```

The DB update block was refactored to skip storing `refresh_token` for Instagram (long-lived token renewal pattern — Instagram doesn't return a new refresh_token).

## Test Results

| Suite | Before | After |
|-------|--------|-------|
| test_platform_oauth.py | 14 passed | 21 passed (+7 new) |
| test_publishing.py | 16 passed | 16 passed (no regression) |
| **Total** | 30 | **37 passed, 0 failed** |

New test classes added:
- `TestProactiveTokenRefresh` (4 tests): 12h window triggers refresh, 30h does not, fallback on refresh fail, None on expired+fail
- `TestInstagramTokenRefresh` (3 tests): calls correct endpoint with correct params, stores new token in DB, returns None on 400

## Commits

| Hash | Description |
|------|-------------|
| `4b8d6f9` | feat(30-02): proactive 24h token refresh in get_platform_token |
| `414f659` | feat(30-02): add Instagram token refresh branch to _refresh_token |

## Grep Verification

```
grep -n "timedelta(hours=24)" backend/routes/platforms.py
→ 576:        if time_until_expiry < timedelta(hours=24):

grep -n "fb_exchange_token" backend/routes/platforms.py
→ 448, 451 (Instagram callback — existing)
→ 637, 640 (new _refresh_token branch)

grep -n "elif platform == .instagram" backend/routes/platforms.py
→ 630:            elif platform == "instagram":
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `_make_response()` helper**
- **Found during:** Task 2 tests — plan's `TestInstagramTokenRefresh` referenced `_make_response()` but it didn't exist in the test file
- **Fix:** Added `_make_response(status_code, json_data)` helper at top of test file alongside `_make_test_app()`
- **Files modified:** `backend/tests/test_platform_oauth.py`
- **Commit:** `4b8d6f9`

None of the architectural decisions required changes — plan executed as written with one missing helper added.

## Known Stubs

None — both behaviors are fully implemented with real logic and verified by automated tests.

## Self-Check: PASSED

- `backend/routes/platforms.py` exists and modified: FOUND
- `backend/tests/test_platform_oauth.py` exists and modified: FOUND
- Commit `4b8d6f9` exists: FOUND
- Commit `414f659` exists: FOUND
- `timedelta(hours=24)` present in platforms.py: FOUND (line 576)
- `fb_exchange_token` present in _refresh_token: FOUND (lines 637, 640)
- `elif platform == "instagram"` present in _refresh_token: FOUND (line 630)
- test_platform_oauth.py has 612 lines (min 400 required): PASSED
- 37 tests pass, 0 fail: PASSED
