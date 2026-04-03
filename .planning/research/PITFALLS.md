# Domain Pitfalls: v2.1 Production Hardening — Testing Sprint

**Domain:** Large-scale TDD testing sprint on an existing FastAPI + Motor + Celery/n8n codebase
**Researched:** 2026-04-01
**Overall confidence:** HIGH — grounded in live codebase inspection (781 tests collected, 3 active failures
observed, unawaited coroutine warnings catalogued) plus verified external sources.

---

## Preface: What Makes This Sprint Different

This is not greenfield TDD. You are writing 700+ net new tests against code that already exists and runs in
production. That inversion creates a specific failure mode profile:

- Tests expose bugs that were invisible — and fixing the bug can silently break adjacent tests.
- Mocks written to match current broken behavior become anti-tests after the fix.
- Coverage numbers can rise while real confidence falls if the wrong things are measured.
- The test suite itself can become a source of ordering-dependent failures that mask real regressions.

The pitfalls below are organized from most critical (cause test suite to lie to you) to moderate (waste sprint
velocity) to minor (create noise).

---

## Critical Pitfalls

Mistakes that cause the test suite to give false signals — passing when broken or failing when correct.

---

### Pitfall 1: Ordering-Dependent Test Failures From Shared Mock State

**What goes wrong:**
A test passes in isolation but fails when run after certain other tests. The root cause is that a previous
test patches a module-level object, fixture, or global variable and the patch leaks into the subsequent test.
In Python's unittest.mock, `patch()` calls in session-scoped fixtures or `autouse` fixtures with wrong scope
produce unreverted patches. The next test runs against the contaminated module state.

**Evidence from this codebase:**
`tests/test_sharing_notifications_webhooks.py::TestViralCard::test_analyze_returns_card_with_id_and_share_url`
passes in isolation and passes when its file runs alone (20/20 pass), but fails when the full 781-test suite
runs. The failure is an `ExceptionGroup` from Starlette's middleware task group — a sign that an async
resource (likely an httpx client or Motor connection) was patched by an earlier test and left in a broken
state. This is a live, confirmed ordering-dependent failure in the current codebase.

**Why it happens:**
- `session`-scoped or `module`-scoped fixtures that use `patch()` or `MagicMock()` do not revert between tests
- `with patch(...)` context managers used at module import time (not inside test functions)
- FastAPI `TestClient` or `AsyncClient` instances shared across tests in a class without per-test reset
- Module-level singletons (like the `db` object, `settings`, or LLM clients) partially patched by one test
  remain patched for subsequent tests because Python caches module objects

**Consequences:**
- Tests fail only in CI (full suite) but pass locally (partial suite) — creates trust erosion in CI
- Fix appears to work locally but CI reports failure — blocks merge and wastes engineer hours
- A real regression gets masked by a persistent ordering-dependent failure

**Prevention:**
- Use `function` scope for all mock fixtures. Never use `session` or `module` scope with mutable mock objects.
- Always use `unittest.mock.patch` as a context manager within the test body, or as a `@pytest.fixture` with
  `yield` and explicit function scope.
- Run `pytest --randomly-seed=12345` (with `pytest-randomly`) regularly to expose ordering sensitivity.
  Different seeds surface different ordering bugs. Run the full suite with at least 3 different seeds before
  declaring a batch of tests "clean".
- The `conftest.py` in this codebase already applies `collect_ignore` for live server scripts — extend this
  pattern to any fixture that touches real infrastructure objects.

**Detection:**
- Test passes with `pytest path/to/test.py` but fails with `pytest tests/`
- Error is a Starlette `ExceptionGroup` or event loop error in an otherwise unrelated test class
- `pytest --lf --tb=short` shows the failure disappears when only failed tests re-run

**Phase mapping:** Every phase. Treat as Day 1 hygiene. Run `pytest --randomly-seed=0 tests/` after every
wave of new tests before declaring the wave done.

---

### Pitfall 2: TDD Bug Fix Breaks Existing Tests Written Against the Old (Broken) Behavior

**What goes wrong:**
You write a failing test that exposes BUG-X. You fix the code to make the test pass. But now 3 existing tests
fail — they were written to match the old broken behavior and implicitly asserted that broken behavior was
correct. You now face a dilemma: are those 3 tests wrong, or did your fix introduce a regression?

**Concrete example for this codebase:**
The credit non-atomic deduction bug (BUG: race condition in `services/credits.py`) means that concurrent
requests can each read the same credit balance and both deduct from it. Existing tests may mock `find_one` to
return a balance, then mock `update_one`, asserting that `update_one` was called with a specific delta. After
the fix (adding MongoDB `$inc` with `find_one_and_update` and a minimum balance check), those tests will fail
because `find_one` and `update_one` are no longer called — `find_one_and_update` is. The tests were testing
the broken implementation, not the contract.

**Why it happens:**
When tests are written after the fact (retrofitting), they tend to test "how the code works" (implementation
tests) rather than "what the code does" (contract tests). Implementation tests are brittle by definition —
they break on any internal refactor, including the refactor needed to fix the bug.

**Consequences:**
- Sprint velocity collapses as each bug fix creates a cascade of test updates
- Engineers stop being sure whether a newly failing test means "regression" or "was testing wrong behavior"
- The distinction between "test needs updating" and "bug introduced" becomes opaque

**Prevention:**
- Before fixing a bug, audit every existing test that touches the affected function. Classify each as
  "implementation test" (tests how) or "contract test" (tests what). Update implementation tests to contract
  tests before making the production code change.
- Write the new failing test first (TDD). Fix the code. Run the full suite. For each newly-failing existing
  test, explicitly decide: (a) this test was wrong — update it to test behavior not implementation, or (b)
  this test was correct — my fix introduced a regression, revert and re-examine.
- Never delete a failing existing test without understanding why it failed. Document the decision in the PR
  description.

**Detection:**
- After a production code fix, more than 2-3 previously passing tests now fail
- The failing tests all mock the same internal function that was refactored
- Test failure message says "expected call to `update_one`" but production code now calls
  `find_one_and_update`

**Phase mapping:** Billing & Security phases (BUG: JWT fallback, non-atomic credits, webhook dedup). These
fixes touch heavily-mocked code paths. Highest risk of this pattern.

---

### Pitfall 3: Unawaited Coroutine Warnings Are Silent Test Bugs

**What goes wrong:**
`RuntimeWarning: coroutine 'X' was never awaited` appears in test output and is ignored as "just a warning."
In reality, each unawaited coroutine means an async function was called but its body never ran. The test
passed because the assertion checked a return value from a mock, not the actual execution of the async logic.
The test is green but testing nothing.

**Evidence from this codebase:**
The current suite produces at minimum 6 distinct unawaited coroutine warnings:

```
RuntimeWarning: coroutine 'fire_webhook' was never awaited
RuntimeWarning: coroutine 'cleanup_stale_running_jobs.<locals>._cleanup' was never awaited
RuntimeWarning: coroutine '_call_remotion.<locals>._do_render' was never awaited
RuntimeWarning: coroutine 'validate_media_output' was never awaited
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

Each of these represents a test that passes while the async function under test silently did nothing. When
`fire_webhook` is never awaited, the webhook firing path is untested — the test only verifies the code that
calls `fire_webhook`, not that the webhook actually fires.

**Why it happens:**
- `MagicMock()` used instead of `AsyncMock()` for an async function. When `MagicMock` is called on an async
  function, it returns a coroutine object (not the result). The coroutine is never awaited. The mock "passes"
  because the return value comparison still succeeds.
- `patch('module.async_func')` without `new_callable=AsyncMock` — the patch creates a `MagicMock` by
  default, which is synchronous.
- Tests that use `assert mock.called` without `await` for async paths.

**Consequences:**
- Test suite reports 100% of a module's happy paths passing, but the async code paths were never exercised
- A genuine bug in `fire_webhook` will not be caught until production
- Adding `filterwarnings = error::RuntimeWarning` to `pytest.ini` would turn these into immediate failures —
  do this now, before writing 700 more tests

**Prevention:**
- Add `filterwarnings = error::RuntimeWarning::DeprecationWarning` to `pytest.ini` immediately. This
  converts all unawaited coroutine warnings to test failures. Fix the 6 existing failures before the sprint
  starts.
- For every `patch()` call on an async function, use `new_callable=AsyncMock` explicitly.
- Audit rule: after writing any test that mocks an `async def` function, confirm `AsyncMock` is used and
  that the test body uses `await` where the production code does.
- Use `pytest -W error::RuntimeWarning` locally to verify no new unawaited coroutines are introduced.

**Detection:**
- `RuntimeWarning: coroutine '...' was never awaited` in test output
- `pytest -W error::RuntimeWarning` turns passing tests into failures
- A test for an async function has no `await` keyword anywhere in the test body

**Phase mapping:** All phases. Day 1 fix: add `filterwarnings = error` to `pytest.ini` before writing any
new tests. Forces immediate resolution of the 6 existing silent failures.

---

### Pitfall 4: Coverage Numbers That Lie — Line Coverage Without Branch Coverage

**What goes wrong:**
The sprint targets 85% line coverage and 95% billing coverage. Line coverage counts whether a line ran, not
whether all decision paths were tested. A function like:

```python
async def deduct_credits(user_id: str, amount: int) -> bool:
    user = await db.users.find_one({"user_id": user_id})
    if user and user["credits"] >= amount:
        await db.users.update_one(...)
        return True
    return False
```

A single test that passes `amount=10` against a user with `credits=100` achieves 100% line coverage but never
exercises the `credits < amount` branch — the path that hits the `return False` — and never exercises the
`user is None` path. These are exactly the paths that contain billing bugs.

**Evidence from this codebase:**
The known non-atomic credits bug exists in a function that almost certainly has existing line coverage from
the happy-path tests (credits are deducted successfully). The race condition lives in the gap between `find_one`
and `update_one` — a timing/atomicity issue that line coverage cannot measure at all.

**Why it happens:**
Line coverage tools (coverage.py in default mode) report line hit counts. Branch coverage requires explicit
`--branch` flag. Teams report "85% coverage" without specifying which metric, then treat it as equivalent to
"85% of behavior tested."

**Consequences:**
- 85% line coverage with no branch coverage on billing code can leave 40-60% of actual billing decision
  paths untested
- Coverage reports show green on `services/credits.py` while the race condition path is never exercised
- Meeting the 95% billing coverage target via line coverage alone is insufficient for a production billing
  system

**Prevention:**
- Measure branch coverage from the start: `pytest --cov=. --cov-branch --cov-report=term-missing`
- For billing and auth modules, require 95% branch coverage (not line coverage). This is a materially higher
  bar.
- For the concurrent race condition bug specifically: branch coverage cannot catch it. Write explicit
  concurrent tests using `asyncio.gather()` with multiple simultaneous credit deductions against the same
  user_id and assert the final balance is correct.
- Distinguish "coverage" from "confidence". Coverage measures execution. Confidence comes from assertions
  on the right invariants (e.g., "credits can never go below 0", "the same Stripe event is never processed
  twice").

**Detection:**
- `coverage run --branch` shows significantly lower branch coverage than line coverage on the same modules
- `coverage report --show-missing` shows uncovered branches in error paths and edge cases
- Billing tests all use the same happy-path fixture without testing `credits < amount`, `user not found`,
  `stripe event already processed`

**Phase mapping:** Phase 1 (Billing). Run `--cov-branch` from the start. Do not accept "85% coverage" as
met until branch coverage is the metric.

---

### Pitfall 5: Tests Written Against Celery Beat That No Longer Runs Beat

**What goes wrong:**
Tests assert that `celeryconfig.beat_schedule` contains specific task keys. The codebase migrated from Celery
beat to n8n cron triggers in v2.0. `celeryconfig.py` now explicitly sets `beat_schedule = {}`. Tests written
during v1.x development that checked the beat schedule now fail permanently.

**Evidence from this codebase:**
This is a live, confirmed failure:

```
FAILED tests/test_pipeline_e2e.py::TestBeatScheduleHasCleanupStaleJobs::test_beat_schedule_has_cleanup_stale_jobs
FAILED tests/test_pipeline_e2e.py::TestBeatScheduleHasCleanupStaleJobs::test_all_six_periodic_tasks_are_scheduled
```

The celeryconfig.py comment reads: "Beat schedule has been removed — all 7 periodic tasks are now driven by
n8n cron triggers calling POST /api/n8n/execute/{task_name}."

The tests are not wrong — they are testing the wrong thing. The correct tests for v2.1 should assert that
the n8n bridge endpoints exist and respond correctly, not that `beat_schedule` is populated.

**Why it happens:**
Sprint planning referenced "scheduled tasks" as a testing target without auditing which scheduler is now
canonical. v1.x tests persisted into v2.x without an ownership review.

**Consequences:**
- Two tests fail on every CI run, creating alert fatigue — engineers start ignoring "expected" CI failures
- When a real regression occurs, it gets dismissed as "probably another known failure"
- The tests document a contract (beat schedule) that no longer exists, misleading future engineers

**Prevention:**
- Before writing any new tests in a phase, run the full suite and triage all existing failures. Categorize:
  (a) tests for deprecated behavior — delete with documented reason, (b) tests for migrated behavior — update
  to test the new implementation, (c) tests for genuine regressions — fix the production code.
- Create a "test audit" step at the start of each sprint wave: `pytest --tb=no -q` → review all FAILs before
  adding new tests.
- Never allow known persistent failures in the CI baseline. A clean baseline is the only way to make new
  failures visible.

**Detection:**
- Test failure asserts something about a module that has a comment saying "migrated to X"
- `git log` on the failing test shows it was written for a previous architecture
- The production code behavior the test describes no longer matches the system design

**Phase mapping:** Day 1 of the sprint. Audit and delete/update the 3 existing failures before adding any
new tests. Start the sprint from a clean baseline.

---

## Moderate Pitfalls

Mistakes that waste velocity or create fragile tests without immediately falsifying results.

---

### Pitfall 6: Over-Mocking — Tests That Only Verify the Mock, Not the Code

**What goes wrong:**
A test mocks the database, the LLM client, and the Stripe client, then calls a route handler, then asserts
`mock_db.users.update_one.assert_called_once_with(...)`. The test passes. But it has only verified that the
production code calls `update_one` — not that the call will succeed, not that the query filter is correct,
not that the result is handled correctly. If the database interaction is refactored from `update_one` to
`find_one_and_update`, the test breaks even though behavior is preserved.

**Evidence from this codebase:**
The test suite uses `unittest.mock.patch("database.db")` as a shared conftest fixture. A significant
proportion of tests will be implementation tests against `mock_db.*` call assertions. The risk is highest
in the billing and credit paths where the exact MongoDB operation matters (atomic vs non-atomic).

**Why it happens:**
Over-mocking is the path of least resistance for external dependencies. It is fast to write and always
passes initially. AI-assisted code generation (including Claude Code) has a documented tendency toward
over-mocked test generation (arxiv.org/abs/2602.00409 found AI coding agents generate systematically
over-mocked tests).

**Consequences:**
- Tests pass through major behavioral bugs because only the call site is checked, not the data
- Coverage is high but confidence is low
- Refactoring production code requires proportional refactoring of all mocked tests

**Prevention:**
- Use a layered strategy:
  - Unit tests: mock external dependencies (db, LLM, Stripe), assert call contracts
  - Integration tests: use a real in-memory MongoDB (mongomock or testcontainers), assert actual data
  - E2E tests: use httpx.AsyncClient against the real FastAPI app with real in-memory DB
- For billing tests specifically, prefer mongomock over mock_db for the credit deduction tests. The bug is
  in the atomicity of the MongoDB operation — that cannot be tested without executing the actual query.
- For LLM tests: mock at the transport level (patch `anthropic.Anthropic.messages.create`) not at the
  service level. This preserves the LlmClient wrapper's behavior under test.
- Target: no more than 60% of billing tests should use pure mock_db assertions. The remaining 40% should
  use mongomock or testcontainers for integration-level verification.

**Detection:**
- Test body contains only `mock_X.assert_called_once_with(...)` assertions with no data assertions
- Test passes after any behavioral change that preserves the call site
- `pytest --cov --cov-branch` shows high coverage but the test has no assertions on the function's return
  value or side effects beyond call verification

**Phase mapping:** Phase 1 (Billing), Phase 2 (Security). Establish the layered strategy before writing
the first 255 billing tests.

---

### Pitfall 7: FastAPI Async Test Client Event Loop Conflicts

**What goes wrong:**
Tests using `httpx.AsyncClient` with FastAPI's `app` object produce `RuntimeError: Event loop is closed` or
`RuntimeError: This event loop is already running` when mixing `asyncio_mode = auto` (set in `pytest.ini`)
with synchronous test functions or when sharing a client instance across tests in a class.

**Evidence from this codebase:**
`pytest.ini` has `asyncio_mode = auto`. The Starlette ExceptionGroup failure in the viral card test (the
confirmed ordering failure) wraps an `anyio._backends._asyncio.TaskGroup.__aexit__` call. This is consistent
with an event loop lifecycle conflict between test cases.

**Why it happens:**
- `asyncio_mode = auto` creates a new event loop per test function by default. Fixtures that create
  `httpx.AsyncClient` at session or module scope run on a different loop than the test function.
- FastAPI's lifespan events (startup/shutdown) involve async context managers. If a TestClient instance is
  shared across tests, the lifespan runs once but subsequent tests operate on a "half-initialized" app.
- `anyio.create_task_group()` used by Starlette's BaseHTTPMiddleware requires a running event loop that
  matches the one that created the task group.

**Consequences:**
- Tests fail with cryptic ExceptionGroup errors instead of meaningful assertion failures
- The failure is non-deterministic (depends on event loop state, ordering of other tests)
- CI becomes unreliable because the failure rate changes with the number of tests

**Prevention:**
- For `httpx.AsyncClient` fixtures, use function scope: create and close the client per test, not per session.
  Accept the overhead — it is correct behavior.
- Use the FastAPI TestClient (synchronous) for simple request/response tests that do not need to exercise
  async middleware directly. Reserve `AsyncClient` for tests that explicitly test async streaming or SSE.
- When testing Starlette middleware behavior, create a minimal test app rather than using the full
  production `app` with all middleware registered.
- Configure pytest-asyncio explicitly: add `asyncio_default_fixture_loop_scope = "function"` to `pytest.ini`
  (in addition to `asyncio_mode = auto`) to prevent ambiguity in pytest-asyncio >=0.23.

**Detection:**
- `ExceptionGroup` or `anyio` in test failure traceback with no obvious assertion failure
- Test passes in isolation, fails in suite
- Failure involves Starlette middleware (BaseHTTPMiddleware, CORSMiddleware) even though test is not testing
  middleware behavior

**Phase mapping:** Phase 4 (Frontend/E2E integration tests). Also affects Phase 1 and 2 when writing route
handler integration tests.

---

### Pitfall 8: Stripe Webhook Tests Miss Signature Verification and Idempotency Paths

**What goes wrong:**
Tests mock the entire Stripe webhook handler and assert it processes events correctly. But the two most
important behaviors of the webhook handler are: (1) it rejects events with invalid signatures and (2) it
processes each event exactly once (idempotency). Neither of these is tested by "send an event, assert it was
processed." Both behaviors require specific test patterns.

**Relevance to this codebase:**
The known bugs include webhook deduplication (BUG: non-idempotent webhook processing) and Stripe
configuration issues (BUG: missing Price IDs). Tests for webhook behavior that do not cover these two
paths are testing the wrong things.

**Why it happens:**
The happy path (valid event, first time received, correct signature) is tested first and teams declare
webhook testing "done." The security path (invalid signature) and the reliability path (duplicate event)
require deliberate test design that is easy to skip under time pressure.

**Consequences:**
- A production deployment with broken signature verification is never caught in test
- Duplicate subscription activation (user charged twice, credits doubled) is not caught in test
- The webhook dedup bug that is known to exist remains unfixed because there is no test to make it fail

**Prevention:**
- Test the signature verification path explicitly: `stripe.WebhookSignature.verify_header` raises
  `SignatureVerificationError` for invalid signatures. Test this path first before the happy path.
  Use `patch("stripe.Webhook.construct_event", side_effect=stripe.error.SignatureVerificationError)`.
- For idempotency: test that calling the webhook handler twice with the same `event.id` results in exactly
  one database write. Pattern: call handler → assert write count = 1 → call handler again with same event →
  assert write count still = 1. This requires a mongomock or real DB fixture, not pure mock_db.
- Test timestamp tolerance: Stripe rejects webhook events with timestamps more than 300 seconds old. Test
  that your handler correctly rejects stale payloads.
- Test the `STRIPE_WEBHOOK_SECRET` not-configured path: if `settings.stripe.webhook_secret` is empty, the
  handler should return 400 immediately, not attempt processing.

**Detection:**
- Webhook tests only test the path where `construct_event` succeeds
- No test asserts `SignatureVerificationError` is handled as a 400 response
- No test calls the webhook handler with the same `event.id` twice

**Phase mapping:** Phase 1 (Billing). The webhook dedup fix is a named P0 bug. Tests for it must be written
before the fix so the fix can be TDD-driven.

---

### Pitfall 9: Concurrent Race Condition Tests That Cannot Actually Produce the Race

**What goes wrong:**
A test for the non-atomic credit deduction race condition uses `asyncio.gather()` to fire two concurrent
requests. But because Python's asyncio is single-threaded and the database mock is synchronous, both
"concurrent" coroutines execute sequentially on the same event loop turn. The race condition never actually
occurs in the test. The test passes without demonstrating the bug and passes after the fix without
verifying it was fixed.

**Why it happens:**
Asyncio concurrency does not produce true parallelism. Two coroutines in `asyncio.gather()` will interleave
at `await` points. If the race condition requires two operations to interleave between a `find_one` and
an `update_one` (which are both single `await` calls), the asyncio event loop will complete one entire
sequence before yielding to the other.

For a mock database, there is no yield between `find_one` and `update_one` because both are synchronous
operations wrapped in `AsyncMock`. No interleaving occurs. The test is a false negative.

**Prevention:**
- To test atomicity: test the MongoDB operation itself, not the Python concurrency. Verify that the
  production code uses an atomic MongoDB operation (`find_one_and_update` with `$inc` and a filter that
  includes `credits: {$gte: amount}`) rather than a read-modify-write sequence. If the operation is atomic
  at the query level, no concurrent test is needed — the atomicity guarantee comes from MongoDB.
- For true concurrency testing (load behavior under high request volumes), use `locust` or
  `pytest-benchmark` against a real running server, not unit test mocks.
- Write the atomicity test as: "assert that the production code calls `find_one_and_update` with the correct
  query (including the balance check in the filter, not just in Python)" — this is a contract test that
  verifies the correct MongoDB operation is used.

**Detection:**
- Test description says "concurrent" but uses `asyncio.gather()` with `AsyncMock` database
- Test for race condition passes before the fix is applied (false negative)
- Test does not assert anything about MongoDB query atomicity, only about call counts

**Phase mapping:** Phase 1 (Billing). Write the atomicity contract test: assert `find_one_and_update` is
called with a filter that prevents over-deduction at the query level.

---

### Pitfall 10: LightRAG and Pinecone Tests That Call Live External APIs

**What goes wrong:**
Integration tests for `services/vector_store.py` and `services/lightrag.py` hit the real Pinecone API and
the real LightRAG service. Each Pinecone test takes ~30 seconds. With 30 vector store tests in the billing
and core phases, test suite time increases by 15 minutes. Pinecone tests are documented as heavily flaky
on CI due to concurrent requests hitting the same index (GitHub: deepset-ai/haystack issue #2644).

**Why it happens:**
Vector store services are often written without dependency injection, making them hard to mock at the
right layer. Teams write integration tests against the live API because mocking feels like "testing the
mock, not the behavior."

**Consequences:**
- CI runtime exceeds 20 minutes, making TDD loops impractical
- Flaky Pinecone failures create false CI failures unrelated to the code under test
- Missing `PINECONE_API_KEY` in CI causes test collection to fail rather than skip

**Prevention:**
- Guard all live Pinecone and LightRAG tests with `pytest.mark.skipif(not os.getenv("PINECONE_API_KEY"), ...)`
- Use `unittest.mock.patch` on `pinecone.Index` (not on the ThookAI wrapper) for unit tests. The wrapper
  behavior (namespace isolation, error handling, retry) can be tested without a live connection.
- Use a separate `tests/integration/` directory for live-API tests that run only in CI environments where
  the API keys are available. Keep the main `tests/` directory free of live API calls.
- For LightRAG: mock `httpx.AsyncClient` at the transport level (the approach already used in
  `test_lightrag_isolation.py` — this pattern is correct and should be reused across all LightRAG tests).

**Detection:**
- Test fails with `pinecone.exceptions.UnauthorizedException` when `PINECONE_API_KEY` is not set
- Test takes >10 seconds in isolation (sign of a real network call)
- `pytest --co` shows the test collects fine but `pytest -k pinecone` reveals 30-second test times

**Phase mapping:** Phase 3 (Core features). Establish the mock strategy for vector store before writing
the 240 core feature tests.

---

## Minor Pitfalls

Matters that create friction and reduce output quality but do not falsify results.

---

### Pitfall 11: 85% Coverage Target Creates Incentive to Test Trivial Code

**What goes wrong:**
When coverage is a sprint completion criterion, engineers write tests for simple getters, property accessors,
and configuration validation rather than complex business logic. This is the fastest way to raise coverage
numbers. The `TIER_CONFIGS` dict in `services/credits.py` is easy to hit 100% on with a single test. The
webhook dedup logic is hard to test correctly. Coverage-chasing selects for easy tests, not important tests.

**Why it happens:**
Coverage tools report all code equally. There is no signal that `TIER_CONFIGS` is less important than
`handle_checkout_completed`. Sprint metrics that are purely coverage-percentage-based create perverse
incentives.

**Prevention:**
- Assign coverage targets by criticality, not evenly: 95% branch coverage for billing/auth, 80% for
  everything else.
- Use `coverage.py` exclusion comments (`# pragma: no cover`) for trivially unimportant code (config dicts,
  `__repr__` methods, type stubs) to prevent them from diluting coverage stats.
- Prioritize coverage of code paths that contain known bugs first. A test that exposes BUG-X is worth more
  than 10 tests for `build_plan_preview` edge cases.
- Track "P0 bug coverage" as a separate metric: all 4 known P0 bugs (JWT fallback, non-atomic credits,
  webhook dedup, LightRAG lambda injection) must have failing tests before fixes are applied.

**Detection:**
- Coverage is increasing but the known P0 bugs have no corresponding failing tests yet
- Test names describe trivial accessors (`test_tier_config_has_credits_field`)
- P0 bugs are fixed before tests that expose them are written

**Phase mapping:** All phases. Establish coverage priorities at the start of each wave.

---

### Pitfall 12: n8n Bridge Tests That Require a Running n8n Instance

**What goes wrong:**
`tests/test_n8n_bridge.py` and `tests/test_n8n_workflow_status.py` may call the n8n API directly. If the
n8n instance is not running locally or in CI, these tests silently skip or fail with connection errors,
creating a false clean test run.

**Why it happens:**
n8n is a self-hosted service that cannot be mocked in-process (unlike MongoDB or Redis). Tests for the n8n
bridge layer are tempting to write as integration tests against a live n8n instance, but this creates a CI
dependency that is fragile.

**Prevention:**
- Mock the `httpx.AsyncClient` used by the n8n bridge service at the transport level (same pattern as
  LightRAG isolation tests). Test the bridge service behavior (request construction, error handling, response
  parsing) without a live n8n instance.
- Use `pytest.mark.integration` to tag tests that require a live n8n instance. Exclude them from the default
  `pytest` run with `pytest -m "not integration"`.
- Contract tests: assert that the bridge constructs the correct HTTP request to n8n (correct URL, correct
  authentication header, correct payload schema). This verifies the integration contract without needing
  n8n to respond.

**Phase mapping:** Phase 1 (Billing) when testing Celery→n8n triggered tasks. Phase 3 (Core) when testing
content pipeline n8n workflows.

---

### Pitfall 13: Playwright E2E Tests That Hardcode Timing Assumptions

**What goes wrong:**
E2E tests for the content generation pipeline (which can take 30-60 seconds in real LLM calls) use
`page.wait_for_timeout(5000)` to wait for results. When the LLM is slow (cold start, high load), the test
times out. When the pipeline is fast (warm cache), the test passes on an intermediary loading state.
45% of E2E flaky test failures are caused by async timing assumptions (Semaphore research, 2025).

**Evidence from this codebase:**
The content generation pipeline goes through multiple status transitions: `pending → processing → reviewing`.
An E2E test that asserts "content appears in reviewing state" within 5 seconds will fail under realistic
LLM latency.

**Prevention:**
- Never use `waitForTimeout()` in Playwright tests. Replace with `waitForSelector('[data-testid=...]')` or
  `waitForResponse(url => url.includes('/api/content'))`.
- For long-running pipeline tests, mock the LLM at the service level and return a fixture response in <100ms.
  The E2E test verifies the UI flow, not the LLM output.
- Use `page.waitForLoadState('networkidle')` after triggering pipeline actions.
- Set realistic `expect.timeout` defaults in `playwright.config.ts`: `timeout: 30000` per test,
  `expect: { timeout: 10000 }` per assertion.
- Tag slow E2E tests with `@pytest.mark.slow` or Playwright's `test.slow()` and run them separately from
  the fast suite.

**Phase mapping:** Phase 4 (Frontend/E2E tests). Establish the timing conventions before writing 105 tests.

---

### Pitfall 14: Test Helper Functions That Become Load-Bearing Infrastructure

**What goes wrong:**
A `make_user()` helper is defined in `test_stripe_billing.py`. A similar `_make_user()` helper is defined in
`test_credits_billing.py`. Both exist independently. A third test file imports from one of them. When the
billing schema changes (e.g., a new required field `plan_builder_config`), all three helper definitions must
be updated independently, and the one that was missed produces misleading test failures.

**Evidence from this codebase:**
`test_stripe_billing.py` already defines `make_user()` and `_user_id()` helper factories at module level.
As the test suite grows from 781 to 1050+ tests, this pattern will proliferate.

**Prevention:**
- Move shared test factories to `tests/conftest.py` or a dedicated `tests/factories.py` module. Import
  from there.
- Use a consistent naming convention: all factory functions are `make_X()` and live in a single place.
- When a domain model changes (e.g., `users` schema adds a field), update `make_user()` in one place.
  All tests that use `make_user()` pick up the change automatically.

**Detection:**
- The same helper function name appears in more than one test file
- `grep -r "make_user\|_user_id\|make_job\|make_persona" tests/` returns results from more than 3 files

**Phase mapping:** Day 1. Audit existing helpers in `conftest.py` and the major test files. Consolidate
before writing 700 more tests.

---

## Phase-Specific Warnings

How the pitfalls map to the 4 sprint phases.

| Phase | Test Targets | Highest-Risk Pitfalls | Specific Mitigation |
|-------|-------------|----------------------|---------------------|
| Phase 1: Billing (255 tests) | Non-atomic credits, webhook dedup, JWT fallback, Stripe flows | P2 (fix breaks existing tests), P4 (branch coverage), P8 (webhook signature/idempotency), P9 (fake concurrency tests) | Use mongomock for credit tests; write dedup test before fix; branch coverage from the start |
| Phase 2: Security/Auth (100 tests) | JWT validation, OAuth flows, rate limiting, OWASP | P1 (ordering failures), P3 (unawaited coroutines), P7 (event loop conflicts) | All auth mocks use `function` scope; run `--randomly-seed` variants; test JWT expiry with real time manipulation |
| Phase 3: Core Features (240 tests) | Content pipeline, LangGraph, media orchestration, LightRAG | P6 (over-mocking), P10 (live API calls), P12 (n8n bridge) | Mock LLM at transport level; use existing LightRAG httpx mock pattern; no live Pinecone in default suite |
| Phase 4: Frontend/E2E (105 tests) | Playwright flows, load testing, Docker smoke | P7 (async race conditions), P13 (timing assumptions) | No `waitForTimeout`; mock LLM for E2E; `--retries=2` in CI; test slow tag for pipeline tests |

---

## Pre-Sprint Hygiene Checklist

Actions to take before writing test #1.

- [ ] **Fix the 3 existing failures.** Delete the 2 Celery beat schedule tests (architecture is now n8n).
  Diagnose and fix the viral card ordering failure. Start with a clean baseline.
- [ ] **Add `filterwarnings = error::RuntimeWarning` to `pytest.ini`.** This converts the 6 unawaited
  coroutine warnings to failures. Fix all 6 before proceeding.
- [ ] **Audit `asyncio_default_fixture_loop_scope`.** Add `asyncio_default_fixture_loop_scope = "function"`
  to `pytest.ini` to prevent event loop scope ambiguity.
- [ ] **Consolidate test helpers.** Move `make_user()`, `_user_id()`, and any other shared factories to
  `tests/conftest.py`.
- [ ] **Add `pytest-randomly` to dev dependencies.** Run `pytest --randomly-seed=0 tests/` and
  `pytest --randomly-seed=1234 tests/` and confirm zero ordering-dependent failures.
- [ ] **Add `--cov-branch` to the coverage command.** Update the CI coverage command to use branch coverage.
  Record the current branch coverage baseline before writing new tests.

---

## "Looks Done But Isn't" Checklist for Testing Sprint

Things that can appear complete but leave the suite in a misleading state.

- [ ] **Coverage is 85%:** Check that it is 85% _branch_ coverage, not line coverage. Confirm billing/auth
  modules are at 95% branch coverage specifically.
- [ ] **All 1050 tests pass:** Confirm `pytest --randomly-seed=0` and `pytest --randomly-seed=1234` both
  pass. A suite that passes at a fixed seed but fails at another seed has hidden ordering failures.
- [ ] **Webhook dedup is tested:** Confirm there is a test that calls the Stripe webhook handler twice with
  the same `event.id` and asserts exactly one database write occurred.
- [ ] **JWT fallback is tested:** Confirm there is a test that calls the onboarding endpoint with the wrong
  model name and asserts it fails (not silently falls back to mock persona).
- [ ] **Non-atomic credits fix is tested:** Confirm there is a test that asserts `find_one_and_update` (or
  equivalent atomic operation) is called, not a read-modify-write sequence.
- [ ] **LightRAG lambda injection is tested:** Confirm there is a test that sends a payload containing
  common injection strings to the LightRAG query endpoint and asserts they are sanitized.
- [ ] **No live external API calls in the default `pytest` run:** Confirm `pytest tests/ -q` completes in
  under 60 seconds. If it takes longer, a test is calling a live API.
- [ ] **No unawaited coroutine warnings:** Confirm `pytest -W error::RuntimeWarning tests/` exits clean.

---

## Sources

- [Are Coding Agents Generating Over-Mocked Tests? An Empirical Study](https://arxiv.org/abs/2602.00409) —
  AI agents systematically over-mock; applies to Claude Code-generated tests in this sprint
- [FastAPI Async Tests](https://fastapi.tiangolo.com/advanced/async-tests/) — AsyncClient vs TestClient
  event loop behavior (HIGH confidence — official FastAPI docs)
- [pytest-asyncio Concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html) — Loop scope,
  auto mode behavior (HIGH confidence — official docs)
- [Testing with Celery](https://docs.celeryq.dev/en/stable/userguide/testing.html) — Eager mode
  limitations, worker thread cleanup issues (HIGH confidence — official Celery docs)
- [Mocking Stripe Signature Checks in pytest](https://til.simonwillison.net/pytest/pytest-stripe-signature)
  — `patch("stripe.WebhookSignature.verify_header")` pattern (MEDIUM confidence)
- [Branch Coverage vs Line Coverage](https://about.codecov.io/blog/line-or-branch-coverage-which-type-is-right-for-you/)
  — When line coverage lies (HIGH confidence — authoritative source)
- [Troubleshooting Fixture Leakage in pytest](https://www.mindfulchase.com/explore/troubleshooting-tips/testing-frameworks/troubleshooting-fixture-leakage-and-state-contamination-in-pytest.html)
  — Session-scoped fixture mutation patterns (MEDIUM confidence)
- [Preventing Race Conditions in Async Python](https://johal.in/preventing-race-conditions-in-async-python-code/)
  — asyncio.gather and its limits for testing true concurrency (MEDIUM confidence)
- [How to Avoid Flaky Tests in Playwright](https://semaphore.io/blog/flaky-tests-playwright) —
  45% of E2E flakiness is async timing; waitForTimeout anti-pattern (MEDIUM confidence)
- [Pinecone Testing Strategy](https://github.com/deepset-ai/haystack/issues/2644) — Flaky CI from
  concurrent requests to shared Pinecone index (MEDIUM confidence — community verified)
- [TDD Anti-Patterns](https://www.codurance.com/publications/tdd-anti-patterns-chapter-1) — Inspector
  anti-pattern, coverage pressure causing trivial tests (HIGH confidence — widely cited)
- [Software Testing Anti-Patterns](https://blog.codepipes.com/testing/software-testing-antipatterns.html)
  — Comprehensive anti-pattern catalogue (HIGH confidence — widely cited)

---

*Pitfalls research for: ThookAI v2.1 — Production Hardening, 50x Testing Sprint*
*Researched: 2026-04-01*
*Grounded in: live codebase inspection (781 tests, 3 confirmed failures, 6 unawaited coroutine warnings)*
