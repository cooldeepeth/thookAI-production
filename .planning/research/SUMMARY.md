# Project Research Summary

**Project:** ThookAI v2.1 — Production Hardening (50x Testing Sprint)
**Domain:** Large-scale TDD retrofit on an existing FastAPI + Motor + n8n + LightRAG + LangGraph SaaS platform
**Researched:** 2026-04-01
**Confidence:** HIGH

---

## Executive Summary

ThookAI v2.1 is a test infrastructure build-out sprint, not a feature sprint. The platform has 768 existing tests but lacks branch coverage measurement, has zero frontend or E2E tests, carries 3 known CI failures that erode alert signal, and has 4 confirmed P0 bugs with no failing tests to drive the fixes. The research is emphatic that this sprint — retrofitting TDD onto a production codebase — follows different rules than greenfield TDD. The dominant risk is not writing too few tests; it is writing tests that assert implementation details rather than behavioral contracts, causing each bug fix to cascade into test churn that consumes velocity without improving confidence.

The recommended approach is a strict four-wave structure ordered by revenue risk. Wave 1 (billing and auth) must happen first and in TDD order: write a failing test that exposes the P0 bug, then fix the production code, then verify the fix did not break existing tests. Before any new tests are written, three preparatory actions are mandatory: (1) delete or update the 3 existing CI failures to establish a clean baseline, (2) add `filterwarnings = error::RuntimeWarning` to `pytest.ini` to surface the 6 confirmed unawaited coroutine silent bugs, and (3) install `pytest-mock` to enable automatic mock cleanup. Without these steps, the suite becomes unreliable as scale increases.

The single greatest structural risk in this sprint is the ordering-dependent test failure pattern already confirmed live in the codebase — `test_sharing_notifications_webhooks.py::TestViralCard` passes in isolation but fails in full-suite runs due to leaked mock state. This pattern will amplify as 700 new tests are added unless `pytest-randomly` is run after every wave to detect ordering sensitivity. The stack additions are minimal and precisely justified: six backend packages, three frontend packages, one E2E framework. All versions are verified against the project's Python 3.11.11 and Node 18 environments.

---

## Key Findings

### Recommended Stack

The existing test foundation (pytest, pytest-asyncio, httpx) is solid but missing the tooling needed to reach 1,050+ tests with 85%+ branch coverage. Every new package has a specific, non-overlapping purpose. The most consequential gaps are: no branch coverage enforcement (the stated 85% target has no enforcement mechanism), no automatic mock cleanup (the root cause of ordering failures at scale), and zero frontend and E2E infrastructure.

**Core new technologies:**

- `pytest-cov >=7.1.0` — branch coverage measurement and CI gate — must configure `branch = true` and `concurrency = greenlet,thread` in `backend/.coveragerc` to prevent async FastAPI line undercounting; add `--cov-fail-under=85` globally and run a separate billing-scoped pass at `--cov-fail-under=95`
- `pytest-mock >=3.15.1` — automatic mock cleanup after every test function — eliminates the entire class of ordering-dependent failures caused by unreverted patches; the current `unittest.mock` usage is compatible and does not need rewriting
- `mongomock-motor >=0.0.36` — in-memory async Motor client for integration tests that need real query semantics — required to test credit atomicity (the P0 bug) since AsyncMock cannot verify MongoDB filter logic
- `respx >=0.22.0` — mock outbound httpx calls (Anthropic, Stripe, Perplexity, n8n, LightRAG) at the transport layer — the correct tool for async httpx; patching at the Python level is fragile
- `Faker >=40.12.0` — realistic test data generation — eliminates `test@test.com` antipatterns at 1,000-test scale; do NOT use `factory_boy` (designed for ORM models, MongoDB dicts do not benefit)
- `locust >=2.43.4` — load testing for concurrency validation — pure Python, no separate toolchain; place in `tests/locustfile.py` excluded from pytest collection via `pytest.ini` `testpaths`
- `@testing-library/user-event >=14.x` + `@testing-library/jest-dom >=6.x` + `msw >=2.7.x` — frontend component testing on top of CRA's built-in Jest+RTL; do NOT install Jest separately or eject CRA — it causes version conflicts
- `@playwright/test >=1.50.x` — E2E at repo root targeting the full stack — superior to Cypress for SSE testing (required by the notification system) and multi-tab scenarios; install Chromium only in CI
- `stripe/stripe-mock` (Docker service) — Stripe API mock for integration tests only; unit tests mock `stripe.Webhook.construct_event` via pytest-mock

### Expected Features (Test Categories and Priority)

Research frames "features" as test coverage categories. Priority ordering is: revenue risk × bug probability × blast radius.

**Wave 1 — Must reach full coverage before launch (revenue at risk):**
- Billing webhook idempotency + dedup — P0 confirmed; duplicate `checkout.session.completed` events double-activate subscriptions and corrupt the financial ledger
- Atomic credit deduction — P0 confirmed; non-atomic `find_one` + `update_one` race allows negative balance under concurrent requests
- JWT fallback path lockdown — P0 confirmed; fallback that accepts malformed tokens grants unauthenticated access to all `/api/*` routes
- Subscription lifecycle state machine — trial → active → cancelled → downgrade path must be verified for all `customer.subscription.*` Stripe events
- Auth rate limiting — brute-force protection is a legal/compliance requirement for any paid platform; test concurrent burst (100 req/s) and verify 429 threshold

**Wave 2 — Required before first paying user:**
- LangGraph node-level isolation — each agent (Commander, Scout, Thinker, Writer, QC) testable with deterministic LLM mocks; foundational for all pipeline regression protection
- LightRAG per-user isolation + lambda client fix — BUG-4 confirmed; lambda-scoped client leaks connection state across users
- Publishing token refresh + expiry simulation — platform tokens expire silently; scheduled posts fail with no user alert
- Custom plan price calculation purity tests — 20 pure function tests for `build_plan_preview` and `calculate_plan_price`; no mocks needed; highest ROI for financial accuracy
- CORS + CSP + NoSQL injection security tests

**Wave 3 — Before public announcement:**
- n8n webhook contract tests (schema drift detection between FastAPI and n8n payloads)
- Media orchestration format routing (verify Designer → Orchestrator → provider routing for all 8 format types)
- Agency RBAC enforcement (viewer/editor/owner role gates on publish, approve, member management)
- SSE tenant scoping (cross-tenant event leakage test)
- Playwright E2E: auth → onboard → generate → approve → schedule → billing upgrade full funnel

**Wave 4 — Quality bar completion:**
- Locust load test (50 concurrent users, credit deduction stress, Celery queue depth, verify atomicity holds)
- Docker Compose smoke test (FastAPI + MongoDB + Redis + n8n + LightRAG + Remotion all healthy)
- Stripe Test Clock lifecycle (trial → active → renewal → cancel compressed to minutes)
- Final coverage report at 85%+ line with branch and 95%+ billing branch

**Anti-features to explicitly avoid:**
- Integration tests against real Stripe API in CI (slow, flaky, requires live keys — use SDK mocks)
- Real LLM calls in unit/integration tests (non-deterministic, 30+ minute CI runs; move to `tests/evals/` gated behind a flag)
- Single giant "everything" integration test (fails at step 3, gives no signal on steps 4-50)
- 100% line coverage as the only metric (creates coverage theater; billing needs branch coverage to be meaningful)

### Architecture Approach

The v2.1 sprint adds no new product architecture — it overlays test infrastructure onto the existing v2.0 system (FastAPI + LangGraph agents + n8n + LightRAG + Remotion + Celery). The key architectural insight for testing is that the v2.0 service boundaries are already well-defined and HTTP-first, making each component independently mockable at the transport layer rather than requiring live services. The Playwright E2E layer lives at repo root (sibling to `backend/` and `frontend/`) and targets the full stack running via Docker Compose.

**Major components and their test strategies:**

1. **Billing routes + services** — mongomock-motor for atomicity and state machine tests; SDK-level mocking for Stripe checkout/webhook; separate pytest run for `services/credits.py`, `services/stripe_service.py`, `routes/billing.py` with `--cov-fail-under=95`; stripe-mock Docker service for integration tests that need realistic Stripe responses
2. **Agent pipeline (LangGraph nodes)** — each node receives a deterministic LLM fixture via `mocker.patch` on `LlmChat.generate()`; pipeline integration tests run the full node graph with all external services mocked via respx
3. **n8n bridge + external integrations** — respx mocking at httpx transport layer; contract tests assert correct URL, HMAC auth header, and payload schema without a live n8n instance; `pytest.mark.integration` tags tests that require live n8n
4. **LightRAG service** — respx mocking at httpx transport layer (same pattern as n8n); per-user isolation tested by verifying user A's queries cannot return user B's documents
5. **Frontend components** — Jest + RTL (CRA built-in), `msw` for API call interception, `@testing-library/user-event` for realistic interactions; test files adjacent to components as `ComponentName.test.js`
6. **E2E critical flows** — Playwright at repo root with `webServer` config launching both `uvicorn` backend and `npm start` frontend; Chromium only; `retries: 2` in CI; function-scoped test fixtures to prevent event loop conflicts

### Critical Pitfalls

1. **Ordering-dependent test failures from shared mock state** — already confirmed live (`test_sharing_notifications_webhooks.py::TestViralCard` fails in full suite, passes alone). Fix on Day 1: install `pytest-mock` for automatic cleanup; use function scope for all mock fixtures; run `pytest --randomly-seed=12345 tests/` after every wave with at least 3 different seeds before declaring a wave clean.

2. **TDD bug fix breaks existing implementation tests** — fixing the credit atomicity bug (changing `find_one` + `update_one` to `find_one_and_update`) will break existing tests that assert `update_one` was called. Before any production code fix: audit every test touching the affected function, classify as "implementation test" vs "contract test", update implementation tests to assert behavioral outcomes. Never delete a failing test without understanding why it failed.

3. **Unawaited coroutine warnings are silent test bugs** — 6 confirmed: `fire_webhook`, `_cleanup`, `_do_render`, `validate_media_output`, `AsyncMockMixin._execute_mock_call`. Each means the async function body never ran but the test passed. Day 1 fix: add `filterwarnings = error::RuntimeWarning` to `pytest.ini` and fix all 6 before writing new tests.

4. **Line coverage without branch coverage is misleading for billing code** — the credit race condition exists in a path that has full line coverage from happy-path tests. `--cov-branch` must be used from day one; 95% branch coverage (not line) is the correct billing target. Write explicit concurrent tests using `asyncio.gather()` against mongomock-motor for the atomicity contract.

5. **Dead tests for deprecated architecture cause persistent CI failures** — 2 confirmed: `test_beat_schedule_has_cleanup_stale_jobs` and `test_all_six_periodic_tasks_are_scheduled` fail because `celeryconfig.beat_schedule = {}` since n8n took over scheduling. Sprint must start with a full baseline audit: run `pytest --tb=no -q`, categorize every failure as deprecated/migrated/genuine regression, delete or update before adding new tests.

---

## Implications for Roadmap

The wave structure maps directly to four phases. The only acceptable phase order is 1 → 2 → 3 → 4 because later phases depend on the correctness guarantees established in earlier ones.

### Phase 1: Test Foundation + Billing and Auth P0 Hardening

**Rationale:** Revenue cannot flow safely until the 3 P0 bugs are fixed via TDD. The existing CI failures and silent async bugs must be resolved first or they mask every new failure. Coverage infrastructure (pytest-cov, branch coverage) must be established here so it cannot be retroactively avoided.

**Delivers:** Clean CI baseline (3 existing failures resolved); `filterwarnings = error::RuntimeWarning` active; pytest-cov with branch coverage gating CI at 85% global and 95% billing; JWT fallback fixed; atomic credit deduction via `find_one_and_update`; webhook idempotency + dedup; full subscription lifecycle state machine tested; auth rate limiting verified.

**Addresses:** Wave 1 table-stakes categories. Fixes BUG: JWT fallback (auth_utils.py), BUG: non-atomic credits (services/credits.py), BUG: webhook dedup (routes/billing.py).

**Avoids:** Pitfall 3 (unawaited coroutine setup done first), Pitfall 4 (branch coverage from start), Pitfall 5 (clean baseline before adding tests), Pitfall 8 (Stripe webhook signature verification and idempotency test patterns written before happy-path tests), Pitfall 9 (atomicity tested via MongoDB operation contract, not asyncio.gather with AsyncMock).

**Research flag:** STANDARD — pytest-cov setup is mechanical, documented, HIGH confidence. Stripe Test Clock (Wave 1 stretch) needs verification against stripe SDK 8.0.0 method signatures before implementation.

### Phase 2: Content Pipeline and LightRAG Isolation

**Rationale:** The content pipeline is the core product value; pipeline regression protection requires LangGraph node isolation tests. LightRAG lambda bug must be fixed before agency RBAC can verify per-user knowledge graph isolation.

**Delivers:** Each LangGraph agent node testable in isolation with deterministic LLM fixtures; LightRAG lambda client fixed (per-request instantiation); per-user knowledge graph isolation verified; publishing token refresh + expiry simulation; custom plan price calculation purity tests; security tests (CORS, CSP, NoSQL injection).

**Addresses:** Wave 2 categories. Fixes BUG-4 (LightRAG lambda-scoped client leaks state across users).

**Avoids:** Pitfall 2 (audit existing pipeline tests for implementation vs contract nature before fixing LangGraph internals), Pitfall 6 (layered mock strategy: unit tests mock LLM + DB + external; integration tests use mongomock-motor for data assertions), Pitfall 10 (LightRAG mocked at httpx transport level — never call live LightRAG service from unit or integration tests).

**Research flag:** NEEDS RESEARCH — the specific `asyncio_mode = auto` interaction with LangGraph's internal task group may require investigation before writing node isolation tests; reference the Nov 2025 LangGraph unit testing article in FEATURES.md sources.

### Phase 3: Agency, Media, n8n Contract Tests and Playwright E2E

**Rationale:** These categories block the public announcement, not the first paying user. They cover secondary product surfaces and the full funnel E2E smoke test that catches silent regressions across the entire user journey.

**Delivers:** Agency RBAC enforcement tests; media orchestration format routing (all 8 format types); n8n webhook contract tests (schema drift detection); SSE tenant scoping; Playwright E2E covering auth → onboard → generate → approve → schedule → billing upgrade.

**Addresses:** Wave 3 categories from FEATURES.md.

**Avoids:** Pitfall 7 (AsyncClient event loop conflicts in Playwright — use function-scoped client fixtures; use minimal test app for middleware-specific tests rather than full production app), Pitfall 12 (n8n tests use respx transport mocking — no live n8n instance required in default `pytest` run; `pytest.mark.integration` isolates live-n8n tests).

**Research flag:** NEEDS RESEARCH — Playwright + CRA `react-scripts` dev server startup time may exceed the 120s `webServer.timeout` default; validate before implementing the E2E CI job. Playwright recommends Node 20+ while CI uses Node 18 — consider upgrading Playwright CI job only.

### Phase 4: Load Testing and Production Smoke

**Rationale:** Correctness bugs must be proven fixed before load testing has meaning. Locust and Docker smoke tests are the final confidence layer before public announcement. They validate that the Phase 1 atomicity fixes hold under concurrency at realistic scale.

**Delivers:** Locust load test (50 concurrent users, credit deduction stress, verify atomicity guarantee holds at load); Docker Compose smoke test (all services healthy: FastAPI, MongoDB, Redis, n8n, LightRAG, Remotion); Stripe Test Clock lifecycle (trial → active → renewal → cancel compressed to minutes); final coverage report at 85%+ global line/branch and 95%+ billing branch.

**Addresses:** Wave 4 categories from FEATURES.md.

**Avoids:** Pitfall 9 (Locust provides real HTTP concurrency via gevent — this is the correct tool for validating atomicity under load, unlike asyncio.gather with AsyncMock which cannot produce true race conditions).

**Research flag:** STANDARD — Locust headless CI flags are documented in STACK.md. Docker Compose smoke test pattern follows existing `test_e2e_ship.py` approach.

---

### Phase Ordering Rationale

- Phase 1 must precede all others because auth bugs allow unauthenticated access to all routes — pipeline and agency tests against an insecure system are not meaningful tests. Credit atomicity bugs mean billing tests against broken accounting are actively misleading.
- Clean baseline at Phase 1 start before any new tests are written — the 3 existing CI failures create alert fatigue; new failures are invisible against a noisy baseline.
- Branch coverage configured in Phase 1 so every subsequent test is written against the correct metric from the start; retroactive application requires test rewrites.
- Playwright E2E deferred to Phase 3 because E2E tests against broken auth/billing (pre-Phase 1 fixes) produce green results for the wrong reasons.
- Load testing in Phase 4 last because it validates correctness guarantees established in Phase 1 — running Locust before the atomicity fix is verified provides no useful signal.

### Research Flags

Phases needing deeper research during planning:
- **Phase 1 — Stripe Test Clock:** Verify `stripe.test_helpers.test_clocks` method signatures against installed `stripe==8.0.0` SDK before implementation. The source references this as HIGH complexity.
- **Phase 2 — LangGraph node isolation:** The interaction between `asyncio_mode = auto` (in `pytest.ini`) and LangGraph's internal async task group needs investigation. Reference the Nov 2025 practitioner article in FEATURES.md before writing the first node test.
- **Phase 3 — Playwright + CRA:** Validate that CRA's dev server starts within 120s in CI before committing to the `webServer` timeout; adjust if needed.

Phases with standard patterns (research not needed):
- **Phase 1 — pytest-cov + pytest-mock setup:** Fully documented, mechanical steps, all versions verified at HIGH confidence.
- **Phase 1 — mongomock-motor for credit atomicity:** Pattern documented with example in STACK.md; no additional research needed.
- **Phase 4 — Locust headless CI:** Exact CLI flags documented in STACK.md.
- **Phase 4 — Docker Compose smoke:** Follows existing `test_e2e_ship.py` pattern already in the codebase.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified against PyPI and official docs; full compatibility matrix checked against Python 3.11.11 and Node 18; alternatives considered and rejected with documented rationale |
| Features (test categories) | HIGH | Based on official Stripe docs, FastAPI docs, OWASP checklist 2026, and live codebase inspection (781 tests collected, 3 active failures observed, 4 P0 bugs confirmed against source files) |
| Architecture | HIGH for core patterns; MEDIUM for ThookAI-specific test topology | Standard testing patterns (mongomock-motor for MongoDB, respx for httpx, Playwright webServer config) verified via official docs; specific fixture scoping recommendations derived from the confirmed codebase failures |
| Pitfalls | HIGH | All critical pitfalls grounded in live codebase evidence: ordering failure confirmed by test name, 6 unawaited coroutine warnings catalogued, 3 CI failure names identified, all 4 P0 bugs verified against source files. Moderate/minor pitfalls corroborated by referenced arxiv paper and community sources. |

**Overall confidence:** HIGH

### Gaps to Address

- **Playwright + Node 18 compatibility:** Playwright now recommends Node 20+; Node 18 is in maintenance mode. The CI workflow uses Node 18 throughout. Recommend adding a separate Node 20 setup step specifically for the `playwright-e2e` CI job. This is a one-line config change, not a blocker.
- **Stripe Test Clock with stripe SDK 8.0.0:** The `stripe.test_helpers.test_clocks` API was introduced in stripe-python v4+. The installed `stripe==8.0.0` includes it, but the exact method signatures for creating a frozen clock and advancing time need verification against the SDK before writing test clock tests in Phase 1.
- **mongomock-motor aggregation pipeline limitations:** Version `>=0.0.36` does not support `$vectorSearch` or Atlas `$search` operators. If any billing or core tests exercise aggregation pipelines using these operators, those tests need a real MongoDB CI service (via Docker). This affects a small subset; audit `backend/services/` for Atlas-specific operators before Phase 2 begins.
- **LangGraph internal async behavior with pytest-asyncio 1.3.0:** The upgrade from `pytest-asyncio >=0.23.0` to `>=1.3.0` changes default fixture loop scope. If any existing LangGraph tests use module-scoped async fixtures, they may need `asyncio_default_fixture_loop_scope = "module"` overrides. Audit existing pipeline tests during Phase 2 planning.

---

## Sources

### Primary (HIGH confidence)
- [pytest-cov 7.1.0 — PyPI](https://pypi.org/project/pytest-cov/) — version, `--cov-fail-under`, branch coverage
- [coverage.py configuration reference](https://coverage.readthedocs.io/en/latest/config.html) — `concurrency = greenlet,thread` for async FastAPI
- [pytest-asyncio 1.3.0 — PyPI](https://pypi.org/project/pytest-asyncio/) — `asyncio_default_fixture_loop_scope` requirement
- [pytest-mock 3.15.1 — PyPI](https://pypi.org/project/pytest-mock/) — automatic mock cleanup rationale
- [mongomock-motor 0.0.36 — PyPI](https://pypi.org/project/mongomock-motor/) — version, Atlas operator limitations
- [respx 0.22.0 — PyPI](https://pypi.org/project/respx/) — async httpx transport mocking
- [Faker 40.12.0 — PyPI](https://pypi.org/project/faker/) — pytest fixture integration
- [Locust 2.43.4 — PyPI](https://pypi.org/project/locust/) — headless CI mode flags
- [Playwright docs — intro + CI + webServer](https://playwright.dev/docs/intro) — install, browser targets, `webServer` config
- [CRA running tests docs](https://create-react-app.dev/docs/running-tests/) — built-in Jest, setupTests.js, no eject
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) — bundled in CRA
- [stripe/stripe-mock GitHub](https://github.com/stripe/stripe-mock) — Docker image, `api_base` override
- [Stripe Idempotent Requests — Official Stripe API Reference](https://docs.stripe.com/api/idempotent_requests) — webhook dedup patterns
- [FastAPI Async Tests — Official FastAPI docs](https://fastapi.tiangolo.com/advanced/async-tests/) — AsyncClient patterns
- [OWASP API Security Testing Checklist 2026 — AccuKnox](https://accuknox.com/blog/owasp-api-security-top-10-the-complete-testing-checklist-2026) — auth and injection test requirements
- [Webhook Idempotency Implementation — Hookdeck](https://hookdeck.com/webhooks/guides/implement-webhook-idempotency) — dedup test patterns
- [coveragepy issue #1240](https://github.com/nedbat/coveragepy/issues/1240) — async line undercounting, greenlet workaround (confirmed)

### Secondary (MEDIUM confidence)
- [Stripe Webhooks Best Practices — Stigg Engineering](https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks) — production webhook experience
- [How We Unit Test LangGraph Agents — Andrew Larsen, Medium, Nov 2025](https://andrew-larse514.medium.com/how-we-unit-test-langgraph-agents-29f5d6ef82c6) — node isolation patterns
- [Scaling E2E Tests for Multi-Tenant SaaS with Playwright — CyberArk Engineering](https://medium.com/cyberark-engineering/scaling-e2e-tests-for-multi-tenant-saas-with-playwright-c85f50e6c2ae) — tenant scoping patterns
- [Testing SaaS Billing with Playwright + Stripe Test Clocks — MEXC News](https://www.mexc.com/news/no-more-ship-and-pray-testing-saas-billing-systems-with-playwright-stripe-test-clocks/67679) — Test Clock patterns
- [k6 API Load Testing Guide — Grafana k6 Official Docs](https://grafana.com/docs/k6/latest/testing-guides/api-load-testing/) — used as comparison basis for Locust selection
- [AI coding agents generate systematically over-mocked tests — arxiv.org/abs/2602.00409](https://arxiv.org/abs/2602.00409) — over-mocking risk (corroborates Pitfall 6)

### Primary codebase (HIGH confidence)
- ThookAI `CLAUDE.md` + `PROJECT.md` — canonical platform truth
- Live test suite observation: 781 tests collected, 3 active failures by test name, 6 unawaited coroutine warning strings catalogued, 4 P0 bugs verified against source files — ground truth for all pitfall severity assessments

---

*Research completed: 2026-04-01*
*Ready for roadmap: yes*
