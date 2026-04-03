# Phase 17: Test Foundation + Billing & Payments - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean CI baseline (fix 3 existing failures, 6 unawaited coroutine warnings), install coverage infrastructure (pytest-cov, pytest-randomly, .coveragerc), standardize fixtures in conftest.py, configure CI matrix. Then write 255 billing tests covering checkout, subscriptions, credit atomicity, webhook idempotency, volume pricing. TDD fix 3 P0 bugs: JWT fallback secret, non-atomic add_credits, missing webhook deduplication. Enforce 95%+ branch coverage on billing modules.

</domain>

<decisions>
## Implementation Decisions

### Test Foundation
- **D-01:** Fix 3 existing broken tests before writing any new ones — clean baseline is prerequisite
- **D-02:** Add `filterwarnings = error::RuntimeWarning` to `pytest.ini` to enforce coroutine discipline
- **D-03:** Add `pytest-randomly` to detect ordering-dependent failures at scale
- **D-04:** Install `pytest-cov` 7.1.0 with `.coveragerc` including `concurrency = greenlet,thread` and `branch = true`
- **D-05:** Standardize fixtures in root `conftest.py` — async client factory, mock DB (mongomock-motor), mock user, respx mock
- **D-06:** CI matrix: separate jobs per domain with per-domain coverage thresholds (billing 95%, others 85%)

### P0 Bug Fixes (TDD)
- **D-07:** JWT fallback secret — write failing test first exposing auth bypass on malformed tokens, then fix production code
- **D-08:** Non-atomic add_credits — write failing test with `asyncio.gather` concurrent requests, verify race condition, then fix to use `find_one_and_update`
- **D-09:** Webhook deduplication — write failing test delivering same Stripe event twice, verify double-activation, then add idempotency guard

### Billing Test Strategy
- **D-10:** Use `mongomock-motor` for credit atomicity tests (not AsyncMock) — must verify MongoDB filter/operation semantics
- **D-11:** Use `respx` for Stripe HTTP interception — real httpx code runs and gets covered
- **D-12:** 95%+ branch coverage enforced on `services/credits.py`, `services/stripe_service.py`, `routes/billing.py`
- **D-13:** Test file organization: `tests/billing/` subdirectory with `test_credits.py`, `test_stripe.py`, `test_billing_routes.py`, `test_webhooks.py`, `test_checkout.py`, `test_subscriptions.py`

### Claude's Discretion
- Exact test counts per file
- Mock factory implementation details
- CI YAML configuration specifics
- Which 3 existing tests are broken and how to fix them

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Billing Code
- `backend/services/credits.py` — Credit deduction, tier configs, add_credits (P0 bug target)
- `backend/services/stripe_service.py` — Checkout, webhook handling, subscription management
- `backend/routes/billing.py` — Billing API routes

### Test Infrastructure
- `backend/tests/conftest.py` — Current fixtures, collect_ignore list
- `backend/pytest.ini` — Current config (asyncio_mode = auto only)
- `backend/requirements.txt` — Current test dependencies

### Auth (for JWT bug)
- `backend/auth_utils.py` — JWT creation/verification, get_current_user dependency

### Research
- `.planning/research/SUMMARY.md` — Testing sprint research summary
- `.planning/research/STACK.md` — Tool versions and configuration
- `.planning/research/PITFALLS.md` — 14 pitfalls including baseline hygiene, over-mocking, coverage gaps

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `conftest.py` — Has basic fixtures but needs standardization; 8-file collect_ignore list
- Existing test patterns: `patch("database.db")`, `AsyncMock`, `httpx.AsyncClient` + `ASGITransport`
- `test_n8n_bridge.py` — 20 tests with good HMAC/dependency override patterns

### Established Patterns
- `from database import db` — lazy import inside function bodies
- `app.dependency_overrides[get_current_user]` — auth bypass in tests
- `patch("routes.module.db")` — route-level DB mocking (not `database.db`)

### Integration Points
- `pytest.ini` — needs coverage, randomly, filterwarnings additions
- `requirements.txt` — needs pytest-cov, pytest-randomly, mongomock-motor, respx, Faker
- `.coveragerc` — new file for coverage configuration
- `.github/workflows/` — CI matrix configuration

</code_context>

<specifics>
## Specific Ideas

No specific requirements — research recommendations guide the approach. User trusts technical judgment on testing infrastructure and TDD bug fix approach.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-test-foundation-billing-payments*
*Context gathered: 2026-04-03*
