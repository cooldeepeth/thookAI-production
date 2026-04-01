---
phase: 16-e2e-audit-security-hardening-production-ship
plan: 05
subsystem: testing
tags: [stripe, oauth, linkedin, twitter, instagram, google, payments, webhooks, pkce, jwt, encryption]

# Dependency graph
requires:
  - phase: backend/services/stripe_service.py
    provides: "Stripe billing service with create_custom_plan_checkout, create_credit_checkout, handle_webhook_event"
  - phase: backend/routes/billing.py
    provides: "Billing routes: /plan/checkout, /credits/checkout, /webhook/stripe"
  - phase: backend/routes/platforms.py
    provides: "Platform OAuth: LinkedIn, X/Twitter (PKCE), Instagram connect/callback/disconnect"
  - phase: backend/routes/auth_google.py
    provides: "Google OAuth: /auth/google and /auth/google/callback"
provides:
  - "50 comprehensive tests covering Stripe billing E2E and OAuth platform flows"
  - "E2E-06: Stripe checkout, webhook verification, subscription lifecycle verified"
  - "E2E-07: All 4 OAuth platforms verified with redirect URL construction and token storage"
affects: [phase-16-e2e-audit, production-ship, billing-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "patch.object(module.settings, field) for settings patched at module load time — avoids config.settings mock not propagating"
    - "Parameterized tests for credit package coverage (small/medium/large)"
    - "mock_stripe.error.SignatureVerificationError for real stripe error class reference in tests"

key-files:
  created:
    - backend/tests/test_stripe_e2e.py
    - backend/tests/test_oauth_flows.py
  modified: []

key-decisions:
  - "patch.object(google_module.settings, 'google', mock_config) preferred over patch('config.settings') for routes that import settings at module level — config.settings patch does not propagate to already-imported references"
  - "Parameterize credit package tests over [small/medium/large] rather than separate test methods — avoids duplication and ensures all packages tested"
  - "Use real stripe.error.SignatureVerificationError class for mock side_effect — MagicMock TypeError otherwise when stripe exception hierarchy is inspected"

patterns-established:
  - "Google OAuth tests: use patch.object on the module's settings reference, not config.settings"
  - "Platform OAuth redirect tests: assert specific URL fragments (code_challenge, S256, client_id) not just 200 status"
  - "Stripe webhook tests: must patch both STRIPE_WEBHOOK_SECRET constant and stripe.Webhook.construct_event"

requirements-completed: [E2E-06, E2E-07]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 16 Plan 05: Stripe Billing & OAuth Flow E2E Tests Summary

**50 tests verifying Stripe billing (checkout, webhooks, subscription lifecycle) and OAuth flows for all 4 platforms (LinkedIn, X/Twitter PKCE, Instagram, Google) — all API calls mocked**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-01T12:31:56Z
- **Completed:** 2026-04-01T12:36:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- 26 Stripe E2E tests: all 3 credit packages, custom plan checkout, webhook signature verification (valid + invalid), subscription lifecycle (checkout.completed, subscription.created, subscription.deleted), billing route auth guards
- 24 OAuth flow tests: LinkedIn/X/Instagram connect endpoints, PKCE code_challenge verification for Twitter, token encryption assertion, Google OAuth redirect + user create/find + JWT redirect
- 100% mocked — no real Stripe API calls, no real OAuth provider HTTP calls

## Task Commits

1. **Task 1: Stripe billing comprehensive verification** - `90724a0` (feat)
2. **Task 2: OAuth flow verification for all platforms** - `5b03867` (feat)

## Files Created/Modified

- `backend/tests/test_stripe_e2e.py` (685 lines) — Stripe billing E2E: checkout for 3 credit packages + custom plan, webhook HMAC verification, subscription lifecycle, billing route auth
- `backend/tests/test_oauth_flows.py` (801 lines) — OAuth flows: LinkedIn/X/Instagram connect+callback, PKCE verification, disconnect, connections list, Google OAuth user create/find/JWT

## Decisions Made

- `patch.object(google_module.settings, "google", mock_config)` used instead of `patch("config.settings")` for `auth_google.py` tests — the module imports `settings` at load time so `config.settings` patches don't propagate; patching the attribute on the already-imported module object does.
- Real `stripe.error.SignatureVerificationError` class used as `side_effect` in invalid-signature test — MagicMock for exception classes fails when the exception hierarchy is inspected by pytest.
- Twitter PKCE test verifies `code_verifier` presence in the token exchange POST body, not just `code_challenge` in the auth URL — validates the full PKCE round-trip.

## Deviations from Plan

None - plan executed exactly as written.

The test for `test_google_auth_redirects_when_configured` initially failed due to a settings mock propagation issue (Rule 1 — bug in test approach, not in production code). Fixed inline by switching from `patch("config.settings")` to `patch.object(module.settings, field)`. This is a test-authoring correction, not a production code change.

## Issues Encountered

- Google OAuth tests required `patch.object` on module-level settings rather than `patch("config.settings")`. Root cause: `auth_google.py` uses `settings` from a module-level `from config import settings` import. Once imported, `config.settings` patches don't reach the already-bound name in the routes module. Fixed immediately with `patch.object(google_module.settings, "google", mock_config)`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- E2E-06 and E2E-07 requirements verified and committed
- Stripe billing flows confirmed: checkout session creation, webhook signature validation, subscription lifecycle
- All 4 OAuth platforms verified with correct redirect URL construction, PKCE for X/Twitter, and encrypted token storage
- Ready for final phase 16 plans (security hardening, production ship)

---
*Phase: 16-e2e-audit-security-hardening-production-ship*
*Completed: 2026-04-01*
