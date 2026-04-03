# Feature Landscape — Testing Categories for v2.1 Production Hardening

**Domain:** Billing SaaS platform with AI content pipeline — pre-public-launch testing sprint
**Researched:** 2026-04-01
**Confidence:** HIGH (official Stripe docs + FastAPI docs + multiple verified sources)

---

## Context

This document answers: **what test categories are table stakes before public launch of a billing SaaS, and in what priority order?**

ThookAI enters v2.1 with 768 existing tests across 56 test files. Target is 1,050+ tests, 85%+ line coverage, 95%+ billing coverage, zero P0 failures. The platform has Stripe billing, JWT auth, Google OAuth, a 5-agent AI pipeline orchestrated by LangGraph, n8n workflow orchestration, LightRAG knowledge graph, Remotion media assembly, and agency workspaces.

Four confirmed critical bugs anchor the TDD work: (1) JWT fallback path bypasses auth, (2) non-atomic credit deductions allow negative balance, (3) webhook dedup missing so duplicate events activate subscriptions twice, (4) LightRAG lambda-scoped client leaks connections.

---

## Table Stakes

Test categories that must exist before any revenue flows. Missing these means real money can be lost or real users can be locked out.

| Category | Why Required | Complexity | Current Coverage Signal |
|----------|--------------|------------|------------------------|
| **Billing: Webhook idempotency** | Stripe retries webhooks for up to 72h. Without dedup, `checkout.session.completed` fires twice → user gets double credits or double subscription activation → financial ledger corrupted | MEDIUM | `test_stripe_billing.py` exists but dedup path untested |
| **Billing: Credit atomicity** | Concurrent requests to `/api/content/generate` race on `credits` field. Non-atomic read-modify-write allows negative balance → users generate unlimited content for free | HIGH | `test_credits_billing.py` has unit tests; concurrent stress test absent |
| **Billing: Webhook signature verification** | Invalid or replayed webhooks must be rejected. Without `STRIPE_WEBHOOK_SECRET` check, any attacker can craft a fake `customer.subscription.created` event | LOW | Covered in `test_stripe_e2e.py` |
| **Billing: Subscription lifecycle** | Trial → active → cancelled → downgrade path must work end-to-end. Stripe sends `customer.subscription.updated` and `customer.subscription.deleted`. If either is unhandled, users keep premium features after cancelling | HIGH | `test_stripe_billing.py` covers deletion; upgrade path gap |
| **Billing: Checkout session creation** | Price ID lookup, plan preview calculation, credit pack SKUs must all resolve without throwing. Any Stripe `InvalidRequest` here = 100% conversion failure | MEDIUM | Covered for happy path; missing-config path needs test |
| **Auth: JWT validation** | Every protected route depends on `get_current_user`. The confirmed BUG-1 variant for v2.1 is a JWT fallback that lets through malformed tokens. Must be locked down before first paid user | HIGH | `test_auth_core.py` exists; fallback path is the gap |
| **Auth: Rate limiting on auth endpoints** | Without rate limit on `/api/auth/login`, brute-force attacks enumerate passwords. PCI DSS and OWASP require lockout policy | MEDIUM | `test_rate_limit.py` exists; concurrent burst tests absent |
| **Auth: Google OAuth token exchange** | OAuth callback must not expose state parameter to CSRF. Token exchange must use PKCE or state validation | MEDIUM | `test_oauth_flows.py` exists |
| **Content pipeline: Happy path E2E** | Commander → Scout → Thinker → Writer → QC must produce a job in `reviewing` status within 60s. If this is broken, zero revenue is possible regardless of billing | HIGH | `test_pipeline_e2e.py` exists |
| **Content pipeline: Credit gating** | Insufficient credits must return HTTP 402 before the pipeline runs, not after. Post-run credit failure wastes LLM tokens and confuses users | LOW | `test_credits_billing.py` has unit-level check |
| **Publishing: Platform OAuth token refresh** | LinkedIn/X/Instagram tokens expire. If refresh logic is broken, all scheduled posts silently fail after token expiry with no user alert | HIGH | `test_publishing.py` exists; token expiry simulation gap |
| **Security: CORS + CSP headers** | Production CORS must allow only Vercel frontend origin. CSP must block inline scripts. Both are rejected by enterprise users (agency tier target) if misconfigured | LOW | `test_e2e_critical_path.py` covers headers |

---

## Differentiators (Test Coverage That Signals Quality)

Beyond table stakes, these test categories are what separates a professional QA baseline from a "ship and pray" release. They are expected by any enterprise buyer doing due diligence.

| Category | Value Proposition | Complexity | Notes |
|----------|-------------------|------------|-------|
| **Billing: Stripe Test Clock lifecycle** | Compresses trial-to-renewal verification from 30 days to 2 minutes. Proves the full subscription arc without real time passage — used by Stripe, Vercel, Linear | HIGH | Requires `stripe.test_helpers.test_clocks`; documents expected invoice amounts and status transitions |
| **Billing: Custom plan price calculation accuracy** | ThookAI's pricing is volume-tiered with add-ons. A calculation bug silently charges the wrong amount. Verified pure-function tests are the cheapest protection | MEDIUM | Pure functions in `services/credits.py` — no mocks needed |
| **LangGraph: Node-level unit tests** | Each agent node (Commander, Scout, Thinker, Writer, QC) should be testable in isolation with deterministic LLM mocks. Proves pipeline logic independent of LLM availability | HIGH | Industry standard as of Nov 2025; LangGraph's node architecture enables this; reduces CI flakiness |
| **LightRAG: Per-user isolation** | The confirmed BUG-4 is a lambda-scoped LightRAG client that leaks connection state across users. Test that user A's knowledge graph queries cannot return user B's content | HIGH | `test_lightrag_isolation.py` exists but lambda bug is specifically untested |
| **n8n: Webhook trigger contracts** | n8n workflows trigger on HTTP webhooks from the FastAPI backend. If the payload schema changes, workflows silently fail. Contract tests lock the schema | MEDIUM | `test_n8n_bridge.py` exists; schema drift detection absent |
| **Media orchestration: Format routing** | The Designer agent routes to different media providers by format (image → fal.ai, video → Luma/Kling, TTS → ElevenLabs). Wrong routing sends expensive requests to wrong provider | MEDIUM | `test_media_orchestrator.py` exists |
| **SSE: Tenant scoping** | SSE events must only be delivered to the user who owns the job. Cross-tenant event leakage is both a security bug and a confusing UX | MEDIUM | `test_sse_scoping.py` exists |
| **Agency: Role enforcement** | Workspace members with `viewer` role must not be able to approve or publish content. RBAC gap = accidental content publishing by client | MEDIUM | `test_admin_agency.py` exists |
| **Load testing: Credit endpoint concurrency** | The atomic credit deduction bug (BUG-2) only manifests under concurrent load. A stress test with 50 simultaneous generation requests proves the fix holds | HIGH | `test_rate_limit_concurrent.py` exists; credit-specific concurrent stress absent |
| **Playwright E2E: Critical user flows** | Auth → onboard → generate → approve → schedule → billing upgrade. If any step in this flow breaks silently, the whole funnel is dead. Playwright catches it before users do | HIGH | `frontend/` tests unclear; PROJECT.md targets 105 frontend tests |

---

## Anti-Features (Test Approaches to Explicitly Avoid)

Test patterns that sound thorough but create maintenance burden or false confidence.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Integration tests against real Stripe API in CI** | Stripe API calls in CI are slow (500ms+), require real test keys in environment, and occasionally fail due to Stripe infra issues causing false CI failures | Use `unittest.mock` to mock Stripe SDK calls; reserve real Stripe CLI calls for local pre-merge smoke tests |
| **Real LLM calls in unit/integration tests** | Claude API latency (2-5s per call) × 700+ tests = 30+ minute CI runs; also introduces non-determinism, making tests flaky | Mock `LlmChat.generate()` with deterministic fixtures; reserve real LLM calls for a separate `tests/evals/` suite gated behind a flag |
| **Single giant integration test that covers "everything"** | 500-line test file with sequential steps fails at step 3, giving no signal on steps 4-50; also takes 60s to run | Pyramid: many fast unit tests, fewer medium integration tests, a handful of E2E smoke tests |
| **Testing Stripe webhook by manually POSTing to staging** | No signature header → your own signature validation rejects it; teaches nothing about real webhook flow | Use `stripe listen --forward-to localhost:8000/api/billing/webhook` locally; in CI use mocked Stripe events with correct signature construction |
| **Testing mongo operations with real MongoDB in CI** | CI MongoDB setup is slow, flaky on shared runners; test isolation requires teardown that often gets skipped | Use `mongomock_motor` for unit/integration tests; reserve real MongoDB tests for Docker Compose smoke tests (`test_e2e_ship.py` pattern) |
| **100% line coverage as the only metric** | 100% line coverage with trivial assertions (assertEqual(True, True)) is worthless; creates coverage theater | Target 85%+ line coverage but enforce that billing-path tests assert specific state transitions, not just "no exception raised" |

---

## Priority Order for Testing Coverage

Ordered by: (revenue risk × bug probability × blast radius). Fix bugs via TDD in this order.

### Wave 1 — Block on These (Revenue at Risk)

These categories must reach full coverage before launch. Any gap here directly maps to money or user trust being lost.

1. **Billing: Webhook idempotency + dedup** — P0 bug confirmed. Every duplicate webhook activation is a support ticket and potential double-charge dispute. Write failing test first (idempotent event replay), then fix `routes/billing.py` dedup guard.

2. **Billing: Atomic credit deduction** — P0 bug confirmed. Non-atomic `find → modify → update` allows negative balance under concurrency. Write failing concurrent stress test (50 coroutines), then fix to `find_one_and_update` with `$gte: cost` filter.

3. **Auth: JWT fallback path** — P0 bug confirmed. Fallback that accepts malformed tokens means unauthenticated access to all `/api/*` routes. Write failing test with deliberately malformed JWT, then fix `auth_utils.py`.

4. **Billing: Subscription lifecycle state machine** — Without verified event handling for all subscription states, upgrades/downgrades/cancellations are a black box. Write tests for `subscription.updated`, `subscription.deleted`, `payment_intent.succeeded`, `payment_intent.payment_failed`.

5. **Auth: Rate limiting on login + register** — Brute-force protection is a legal/compliance requirement for any paid platform. Write concurrent burst test (100 req/s against `/api/auth/login`), verify 429 after threshold.

### Wave 2 — Required Before First Paying User

6. **Content pipeline: LangGraph node isolation** — Each agent node testable with LLM mock. Commander, Scout, Thinker, Writer, QC all have deterministic unit tests. Protects pipeline from silent regressions when prompts change.

7. **LightRAG: Per-user isolation + lambda bug** — BUG-4 (lambda-scoped client) confirmed. Write failing test for user cross-contamination, then fix to per-request client instantiation.

8. **Publishing: Token refresh + expiry simulation** — Publish flows silently drop scheduled posts when tokens expire. Write test simulating expired token → refresh → retry sequence.

9. **Billing: Custom plan price calculation** — 20 pure function tests for `build_plan_preview` and `calculate_plan_price`. Volume tiers, add-ons, credit pack SKUs. Cheapest category to test, highest ROI for financial accuracy.

10. **Security: CORS + CSP + SQL/NoSQL injection** — OWASP A01 (Broken Access Control) and A03 (Injection). Test that MongoDB queries use parameterized inputs; test that CORS rejects unauthorized origins.

### Wave 3 — Before Public Announcement

11. **n8n: Webhook contract tests** — Lock the payload schema between FastAPI and n8n workflows. Any schema drift breaks publishing silently.

12. **Media orchestration: Format routing accuracy** — Verify Designer → Orchestrator → provider routing for all 8 format types. Prevents expensive misdirected API calls.

13. **Agency: RBAC enforcement** — Viewer/editor/owner role gates on publish, approve, member management.

14. **SSE: Tenant scoping verification** — Cross-tenant event leakage test.

15. **Playwright E2E: Auth + onboard + generate + billing upgrade flows** — End-to-end smoke test covering the entire monetization funnel.

### Wave 4 — Quality Bar Completion

16. **Load testing: Concurrent content generation** — k6 or Locust, 50 concurrent users, credit deduction stress, verify atomicity holds under load.

17. **Docker smoke: Full service stack** — `docker-compose up` + health check all services (FastAPI, MongoDB, Redis, n8n, Remotion). Catches environment configuration bugs before deploy.

18. **Stripe Test Clock lifecycle** — Full subscription arc (trial → active → renewal → cancel) compressed to minutes. Documents expected financial state at each transition.

---

## Feature Dependencies (Testing)

```
[Wave 1: Credit atomicity test]
    └──requires──> [find_one_and_update fix in services/credits.py]
    └──validates──> [Wave 4: Load test concurrency]

[Wave 1: JWT fallback test]
    └──requires──> [auth_utils.py fix]
    └──validates──> [Wave 2: All pipeline auth tests]

[Wave 1: Webhook idempotency test]
    └──requires──> [dedup guard in routes/billing.py]
    └──validates──> [Wave 3: Stripe Test Clock lifecycle]

[Wave 2: LangGraph node isolation]
    └──requires──> [LLM mock fixtures in conftest.py]
    └──enables──> [All pipeline regression tests]

[Wave 2: LightRAG isolation]
    └──requires──> [lambda client fix in services/lightrag_service.py]
    └──validates──> [Wave 3: Agency RBAC tests (per-user knowledge graph)]

[Wave 3: Playwright E2E]
    └──requires──> [Wave 1 + Wave 2 complete]
    └──requires──> [Frontend + backend running in Docker Compose]
    └──validates──> [Wave 4: Load test user flows]
```

---

## Coverage Targets by Category

| Category | Target Coverage | Current Signal | Notes |
|----------|-----------------|----------------|-------|
| Billing / payments | 95%+ | ~60% estimated | Critical — highest priority |
| Auth / JWT / OAuth | 90%+ | ~70% estimated | JWT fallback is confirmed gap |
| Content pipeline | 85%+ | ~75% estimated | LangGraph node isolation is main gap |
| Media orchestration | 80%+ | ~50% estimated | v2.0 features newly built |
| LightRAG + knowledge graph | 80%+ | ~40% estimated | Lambda bug confirms gap |
| n8n integration | 75%+ | ~50% estimated | Contract tests are absent |
| Strategist Agent | 80%+ | ~60% estimated | Deterministic fixtures needed |
| Frontend E2E (Playwright) | Critical flows | 0% estimated | Not yet built |
| Load / concurrency | Defined thresholds | 0% estimated | Not yet built |
| **Overall line coverage** | **85%+** | **~65% estimated** | Estimate based on 768/1050 ratio |

---

## Sources

- [Stripe Webhooks Best Practices — Stigg Engineering](https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks) — HIGH confidence (engineering team, production experience)
- [Testing SaaS Billing with Playwright + Stripe Test Clocks — MEXC News](https://www.mexc.com/news/no-more-ship-and-pray-testing-saas-billing-systems-with-playwright-stripe-test-clocks/67679) — MEDIUM confidence (technical article, Stripe documentation referenced)
- [Stripe Idempotent Requests — Official Stripe API Reference](https://docs.stripe.com/api/idempotent_requests) — HIGH confidence (official)
- [FastAPI Async Tests — Official FastAPI Documentation](https://fastapi.tiangolo.com/advanced/async-tests/) — HIGH confidence (official)
- [How We Unit Test LangGraph Agents — Andrew Larsen, Medium, Nov 2025](https://andrew-larse514.medium.com/how-we-unit-test-langgraph-agents-29f5d6ef82c6) — MEDIUM confidence (practitioner, current)
- [OWASP API Security Testing Checklist 2026 — AccuKnox](https://accuknox.com/blog/owasp-api-security-top-10-the-complete-testing-checklist-2026) — HIGH confidence (OWASP-derived, current)
- [Scaling E2E Tests for Multi-Tenant SaaS with Playwright — CyberArk Engineering](https://medium.com/cyberark-engineering/scaling-e2e-tests-for-multi-tenant-saas-with-playwright-c85f50e6c2ae) — MEDIUM confidence (enterprise engineering, verified patterns)
- [Webhook Idempotency Implementation — Hookdeck](https://hookdeck.com/webhooks/guides/implement-webhook-idempotency) — HIGH confidence (webhook infrastructure company, verified against Stripe docs)
- [k6 API Load Testing Guide — Grafana k6 Official Docs](https://grafana.com/docs/k6/latest/testing-guides/api-load-testing/) — HIGH confidence (official)
- [ThookAI PROJECT.md + CLAUDE.md — in-repo authoritative docs](../) — HIGH confidence (project ground truth)

---

*Feature (testing categories) research for: ThookAI v2.1 Production Hardening — 50x Testing Sprint*
*Researched: 2026-04-01*
