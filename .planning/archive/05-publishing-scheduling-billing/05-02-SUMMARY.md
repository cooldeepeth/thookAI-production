---
phase: 05-publishing-scheduling-billing
plan: "02"
subsystem: billing/credits
tags: [credits, race-condition, atomic, starter-tier, platform-restriction, billing]
dependency_graph:
  requires: []
  provides: [atomic-credit-deduction, starter-platform-restriction, credit-tests]
  affects: [backend/services/credits.py, backend/routes/content.py]
tech_stack:
  added: [pymongo.ReturnDocument]
  patterns: [find_one_and_update atomic write, FastAPI dependency_overrides for testing]
key_files:
  modified:
    - backend/services/credits.py
    - backend/routes/content.py
  created:
    - backend/tests/test_credits_billing.py
decisions:
  - "Use find_one_and_update with credits >= amount filter for atomic deduction — eliminates race condition without transactions"
  - "Platform restriction added in route handler (not credits service) — keeps concerns separate and makes it testable via FastAPI test client"
  - "Test both database.db (for service-level) and routes.content.db (for route-level) patches — each import creates a separate reference"
metrics:
  duration_minutes: 4
  tasks_completed: 2
  files_modified: 3
  tests_added: 11
  completed_date: "2026-03-31"
requirements: [BILL-04, BILL-05]
---

# Phase 05 Plan 02: Credit Atomicity and Starter Tier Restrictions Summary

Replaced non-atomic read-then-write credit deduction with MongoDB `find_one_and_update` using a `credits >= amount` filter guard, eliminating the race condition where concurrent requests could both read the same balance and both succeed.

## What Was Built

### Task 1: Atomic Credit Deduction + Starter Platform Restriction

**`backend/services/credits.py`** — replaced the broken two-step pattern:

Old (broken): `find_one` → check credits → `update_one` (race window between read and write)

New (atomic): `find_one_and_update({"user_id": uid, "credits": {"$gte": amount}}, {"$inc": {"credits": -amount}}, return_document=ReturnDocument.AFTER)` — if two concurrent requests race, only one matches the filter; the other gets `None` back and returns "Not enough credits".

**`backend/routes/content.py`** — added starter platform restriction before credit deduction in `create_content`:

```python
user_tier = current_user.get("subscription_tier", "starter")
if user_tier in ("starter", "free") and data.platform.lower() != "linkedin":
    raise HTTPException(status_code=402, detail="Starter accounts can only create content for LinkedIn...")
```

### Task 2: Comprehensive Tests (11 tests, all passing)

**`backend/tests/test_credits_billing.py`** — covers:
- `test_deduct_credits_success` — success=True, correct new_balance, transaction recorded
- `test_deduct_credits_insufficient` — success=False, "Not enough credits" error with available/required
- `test_deduct_credits_atomic_concurrent` — asyncio.gather concurrent calls, exactly one wins, balance never negative
- `test_starter_hard_cap_video` — 2 existing VIDEO_GENERATE → blocked with "limited to 2 video"
- `test_starter_hard_cap_carousel` — 5 existing CAROUSEL_GENERATE → blocked with "limited to 5 carousel"
- `test_starter_platform_restriction_blocks_x` — HTTP 402 with LinkedIn mention for platform="x"
- `test_starter_platform_restriction_allows_linkedin` — no platform restriction 402 for platform="linkedin"
- `test_custom_tier_no_platform_restriction` — custom tier user not blocked for platform="x"
- `test_add_credits_success` — balance increases by correct amount
- `test_build_plan_preview_calculates_correctly` — total_credits = 10*10 + 5*8 = 140
- `test_build_plan_preview_volume_discount` — higher volumes get lower per-credit pricing

## Deviations from Plan

None — plan executed exactly as written.

The TDD cycle was applied: RED (wrote failing tests first), GREEN (implemented code to pass), REFACTOR (test patch targets corrected from `services.credits.db` to `database.db` since the service uses `from database import db` inside functions).

## Key Decisions

1. **`find_one_and_update` instead of transactions** — MongoDB single-document atomic operations are sufficient here. No need for multi-document transactions, keeping the fix minimal.

2. **`ReturnDocument.AFTER`** — returns the post-update document so `new_balance = result.get("credits")` is correct without a second read.

3. **Platform restriction in route, not credits service** — the credits service handles credit economics; platform access control belongs in the route layer. This also makes it trivially testable via FastAPI's `dependency_overrides`.

4. **Two-level DB patching in tests** — `routes.content.db` and `database.db` are separate Python objects (different import bindings). Tests patch both to avoid Motor attempting real connections.

## Self-Check: PASSED

- FOUND: backend/services/credits.py
- FOUND: backend/routes/content.py
- FOUND: backend/tests/test_credits_billing.py
- FOUND: commit 1d3df68 (fix: atomic credit deduction and starter platform restriction)
- FOUND: commit ef7e9ec (test: credit atomicity, starter caps, and platform restriction tests)
