# Requirements: ThookAI v2.1 — Production Hardening (50x Testing Sprint)

**Defined:** 2026-04-03
**Core Value:** Zero P0 failures before public launch — every revenue path, auth flow, and content pipeline verified with automated tests.

## v2.1 Requirements

### Test Foundation

- [ ] **FOUND-01**: Clean test baseline — fix 3 existing failures, enforce `filterwarnings = error::RuntimeWarning`, add `pytest-randomly`
- [ ] **FOUND-02**: Coverage infrastructure — `pytest-cov` with `.coveragerc` (`concurrency = greenlet,thread`), branch coverage enabled, `--cov-branch` flag
- [ ] **FOUND-03**: Standardized test fixtures in root `conftest.py` — async client factory, mock DB factory, mock user factory, respx mock factory
- [ ] **FOUND-04**: CI matrix configuration — separate jobs per domain (billing, security, pipeline, e2e) with per-domain coverage thresholds

### Billing & Payments

- [ ] **BILL-01**: Stripe checkout flow tests — custom plan builder, credit packages (small/medium/large), checkout session creation, success/cancel URLs
- [ ] **BILL-02**: Subscription lifecycle tests — create, upgrade, downgrade, cancel, reactivate, webhook-driven state transitions
- [ ] **BILL-03**: Credit atomicity tests — `find_one_and_update` atomic deduction verified, race condition under concurrent requests, negative balance prevention
- [ ] **BILL-04**: Webhook idempotency tests — duplicate event handling, signature verification, retry behavior, event ordering
- [ ] **BILL-05**: Volume pricing tests — tier boundary calculations, proration, add-on credits
- [ ] **BILL-06**: TDD bug fix: JWT fallback secret — failing test exposing auth bypass, then fix
- [ ] **BILL-07**: TDD bug fix: non-atomic `add_credits` — failing test exposing race condition, then fix
- [ ] **BILL-08**: TDD bug fix: missing webhook deduplication — failing test exposing double-activation, then fix
- [ ] **BILL-09**: 95%+ branch coverage on `services/credits.py`, `services/stripe_service.py`, `routes/billing.py`

### Security & Auth

- [ ] **SEC-01**: JWT validation tests — token expiry, malformed tokens, missing claims, algorithm confusion, secret rotation
- [ ] **SEC-02**: OAuth flow tests — all 4 platforms (LinkedIn, X/Twitter PKCE, Instagram, Google), state parameter validation, token storage encryption
- [ ] **SEC-03**: Rate limiting tests — per-IP counting, threshold enforcement, concurrent request behavior, auth-specific lower limits
- [ ] **SEC-04**: Security headers tests — CSP, HSTS, X-Frame-Options, X-Content-Type-Options on all routes
- [ ] **SEC-05**: Input validation tests — NoSQL injection prevention, XSS in user input, path traversal in file operations, request size limits
- [ ] **SEC-06**: Admin authorization tests — admin-only routes reject non-admin users, workspace role enforcement
- [ ] **SEC-07**: OWASP Top 10 verification — automated checks for the 10 most critical web application security risks

### Core Features

- [ ] **CORE-01**: Content pipeline comprehensive tests — Commander, Scout, Thinker, Writer, QC individually with deterministic LLM mocks
- [ ] **CORE-02**: LangGraph orchestrator tests — node-level unit tests, debate protocol, quality loop retry behavior
- [ ] **CORE-03**: Media orchestrator comprehensive tests — all 8 format handlers, credit ledger partial failure, R2 staging, Remotion client
- [ ] **CORE-04**: n8n bridge contract tests — all execute endpoints, HMAC verification, callback handling, workflow trigger dispatch
- [ ] **CORE-05**: LightRAG integration tests — insert/query with per-user isolation, entity extraction, embedding lock assertion
- [ ] **CORE-06**: Strategist Agent tests — cadence controls, dismissal tracking, adaptive throttle, generate_payload validation
- [ ] **CORE-07**: Analytics feedback loop tests — poll endpoints, publish_results write-back, optimal_posting_times calculation
- [ ] **CORE-08**: Obsidian integration tests — vault search, path sandboxing, graceful degradation, per-user config
- [ ] **CORE-09**: TDD bug fix: LightRAG lambda injection — failing test exposing cross-user data via lambda scope, then fix
- [ ] **CORE-10**: 85%+ branch coverage across `agents/`, `services/`, `routes/`

### Frontend E2E & Integration

- [ ] **E2E-01**: Playwright setup — install, configure for CRA + FastAPI dual webServer, CI integration
- [ ] **E2E-02**: Critical path E2E — signup → onboard → generate → schedule → publish → analytics → strategy → approve
- [ ] **E2E-03**: Billing E2E — plan selection → checkout → subscription active → credit usage → upgrade
- [ ] **E2E-04**: Agency workspace E2E — create workspace → invite member → switch context → generate as member
- [ ] **E2E-05**: Load testing — Locust concurrent user simulation, API response time thresholds, connection pool behavior
- [ ] **E2E-06**: Docker Compose integration smoke — full stack startup, health checks pass, cross-service connectivity
- [ ] **E2E-07**: Dead link detection — all media URLs resolve, all API endpoints respond, no broken internal routes

## Future Requirements

Deferred beyond v2.1.

### Performance

- **PERF-F01**: API response time benchmarks with historical tracking (v3.0)
- **PERF-F02**: Database query optimization with slow query monitoring (v3.0)

### Observability

- **OBS-F01**: Structured logging with correlation IDs (v3.0)
- **OBS-F02**: Sentry error tracking with custom contexts (v3.0)

## Out of Scope

| Feature | Reason |
|---------|--------|
| New feature development | Testing sprint only — no new capabilities |
| UI/UX changes | Only Playwright tests, no UI modifications |
| Database migrations | Schema changes deferred to feature milestones |
| Performance optimization | Measure only, optimize in v3.0 |
| Mobile testing | Web-first, mobile deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | — | Pending |
| FOUND-02 | — | Pending |
| FOUND-03 | — | Pending |
| FOUND-04 | — | Pending |
| BILL-01 | — | Pending |
| BILL-02 | — | Pending |
| BILL-03 | — | Pending |
| BILL-04 | — | Pending |
| BILL-05 | — | Pending |
| BILL-06 | — | Pending |
| BILL-07 | — | Pending |
| BILL-08 | — | Pending |
| BILL-09 | — | Pending |
| SEC-01 | — | Pending |
| SEC-02 | — | Pending |
| SEC-03 | — | Pending |
| SEC-04 | — | Pending |
| SEC-05 | — | Pending |
| SEC-06 | — | Pending |
| SEC-07 | — | Pending |
| CORE-01 | — | Pending |
| CORE-02 | — | Pending |
| CORE-03 | — | Pending |
| CORE-04 | — | Pending |
| CORE-05 | — | Pending |
| CORE-06 | — | Pending |
| CORE-07 | — | Pending |
| CORE-08 | — | Pending |
| CORE-09 | — | Pending |
| CORE-10 | — | Pending |
| E2E-01 | — | Pending |
| E2E-02 | — | Pending |
| E2E-03 | — | Pending |
| E2E-04 | — | Pending |
| E2E-05 | — | Pending |
| E2E-06 | — | Pending |
| E2E-07 | — | Pending |

**Coverage:**
- v2.1 requirements: 37 total
- Mapped to phases: 0
- Unmapped: 37

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after initial definition*
