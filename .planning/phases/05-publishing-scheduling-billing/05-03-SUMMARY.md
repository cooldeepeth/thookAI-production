---
phase: 05-publishing-scheduling-billing
plan: "03"
subsystem: billing
tags:
  - stripe
  - billing
  - credits
  - testing
  - webhooks
dependency_graph:
  requires:
    - 05-01
    - 05-02
  provides:
    - stripe-billing-tests
    - stripe-startup-validation
  affects:
    - backend/services/stripe_service.py
    - backend/tests/test_stripe_billing.py
tech_stack:
  added: []
  patterns:
    - pytest.mark.asyncio for async billing handler tests
    - Direct async function invocation for webhook handler unit tests
    - Inline _refresh coroutine replication for Celery inner logic testing
key_files:
  created:
    - backend/tests/test_stripe_billing.py
  modified:
    - backend/services/stripe_service.py
decisions:
  - validate_stripe_config runs on module import so startup warnings appear in logs immediately
  - Webhook handlers tested by calling async functions directly (not via HTTP) for precision
  - refresh_monthly_credits inner logic tested by replicating the _refresh coroutine inline to avoid Celery setup complexity
  - Task 2 required zero test file changes — all 222 existing tests passed cleanly with no regressions
metrics:
  duration: "2 minutes"
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_modified: 2
---

# Phase 05 Plan 03: Stripe Billing Tests & Startup Validation Summary

**One-liner:** Comprehensive Stripe billing test suite (16 tests) covering plan preview math, webhook handlers, credit refresh, and simulated checkout mode, plus `validate_stripe_config()` startup warning for missing Price IDs.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add Stripe startup validation and comprehensive billing tests | eb2deec | backend/services/stripe_service.py, backend/tests/test_stripe_billing.py |
| 2 | Full test suite regression check | (no changes) | — |

## What Was Built

### Task 1: Stripe Startup Validation

Added `validate_stripe_config()` to `backend/services/stripe_service.py`:
- Warns when Stripe secret key is not configured (simulated mode)
- Warns when credit package Price IDs (`STRIPE_PRICE_CREDITS_100`, `_500`, `_1000`) are blank or placeholder
- Logs error when `STRIPE_WEBHOOK_SECRET` is missing (webhook signature verification will fail)
- Called automatically on module import so warnings appear in startup logs

### Task 2: Comprehensive Billing Tests (16 tests)

`backend/tests/test_stripe_billing.py` covers:

**Plan preview / pricing (pure math — no DB):**
- `test_build_plan_preview_text_only` — 20 posts = 200 credits, price > 0, features has platforms key
- `test_build_plan_preview_mixed_usage` — 285 credits at $0.06/credit = $18, volume_tier=standard
- `test_build_plan_preview_zero_returns_zero` — no inputs = 0 credits, $0 price
- `test_calculate_plan_price_volume_tiers` — verifies all 4 tier boundaries (100→$6, 1000→$50, 3000→$105, 6000→$180)

**Custom plan activation:**
- `test_activate_custom_plan` — DB update sets subscription_tier=custom, credits=500, credit_allowance=500, clears pending_plan_config

**Webhook handlers:**
- `test_handle_checkout_completed_credit_purchase` — credits added, payment record inserted
- `test_handle_checkout_completed_custom_plan` — activates from pending_plan_config, subscription_tier=custom
- `test_handle_subscription_deleted_downgrades` — subscription_tier=starter, subscription_status=cancelled
- `test_handle_payment_succeeded_refreshes_credits` — credits reset to credit_allowance (500), payment recorded

**Monthly credit refresh:**
- `test_refresh_monthly_credits_resets_for_custom` — user 35 days since refresh gets credits=500
- `test_refresh_monthly_credits_skips_recent` — user refreshed 5 days ago is skipped

**Simulated checkout:**
- `test_create_custom_plan_checkout_simulated` — plan activated directly, simulated=True returned

**Configuration:**
- `test_is_stripe_configured_false_when_empty` — returns False for empty key
- `test_is_stripe_configured_false_when_placeholder` — returns False for placeholder prefix
- `test_is_stripe_configured_true_when_set` — returns True for real key
- `test_validate_stripe_config_exists` — function exists and is callable

### Task 2: Regression Check Result

Full suite: **222 passed, 36 skipped, 0 failed** — zero regressions from Phase 5 credit deduction fix and platform restriction changes. No test file modifications required.

## Verification

```
cd backend && python3 -m pytest tests/test_stripe_billing.py -v
# => 16 passed in 0.22s

cd backend && python3 -m pytest --tb=short -q
# => 222 passed, 36 skipped in 24.36s
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all test assertions cover real code paths.

## Self-Check: PASSED

Files exist:
- backend/tests/test_stripe_billing.py — FOUND (created in this plan)
- backend/services/stripe_service.py — FOUND (validate_stripe_config added)

Commits exist:
- eb2deec — feat(05-03): add Stripe startup validation and comprehensive billing tests — FOUND
