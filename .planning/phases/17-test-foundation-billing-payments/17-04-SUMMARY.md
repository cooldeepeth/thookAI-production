---
phase: 17-test-foundation-billing-payments
plan: "04"
subsystem: billing-tests
tags:
  - billing
  - stripe
  - checkout
  - subscriptions
  - credits
  - volume-pricing
  - tests
dependency_graph:
  requires:
    - "17-01"
    - "17-02"
  provides:
    - "checkout-flow-test-coverage"
    - "subscription-lifecycle-test-coverage"
    - "volume-pricing-test-coverage"
  affects:
    - "CI billing job (95% coverage gate)"
tech_stack:
  added: []
  patterns:
    - "mongomock-motor for DB-backed async tests"
    - "MagicMock/AsyncMock for Stripe SDK objects"
    - "ASGITransport + httpx.AsyncClient for route-level tests"
    - "patch('services.stripe_service.db') + patch('database.db') for DB injection"
key_files:
  created:
    - backend/tests/billing/test_checkout.py
    - backend/tests/billing/test_subscriptions.py
    - backend/tests/billing/test_credits.py
  modified: []
decisions:
  - "Patching both 'services.stripe_service.db' and 'database.db' is required because stripe_service binds db at import time and credits.py uses lazy 'from database import db' inside functions"
  - "services.subscriptions.py uses lazy 'from database import db' inside functions — patch 'database.db' not 'services.subscriptions.db'"
  - "Sync pure-function tests inside @pytest.mark.asyncio classes generate PytestWarning — separated into distinct sync/async classes"
  - "Growth tier threshold is $79; 50 videos = 2500 credits → $88 at tier3 (not 40 videos = $70)"
metrics:
  duration: "7 minutes"
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_created: 3
  tests_added: 132
---

# Phase 17 Plan 04: Checkout, Subscriptions & Volume Pricing Tests Summary

Comprehensive billing test suite covering Stripe checkout flows, subscription lifecycle state machine, and volume pricing calculations. 132 new tests across 3 files; zero external API calls.

## What Was Built

**test_checkout.py** — 30 tests for BILL-01:
- `TestCustomPlanCheckoutSimulated` (8 tests): Happy path for 6 credit amounts (100, 250, 500, 1000, 2500, 5000), zero price error, negative price error
- `TestCustomPlanCheckoutStripe` (5 tests): Real Stripe path — URL returned, metadata correctness, success/cancel URL pass-through, pending config stored in DB, API exception handled
- `TestCreditCheckout` (6 tests): All 3 package sizes (small/medium/large), invalid package, Stripe mode, metadata verification
- `TestStripeCustomerManagement` (4 tests): New user creation + DB persistence, existing user retrieval (no re-creation), API error handling, simulated mode
- `TestBillingRoutes` (7 tests): GET /api/billing/config (200), POST plan/checkout (200 simulated, 400 zero credits, 422 invalid body), POST credits/checkout (200 valid, 400 invalid package), auth guard (401)

**test_subscriptions.py** — 47 tests for BILL-02:
- `TestHandleCheckoutCompleted` (5 tests): Credit purchase adds credits + records payment, custom plan activates from pending_plan_config, missing user_id / missing type handled gracefully
- `TestHandleSubscriptionCreated` (4 tests): DB record written, credits updated, lookup by customer_id when no metadata, unknown user no crash
- `TestHandleSubscriptionUpdated` (4 tests): Status update, credit_allowance refresh on active, past_due preserves allowance, customer lookup fallback
- `TestHandleSubscriptionDeleted` (3 tests): Reverted to starter tier, pre-paid credits preserved, unknown customer no crash
- `TestHandlePaymentSucceeded` (4 tests): Credits reset to allowance, payment record written, no subscription → ignored, unknown user → ignored
- `TestHandlePaymentFailed` (2 tests): User marked past_due, no subscription → ignored
- `TestCancelStripeSubscription` (6 tests): Simulated cancel, DB flag written, Stripe modify (at period end), Stripe delete (immediate), no subscription error, API error
- `TestModifySubscription` (4 tests): Simulated upgrade/downgrade credits, no subscription error, unknown user error
- `TestSubscriptionRoutes` (4 tests): GET /subscription 200, POST /subscription/cancel 200, POST /plan/modify 200, missing signature 400

**test_credits.py** — 55 tests for BILL-05:
- `TestCalculatePlanCredits` (6 tests): Zero, text only, images, videos, mixed, repurposes+voice
- `TestCalculatePlanPrice` (12 tests): All tier boundaries (100, 500, 501, 1000, 1500, 1501, 3000, 5000, 5001, 6000), ceiling rounding
- `TestGetFeaturesForPrice` (5 tests): $0 base, $29.99 paid, $79 growth unlock, $149 scale unlock, dict not None
- `TestBuildPlanPreview` (6 tests): Zero, text only, required keys, growth unlock verification, breakdown sum equals total, volume label
- `TestGetOperationCost` (5 tests): CONTENT_CREATE, VIDEO_GENERATE, case insensitive, invalid default 0, REPURPOSE
- `TestGetAllTiers` (5 tests): Returns list ≥2, includes starter/custom, starter free, custom has volume_tiers
- `TestGetCreditBalance` (6 tests): Happy path, nonexistent user, tier_name present, low balance flag, sufficient balance, custom plan config
- `TestDeductCredits` (7 tests): Happy path reduces balance, transaction recorded, insufficient → error balance unchanged, zero credits fails, exact cost → balance=0, video cap (starter), carousel cap (starter)
- `TestGetUsageHistory` (5 tests): Returns transactions, days filter, limit respected, summary aggregates, empty returns []
- `TestCheckFeatureAccess` (5 tests): series_enabled false, voice_enabled false, custom plan allows voice, unknown feature, nonexistent user
- `TestBoundaryValuesAsync` (2 tests): Exact cost succeeds → balance=0, one below → fails
- `TestBoundaryValuesPure` (2 tests): 50000 credits handled, all operations sum correctly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] services.subscriptions.db patching failure**
- **Found during:** Task 2 route-level tests
- **Issue:** `services.subscriptions.py` uses lazy `from database import db` inside functions, not a module-level `db` attribute. `patch("services.subscriptions.db", ...)` raised `AttributeError`.
- **Fix:** Removed the `services.subscriptions.db` patch; `patch("database.db", ...)` is sufficient because the lazy import resolves at call time.
- **Files modified:** `backend/tests/billing/test_subscriptions.py`
- **Commit:** cc635e8 (included in Task 2 commit)

**2. [Rule 1 - Bug] Growth tier test used wrong video count**
- **Found during:** Task 2 test_credits.py TestBuildPlanPreview
- **Issue:** 40 videos = 2000 credits → $70 (at tier3 $0.035/credit), which is below $79 growth threshold. Test asserted `>= 79` incorrectly.
- **Fix:** Used 50 videos = 2500 credits → ceil(2500 * 0.035) = 88, which is ≥ $79.
- **Files modified:** `backend/tests/billing/test_credits.py`
- **Commit:** cc635e8 (included in Task 2 commit)

**3. [Rule 1 - Bug] PytestWarning for sync methods in async class**
- **Found during:** Task 2 test_credits.py TestBoundaryValues
- **Issue:** Two sync test methods were inside `@pytest.mark.asyncio` class, triggering PytestWarning.
- **Fix:** Split into `TestBoundaryValuesAsync` (async DB tests) and `TestBoundaryValuesPure` (sync pure-function tests).
- **Files modified:** `backend/tests/billing/test_credits.py`
- **Commit:** cc635e8

## Known Stubs

None — all tests verify real production code paths. No stub data or placeholder assertions.

## Commits

| Commit | Task | Description |
|--------|------|-------------|
| 44fb2cb | Task 1 | test(17-04): checkout flow tests — custom plan builder + credit packages |
| cc635e8 | Task 2 | test(17-04): subscription lifecycle + volume pricing tests |

## Self-Check: PASSED
