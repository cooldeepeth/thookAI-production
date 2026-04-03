---
phase: 17-test-foundation-billing-payments
plan: "02"
subsystem: billing-security
tags: [tdd, p0-bugs, jwt-security, credits-atomicity, webhook-dedup, billing]
dependency_graph:
  requires: ["17-01"]
  provides: ["BILL-06", "BILL-07", "BILL-08"]
  affects: ["auth_utils", "services/credits", "services/stripe_service", "db_indexes"]
tech_stack:
  added: []
  patterns:
    - "TDD: failing test committed before production fix for each P0 bug"
    - "Atomic $inc via find_one_and_update — no read-modify-write race"
    - "Stripe webhook idempotency via stripe_events collection with unique index + 7d TTL"
    - "_TEST_JWT_SECRET constant pattern for unit tests after removing fallback secret"
key_files:
  created:
    - backend/tests/billing/test_p0_jwt_fallback.py
    - backend/tests/billing/test_p0_add_credits_atomic.py
    - backend/tests/billing/test_p0_webhook_dedup.py
  modified:
    - backend/auth_utils.py
    - backend/services/credits.py
    - backend/services/stripe_service.py
    - backend/db_indexes.py
    - backend/tests/test_auth_core.py
    - backend/tests/test_stripe_billing.py
    - backend/tests/test_stripe_e2e.py
decisions:
  - "TDD RED commit before GREEN fix: each bug got a failing test committed before the production fix"
  - "Patch database.db (not services.credits.db) because credits.py uses lazy import pattern"
  - "mongomock serializes operations so concurrent test validates correct post-fix behavior, not the bug"
  - "Use _TEST_JWT_SECRET constant in test helpers; patch auth_utils.settings.security in tests that call decode_token indirectly"
  - "stripe_events unique index provides O(1) dedup check; 7d TTL prevents unbounded growth"
metrics:
  duration_minutes: 9
  tasks_completed: 2
  files_modified: 10
  completed_date: "2026-04-03"
---

# Phase 17 Plan 02: TDD — P0 Security & Data Integrity Bugs Summary

TDD fixes for 3 P0 production bugs: JWT fallback secret bypass (BILL-06), non-atomic add_credits race condition (BILL-07), and missing Stripe webhook deduplication (BILL-08). Each bug got a failing test committed before the production fix — 12 total tests in 3 new files, all passing after fixes.

## Tasks Completed

### Task 1: TDD — JWT fallback secret bypass (BILL-06)

**RED commit:** `f7e1a0e` — 4 tests exposing fallback secret acceptance
**GREEN commit:** `3c831b0` — Removed `or "thook-dev-secret"` fallback

Bug: `auth_utils.decode_token` used `settings.security.jwt_secret_key or "thook-dev-secret"`. A token signed with the hardcoded fallback would pass verification on any deployment where `JWT_SECRET_KEY` is set.

Fix: Replaced with explicit check: raise `JWTError("JWT secret key not configured")` when secret is empty. Tokens signed with the dev fallback are now rejected unconditionally.

Tests: 4 tests — fallback rejected, valid accepted, empty raises, wrong secret rejected. All pass.

### Task 2: TDD — Non-atomic add_credits (BILL-07) and Webhook deduplication (BILL-08)

**RED commits:** `5c67b7a` (add_credits), `db47ba2` (webhook dedup)
**GREEN commits:** `e67766b` (add_credits), `81f9921` (webhook dedup + regression fixes)

**BILL-07 — Non-atomic add_credits:**
Bug: `add_credits` used `find_one + update_one($set)` — two concurrent calls could both read the same balance and both write a stale total, losing credits.

Fix: Replaced with `find_one_and_update($inc, return_document=AFTER)`. MongoDB's atomic `$inc` ensures both concurrent calls always produce the correct sum.

Tests: 4 tests — single add, concurrent no lost updates, nonexistent user error, transaction recorded. All pass.

**BILL-08 — Webhook deduplication:**
Bug: `handle_webhook_event` had no idempotency guard. Stripe retries events up to 3 days — duplicates caused double credit additions.

Fix: After `construct_event`, read `stripe_events` collection for the event ID. If found, return `{duplicate: True}` immediately. Otherwise insert the event record then process. TTL index auto-expires records after 7 days.

Tests: 4 tests — first event succeeds, duplicate skipped with duplicate=True, different IDs both process, event recorded in stripe_events. All pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JWT fix broke 4 pre-existing tests that relied on fallback secret**

- **Found during:** Task 1 GREEN phase — full suite regression run
- **Issue:** `test_auth_core.py._make_valid_jwt` used `or "thook-dev-secret"` to sign tokens; `test_stripe_e2e.py` mock events were missing top-level `"id"` key required by new dedup guard; `test_stripe_billing.py` and `test_stripe_e2e.py` mocked `update_one` instead of `find_one_and_update`
- **Fix:**
  - Added `_TEST_JWT_SECRET = "test-secret-key-for-unit-tests-32-chars!!"` constant to `test_auth_core.py`
  - Updated `_make_valid_jwt` and `_make_expired_jwt` to use `_TEST_JWT_SECRET`
  - Updated `test_me_with_valid_bearer_token_returns_user_data` to patch `auth_utils.settings.security` with matching secret
  - Added `"id": "evt_*"` to mock events in `test_stripe_e2e.py`
  - Added `mock_db.users.find_one_and_update = AsyncMock(return_value=updated_user)` to 3 tests
  - Added `mock_db.stripe_events.find_one = AsyncMock(return_value=None)` and `stripe_events.insert_one` mocks
- **Files modified:** `tests/test_auth_core.py`, `tests/test_stripe_billing.py`, `tests/test_stripe_e2e.py`
- **Commit:** `81f9921`

**2. [Rule 1 - Bug] patch path corrected — services.credits.db vs database.db**

- **Found during:** Task 2 RED phase
- **Issue:** `services/credits.py` uses lazy `from database import db` inside each function, so the module has no `db` attribute — `patch("services.credits.db")` raises `AttributeError`
- **Fix:** Changed all test patches to `patch("database.db", mongomock_db)` — the source module that gets imported at call time
- **Files modified:** `tests/billing/test_p0_add_credits_atomic.py`

## Final Test Results

```
tests/billing/test_p0_jwt_fallback.py        4 passed
tests/billing/test_p0_add_credits_atomic.py  4 passed
tests/billing/test_p0_webhook_dedup.py       4 passed
Full suite: 753 passed, 0 failed, 40 skipped
```

## Known Stubs

None — all 3 bugs are fully fixed with no stubs or placeholders.

## Self-Check: PASSED
