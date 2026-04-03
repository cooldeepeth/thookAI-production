# Milestones

## v2.1 Production Hardening — 50x Testing Sprint (Shipped: 2026-04-03)

**Phases completed:** 4 phases (17-20), 19 plans

**Key accomplishments:**

- Clean CI baseline: fixed 3 broken tests, 6 unawaited coroutine warnings, installed 6 test packages, configured branch coverage with `.coveragerc`
- 3 P0 TDD bug fixes: JWT fallback secret removed, `add_credits` made atomic with `$inc`, Stripe webhook deduplication via `stripe_events` unique index
- 324 billing tests achieving 95%+ branch coverage on credits.py, stripe_service.py, and billing routes
- 126 security tests covering JWT lifecycle, OAuth 4 platforms, OWASP Top 10, rate limiting, input validation, admin RBAC
- 240 core feature tests covering all pipeline agents, LangGraph orchestrator, media orchestration (8 formats), n8n bridge contracts, LightRAG isolation, Strategist, analytics, Obsidian
- LightRAG lambda injection TDD fix: `re.sub` user_id sanitization prevents f-string cross-user data leak
- Playwright E2E infrastructure with dual webServer config, critical path + billing + agency specs
- GitHub Actions CI matrix with 4 domain-specific jobs and per-domain coverage gates
- Locust 50-user load test + Docker Compose 7-service smoke test

---

## v2.0 Intelligent Content Operating System (Shipped: 2026-04-01)

**Phases completed:** 8 phases (9-16), 27 plans

**Key accomplishments:**

- n8n replaces Celery beat: HMAC webhook bridge, 7 execute endpoints, hard cutover with idempotency guard, Docker Compose with PostgreSQL queue mode
- LightRAG knowledge graph: sidecar container with per-user namespace isolation, domain-specific entity extraction, Thinker multi-hop retrieval, Learning dual-write
- Multi-model media orchestration: Remotion Express service (5 compositions), MediaOrchestrator with 8 format handlers, pipeline credit ledger, Designer format auto-selection, QC brand/anti-slop validation
- Strategist Agent: nightly n8n-triggered synthesis, cadence controls (3/day max), 14-day topic suppression, adaptive throttle, one-click generate_payload
- Analytics feedback loop: real social metrics polling (24h + 7d), publish_results write-back, optimal_posting_times from real data
- Strategy Dashboard: SSE-driven recommendation cards, one-click approve, History tab, sidebar navigation
- Obsidian vault integration: Scout enrichment, Strategist signal, PurePosixPath sandboxing, per-user config with Fernet encryption
- E2E audit + security hardening: 96 tests, n8n network isolation, LightRAG scoping, Remotion load test, Stripe billing, OAuth flows

---

## v1.0 ThookAI Stabilization (Shipped: 2026-03-31)

**Phases completed:** 8 phases (1-8), 22 plans

**Key accomplishments:**

- Test suite fixed from INTERNALERROR to 95 collected/59 passing via conftest.py exclusions and httpx migration
- JWT secret mismatch between create and decode paths fixed
- Celery beat schedule hardened with explicit task names and video queue routing
- Content pipeline verified end-to-end (Commander → Scout → Thinker → Writer → QC)
- Real HTTP dispatch to social platforms via publisher.py (replaced simulated placeholder)
- Atomic credit deduction via find_one_and_update (race condition eliminated)
- 26-test frontend quality suite (error boundaries, empty states, 401 handling, mobile responsive)
- CRA env var collision fixed in 12 frontend files

---
