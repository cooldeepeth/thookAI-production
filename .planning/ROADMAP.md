# Roadmap: ThookAI

## Milestones

- v1.0 ThookAI Stabilization — Phases 1-8 (shipped 2026-04-01) — [archive](milestones/v1.0-ROADMAP.md)
- v2.0 Intelligent Content Operating System — Phases 9-16 (shipped 2026-04-01)
- v2.1 Production Hardening — 50x Testing Sprint — Phases 17-20 (shipped 2026-04-03)
- v2.2 Frontend Hardening & Production Ship — Phases 21-25 (in progress)

## Phases

<details>
<summary>v1.0 ThookAI Stabilization (Phases 1-8) — SHIPPED 2026-04-01</summary>

- [x] Phase 1: Git & Branch Cleanup (2/2 plans)
- [x] Phase 2: Infrastructure & Celery (3/3 plans)
- [x] Phase 3: Auth, Onboarding & Email (3/3 plans)
- [x] Phase 4: Content Pipeline (2/2 plans)
- [x] Phase 5: Publishing, Scheduling & Billing (3/3 plans)
- [x] Phase 6: Media Generation & Analytics (3/3 plans)
- [x] Phase 7: Platform Features, Admin & Frontend Quality (4/4 plans)
- [x] Phase 8: Gap Closure & Tech Debt (2/2 plans)

</details>

<details>
<summary>v2.0 Intelligent Content Operating System (Phases 9-16) — SHIPPED 2026-04-01</summary>

- [x] **Phase 9: n8n Infrastructure + Real Publishing** - Replace Celery beat with n8n for all scheduled/external-API tasks; establish webhook bridge; hard cutover with idempotency keys (completed 2026-03-31)
- [x] **Phase 10: LightRAG Knowledge Graph** - Deploy per-user knowledge graph sidecar; wire Thinker agent with multi-hop retrieval; lock embedding model before first insert (completed 2026-03-31)
- [x] **Phase 11: Multi-Model Media Orchestration** - Media Orchestrator service routing to best provider per asset type; Remotion compositions for all formats; credit ledger for partial-failure accounting (completed 2026-04-01)
- [x] **Phase 12: Strategist Agent** - Nightly n8n-triggered agent synthesizing LightRAG + persona + analytics into ranked recommendation cards with cadence controls (completed 2026-04-01)
- [x] **Phase 13: Analytics Feedback Loop** - Real social metrics polling 24h + 7d post-publish via n8n; performance data feeds Strategist and persona intelligence (completed 2026-04-01)
- [x] **Phase 14: Strategy Dashboard + Notifications** - New React page with SSE-driven recommendation feed; one-click approve; dismissed cards archived; strategy API routes (completed 2026-04-01)
- [x] **Phase 15: Obsidian Vault Integration** - Scout enrichment from personal vault; Strategist uses vault as recommendation signal; opt-in with explicit path sandboxing (completed 2026-04-01)
- [x] **Phase 16: E2E Audit + Security Hardening + Production Ship** - Full critical-path smoke testing; n8n security config; per-user graph isolation verified; load testing; dead link detection (completed 2026-04-01)

</details>

<details>
<summary>v2.1 Production Hardening — 50x Testing Sprint (Phases 17-20) — SHIPPED 2026-04-03</summary>

- [x] **Phase 17: Test Foundation + Billing & Payments** - Clean CI baseline, coverage infrastructure, standardized fixtures, CI matrix, then 255 billing tests with TDD fixes for 3 P0 bugs (completed 2026-04-03)
- [x] **Phase 18: Security & Auth** - 100 tests covering JWT, OAuth (all 4 platforms), rate limiting, security headers, input validation, RBAC, and OWASP Top 10 (completed 2026-04-03)
- [x] **Phase 19: Core Features** - 240 tests covering content pipeline, LangGraph orchestrator, media orchestration, n8n bridge, LightRAG, Strategist Agent, analytics, Obsidian, with LightRAG lambda TDD fix (completed 2026-04-03)
- [x] **Phase 20: Frontend E2E & Integration** - Playwright setup, critical path E2E, billing E2E, agency workspace E2E, load testing, Docker Compose smoke, dead link detection (completed 2026-04-03)

</details>

### v2.2 Frontend Hardening & Production Ship (In Progress)

**Milestone Goal:** Harden the React frontend for production launch — CI strictness, httpOnly cookie auth, centralized API client, frontend unit tests, content download/redirect feature, final E2E verification and ship.

- [x] **Phase 21: CI Strictness + httpOnly Cookie Auth Migration** - Remove all CI blind spots (continue-on-error), then migrate auth from localStorage JWT to httpOnly secure cookies with CSRF protection (completed 2026-04-03)
- [ ] **Phase 22: apiFetch Migration + Error Handling** - Create centralized fetch wrapper with timeout, retry, error handling, and replace all 41 raw fetch() calls across the frontend
- [ ] **Phase 23: Frontend Unit Test Suite** - Install testing libraries, configure Jest, write 45+ unit/component tests across 10+ files, wire into CI
- [ ] **Phase 24: Content Download + Redirect-to-Platform** - Download text/images/zip from content detail view, open-in-platform compose URL buttons for LinkedIn and X
- [ ] **Phase 25: E2E Verification + Production Ship Checklist** - Full Playwright E2E verification, dependency audit, security sweep, env documentation, and ship checklist

## Phase Details

### Phase 9: n8n Infrastructure + Real Publishing
**Goal**: All scheduled operations run through observable n8n workflows with verified webhook contracts and a clean Celery cutover
**Depends on**: Phase 8 (v1.0 complete)
**Requirements**: N8N-01, N8N-02, N8N-03, N8N-04, N8N-05, N8N-06
**Success Criteria** (what must be TRUE):
  1. User can see live workflow status for any in-progress publishing or analytics operation (countdown/polling state visible in UI)
  2. A scheduled post reaches LinkedIn/X/Instagram via n8n workflow — the n8n execution log shows the publish node completing successfully
  3. All six previously Celery-beat tasks (publishing, analytics polling, credit resets, cleanup, strategist trigger, monthly credits) run on schedule via n8n and not Celery beat
  4. Submitting the same publish operation twice within 2 minutes produces exactly one social post (idempotency key prevents duplicate)
  5. Image/video generation tasks still run via Celery (Motor-coupled) — no regression on media generation after n8n cutover
**Plans**: 3 plans
Plans:
- [x] 09-01-PLAN.md — N8nConfig dataclass + webhook bridge route (callback + trigger) + tests
- [x] 09-02-PLAN.md — Execute endpoints + Celery beat cutover + Docker Compose n8n + idempotency
- [x] 09-03-PLAN.md — Workflow status notifications + n8n workflow JSON templates
**UI hint**: yes

### Phase 10: LightRAG Knowledge Graph
**Goal**: Every user has a live knowledge graph of their approved content, and the Thinker agent queries it for topic gap analysis before angle selection
**Depends on**: Phase 9
**Requirements**: LRAG-01, LRAG-02, LRAG-03, LRAG-04, LRAG-05, LRAG-06, LRAG-07
**Success Criteria** (what must be TRUE):
  1. LightRAG sidecar container starts and connects to its own MongoDB database (`thookai_lightrag`) without touching the ThookAI application database
  2. Approving a content job triggers entity extraction and writes to both Pinecone (similarity) and LightRAG (relationships) — the user's knowledge graph gains nodes for that content's topics, hooks, and tones
  3. Generating content on a topic the user has covered extensively surfaces noticeably different angles than before — Thinker retrieval identifies "angles NOT used" via multi-hop graph query
  4. User A's knowledge graph nodes are never visible in User B's query results (per-user namespace isolation enforced at storage level)
  5. Starting the LightRAG service with the wrong embedding model dimension causes a startup assertion failure, not silent data corruption
**Plans**: 3 plans
Plans:
- [x] 10-01-PLAN.md — LightRAGConfig dataclass + docker-compose sidecar + lightrag_service.py HTTP client + startup assertion
- [x] 10-02-PLAN.md — Learning agent dual-write (Pinecone + LightRAG) + Thinker graph query injection + routing contract
- [x] 10-03-PLAN.md — Unit tests for lightrag_service.py + integration tests for routing contract and entity type config

### Phase 11: Multi-Model Media Orchestration
**Goal**: Users can generate professional-grade social media visuals and video in all major formats — the platform routes each asset to the optimal provider and assembles the final output via Remotion
**Depends on**: Phase 9
**Requirements**: MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07, MEDIA-08, MEDIA-09, MEDIA-10, MEDIA-11, MEDIA-12, MEDIA-13, MEDIA-14
**Success Criteria** (what must be TRUE):
  1. User can generate a brand-consistent static image with typography (quote card, meme, infographic) for any approved content job — image appears in media assets with correct platform dimensions
  2. User can generate a multi-slide image carousel (up to 10 slides) for LinkedIn/Instagram — all slides share persona branding and download as a single deliverable
  3. User can generate a talking-head video with text/graphic overlays and a short-form reel (15-60s) with voice narration, B-roll, and music bed
  4. If any single provider fails mid-pipeline, the credit ledger records the exact stage of failure and the user is charged only for completed stages — no silent credit drain
  5. The Designer agent selects the optimal content format for the platform and content angle without user guidance — format choices are explained in the job details
**Plans**: 5 plans
Plans:
- [x] 11-01-PLAN.md — Remotion Express API service with 5 compositions + docker-compose sidecar
- [x] 11-02-PLAN.md — RemotionConfig + pipeline credit ledger + MediaOrchestrator core + R2 pre-staging
- [x] 11-03-PLAN.md — Static image orchestration (static_image, quote_card, meme, infographic)
- [x] 11-04-PLAN.md — Carousel + video orchestration (carousel, talking_head, short_form_video, text_on_video)
- [x] 11-05-PLAN.md — Designer format selection + QC media validation
**UI hint**: yes

### Phase 12: Strategist Agent
**Goal**: A nightly AI agent synthesizes each user's content history, performance signals, and persona into a ranked list of recommendation cards that appear waiting for them the next morning
**Depends on**: Phase 10 (LightRAG populated), Phase 13 (analytics data flowing)
**Requirements**: STRAT-01, STRAT-02, STRAT-03, STRAT-04, STRAT-05, STRAT-06, STRAT-07
**Success Criteria** (what must be TRUE):
  1. Every morning (after nightly n8n cron), a user with approved content history sees up to 3 new recommendation cards in their strategy feed — no more than 3 are added per day regardless of signal volume
  2. Every recommendation card includes a "Why now: [signal]" rationale — the user can read exactly which signal (trending topic, content gap, recent performance, new vault note) triggered the recommendation
  3. One-click approve on a card fires content generation with a pre-filled payload — no additional form fields required before generation starts
  4. Dismissing a card archives it and suppresses the same topic for 14 days — the user never sees the same topic resurface within the suppression window
  5. After 5 consecutive dismissals, the generation rate halves and a "calibrate preferences" prompt appears — the agent adapts rather than continuing to spam
**Plans**: 4 plans
Plans:
- [x] 12-01-PLAN.md — StrategistConfig dataclass + N8nConfig workflow field + DB indexes + .env.example
- [x] 12-02-PLAN.md — Strategist agent core (strategist.py) with cadence controls, LightRAG integration, dismissal tracking
- [x] 12-03-PLAN.md — n8n bridge execute endpoint + workflow map + notification map
- [x] 12-04-PLAN.md — Comprehensive tests for all STRAT requirements (STRAT-01 through STRAT-07)

### Phase 13: Analytics Feedback Loop
**Goal**: Real engagement data from LinkedIn, X, and Instagram flows back into the platform 24 hours and 7 days after each published post, feeding Strategist recommendations and persona intelligence
**Depends on**: Phase 9 (n8n publishing confirmed working)
**Requirements**: ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04
**Success Criteria** (what must be TRUE):
  1. A post published today shows real engagement metrics (impressions, reach, likes, comments) in the platform 24-25 hours after publishing — the data comes from the social platform API, not ThookAI's internal counts
  2. Performance data is written to `content_jobs.performance_data` with both 24h and 7d snapshots — the content detail view shows two data points over time
  3. `persona_engines.performance_intelligence.optimal_posting_times` updates after each 7-day analytics cycle — posting time recommendations change as real data accumulates
  4. The Strategist Agent's next nightly run incorporates the latest performance data — recommendation rationales reference actual post performance ("your last 3 posts about X underperformed; try angle Y")
**Plans**: 2 plans
Plans:
- [x] 13-01-PLAN.md — N8nConfig analytics fields + DB indexes + publish_results write-back to content_jobs
- [x] 13-02-PLAN.md — poll-analytics-24h/7d execute endpoints + comprehensive ANLYT tests

### Phase 14: Strategy Dashboard + Notifications
**Goal**: Users have a dedicated Strategy page that surfaces Strategist recommendations in real time via SSE, with one-click workflows and a complete history of past recommendations
**Depends on**: Phase 12 (Strategist producing cards), Phase 13 (analytics feeding Strategist)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. User can navigate to a Strategy page and see up to 3 active recommendation cards — the page updates in real time when a new card arrives (no page refresh needed)
  2. Clicking "Approve" on a card triggers content generation immediately and shows a generation-in-progress indicator — no additional configuration required
  3. Dismissed cards move to a History tab and are never permanently deleted — user can browse all past recommendations
  4. User receives an SSE notification when a content job completes, when a scheduled post publishes, and when a new trending topic recommendation arrives
  5. Strategy API routes (`GET /api/strategy`, `POST /api/strategy/:id/approve`, `POST /api/strategy/:id/dismiss`) respond correctly and are protected by auth middleware
**Plans**: 2 plans
Plans:
- [x] 14-01-PLAN.md — Strategy API routes (GET feed, POST approve, POST dismiss) + server registration + unit tests
- [x] 14-02-PLAN.md — StrategyDashboard React page + useStrategyFeed hook + sidebar nav + NotificationBell icon
**UI hint**: yes

### Phase 15: Obsidian Vault Integration
**Goal**: Users who run Obsidian can connect their personal research vault as a Scout enrichment source and Strategist signal — content is grounded in the user's own knowledge, not just web research
**Depends on**: Phase 12 (Strategist built), Phase 14 (Strategy Dashboard showing results)
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04, OBS-05, OBS-06
**Success Criteria** (what must be TRUE):
  1. A user who has connected their Obsidian vault sees their vault notes cited in Scout's research output during content generation — the generation output references vault content by note title
  2. The Strategist identifies new vault notes created in the last 24 hours as a recommendation trigger signal — adding a new research note to the vault can appear as a recommendation card the next morning
  3. Generating content without Obsidian configured works identically to before — Scout falls back to Perplexity only with no errors or degraded output
  4. The opt-in UI shows the exact vault subdirectory path ThookAI will read before activation — user must explicitly confirm the path
  5. A path traversal attempt (configuring `OBSIDIAN_BASE_URL` with a path outside the designated subdirectory) is blocked at the service level with a logged error — no vault files outside the designated directory are ever read
**Plans**: TBD
**UI hint**: yes

### Phase 16: E2E Audit + Security Hardening + Production Ship
**Goal**: Every user-facing workflow is verified end-to-end, all new integration points are security-hardened, and the platform is production-ready for public launch
**Depends on**: Phases 9-15 (all v2.0 features complete)
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04, E2E-05, E2E-06, E2E-07, E2E-08, E2E-09, E2E-10
**Success Criteria** (what must be TRUE):
  1. The full critical path (signup -> onboard -> generate -> schedule -> publish -> analytics -> strategy recommend -> one-click approve -> publish again) completes without errors in a smoke test run
  2. The n8n instance is not publicly accessible — direct HTTP requests to the n8n URL from outside the private network return 401 or connection refused; `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` is confirmed in production env
  3. LightRAG per-user graph isolation is verified: authenticated as User A, a direct query to the LightRAG API with User B's user_id returns zero results
  4. Remotion render queue handles 5 concurrent render requests without timeout or OOM — load test results documented in audit report
  5. All Stripe billing flows, OAuth platform connections, and API rate limits work correctly under concurrent load — no silent failures
**Plans**: 5 plans
Plans:
- [x] 16-01-PLAN.md — E2E critical path smoke test + dead link detection
- [x] 16-02-PLAN.md — n8n security hardening (production Docker Compose + verification tests)
- [x] 16-03-PLAN.md — LightRAG per-user isolation + SSE notification scoping verification
- [x] 16-04-PLAN.md — Remotion load test + API rate limit concurrent verification
- [x] 16-05-PLAN.md — Stripe billing E2E + OAuth flow verification for all platforms

### Phase 17: Test Foundation + Billing & Payments
**Goal**: A clean, reliable CI baseline exists with branch coverage enforcement, then every revenue path in billing is verified with 255 tests and 3 P0 bugs fixed via TDD — no revenue can be double-charged, skipped, or bypassed before Phase 18 begins
**Depends on**: Phase 16 (v2.0 complete)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, BILL-06, BILL-07, BILL-08, BILL-09
**Success Criteria** (what must be TRUE):
  1. `pytest -q` exits 0 with zero failures and zero RuntimeWarning-as-error emissions — the 3 previously broken CI tests are resolved and the 6 known unawaited coroutine warnings are fixed
  2. Running `pytest --cov --cov-branch` on billing modules reports 95%+ branch coverage for `services/credits.py`, `services/stripe_service.py`, and `routes/billing.py`
  3. A Stripe webhook delivered twice with the same event ID activates a subscription exactly once — no double-activation occurs in the test suite under mongomock-motor
  4. Two concurrent requests to deduct credits from the same user account never produce a negative balance — the atomic `find_one_and_update` contract is verified with `asyncio.gather` under mongomock-motor
  5. The JWT fallback path that previously accepted malformed tokens now returns 401 — a failing test exposes the bug before the production fix lands
**Plans**: 5 plans
Plans:
- [x] 17-01-PLAN.md — Clean CI baseline: fix 3 broken tests, fix 6 unawaited coroutines, install 6 packages, coverage infrastructure, standardize conftest.py fixtures
- [x] 17-02-PLAN.md — TDD fix 3 P0 bugs: JWT fallback secret, non-atomic add_credits, missing webhook deduplication
- [x] 17-03-PLAN.md — CI matrix: 4 domain-specific test jobs with per-domain coverage thresholds
- [x] 17-04-PLAN.md — Billing tests: checkout flows, subscription lifecycle, volume pricing (~120 tests)
- [x] 17-05-PLAN.md — Billing tests: webhook idempotency, credit atomicity, route integration, 95% coverage gate (~120 tests)

### Phase 18: Security & Auth
**Goal**: Every auth boundary and security control across the platform is verified — JWT lifecycle, all 4 OAuth platform flows, rate limiting thresholds, security headers, injection prevention, and RBAC are all tested to the OWASP Top 10 standard
**Depends on**: Phase 17 (clean baseline, JWT bug fixed, coverage infrastructure in place)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, SEC-07
**Success Criteria** (what must be TRUE):
  1. A malformed, expired, or algorithm-confused JWT token returns 401 on all protected routes — not a 500 or silent grant of access
  2. OAuth flows for LinkedIn, X/Twitter PKCE, Instagram, and Google all complete with state parameter validation — a forged state parameter is rejected with 400
  3. Sending 100 auth requests per second to `/api/auth/login` triggers a 429 response — the rate limiter threshold is verified under concurrent load
  4. Every route in the application returns the expected CSP, HSTS, X-Frame-Options, and X-Content-Type-Options headers — no route is missing a required security header
  5. A NoSQL injection payload (`{"$gt": ""}`) in any user-facing input field does not return unauthorized data — input validation middleware blocks it at the boundary
  6. An authenticated non-admin user calling any admin-only route receives 403 — workspace member role enforcement is verified for viewer/editor/owner boundaries
**Plans**: 4 plans
Plans:
- [x] 18-01-PLAN.md — Security test directory + conftest.py + JWT lifecycle tests + security headers tests (SEC-01, SEC-04)
- [ ] 18-02-PLAN.md — OAuth state forgery + token encryption + rate limiting hardening (SEC-02, SEC-03)
- [x] 18-03-PLAN.md — Input validation (NoSQL injection, XSS, path traversal) + OWASP Top 10 (SEC-05, SEC-07)
- [x] 18-04-PLAN.md — Admin authorization + workspace RBAC enforcement (SEC-06)

### Phase 19: Core Features
**Goal**: Every agent in the content pipeline, every v2.0 subsystem (LangGraph, media orchestration, n8n bridge, LightRAG, Strategist, analytics, Obsidian), and the LightRAG lambda cross-user bug are all verified with 240 tests using deterministic mocks — 85%+ branch coverage enforced globally
**Depends on**: Phase 17 (clean baseline, coverage gates active), Phase 18 (security contracts verified)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06, CORE-07, CORE-08, CORE-09, CORE-10
**Success Criteria** (what must be TRUE):
  1. Each LangGraph agent node (Commander, Scout, Thinker, Writer, QC) is testable in isolation — a deterministic LLM mock fixture replaces `LlmChat.generate()` and the node's output contract is verified without network calls
  2. User A's LightRAG query never returns documents belonging to User B — the per-user isolation bug (lambda-scoped client leaking connection state) is fixed via TDD: failing test written first, production fix applied second
  3. All 8 media format handlers (static_image, quote_card, meme, infographic, carousel, talking_head, short_form_video, text_on_video) route correctly through MediaOrchestrator — partial provider failure triggers correct credit ledger behavior
  4. An n8n bridge execute endpoint called with a tampered HMAC signature returns 401 — all n8n contract tests pass without a live n8n instance (respx transport mocking)
  5. `pytest --cov --cov-branch agents/ services/ routes/` reports 85%+ branch coverage — the global coverage gate enforced in CI passes
**Plans**: 5 plans
Plans:
- [x] 19-01-PLAN.md — Pipeline agent isolated tests (Commander/Scout/Thinker/Writer/QC) + LangGraph orchestrator node tests (CORE-01, CORE-02)
- [x] 19-02-PLAN.md — Media orchestrator comprehensive tests: all 8 format handlers + credit ledger partial failure (CORE-03)
- [x] 19-03-PLAN.md — TDD LightRAG lambda injection fix + comprehensive isolation tests (CORE-05, CORE-09)
- [x] 19-04-PLAN.md — n8n bridge contract tests for all execute endpoints + analytics feedback loop tests (CORE-04, CORE-07)
- [x] 19-05-PLAN.md — Strategist cadence/dismissal/throttle tests + Obsidian path sandboxing + 85% coverage gate (CORE-06, CORE-08, CORE-10)

### Phase 20: Frontend E2E & Integration
**Goal**: The full user journey is verified end-to-end via Playwright, the system holds under 50-concurrent-user load, Docker Compose brings all services to healthy, and every URL in the platform resolves — the platform is ready for public announcement
**Depends on**: Phases 17-19 (all backend test contracts verified and P0 bugs fixed)
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04, E2E-05, E2E-06, E2E-07
**Success Criteria** (what must be TRUE):
  1. Playwright executes the full critical path (signup → onboard → generate → schedule → publish → analytics → strategy → approve) against the live dev stack and all steps pass in CI
  2. The billing E2E flow (plan selection → Stripe checkout → subscription active → credit usage → upgrade) completes without errors — Stripe Test Clock compresses the lifecycle to seconds
  3. `docker compose up` starts all services (FastAPI, MongoDB, Redis, n8n, LightRAG, Remotion) and all health checks pass within 120 seconds
  4. Locust reports p95 response time under 500ms for the content generation endpoint under 50 concurrent users — credit deduction atomicity holds at load (no negative balance observed in Locust run)
  5. Dead link scan confirms all media asset URLs resolve and all internal API routes return expected status codes — no broken links exist in the deployed build
**Plans**: 5 plans
Plans:
- [x] 20-01-PLAN.md — Playwright setup + dual webServer config + CI workflow (E2E-01)
- [x] 20-02-PLAN.md — Locust load test (50 users) + Docker Compose smoke (E2E-05, E2E-06)
- [x] 20-03-PLAN.md — Critical path E2E: signup -> onboard -> generate -> schedule -> publish -> analytics -> strategy -> approve (E2E-02)
- [x] 20-04-PLAN.md — Billing E2E + Agency workspace E2E (E2E-03, E2E-04)
- [x] 20-05-PLAN.md — Dead link detection: static analysis + dynamic API route liveness (E2E-07)

### Phase 21: CI Strictness + httpOnly Cookie Auth Migration
**Goal**: Every CI failure is a hard failure (no silent blind spots), and all frontend auth is migrated from localStorage JWT to httpOnly secure cookies with CSRF protection
**Depends on**: Phase 20 (v2.1 complete, Playwright E2E passing)
**Requirements**: CI-01, CI-02, CI-03, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):
  1. A deliberate test failure in any backend test job or the Playwright E2E job causes the CI run to fail with a red status — no job can pass while tests are broken due to continue-on-error
  2. User can log in and the browser receives a Set-Cookie header with httpOnly and Secure flags — no JWT token is written to localStorage after the migration is complete
  3. A subsequent page reload after login shows the user as authenticated without any JavaScript reading from localStorage — the session is established purely via cookie
  4. A request to any protected API route with a forged CSRF token (or missing CSRF token) is rejected with 403 — the double-submit or synchronizer token pattern blocks cross-site request forgery
  5. Existing Authorization header-based auth (for non-browser API clients) continues to work alongside cookie auth — no regression for direct API consumers
**Plans**: 3 plans
Plans:
- [x] 21-01-PLAN.md — Remove all continue-on-error from ci.yml and e2e.yml (CI-01, CI-02, CI-03)
- [x] 21-02-PLAN.md — CSRF middleware + auth cookie CSRF token setup + tests (AUTH-01, AUTH-02, AUTH-05)
- [x] 21-03-PLAN.md — Frontend AuthContext + AuthPage + api.js cookie auth migration (AUTH-03, AUTH-04)
**UI hint**: yes

### Phase 22: apiFetch Migration + Error Handling
**Goal**: Every HTTP request in the React frontend flows through a single centralized client with consistent timeout, retry, error handling, and 401/403/5xx behavior — no raw fetch() calls remain
**Depends on**: Phase 21 (cookie auth in place — apiFetch must send cookies by default)
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06
**Success Criteria** (what must be TRUE):
  1. A request to any backend route from the frontend automatically includes credentials (cookies), applies a 15-second timeout, and parses JSON — no per-call configuration needed
  2. A 5xx response from any backend endpoint is automatically retried once after a short backoff — the user sees a loading state during the retry, not an immediate error
  3. A 401 response from any route redirects the user to /auth without any page-level try/catch in the calling component
  4. `grep -r "fetch(" frontend/src/` returns zero results — all 41 raw fetch calls have been replaced with apiFetch
  5. All feature flags and the API base URL are sourced from `frontend/src/lib/constants.js` — no hardcoded URLs or ad-hoc config values remain in component files
**Plans**: 3 plans
Plans:
- [x] 22-01-PLAN.md — Create constants.js + enhance apiFetch with timeout, retry, error handling (API-01, API-02, API-03, API-04)
- [ ] 22-02-PLAN.md — Migrate lib/ modules, hooks, components, AuthContext, non-Dashboard pages (API-05)
- [ ] 22-03-PLAN.md — Migrate all 17 Dashboard pages + final zero-fetch grep verification (API-05, API-06)
**UI hint**: yes

### Phase 23: Frontend Unit Test Suite
**Goal**: The React frontend has a complete unit and component test suite with 45+ tests covering the core auth, API, and feature components — tests run in CI on every push
**Depends on**: Phase 22 (apiFetch stable — tests can mock it reliably)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. Running `npm test -- --watchAll=false` from `frontend/` exits 0 with 45+ tests passing across 10+ test files — no test framework configuration errors
  2. AuthContext tests verify that an authenticated user state is established from cookie session and that logout clears the session — no localStorage interactions are tested or expected
  3. apiFetch tests verify timeout enforcement, retry-on-5xx, 401 redirect behavior, and JSON parsing using MSW request interception — no real network calls are made
  4. Component tests for StrategyDashboard, ContentStudio, Sidebar, and NotificationBell render correctly given mocked API responses — no snapshot-only tests (behavior is verified)
  5. The `frontend-test` CI job in `.github/workflows/ci.yml` runs on every push and blocks merge on failure
**Plans**: TBD
**UI hint**: yes

### Phase 24: Content Download + Redirect-to-Platform
**Goal**: Users can download any approved content as a file (text, images, zip) and open platform compose windows pre-filled with their content — without leaving the content detail view
**Depends on**: Phase 22 (apiFetch in place for any new API calls)
**Requirements**: DL-01, DL-02, DL-03, DL-04, DL-05, DL-06
**Success Criteria** (what must be TRUE):
  1. Clicking "Download Text" on any approved content job downloads a .txt file containing the final content — the filename includes the platform and a date stamp
  2. Clicking "Download Images" on a carousel content job downloads a .zip archive containing all slide images — single-image jobs download the image directly (no unnecessary zip)
  3. Clicking "Open in LinkedIn" opens a new tab to the LinkedIn share compose URL with the post text pre-filled — the URL uses the official LinkedIn share endpoint
  4. Clicking "Open in X" opens a new tab to the X tweet intent URL with the post text pre-filled and within the character limit
  5. The Instagram button shows an inline tooltip explaining that Instagram has no web compose URL and walks the user through copy-paste workflow — no broken link or dead button
  6. All download and redirect buttons appear in the content detail view alongside the existing Publish button — the layout is not broken on mobile viewports
**Plans**: TBD
**UI hint**: yes

### Phase 25: E2E Verification + Production Ship Checklist
**Goal**: The platform passes a full end-to-end Playwright verification including the new download/redirect features, all dependencies are audited clean, and a documented ship checklist confirms production readiness
**Depends on**: Phases 21-24 (all v2.2 features complete)
**Requirements**: SHIP-01, SHIP-02, SHIP-03, SHIP-04, SHIP-05, SHIP-06
**Success Criteria** (what must be TRUE):
  1. Playwright E2E passes green across the full critical path plus the new download/redirect flows (download text, open in LinkedIn, open in X) — all steps pass in CI without manual intervention
  2. `npm audit --audit-level=high` in `frontend/` reports zero high or critical vulnerabilities — any findings are resolved or explicitly risk-accepted with a written note
  3. `pip-audit` or `safety check` in `backend/` reports zero critical vulnerabilities — any findings are resolved or explicitly risk-accepted with a written note
  4. Every environment variable in `.env.example` has a comment explaining its purpose and whether it is required or optional — no blank or undocumented entries remain
  5. A production ship checklist document exists at `.planning/SHIP-CHECKLIST.md` and every item is checked off — the checklist covers env vars, secrets, DB indexes, Stripe config, n8n config, monitoring, and rollback procedure
  6. A grep for hardcoded secrets, `console.log` statements, and debug-only endpoints across the full codebase returns zero production-facing findings
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Git & Branch Cleanup | v1.0 | 2/2 | Complete | 2026-03-31 |
| 2. Infrastructure & Celery | v1.0 | 3/3 | Complete | 2026-03-31 |
| 3. Auth, Onboarding & Email | v1.0 | 3/3 | Complete | 2026-03-31 |
| 4. Content Pipeline | v1.0 | 2/2 | Complete | 2026-03-31 |
| 5. Publishing, Scheduling & Billing | v1.0 | 3/3 | Complete | 2026-03-31 |
| 6. Media Generation & Analytics | v1.0 | 3/3 | Complete | 2026-03-31 |
| 7. Platform Features, Admin & Frontend Quality | v1.0 | 4/4 | Complete | 2026-03-31 |
| 8. Gap Closure & Tech Debt | v1.0 | 2/2 | Complete | 2026-04-01 |
| 9. n8n Infrastructure + Real Publishing | v2.0 | 3/3 | Complete | 2026-03-31 |
| 10. LightRAG Knowledge Graph | v2.0 | 3/3 | Complete | 2026-03-31 |
| 11. Multi-Model Media Orchestration | v2.0 | 5/5 | Complete | 2026-04-01 |
| 12. Strategist Agent | v2.0 | 4/4 | Complete | 2026-04-01 |
| 13. Analytics Feedback Loop | v2.0 | 2/2 | Complete | 2026-04-01 |
| 14. Strategy Dashboard + Notifications | v2.0 | 2/2 | Complete | 2026-04-01 |
| 15. Obsidian Vault Integration | v2.0 | 0/TBD | Not started | - |
| 16. E2E Audit + Security Hardening + Production Ship | v2.0 | 5/5 | Complete | 2026-04-01 |
| 17. Test Foundation + Billing & Payments | v2.1 | 5/5 | Complete | 2026-04-03 |
| 18. Security & Auth | v2.1 | 3/4 | Complete | 2026-04-03 |
| 19. Core Features | v2.1 | 5/5 | Complete | 2026-04-03 |
| 20. Frontend E2E & Integration | v2.1 | 5/5 | Complete | 2026-04-03 |
| 21. CI Strictness + httpOnly Cookie Auth Migration | v2.2 | 3/3 | Complete    | 2026-04-03 |
| 22. apiFetch Migration + Error Handling | v2.2 | 1/3 | In Progress|  |
| 23. Frontend Unit Test Suite | v2.2 | 0/TBD | Not started | - |
| 24. Content Download + Redirect-to-Platform | v2.2 | 0/TBD | Not started | - |
| 25. E2E Verification + Production Ship Checklist | v2.2 | 0/TBD | Not started | - |
