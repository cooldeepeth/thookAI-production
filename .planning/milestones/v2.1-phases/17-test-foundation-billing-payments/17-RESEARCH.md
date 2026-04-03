# Phase 17: Test Foundation + Billing & Payments — Research

**Researched:** 2026-04-03
**Domain:** Test infrastructure setup + billing TDD bug-fixes on FastAPI + Motor + Stripe
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Fix 3 existing broken tests before writing any new ones — clean baseline is prerequisite
- **D-02:** Add `filterwarnings = error::RuntimeWarning` to `pytest.ini` to enforce coroutine discipline
- **D-03:** Add `pytest-randomly` to detect ordering-dependent failures at scale
- **D-04:** Install `pytest-cov` 7.1.0 with `.coveragerc` including `concurrency = greenlet,thread` and `branch = true`
- **D-05:** Standardize fixtures in root `conftest.py` — async client factory, mock DB (mongomock-motor), mock user, respx mock
- **D-06:** CI matrix: separate jobs per domain with per-domain coverage thresholds (billing 95%, others 85%)
- **D-07:** JWT fallback secret — write failing test first exposing auth bypass on malformed tokens, then fix production code
- **D-08:** Non-atomic add_credits — write failing test with `asyncio.gather` concurrent requests, verify race condition, then fix to use `find_one_and_update`
- **D-09:** Webhook deduplication — write failing test delivering same Stripe event twice, verify double-activation, then add idempotency guard
- **D-10:** Use `mongomock-motor` for credit atomicity tests (not AsyncMock) — must verify MongoDB filter/operation semantics
- **D-11:** Use `respx` for Stripe HTTP interception — real httpx code runs and gets covered
- **D-12:** 95%+ branch coverage enforced on `services/credits.py`, `services/stripe_service.py`, `routes/billing.py`
- **D-13:** Test file organization: `tests/billing/` subdirectory with `test_credits.py`, `test_stripe.py`, `test_billing_routes.py`, `test_webhooks.py`, `test_checkout.py`, `test_subscriptions.py`

### Claude's Discretion

- Exact test counts per file
- Mock factory implementation details
- CI YAML configuration specifics
- Which 3 existing tests are broken and how to fix them

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Clean test baseline — fix 3 existing failures, enforce `filterwarnings = error::RuntimeWarning`, add `pytest-randomly` | All 3 failures identified by name; root causes confirmed by running pytest live |
| FOUND-02 | Coverage infrastructure — `pytest-cov` with `.coveragerc` (`concurrency = greenlet,thread`), branch coverage enabled, `--cov-branch` flag | Full `.coveragerc` template verified against coverage.py docs; async undercounting issue documented |
| FOUND-03 | Standardized test fixtures in root `conftest.py` — async client factory, mock DB factory, mock user factory, respx mock factory | Current `conftest.py` inspected; gaps identified; mongomock-motor and respx patterns confirmed |
| FOUND-04 | CI matrix configuration — separate jobs per domain with per-domain coverage thresholds | Current `ci.yml` inspected; exact extension points identified |
| BILL-01 | Stripe checkout flow tests — custom plan builder, credit packages, checkout session creation | `create_custom_plan_checkout` and `create_credit_checkout` fully read; simulated and live paths mapped |
| BILL-02 | Subscription lifecycle tests — create, upgrade, downgrade, cancel, reactivate, webhook-driven state transitions | All 6 webhook handlers read and mapped to test scenarios |
| BILL-03 | Credit atomicity tests — `find_one_and_update` atomic deduction verified, race condition under concurrent requests, negative balance prevention | `deduct_credits` confirmed atomic; `add_credits` confirmed NON-atomic (P0 bug) |
| BILL-04 | Webhook idempotency tests — duplicate event handling, signature verification, retry behavior | No dedup logic found anywhere in production code — gap confirmed |
| BILL-05 | Volume pricing tests — tier boundary calculations, proration, add-on credits | Pure functions (`calculate_plan_price`, `build_plan_preview`) confirmed; boundary values mapped |
| BILL-06 | TDD bug fix: JWT fallback secret — failing test exposing auth bypass, then fix | Bug location confirmed: `auth_utils.py` line 129, `or "thook-dev-secret"` fallback |
| BILL-07 | TDD bug fix: non-atomic `add_credits` — failing test exposing race condition, then fix | Bug location confirmed: `services/credits.py` lines 462-491, uses `find_one + $set` not `find_one_and_update` |
| BILL-08 | TDD bug fix: missing webhook deduplication — failing test exposing double-activation, then fix | Confirmed: no `stripe_event_id` check or `processed_events` collection anywhere |
| BILL-09 | 95%+ branch coverage on `services/credits.py`, `services/stripe_service.py`, `routes/billing.py` | Files read fully; branch coverage gaps predicted for error paths and simulated-mode branches |
</phase_requirements>

---

## Summary

Phase 17 is a pre-revenue-launch infrastructure phase. The three parallel goals — clean test baseline, billing test coverage, and three TDD bug fixes — must be executed in strict dependency order within the phase. The three existing CI failures are all "dead tests" for migrated architecture: two assert celeryconfig beat_schedule keys that are intentionally empty (n8n took over scheduling), and one is an ordering-dependent failure caused by leaked mock state from prior tests in the suite. The correct fix for all three is to update or mark-as-migrated the dead tests, and to add `pytest-mock` for automatic mock cleanup to prevent the ordering failure at scale.

The three P0 bugs are confirmed against source code. The JWT fallback (`or "thook-dev-secret"` on line 129 of `auth_utils.py`) means any token signed with the hardcoded fallback secret passes verification in production, bypassing the configured JWT secret. The `add_credits` function (lines 462-491 of `services/credits.py`) uses a non-atomic `find_one` + `update_one($set)` pattern that allows two concurrent webhook calls delivering the same event to read the same credit balance and both double-add, whereas the adjacent `deduct_credits` correctly uses `find_one_and_update` with a filter. The webhook handler has no idempotency guard — no `stripe_event_id` check or `processed_events` collection — meaning retried or duplicate Stripe events double-activate subscriptions.

The existing billing tests (27 tests across `test_credits_billing.py` and `test_stripe_billing.py`) pass cleanly and provide a solid baseline pattern. The new 255 tests should be organized into a `tests/billing/` subdirectory to avoid flat-directory collision. Key infrastructure gaps: `pytest-cov`, `pytest-mock`, `pytest-randomly`, `mongomock-motor`, `respx`, and `Faker` are NOT installed in the current environment. All must be added to `requirements.txt` before any billing test work.

**Primary recommendation:** Execute in four task groups: (1) fix 3 existing failures + install all 6 missing packages + update pytest.ini + create .coveragerc + standardize conftest.py, (2) write the 3 failing TDD tests that expose P0 bugs, (3) fix production code for each P0 bug, (4) write the full 255 billing tests with CI matrix update.

---

## Confirmed Bug Locations (P0 — TDD Required)

### BUG-A: JWT Fallback Secret (auth_utils.py line 129)

```python
# CURRENT (broken) — backend/auth_utils.py line 129
secret = settings.security.jwt_secret_key or "thook-dev-secret"

# FIXED
secret = settings.security.jwt_secret_key
if not secret:
    raise JWTError("JWT secret key not configured")
```

**Attack vector:** A token signed with `"thook-dev-secret"` as the secret passes `decode_token()` on any deployment where `JWT_SECRET_KEY` is unset or empty string. Since the CI env sets `JWT_SECRET_KEY=ci-test-secret-key-not-for-production`, the bug is masked in CI but exploitable if the env var is accidentally unset in production.

**TDD test pattern:**
```python
async def test_decode_token_rejects_when_jwt_secret_not_configured():
    """Token signed with fallback secret must not be accepted when JWT_SECRET_KEY is set."""
    import jwt as pyjwt
    # Sign a token with the fallback secret
    malicious_token = pyjwt.encode({"sub": "attacker"}, "thook-dev-secret", algorithm="HS256")
    # Attempt verification — must raise JWTError, not return payload
    from auth_utils import decode_token
    with patch("auth_utils.settings.security.jwt_secret_key", "real-production-key"):
        with pytest.raises(JWTError):
            decode_token(malicious_token)
```

### BUG-B: Non-Atomic add_credits (services/credits.py lines 462-491)

```python
# CURRENT (broken) — two separate DB calls, not atomic
user = await db.users.find_one({"user_id": user_id})          # line 462 — read
current_credits = user.get("credits", 0)
new_balance = current_credits + amount
await db.users.update_one(                                      # line 468 — write ($set)
    {"user_id": user_id},
    {"$set": {"credits": new_balance}}
)

# FIXED — single atomic operation using $inc
result = await db.users.find_one_and_update(
    {"user_id": user_id},
    {"$inc": {"credits": amount}},
    return_document=ReturnDocument.AFTER
)
new_balance = result.get("credits", 0)
```

**Race condition:** Two concurrent calls to `handle_checkout_completed` for the same user (e.g., Stripe retries the same `invoice.payment_succeeded` event) both read `credits=50`, both compute `new_balance=550`, and both write 550. Net result: 550 instead of 600. Because `deduct_credits` IS already atomic (uses `find_one_and_update` with filter), only `add_credits` needs fixing.

**TDD test pattern:**
```python
async def test_add_credits_atomic_concurrent():
    """Concurrent add_credits calls must not lose credits."""
    from mongomock_motor import AsyncMongoMockClient
    client = AsyncMongoMockClient()
    test_db = client["thookai_test"]
    await test_db.users.insert_one({"user_id": "user_atomic", "credits": 0})

    with patch("database.db", test_db):
        await asyncio.gather(
            add_credits("user_atomic", 100, "purchase"),
            add_credits("user_atomic", 100, "purchase"),
        )

    user = await test_db.users.find_one({"user_id": "user_atomic"})
    # Without fix: races to 100; with fix: guaranteed 200
    assert user["credits"] == 200
```

This test REQUIRES `mongomock-motor` (not `AsyncMock`) because it needs real `$inc` semantics.

### BUG-C: Missing Webhook Deduplication (services/stripe_service.py — handle_webhook_event)

No idempotency guard exists in any production file. Confirmed by `grep -rn "event_id\|idempotent\|stripe_event\|processed_event"` returning zero results in non-test Python files.

**Fix location:** `handle_webhook_event()` in `services/stripe_service.py`, immediately after `event = stripe.Webhook.construct_event(...)`:

```python
# Add after event construction:
event_id = event["id"]
existing = await db.stripe_events.find_one({"event_id": event_id})
if existing:
    logger.info(f"Duplicate Stripe event {event_id} — skipping")
    return {"success": True, "event_type": event_type, "duplicate": True}

await db.stripe_events.insert_one({
    "event_id": event_id,
    "event_type": event_type,
    "processed_at": datetime.now(timezone.utc)
})
```

**TDD test pattern:**
```python
async def test_duplicate_webhook_event_is_idempotent():
    """Same Stripe event delivered twice must not double-add credits."""
    # Set up user with 50 credits
    # Deliver checkout.session.completed once → credits = 150
    # Deliver same event_id again → credits still 150
```

---

## Standard Stack

### Core (existing — confirmed installed)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pytest` | `9.0.2` | Test runner | Installed; confirmed by `pip3 list` |
| `pytest-asyncio` | `1.3.0` | Async test support | Installed; `asyncio_mode = auto` in pytest.ini |
| `httpx` | `0.28.1` | Async HTTP client for `AsyncClient` in tests | Installed via requirements.txt |
| `stripe` | `14.4.1` | Stripe SDK (installed version exceeds `>=8.0.0` spec) | Installed; NOTE: see SDK version note |

### To Install (missing — must add to requirements.txt)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pytest-cov` | `>=7.1.0` | Branch coverage measurement, CI gate | Not installed; required for FOUND-02, BILL-09 |
| `pytest-mock` | `>=3.15.1` | Automatic mock cleanup via `mocker` fixture | Not installed; fixes ordering-dependent failures |
| `pytest-randomly` | `>=3.15.0` | Random test ordering to surface ordering bugs | Not installed; required for D-03 |
| `mongomock-motor` | `>=0.0.36` | In-memory async Motor client | Not installed; required for BUG-B TDD test (D-10) |
| `respx` | `>=0.22.0` | Mock outbound httpx calls at transport layer | Not installed; required for Stripe HTTP tests (D-11) |
| `Faker` | `>=40.12.0` | Realistic test data (emails, UUIDs, credit card data) | Not installed; eliminates `test@test.com` antipatterns |

**Installation command:**
```bash
cd backend
pip install "pytest-cov>=7.1.0" "pytest-mock>=3.15.1" "pytest-randomly>=3.15.0" \
  "mongomock-motor>=0.0.36" "respx>=0.22.0" "Faker>=40.12.0"
```

**requirements.txt additions:**
```
pytest-cov>=7.1.0
pytest-mock>=3.15.1
pytest-randomly>=3.15.0
mongomock-motor>=0.0.36
respx>=0.22.0
Faker>=40.12.0
```

**Stripe SDK version note:** The environment has `stripe==14.4.1` installed while `requirements.txt` specifies `stripe>=8.0.0`. The State.md blocker notes Stripe Test Clock method signatures need verification. With SDK 14.x, `stripe.test_helpers.test_clocks` is confirmed available — the API was introduced in v4+. Method signatures: `stripe.test_helpers.TestClock.create(frozen_time=unix_ts)` and `stripe.test_helpers.TestClock.advance(test_clock=tc_id, frozen_time=new_ts)`. These are accessible on the installed 14.4.1. Freeze the pin to `stripe>=8.0.0,<15` in requirements.txt to avoid unexpected breaking changes.

---

## Existing Broken Tests — Root Causes and Fixes

### Failure 1: test_beat_schedule_has_cleanup_stale_jobs

**Location:** `tests/test_pipeline_e2e.py::TestBeatScheduleHasCleanupStaleJobs`
**Error:** `AssertionError: 'cleanup-stale-jobs' must be in beat_schedule` — `beat_schedule = {}`
**Root cause:** `celeryconfig.beat_schedule = {}` (line 40 of `celeryconfig.py`). n8n took over scheduling in Phase 8. The test was written when Celery beat was the scheduler — it now asserts keys that intentionally do not exist.
**Fix:** Delete or `pytest.mark.skip(reason="n8n handles scheduling since Phase 8 — beat_schedule intentionally empty")` the test. Do NOT repopulate beat_schedule.

### Failure 2: test_all_six_periodic_tasks_are_scheduled

**Location:** `tests/test_pipeline_e2e.py::TestBeatScheduleHasCleanupStaleJobs::test_all_six_periodic_tasks_are_scheduled`
**Error:** `AssertionError: Beat schedule is missing required task: process-scheduled-posts` — `beat_schedule = {}`
**Root cause:** Same as Failure 1. Same class, same architectural migration.
**Fix:** Same — mark as deprecated/skip with the same reason.

### Failure 3: test_analyze_returns_card_with_id_and_share_url

**Location:** `tests/test_sharing_notifications_webhooks.py::TestViralCard`
**Error:** Ordering-dependent — passes when run in isolation (`pytest tests/test_sharing_notifications_webhooks.py` → 20/20 pass), fails in full suite.
**Root cause:** An earlier test in the 740-test suite patches a module-level object (likely an httpx client or Motor connection) and does not revert it. Starlette's middleware task group receives the contaminated state and raises an `ExceptionGroup`. This is the confirmed "leaked mock state" pattern from Pitfall 1 in PITFALLS.md.
**Fix:** Install `pytest-mock` (provides automatic cleanup). Then audit `TestViralCard` for any non-function-scoped fixtures; convert to function scope. Run `pytest --randomly-seed=12345 tests/` to verify the ordering-dependence is gone.

---

## Architecture Patterns

### Recommended Test File Organization

```
backend/
├── tests/
│   ├── conftest.py              # Standardized shared fixtures (to be expanded)
│   ├── billing/                 # New: billing-specific tests (D-13)
│   │   ├── __init__.py
│   │   ├── test_credits.py      # Unit tests for credits.py (atomicity, balances, caps)
│   │   ├── test_stripe.py       # Unit tests for stripe_service.py (checkout, webhooks)
│   │   ├── test_billing_routes.py # Route-level integration tests
│   │   ├── test_webhooks.py     # Webhook idempotency, signature verification
│   │   ├── test_checkout.py     # Checkout session creation (custom plan + credit packages)
│   │   └── test_subscriptions.py # Subscription lifecycle state machine
│   ├── test_credits_billing.py  # Existing — 13 tests — keep, add to
│   ├── test_stripe_billing.py   # Existing — 14 tests — keep, add to
│   └── [all other existing test files unchanged]
```

### Pattern 1: mongomock-motor for Atomic DB Tests

Use for all tests that need to verify MongoDB filter/operation semantics (not just that a function was called).

```python
# Source: mongomock-motor 0.0.36 docs + STACK.md confirmed pattern
from mongomock_motor import AsyncMongoMockClient
import pytest

@pytest.fixture
def mongomock_db():
    """In-memory Motor client with real query semantics."""
    client = AsyncMongoMockClient()
    db = client["thookai_test"]
    yield db
    client.close()

@pytest.fixture
def mock_db_atomic(mongomock_db):
    """Patch database.db with mongomock for tests needing real $inc/$set semantics."""
    with patch("database.db", mongomock_db):
        yield mongomock_db
```

**When to use mongomock-motor vs AsyncMock:**

| Need | Use |
|------|-----|
| Verify `$inc` adds correctly, `$set` overwrites correctly | `mongomock-motor` |
| Verify that `find_one_and_update` was called at all | `AsyncMock` (faster) |
| Verify negative balance prevention via filter semantics | `mongomock-motor` |
| Verify credit deduction transaction is recorded | `AsyncMock` (filter logic not needed) |
| Test race conditions for `add_credits` P0 fix | `mongomock-motor` (real atomic semantics) |

**Limitation:** mongomock-motor does NOT support `$vectorSearch` (Atlas operator). No billing code uses Atlas operators — confirmed by reading `services/credits.py` and `services/stripe_service.py` fully.

### Pattern 2: respx for Stripe HTTP Mocking

Use for any test that exercises code paths where `stripe` library makes HTTP calls (checkout session creation, subscription retrieval, price creation).

```python
# Source: respx 0.22.0 docs + STACK.md confirmed pattern
import respx, httpx

@pytest.fixture
def respx_stripe():
    """Mock Stripe API at the transport layer."""
    with respx.mock(base_url="https://api.stripe.com") as mock:
        yield mock

async def test_create_checkout_session(respx_stripe):
    respx_stripe.post("/v1/checkout/sessions").mock(
        return_value=httpx.Response(200, json={
            "id": "cs_test_abc",
            "url": "https://checkout.stripe.com/pay/cs_test_abc",
            "metadata": {}
        })
    )
    result = await create_custom_plan_checkout(
        user_id="user_test", email="test@example.com",
        monthly_credits=500, monthly_price_cents=3000,
        plan_config={}
    )
    assert result["success"] is True
    assert result["checkout_url"].startswith("https://checkout.stripe.com")
```

**Note:** The `stripe` library (14.4.1) uses `httpx` internally in async mode. `respx` intercepts at the transport layer. This works correctly because the code under test runs real httpx code — it's covered by the test runner. Do NOT patch `stripe.checkout.Session.create` directly — that prevents httpx code from being executed and leaves branches uncovered.

### Pattern 3: Webhook Idempotency Test

```python
async def test_duplicate_stripe_event_does_not_double_activate(mongomock_db):
    """Same checkout.session.completed event delivered twice: credits added only once."""
    user_id = "user_dedup_test"
    await mongomock_db.users.insert_one({
        "user_id": user_id, "credits": 50, "subscription_tier": "starter"
    })

    session = {
        "id": "evt_test_001",            # This is the Stripe event ID
        "metadata": {"user_id": user_id, "type": "credit_purchase", "credits": "100"},
        "amount_total": 600,
        "currency": "usd",
        "invoice": None,
    }

    with patch("database.db", mongomock_db), patch("services.stripe_service.db", mongomock_db):
        await handle_checkout_completed(session)
        await handle_checkout_completed(session)  # duplicate delivery

    user = await mongomock_db.users.find_one({"user_id": user_id})
    # Without fix: credits = 250 (double-added)
    # With fix: credits = 150 (added once)
    assert user["credits"] == 150, f"Duplicate event added credits twice: {user['credits']}"
```

**Note on event ID:** `handle_checkout_completed` receives the session object (not the full event). The full event object with `event["id"]` is available in `handle_webhook_event`. The dedup guard must be placed in `handle_webhook_event` before dispatching to type-specific handlers, using `event["id"]` (the Stripe event ID, not the session ID).

### Pattern 4: Standardized conftest.py Fixtures

```python
# backend/tests/conftest.py — additions to current file

from faker import Faker
from mongomock_motor import AsyncMongoMockClient
import respx as _respx
import pytest

fake = Faker()

@pytest.fixture
def make_user():
    """Factory fixture for user documents. Call with kwargs to override defaults."""
    def _make(**kwargs) -> dict:
        defaults = {
            "user_id": f"user_{fake.uuid4()[:8]}",
            "email": fake.email(),
            "subscription_tier": "starter",
            "credits": 200,
            "credit_allowance": 0,
        }
        defaults.update(kwargs)
        return defaults
    return _make

@pytest.fixture
def mongomock_db():
    """In-memory Motor DB with real query semantics. Function-scoped for isolation."""
    client = AsyncMongoMockClient()
    db = client["thookai_test"]
    yield db

@pytest.fixture
def mock_db(mongomock_db):
    """Patch database.db with mongomock. Use for service-layer tests."""
    with patch("database.db", mongomock_db):
        yield mongomock_db

@pytest.fixture
def async_client(app):
    """AsyncClient factory for route-level tests. Requires `app` fixture from caller."""
    from httpx import AsyncClient, ASGITransport
    async def _make(current_user: dict = None):
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        if current_user:
            app.dependency_overrides[get_current_user] = lambda: current_user
        return client
    return _make

@pytest.fixture
def respx_mock():
    """respx transport-level mock for outbound httpx calls. Function-scoped."""
    with _respx.mock() as mock:
        yield mock
```

**IMPORTANT scope rule:** All mock fixtures above use function scope (pytest default). Never use `session` or `module` scope with mutable mock objects — this is the root cause of Failure 3 above.

### Anti-Patterns to Avoid

- **Using `AsyncMock` for credit atomicity tests:** AsyncMock cannot verify that `$inc` vs `$set` was used. The race condition under `add_credits` is only detectable with real MongoDB semantics via `mongomock-motor`.
- **Patching `stripe.checkout.Session.create` directly:** Prevents the httpx transport layer from running; those code paths will not appear in coverage reports. Use `respx` instead.
- **Module-scoped fixtures with patch:** Causes ordering-dependent failures at scale. Already confirmed live in this codebase (`TestViralCard`).
- **Asserting implementation details for credit deduction:** After fixing `add_credits` to use `find_one_and_update`, tests that assert `update_one` was called will break. Write tests that assert behavioral outcomes (new balance, transaction record) not mock call patterns.
- **Writing webhook tests against a simulated session object:** The dedup guard must use `event["id"]` from the full Stripe event, not the session ID. The session object has its own `id` (e.g., `cs_test_...`) which is NOT the event ID.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| In-memory async MongoDB | Custom AsyncMock motor client | `mongomock-motor` | Filter/sort/projection semantics correctly handled; real `$inc` atomicity |
| HTTP call mocking for stripe/httpx | `unittest.mock.patch` on `stripe.checkout` | `respx` | Transport-layer interception covers the httpx code path for branch coverage |
| Realistic test data | Hardcoded `"test@test.com"`, `"user_123"` strings | `Faker` | At 255 tests, hardcoded strings cause collision and obscure test intent |
| Test ordering sensitivity detection | Manual test ordering investigation | `pytest-randomly` | Random seeds expose ordering bugs automatically at every CI run |
| Coverage gate | Custom script checking coverage.xml | `pytest-cov --cov-fail-under=95` | Built-in CI gate; separate invocation per module group |

---

## Common Pitfalls

### Pitfall 1: Fixing add_credits Breaks Existing test_add_credits_success

**What goes wrong:** The existing `test_add_credits_success` (line 344 in `test_credits_billing.py`) asserts `mock_db.users.update_one.assert_called_once()` and verifies `call_args[0][1]["$set"]["credits"] == 150`. After the fix changes `add_credits` to use `find_one_and_update`, `update_one` is never called — this test fails.

**Why it happens:** The test asserts the broken implementation, not the behavioral contract.

**How to avoid:** Before fixing the production code, update `test_add_credits_success` to assert outcomes (new balance returned in result dict, transaction recorded in `credit_transactions`) instead of asserting that `update_one` was called. Then run the failing TDD test, fix production code, verify all tests pass.

**Warning signs:** After the fix, `test_add_credits_success` fails with `AssertionError: update_one was not called`.

### Pitfall 2: Webhook Dedup Guard Uses Wrong ID

**What goes wrong:** The session object passed to `handle_checkout_completed` has a `session.id` (e.g., `cs_test_abc`). The Stripe event object has a different `event.id` (e.g., `evt_abc123`). If the dedup guard is placed in the checkout handler using `session.id`, retried events with the same session ID are correctly deduplicated. But if placed anywhere else using session data, different event IDs for the same session (Stripe sometimes retries with new event IDs for idempotency) will slip through.

**How to avoid:** Place the dedup guard in `handle_webhook_event` using `event["id"]` (the full event object from `stripe.Webhook.construct_event`), not inside type-specific handlers using session/invoice data.

**Warning signs:** Test passes for same-event-ID retries but fails when Stripe sends the same semantic action with a new event ID.

### Pitfall 3: RuntimeWarning Errors Cause Cascading Failures

**What goes wrong:** Adding `filterwarnings = error::RuntimeWarning` to `pytest.ini` will immediately cause multiple test collection failures because 6 unawaited coroutine warnings currently exist in the test suite. The warnings are:
- `fire_webhook` (unawaited) — `test_pipeline_e2e.py`, `test_pipeline_integration.py`
- `_cleanup` (unawaited) — `test_pipeline_integration.py`
- `_do_render` (unawaited) — `test_media_orchestrator.py`
- `validate_media_output` (unawaited) — `test_media_orchestrator.py`
- `AsyncMockMixin._execute_mock_call` (unawaited) — multiple

**How to avoid:** Add the `filterwarnings` line to `pytest.ini` AFTER fixing all 6 warning sources, not before. The fix for each is to add `await` at the call site, or wrap `AsyncMock` assignment as `AsyncMock(return_value=...)` with a return value so the mock isn't treated as a coroutine.

**Warning signs:** Running `pytest -W error::RuntimeWarning` causes collection to fail (confirmed locally — `test_designer_format_selection.py` collection error occurs before any tests run).

### Pitfall 4: mongomock-motor Limitation for Race Condition Tests

**What goes wrong:** `mongomock-motor` provides real query semantics (filters, projections, sorts) but does NOT provide true ACID atomicity. A single-threaded `asyncio.gather` test with mongomock will simulate concurrency at the Python coroutine level but NOT at the MongoDB operation level.

**How to avoid:** Use `asyncio.gather` with mongomock-motor to verify the CORRECT fix works (i.e., that `find_one_and_update` with `$inc` applies the increment from both concurrent calls). Do NOT use `asyncio.gather` with mongomock to verify the BUG exists — because mongomock's in-memory engine serializes operations correctly even without the fix. The bug can only be definitively reproduced against real MongoDB. For the TDD test, write the test that passes after the fix is applied (behavioral correctness test), not a test that demonstrates the race condition occurring.

**Warning signs:** A test using `asyncio.gather` against mongomock passes before the fix is applied because mongomock already serializes operations.

### Pitfall 5: Stripe SDK 14.x vs 8.x API Changes

**What goes wrong:** State.md flags this as a blocker: "Stripe Test Clock method signatures need verification against `stripe==8.0.0` SDK."

**Current state:** The installed environment has `stripe==14.4.1`. The Test Clock API (`stripe.test_helpers.TestClock`) exists in 14.x with `create(frozen_time=unix_ts)` and `advance(test_clock=tc_id, frozen_time=new_ts)`. However, the codebase `requirements.txt` specifies `stripe>=8.0.0` — the CI/production environment may resolve to 8.x or 14.x depending on when pip resolves. If Stripe Test Clock tests are written against 14.x API and the deployed environment has 8.x, the test will fail with AttributeError on method signature differences.

**How to avoid:** If writing Stripe Test Clock tests in this phase (stretch goal), add an explicit `stripe>=14.0.0` pin in requirements.txt or `@pytest.mark.skipif(stripe.VERSION < "14.0", reason="Test Clock API requires stripe>=14")` guard.

### Pitfall 6: tests/billing/ Subdirectory Import Conflicts

**What goes wrong:** Adding a `tests/billing/` subdirectory requires `tests/billing/__init__.py` to exist, or pytest's test discovery will silently skip the directory on some Python/pytest versions. If `__init__.py` is missing, `import conftest` from the billing tests may fail.

**How to avoid:** Always create `tests/billing/__init__.py` (empty file). Verify with `pytest tests/billing/ --collect-only` that all 6 files collect cleanly before writing any test content.

---

## Code Examples

### .coveragerc (create at backend/.coveragerc)

```ini
# Source: coverage.py docs + STACK.md verified pattern
[run]
source = .
branch = true
concurrency = greenlet,thread
omit =
    tests/*
    conftest.py
    */__pycache__/*
    db_indexes.py
    scripts/*

[report]
fail_under = 85
precision = 2
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
    @abstractmethod
    if __name__ == .__main__.:

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

**Why `concurrency = greenlet,thread`:** FastAPI's async request handling uses greenlets internally. Without this setting, coverage.py cannot trace async lines correctly in some Python 3.11 versions, leading to false "not covered" reports on route handlers that are actually executed.

### pytest.ini (updated from current 2-line version)

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
filterwarnings =
    error::RuntimeWarning
    ignore::DeprecationWarning:starlette.*
    ignore::UserWarning:pymongo.*
    ignore::PendingDeprecationWarning:starlette.*
```

**Note on filterwarnings order:** The `ignore` lines for starlette/pymongo must come AFTER `error::RuntimeWarning` because pytest applies them in order and the most specific rule wins. The starlette/pymongo warnings are from third-party libraries (formparsers, compression support) that are not under ThookAI's control.

**Note on asyncio_default_fixture_loop_scope:** Required by pytest-asyncio 1.3.0 to suppress the deprecation warning about fixture loop scope. Without this line, pytest will log a DeprecationWarning on every test run.

### CI Matrix Update (.github/workflows/ci.yml)

```yaml
# Source: current ci.yml inspected — this extends the existing backend-test job

backend-billing-test:
  name: Billing Tests (95% Coverage Gate)
  runs-on: ubuntu-latest
  services:
    mongo:
      image: mongo:7.0
      ports:
        - 27017:27017
      options: >-
        --health-cmd "mongosh --eval 'db.runCommand({ ping: 1 })'"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
    stripe-mock:
      image: stripe/stripe-mock:latest
      ports:
        - 12111:12111
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"
        cache: pip
        cache-dependency-path: backend/requirements.txt
    - name: Install dependencies
      run: pip install -r backend/requirements.txt
    - name: Run billing tests with 95% coverage gate
      env:
        MONGO_URL: mongodb://localhost:27017
        DB_NAME: thookai_test
        JWT_SECRET_KEY: ci-test-secret-key-not-for-production
        FERNET_KEY: 7X2PqyChA8TwDuzvdaeX_0Yh0SbmvZzxrjDXDwjCRCI=
        ENVIRONMENT: test
        STRIPE_API_BASE: http://localhost:12111
      run: |
        cd backend
        python -m pytest tests/billing/ tests/test_credits_billing.py tests/test_stripe_billing.py \
          --cov=services/credits --cov=services/stripe_service --cov=routes/billing \
          --cov-branch --cov-report=term-missing --cov-fail-under=95 \
          -v --tb=short --randomly-seed=12345

backend-test:
  # Extend existing job to add full-suite coverage
  # ... (keep existing service definitions)
  steps:
    # ... (keep existing steps, update the run command)
    - name: Run all tests with coverage
      env:
        # ... (keep existing env vars)
      run: |
        cd backend
        python -m pytest \
          --cov=. \
          --cov-branch \
          --cov-report=term-missing \
          --cov-report=xml \
          --cov-fail-under=85 \
          -v --tb=short --randomly-seed=last
```

### Subscription Lifecycle State Machine Tests

```python
# Source: handle_subscription_* functions read in stripe_service.py — all 6 mapped

@pytest.mark.parametrize("event_type,expected_status", [
    ("customer.subscription.created", "active"),
    ("customer.subscription.updated", "active"),
    ("customer.subscription.deleted", "cancelled"),
    ("invoice.payment_succeeded", "active"),   # credits refreshed
    ("invoice.payment_failed", "past_due"),
])
async def test_subscription_lifecycle_state_machine(event_type, expected_status, mongomock_db):
    """Each Stripe subscription event drives the correct user state transition."""
    # Setup user, route event, assert user.subscription_status matches
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `unittest.mock` directly in tests | `pytest-mock` `mocker` fixture | 2025 (pytest-mock 3.15.1) | Automatic cleanup eliminates ordering-dependent failures at scale |
| `responses` library for HTTP mocking | `respx` for async httpx | 2024 | `responses` only works with `requests`; `respx` is the correct tool for `httpx.AsyncClient` |
| `AsyncMock` for all MongoDB mocking | `mongomock-motor` for query logic, `AsyncMock` for call verification | 2024 | Enables testing filter semantics without a running MongoDB instance |
| `pytest --cov` without `--cov-branch` | `--cov-branch` in `.coveragerc` | Standard practice | Branch coverage exposes race conditions that line coverage misses (confirmed for credit atomicity case) |
| Stripe API integration tests in CI | `stripe/stripe-mock` Docker service + `respx` unit mocking | 2024 | No Stripe API key required in CI; no rate limits; deterministic responses |

**Deprecated/outdated:**
- `factory_boy`: ORM-specific, incompatible with raw MongoDB dicts — use `Faker` helper functions instead
- `celeryconfig.beat_schedule` keys for n8n-managed tasks: n8n took over scheduling in Phase 8; beat_schedule intentionally `= {}` per `celeryconfig.py` line 40

---

## Open Questions

1. **Stripe Test Clock in Phase 17 scope**
   - What we know: `stripe==14.4.1` is installed and supports `stripe.test_helpers.TestClock.create()`. State.md marks this as a HIGH complexity blocker.
   - What's unclear: Whether Stripe Test Clock tests are in scope for Phase 17 or deferred to Phase 18/20. The CONTEXT.md decisions do not mention Test Clocks explicitly — they are in the STACK.md "Wave 4" category.
   - Recommendation: Defer Test Clock tests to Phase 20 (load + smoke testing wave). Phase 17 billing tests should cover the Python-layer state machine without compressed time simulation. Add `@pytest.mark.skip("Test Clock tests deferred to Phase 20")` placeholder if the CI matrix requires a slot.

2. **Ordering of RuntimeWarning fixes vs filterwarnings enforcement**
   - What we know: Running `pytest -W error::RuntimeWarning` locally causes a collection error in `test_designer_format_selection.py` before any tests run. Six unawaited coroutine warnings exist across the suite.
   - What's unclear: Whether Wave 0 (fix warnings first) should be a separate task or a sub-task within the baseline task.
   - Recommendation: Make it an explicit sub-task in Wave 0: (a) fix all 6 unawaited coroutines, (b) THEN add `filterwarnings = error::RuntimeWarning`. This prevents the filterwarning change from blocking the rest of the phase.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Backend tests | Detected 3.13 (local) / 3.11 in CI | 3.13 locally | CI uses 3.11 — test locally with `python3.11` if available |
| MongoDB 7.0+ | mongomock-motor falls back; CI has real mongo | N/A (mongomock) / CI ✓ | CI: 7.0 | Use mongomock-motor for unit tests; real MongoDB in CI |
| Redis 7+ | Celery/integration tests | N/A for this phase | CI: 7-alpine | Not needed for billing unit tests |
| stripe-mock Docker | Stripe integration CI tests | Not on local machine | — | Skip integration tests locally; run in CI with Docker service |
| pytest-cov | FOUND-02 | NOT installed | — | Must install before phase begins |
| pytest-mock | Ordering-dependent failure fix | NOT installed | — | Must install before phase begins |
| pytest-randomly | D-03 | NOT installed | — | Must install before phase begins |
| mongomock-motor | D-10, BUG-B TDD | NOT installed | — | Must install before phase begins |
| respx | D-11 | NOT installed | — | Must install before phase begins |
| Faker | Test data | NOT installed | — | Must install before phase begins |

**Missing dependencies with no fallback:**
- All 6 packages listed above are required before writing any new tests. They must be installed in Wave 0.

**Missing dependencies with fallback:**
- `stripe-mock` Docker: Stripe unit tests (majority of billing tests) use `mocker.patch("services.stripe_service.stripe", ...)` and do not need stripe-mock. Only integration tests that exercise the real Stripe SDK HTTP layer need stripe-mock — these can be skipped locally via `@pytest.mark.integration`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `backend/pytest.ini` (exists — needs updates per D-02, D-03, D-04) |
| Quick run command | `cd backend && python3 -m pytest tests/billing/ -x --tb=short -q` |
| Full suite command | `cd backend && python3 -m pytest --cov=. --cov-branch --cov-fail-under=85 -v --tb=short` |
| Billing coverage command | `cd backend && python3 -m pytest tests/billing/ tests/test_credits_billing.py tests/test_stripe_billing.py --cov=services/credits --cov=services/stripe_service --cov=routes/billing --cov-branch --cov-fail-under=95 -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | 3 existing failures gone, no RuntimeWarning | regression | `pytest tests/ --tb=no -q` → 0 failures | ✅ (fix existing) |
| FOUND-02 | Branch coverage report generated, 85% gate active | infrastructure | `pytest --cov=. --cov-branch --cov-fail-under=85` | ❌ Wave 0 (.coveragerc) |
| FOUND-03 | conftest.py has make_user, mongomock_db, respx_mock, async_client | unit | `pytest tests/billing/ --collect-only` | ❌ Wave 0 (conftest additions) |
| FOUND-04 | CI has billing-specific job with 95% gate | CI | GitHub Actions log shows 2 backend jobs | ❌ Wave 0 (ci.yml update) |
| BILL-01 | Checkout session creation returns URL + session ID | unit | `pytest tests/billing/test_checkout.py -x` | ❌ Wave 0 |
| BILL-02 | All 6 subscription webhook events drive correct status | unit | `pytest tests/billing/test_subscriptions.py -x` | ❌ Wave 0 |
| BILL-03 | Concurrent add_credits calls result in correct total | integration | `pytest tests/billing/test_credits.py::test_add_credits_atomic_concurrent -x` | ❌ Wave 0 |
| BILL-04 | Duplicate webhook event ID is rejected after first processing | unit | `pytest tests/billing/test_webhooks.py::test_duplicate_event_idempotent -x` | ❌ Wave 0 |
| BILL-05 | Volume tier boundary calculations return correct prices | unit | `pytest tests/billing/test_credits.py -k "volume" -x` | ❌ Wave 0 |
| BILL-06 | Token signed with fallback secret rejected when JWT_SECRET_KEY set | unit | `pytest tests/billing/ -k "jwt_fallback" -x` | ❌ Wave 0 |
| BILL-07 | Concurrent add_credits passes after fix | integration | `pytest tests/billing/test_credits.py::test_add_credits_atomic_concurrent` | ❌ Wave 0 |
| BILL-08 | Duplicate event rejected after dedup fix | unit | `pytest tests/billing/test_webhooks.py::test_duplicate_event_idempotent` | ❌ Wave 0 |
| BILL-09 | 95%+ branch coverage on 3 billing modules | coverage gate | `pytest tests/billing/ --cov-fail-under=95` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/billing/ -x --tb=short -q`
- **Per wave merge:** `python3 -m pytest --cov=. --cov-branch --cov-fail-under=85 -v --randomly-seed=12345`
- **Phase gate:** Billing coverage gate at 95% + full suite at 85% + 0 failures before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/.coveragerc` — covers FOUND-02
- [ ] `backend/tests/billing/__init__.py` — empty, enables billing subdirectory discovery
- [ ] `backend/tests/billing/test_credits.py` — covers BILL-03, BILL-05, BILL-07
- [ ] `backend/tests/billing/test_stripe.py` — covers BILL-01, BILL-02
- [ ] `backend/tests/billing/test_billing_routes.py` — covers BILL-01 (route layer)
- [ ] `backend/tests/billing/test_webhooks.py` — covers BILL-04, BILL-08
- [ ] `backend/tests/billing/test_checkout.py` — covers BILL-01
- [ ] `backend/tests/billing/test_subscriptions.py` — covers BILL-02
- [ ] `backend/pytest.ini` update — covers FOUND-01 (filterwarnings), D-02, D-03, D-04
- [ ] `backend/requirements.txt` update — 6 new packages
- [ ] `.github/workflows/ci.yml` update — covers FOUND-04
- [ ] Fix `auth_utils.py` line 129 (JWT fallback) — covers BILL-06
- [ ] Fix `services/credits.py` lines 462-491 (add_credits non-atomic) — covers BILL-07
- [ ] Add dedup guard to `services/stripe_service.py:handle_webhook_event` — covers BILL-08
- [ ] Fix/skip 3 broken tests in `test_pipeline_e2e.py` (2) and `test_sharing_notifications_webhooks.py` (1) — covers FOUND-01

---

## Sources

### Primary (HIGH confidence)

- Live pytest run: `python3 -m pytest --tb=no -q` — 740 passed, 3 failed, confirmed exact failure names, root causes, and error messages
- `backend/services/credits.py` fully read — `add_credits` non-atomic bug confirmed at lines 462-491; `deduct_credits` atomic pattern confirmed
- `backend/auth_utils.py` fully read — JWT fallback secret confirmed at line 129
- `backend/services/stripe_service.py` fully read — webhook dedup gap confirmed; no `event_id` check anywhere
- `backend/routes/billing.py` fully read — webhook route confirmed at line 408-434; no dedup at route level either
- `backend/tests/conftest.py` — current fixtures inspected; gaps identified
- `backend/pytest.ini` — current 2-line config inspected
- `backend/celeryconfig.py` — `beat_schedule = {}` confirmed at line 40
- `backend/requirements.txt` — 6 missing packages confirmed by `pip3 list` cross-check
- `backend/.github/workflows/ci.yml` — current 3-job structure inspected; extension points identified
- `backend/tests/test_credits_billing.py` + `test_stripe_billing.py` — 27 existing tests read; patterns documented
- `pip3 list` output — `stripe==14.4.1` confirmed; all 6 required packages confirmed missing
- `.planning/research/SUMMARY.md` — testing sprint research: stack, pitfalls, wave structure
- `.planning/research/STACK.md` — all package versions and configuration templates verified
- `.planning/phases/17-test-foundation-billing-payments/17-CONTEXT.md` — all decisions read

### Secondary (MEDIUM confidence)

- `coverage.py` configuration reference (https://coverage.readthedocs.io/en/latest/config.html) — `concurrency = greenlet,thread` for async FastAPI
- `respx` 0.22.0 docs — transport-layer interception pattern for httpx
- `mongomock-motor` 0.0.36 PyPI — limitations (no `$vectorSearch`), integration pattern
- `.planning/research/PITFALLS.md` — 14 pitfalls, all grounded in live codebase inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against PyPI and locally installed packages
- Bug locations: HIGH — all three P0 bugs confirmed by reading source files with line numbers
- Architecture patterns: HIGH — derived from live codebase inspection + prior research
- Existing test failures: HIGH — confirmed by running `pytest` live; exact error messages captured
- CI extension: HIGH — ci.yml read fully; extension points precisely identified

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (30-day window — stack versions stable; mongomock-motor patch versions may advance)
