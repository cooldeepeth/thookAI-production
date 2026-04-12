# Roadmap: ThookAI

## Milestones

- v1.0 ThookAI Stabilization — Phases 1-8 (shipped 2026-04-01) — [archive](milestones/v1.0-ROADMAP.md)
- v2.0 Intelligent Content Operating System — Phases 9-16 (shipped 2026-04-01)
- v2.1 Production Hardening — 50x Testing Sprint — Phases 17-20 (shipped 2026-04-03)
- v2.2 Frontend Hardening & Production Ship — Phases 21-25 (shipped 2026-04-04)
- v3.0 Distribution-Ready Platform Rebuild — Phases 26-35 (in progress)

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

<details>
<summary>v2.2 Frontend Hardening & Production Ship (Phases 21-25) — SHIPPED 2026-04-04</summary>

- [x] **Phase 21: CI Strictness + httpOnly Cookie Auth Migration** - Remove all CI blind spots (continue-on-error), then migrate auth from localStorage JWT to httpOnly secure cookies with CSRF protection (completed 2026-04-03)
- [x] **Phase 22: apiFetch Migration + Error Handling** - Create centralized fetch wrapper with timeout, retry, error handling, and replace all 41 raw fetch() calls across the frontend (completed 2026-04-03)
- [x] **Phase 23: Frontend Unit Test Suite** - Install testing libraries, configure Jest, write 45+ unit/component tests across 10+ files, wire into CI (completed 2026-04-04)
- [x] **Phase 24: Content Download + Redirect-to-Platform** - Download text/images/zip from content detail view, open-in-platform compose URL buttons for LinkedIn and X (completed 2026-04-03)
- [x] **Phase 25: E2E Verification + Production Ship Checklist** - Full Playwright E2E verification, dependency audit, security sweep, env documentation, and ship checklist (completed 2026-04-04)

</details>

### v3.0 Distribution-Ready Platform Rebuild (In Progress)

**Milestone Goal:** Transform ThookAI from "code exists" to "every feature works perfectly end-to-end" — a new user can register, onboard interactively, generate multi-format content, schedule, and publish to real social accounts with zero errors. Ready for real users at scale.

- [x] **Phase 26: Backend Endpoint Hardening** - Audit and harden all 26 route files against production: every endpoint tested with curl, Pydantic validation enforced, standardized error format, auth guards verified, credit-safety checks, rate limiting tuned (completed 2026-04-11)
- [x] **Phase 27: Onboarding Reimagination** - Rebuild the onboarding wizard with voice sample recording, writing style analysis, visual identity selection, multi-step progress, save-as-you-go, and fix the LLM model name bug in onboarding.py (completed 2026-04-11)
- [x] **Phase 28: Content Generation Multi-Format** - Implement platform-specific content generation for all 9 formats (LinkedIn post/article/carousel, X tweet/thread, Instagram feed/reel/story) with persona-aware Writer prompts and real-time pipeline progress (completed 2026-04-12)
- [x] **Phase 29: Media Generation Pipeline** - Wire and verify the full media pipeline: auto-images via DALL-E/FAL.ai, carousel slides via Remotion, video via Runway/Luma, voice narration via ElevenLabs, R2 upload flow end-to-end, media display in UI (completed 2026-04-12)
- [x] **Phase 30: Social Publishing End-to-End** - Fix and verify LinkedIn UGC, X v2, and Instagram Meta Graph publishing with OAuth connect/refresh, token encryption, publish status tracking, and real engagement metrics display (completed 2026-04-12)
- [x] **Phase 31: Smart Scheduling** - Implement AI-suggested optimal posting times, user approval/modification of schedule, calendar view of all scheduled posts, and Celery Beat automatic publishing at scheduled times (completed 2026-04-12)
- [x] **Phase 32: Frontend Core Flows Polish** - Polish every core page: auth, dashboard, ContentStudio, settings — all loading/empty/error states, mobile responsive (375px/768px/1440px), keyboard navigation (completed 2026-04-12)
- [ ] **Phase 33: Design System & Landing Page** - Apply consistent design system across all pages, rebuild the landing page to be conversion-optimized with hero/features/how-it-works/pricing/CTA/footer, SEO meta and OG tags
- [ ] **Phase 34: Security & GDPR** - Full penetration-readiness: input validation, XSS sanitization, injection prevention, CSRF, rate limits, no secrets in code, no stack traces, dependency audit, GDPR data export/deletion, cookie consent, privacy/terms pages
- [ ] **Phase 35: Performance, Monitoring & Launch** - Profile all endpoints to <500ms, optimize frontend bundle (code splitting, lazy loading), Lighthouse >90, Sentry clean 48h, PostHog verified, E2E smoke test, 50-user load test, cross-browser, pre-launch checklist

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

1. LightRAG sidecar container starts and connects to its own MongoDB database without touching the ThookAI application database
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

1. User can generate a brand-consistent static image with typography for any approved content job — image appears in media assets with correct platform dimensions
2. User can generate a multi-slide image carousel for LinkedIn/Instagram — all slides share persona branding and download as a single deliverable
3. User can generate a talking-head video with overlays and a short-form reel with voice narration
4. If any single provider fails mid-pipeline, the credit ledger records the exact stage of failure and the user is charged only for completed stages
5. The Designer agent selects the optimal content format for the platform and content angle without user guidance
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

1. Every morning (after nightly n8n cron), a user with approved content history sees up to 3 new recommendation cards in their strategy feed
2. Every recommendation card includes a "Why now: [signal]" rationale — the user can read exactly which signal triggered the recommendation
3. One-click approve on a card fires content generation with a pre-filled payload — no additional form fields required
4. Dismissing a card archives it and suppresses the same topic for 14 days
5. After 5 consecutive dismissals, the generation rate halves and a "calibrate preferences" prompt appears
   **Plans**: 4 plans
   Plans:

- [x] 12-01-PLAN.md — StrategistConfig dataclass + N8nConfig workflow field + DB indexes + .env.example
- [x] 12-02-PLAN.md — Strategist agent core (strategist.py) with cadence controls, LightRAG integration, dismissal tracking
- [x] 12-03-PLAN.md — n8n bridge execute endpoint + workflow map + notification map
- [x] 12-04-PLAN.md — Comprehensive tests for all STRAT requirements

### Phase 13: Analytics Feedback Loop

**Goal**: Real engagement data from LinkedIn, X, and Instagram flows back into the platform 24 hours and 7 days after each published post, feeding Strategist recommendations and persona intelligence
**Depends on**: Phase 9 (n8n publishing confirmed working)
**Requirements**: ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04
**Success Criteria** (what must be TRUE):

1. A post published today shows real engagement metrics in the platform 24-25 hours after publishing — data comes from the social platform API, not ThookAI's internal counts
2. Performance data is written to content_jobs.performance_data with both 24h and 7d snapshots
3. persona_engines.performance_intelligence.optimal_posting_times updates after each 7-day analytics cycle
4. The Strategist Agent's next nightly run incorporates the latest performance data
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
2. Clicking "Approve" on a card triggers content generation immediately and shows a generation-in-progress indicator
3. Dismissed cards move to a History tab and are never permanently deleted
4. User receives an SSE notification when a content job completes, when a scheduled post publishes, and when a new trending topic recommendation arrives
5. Strategy API routes respond correctly and are protected by auth middleware
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

1. A user who has connected their Obsidian vault sees their vault notes cited in Scout's research output during content generation
2. The Strategist identifies new vault notes created in the last 24 hours as a recommendation trigger signal
3. Generating content without Obsidian configured works identically to before — Scout falls back to Perplexity only with no errors
4. The opt-in UI shows the exact vault subdirectory path ThookAI will read before activation — user must explicitly confirm the path
5. A path traversal attempt (configuring vault path outside the designated subdirectory) is blocked at the service level with a logged error
   **Plans**: 5 plans
   Plans:
   - [x] 26-01-PLAN.md — Wave 0 test scaffolds (test_error_format.py, test_credit_refund_media.py)
   - [x] 26-02-PLAN.md — Error format standardization: server.py exception handlers + middleware
   - [x] 26-03-PLAN.md — Pydantic field constraints: auth.py, content.py, onboarding.py, persona.py, uploads.py
   - [x] 26-04-PLAN.md — Credit refund: sync media paths in content.py + Celery task paths in media_tasks.py
   - [x] 26-05-PLAN.md — Auth guard audit + BACKEND-API-AUDIT.md endpoint registry
         **UI hint**: yes

### Phase 16: E2E Audit + Security Hardening + Production Ship

**Goal**: Every user-facing workflow is verified end-to-end, all new integration points are security-hardened, and the platform is production-ready for public launch
**Depends on**: Phases 9-15 (all v2.0 features complete)
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04, E2E-05, E2E-06, E2E-07, E2E-08, E2E-09, E2E-10
**Success Criteria** (what must be TRUE):

1. The full critical path (signup → onboard → generate → schedule → publish → analytics → strategy recommend → one-click approve → publish again) completes without errors in a smoke test run
2. The n8n instance is not publicly accessible — direct HTTP requests to the n8n URL from outside the private network return 401 or connection refused
3. LightRAG per-user graph isolation is verified: authenticated as User A, a direct query with User B's user_id returns zero results
4. Remotion render queue handles 5 concurrent render requests without timeout or OOM
5. All Stripe billing flows, OAuth platform connections, and API rate limits work correctly under concurrent load
   **Plans**: 5 plans
   Plans:

- [x] 16-01-PLAN.md — E2E critical path smoke test + dead link detection
- [x] 16-02-PLAN.md — n8n security hardening (production Docker Compose + verification tests)
- [x] 16-03-PLAN.md — LightRAG per-user isolation + SSE notification scoping verification
- [x] 16-04-PLAN.md — Remotion load test + API rate limit concurrent verification
- [x] 16-05-PLAN.md — Stripe billing E2E + OAuth flow verification for all platforms

### Phase 17: Test Foundation + Billing & Payments

**Goal**: A clean, reliable CI baseline exists with branch coverage enforcement, then every revenue path in billing is verified with 255 tests and 3 P0 bugs fixed via TDD
**Depends on**: Phase 16 (v2.0 complete)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, BILL-06, BILL-07, BILL-08, BILL-09
**Success Criteria** (what must be TRUE):

1. pytest -q exits 0 with zero failures and zero RuntimeWarning-as-error emissions
2. Running pytest --cov --cov-branch on billing modules reports 95%+ branch coverage for credits.py, stripe_service.py, and billing.py
3. A Stripe webhook delivered twice with the same event ID activates a subscription exactly once
4. Two concurrent requests to deduct credits from the same user account never produce a negative balance
5. Billing plan builder correctly calculates price for any combination of posts/platforms/media options
   **Plans**: 3 plans
   Plans:

- [x] 17-01-PLAN.md — CI baseline fix + test infrastructure (fixtures, conftest, coveragerc, CI matrix)
- [x] 17-02-PLAN.md — Billing TDD: 255 tests covering all billing routes and services
- [x] 17-03-PLAN.md — P0 bug fixes: JWT fallback removal, atomic credits, webhook deduplication

### Phase 18: Security & Auth

**Goal**: Every auth path and security surface is tested and hardened with 100 tests covering JWT, OAuth, OWASP Top 10, rate limiting, input validation, and RBAC
**Depends on**: Phase 17
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10
**Success Criteria** (what must be TRUE):

1. A user attempting to access any protected endpoint without a valid JWT receives 401
2. Rate limiting rejects the 61st auth request per minute per IP with 429
3. OWASP Top 10 inputs (SQL injection, XSS, path traversal) all return 400 with no stack trace
4. Google OAuth callback creates account on first visit and links to existing account on second visit with same email
5. Admin-only endpoints return 403 when called by a non-admin user with a valid JWT
   **Plans**: 2 plans
   Plans:

- [x] 18-01-PLAN.md — 126 security tests (JWT lifecycle, OAuth 4 platforms, OWASP Top 10, rate limiting)
- [x] 18-02-PLAN.md — RBAC tests + admin guard verification + input validation test suite

### Phase 19: Core Features

**Goal**: Every major feature in the content pipeline, LangGraph orchestrator, media orchestration, and learning systems has test coverage with all P0 bugs fixed
**Depends on**: Phase 18
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06, CORE-07
**Success Criteria** (what must be TRUE):

1. Content pipeline test suite exits clean at 85%+ branch coverage on pipeline.py and all agent files
2. LightRAG lambda injection vulnerability is fixed — user_id with special characters cannot cross-contaminate another user's graph
3. LangGraph orchestrator handles debate protocol and quality loop exit conditions without infinite loops
4. Media orchestration correctly routes to all 8 format handlers and accounts for credits at each stage
5. The Strategist agent test suite verifies cadence controls and topic suppression work correctly
   **Plans**: 3 plans
   Plans:

- [x] 19-01-PLAN.md — Content pipeline tests + LangGraph orchestrator tests (240 total)
- [x] 19-02-PLAN.md — Media orchestration tests + n8n bridge contract tests + LightRAG isolation tests
- [x] 19-03-PLAN.md — LightRAG lambda TDD fix + Strategist tests + analytics tests + Obsidian tests

### Phase 20: Frontend E2E & Integration

**Goal**: The frontend is covered by Playwright E2E tests and load tests that verify critical user paths work under realistic conditions
**Depends on**: Phase 19
**Requirements**: FE2E-01, FE2E-02, FE2E-03, FE2E-04
**Success Criteria** (what must be TRUE):

1. Playwright critical path test (register → onboard → generate → schedule) passes 3 consecutive runs without flake
2. Billing E2E test (subscribe → get credits → use credits → cancel) passes with Stripe test cards
3. Locust 50-user load test completes with p95 response time under 2 seconds and zero 5xx errors
4. Docker Compose smoke test starts all 7 services and returns 200 on /health within 60 seconds
   **Plans**: 2 plans
   Plans:

- [x] 20-01-PLAN.md — Playwright setup + critical path E2E + billing E2E + agency workspace E2E
- [x] 20-02-PLAN.md — Locust load test + Docker Compose smoke test + dead link detection

### Phase 21: CI Strictness + httpOnly Cookie Auth Migration

**Goal**: CI has no blind spots (every job must pass), and the frontend uses secure httpOnly cookies for auth instead of localStorage JWT tokens — eliminating XSS attack surface
**Depends on**: Phase 20
**Requirements**: CI-01, CI-02, AUTH-11, AUTH-12, AUTH-13
**Success Criteria** (what must be TRUE):

1. All CI jobs run without continue-on-error — a single test failure blocks the entire CI pipeline
2. User login sets a session_token httpOnly cookie — no auth tokens are ever stored in localStorage or accessible via JavaScript
3. CSRF protection is active on all state-changing endpoints — requests without X-CSRF-Token header return 403
4. Google OAuth flow works end-to-end with cookie auth (no regression from localStorage removal)
5. Logout clears the session cookie server-side — subsequent requests return 401
   **Plans**: 3 plans
   Plans:

- [x] 21-01-PLAN.md — CI strictness: remove all continue-on-error from ci.yml and e2e.yml
- [x] 21-02-PLAN.md — Backend httpOnly cookie auth: session_token cookie + CSRF middleware
- [x] 21-03-PLAN.md — Frontend auth migration: remove localStorage JWT, use cookie-based auth

### Phase 22: apiFetch Migration + Error Handling

**Goal**: All 41 raw fetch() calls in the frontend are replaced with a centralized apiFetch wrapper that provides automatic timeout, retry, CSRF injection, and standardized error handling
**Depends on**: Phase 21
**Requirements**: FE-01, FE-02, FE-03
**Success Criteria** (what must be TRUE):

1. No raw fetch() calls remain in the codebase — grep for "fetch(" in src/ returns only apiFetch.js itself
2. Any API call that times out after 30 seconds shows a user-friendly error toast, not a silent hang
3. All state-changing API calls (POST, PUT, PATCH, DELETE) automatically include the X-CSRF-Token header
4. A 401 response from any API call redirects the user to /auth without showing a raw error
   **Plans**: 3 plans
   Plans:

- [x] 22-01-PLAN.md — Create apiFetch wrapper in src/lib/api.js with timeout, retry, CSRF
- [x] 22-02-PLAN.md — Migrate all 41 fetch() calls in pages and components to apiFetch
- [x] 22-03-PLAN.md — Error handling standardization + 401 redirect + toast integration

### Phase 23: Frontend Unit Test Suite

**Goal**: A Jest + React Testing Library test suite covers all critical frontend components with 45+ tests wired into CI
**Depends on**: Phase 22
**Requirements**: FE-TEST-01, FE-TEST-02, FE-TEST-03
**Success Criteria** (what must be TRUE):

1. npm test exits 0 with 45+ passing tests and no skipped tests
2. AuthContext tests verify login, logout, and token refresh behavior
3. apiFetch tests verify timeout, retry, CSRF injection, and 401 redirect behavior
4. Critical UI component tests verify loading states, error states, and empty states render correctly
   **Plans**: 3 plans
   Plans:

- [x] 23-01-PLAN.md — Install Jest + RTL, configure, create test setup file and CI integration
- [x] 23-02-PLAN.md — AuthContext + apiFetch + api.js unit tests (25+ tests)
- [x] 23-03-PLAN.md — Component tests for ErrorBoundary, MediaUploader, NotificationBell, key pages (20+ tests)

### Phase 24: Content Download + Redirect-to-Platform

**Goal**: Users can download their generated content in multiple formats and open compose windows in LinkedIn and X with content pre-filled
**Depends on**: Phase 22
**Requirements**: FCAT-01, FCAT-02, FCAT-03
**Success Criteria** (what must be TRUE):

1. User can download a content job as plain text (.txt), CSV, or ZIP with all associated assets
2. Clicking "Open in LinkedIn" opens compose.linkedin.com with the generated text pre-filled in the post body
3. Clicking "Open in X" opens twitter.com/intent/tweet with the generated text pre-filled
4. Bulk download with date range filter downloads all matching content jobs as a ZIP file
   **Plans**: 1 plan
   Plans:

- [x] 24-01-PLAN.md — Content download endpoints (text/CSV/ZIP) + redirect URLs + frontend integration

### Phase 25: E2E Verification + Production Ship Checklist

**Goal**: The entire platform is verified against production via Playwright E2E tests, and a complete pre-launch checklist is signed off — no known broken flows remain
**Depends on**: Phases 21-24 (v2.2 features complete)
**Requirements**: SHIP-01, SHIP-02, SHIP-03, SHIP-04
**Success Criteria** (what must be TRUE):

1. Playwright critical path E2E (register → onboard → generate → download → schedule) passes 3 consecutive times against production
2. Dependency audit shows zero critical or high vulnerabilities in both backend and frontend
3. Security sweep finds no hardcoded secrets, no exposed stack traces, and no missing CSRF protection
4. Pre-launch checklist (environment variables, CORS config, rate limiting, SSL, error monitoring) is complete
   **Plans**: 2 plans
   Plans:

- [x] 25-01-PLAN.md — Playwright E2E verification (critical path, billing, agency, download/redirect)
- [x] 25-02-PLAN.md — Dependency audit + security sweep + env documentation + ship checklist

### Phase 26: Backend Endpoint Hardening

**Goal**: Every backend route file is audited against production: endpoints return correct data, input validation is enforced, errors are standardized, auth guards work, credit safety is verified, and rate limiting is tuned per endpoint
**Depends on**: Phase 25 (v2.2 complete)
**Requirements**: BACK-01, BACK-02, BACK-03, BACK-04, BACK-05, BACK-06, BACK-07, BACK-08
**Success Criteria** (what must be TRUE):

1. Calling any protected endpoint without a valid auth cookie returns exactly 401 with {"detail": "...", "error_code": "UNAUTHORIZED"} — verified via curl for all 26 route files
2. Sending a malformed or missing request body to any POST endpoint returns 400/422 (never 500) with a field-level error message identifying the offending field
3. Any content generation or media endpoint deducts credits before execution and auto-refunds if the pipeline fails — verified with concurrent requests and a forced failure
4. The auth endpoints (/api/auth/register, /api/auth/login) accept no more than 10 requests per minute per IP — the 11th request within 60 seconds returns 429
5. BACKEND-API-AUDIT.md exists in .planning/audit/ and lists status (working/broken/partially working) for every endpoint across all 26 route files
   **Plans**: 5 plans
   Plans:
   - [x] 26-01-PLAN.md — Wave 0 test scaffolds (test_error_format.py, test_credit_refund_media.py)
   - [x] 26-02-PLAN.md — Error format standardization: server.py exception handlers + middleware
   - [x] 26-03-PLAN.md — Pydantic field constraints: auth.py, content.py, onboarding.py, persona.py, uploads.py
   - [x] 26-04-PLAN.md — Credit refund: sync media paths in content.py + Celery task paths in media_tasks.py
   - [ ] 26-05-PLAN.md — Auth guard audit + BACKEND-API-AUDIT.md endpoint registry

### Phase 27: Onboarding Reimagination

**Goal**: The onboarding wizard collects voice samples, writing style examples, and visual identity preferences alongside the 7 core questions — resulting in a richer persona, and the LLM model name bug is fixed so persona generation actually works in production
**Depends on**: Phase 26
**Requirements**: ONBD-01, ONBD-02, ONBD-03, ONBD-04, ONBD-05, ONBD-06, ONBD-07, ONBD-08
**Success Criteria** (what must be TRUE):

1. A new user can complete the onboarding wizard in one session — the progress indicator shows which step they are on out of total steps, and they can navigate back to any completed step to edit their answers
2. User can record a 30-second voice sample directly in the browser (no upload required) — the recording is saved and a playback control appears confirming the capture
3. User can paste 3-5 of their past posts into a text area — the system analyzes the writing style and surface a "style fingerprint" summary the user can confirm
4. User can choose a visual identity palette from at least 6 options (e.g., bold/minimal/corporate/creative/warm/dark) — the choice is stored in persona.visual_preferences
5. After completing all onboarding steps, the generated persona includes non-empty values for voice_style, visual_preferences, writing_samples, and personality_traits — no field is null or a generic placeholder
6. Closing the browser mid-onboarding and returning later resumes from the last completed step — no answers are lost
   **Plans**: 5 plans
   Plans:
   - [x] 27-01-PLAN.md — Backend TDD: test stubs + extended GeneratePersonaRequest + persona_doc new fields
   - [x] 27-02-PLAN.md — Wizard container (5-step stepper, localStorage draft) + WritingStyleStep fingerprint confirm
   - [x] 27-03-PLAN.md — VoiceRecordingStep + VisualPaletteStep new components
   - [x] 27-04-PLAN.md — Wire new steps into wizard + InterviewStep counter + human verification checkpoint
   - [x] 27-05-PLAN.md — Backend audit + edge case tests + full suite gate
         **UI hint**: yes

### Phase 28: Content Generation Multi-Format

**Goal**: Users can generate all 9 platform-specific content formats (LinkedIn post/article/carousel, X tweet/thread, Instagram feed/reel/story) with persona-aware Writer prompts, format selection in the UI, and real-time pipeline progress visible during generation
**Depends on**: Phase 27
**Requirements**: CONT-01, CONT-02, CONT-03, CONT-04, CONT-05, CONT-06, CONT-07, CONT-08, CONT-09, CONT-10, CONT-11, CONT-12
**Success Criteria** (what must be TRUE):

1. User can select any of the 9 content formats in ContentStudio (platform picker → format picker) and generate content — the generated output is formatted correctly for that format (e.g., X tweet is under 280 characters, Instagram feed caption has hashtags, LinkedIn article has a header)
2. Generated content for the same topic on LinkedIn vs X reads noticeably differently — the platform-specific Writer prompt uses platform idioms, not a generic template
3. A user with an onboarded persona sees their voice reflected in the generated content (tone, vocabulary, perspective) — content for User A and User B on the same topic reads distinctly different
4. The generation progress bar shows each pipeline stage (Commander → Scout → Thinker → Writer → QC) advancing in real time — the user is never looking at a blank spinner with no information
5. User can edit the generated content inline, approve it, and schedule it — all from within ContentStudio without navigating away
   **Plans**: 5 plans
   Plans:
   - [x] 28-01-PLAN.md — Wave 0 test scaffolds for all 12 CONT requirements (RED state)
   - [x] 28-02-PLAN.md — writer.py FORMAT_RULES (8 keys) + commander.py WORD_COUNT_DEFAULTS + story_sequence allowlist
   - [x] 28-03-PLAN.md — InputPanel 9 formats + InstagramShell story slides + AgentPipeline font-bold
   - [x] 28-04-PLAN.md — ContentOutput schedule API fix (JSON body) + data-testids + CONT-11/12 backend tests
   - [x] 28-05-PLAN.md — Full suite verification, human checkpoint, VALIDATION.md update
         **UI hint**: yes

### Phase 29: Media Generation Pipeline

**Goal**: Every generated content job can have associated media — auto-images via DALL-E/FAL.ai, carousel slides via Remotion, video via Runway/Luma, voice narration via ElevenLabs — all delivered through R2 and displayable in the content preview
**Depends on**: Phase 28
**Requirements**: MDIA-01, MDIA-02, MDIA-03, MDIA-04, MDIA-05, MDIA-06, MDIA-07, MDIA-08
**Success Criteria** (what must be TRUE):

1. Clicking "Generate Image" on any approved content job produces a featured image within 30 seconds — the image appears in the content preview panel with the correct platform dimensions (1200x627 for LinkedIn, 1:1 for Instagram)
2. Clicking "Generate Carousel" on a LinkedIn content job produces a Remotion-rendered slide deck — at least 3 slides with consistent branding — and a download link appears in the media panel
3. Uploading a file via the media uploader completes successfully — the presigned URL flow works end-to-end (request URL → browser upload → confirm → asset appears in media list) with no 403 or CORS errors from R2
4. Generated voice narration for a post text (via ElevenLabs or OpenAI TTS) plays back in an audio player in the content preview — the audio file is stored in R2 and the URL is stable after 24 hours
5. A failed media generation (e.g., provider timeout) logs the error to Sentry, refunds the media credits to the user, and shows a retry button in the UI — no silent failures
   **Plans**: 5 plans
   Plans:
   - [x] 29-01-PLAN.md — Wave 0 test scaffolding (3 failing tests: CreativeProvidersService, voice R2, carousel Remotion)
   - [x] 29-02-PLAN.md — Fix Celery tasks: remove CreativeProvidersService, call agent functions directly (Bug 1)
   - [x] 29-03-PLAN.md — Voice narration R2 upload in narrate_content() + Sentry capture in media except blocks (Bug 2, Bug 5)
   - [x] 29-04-PLAN.md — Wire \_call_remotion(ImageCarousel) into generate_carousel() route (Bug 4)
   - [x] 29-05-PLAN.md — Frontend MediaPanel 202 async polling + R2 CORS verification checkpoint (Bug 3, MDIA-08)
         **UI hint**: yes

### Phase 30: Social Publishing End-to-End

**Goal**: Users can connect LinkedIn, X, and Instagram accounts via OAuth and publish content with media to all three platforms — OAuth tokens refresh automatically before expiry, publish status is tracked, and real engagement metrics appear after publishing
**Depends on**: Phase 28
**Requirements**: PUBL-01, PUBL-02, PUBL-03, PUBL-04, PUBL-05, PUBL-06, PUBL-07
**Success Criteria** (what must be TRUE):

1. User can click "Connect LinkedIn" in Settings → Connections, complete OAuth in a popup, and return to see LinkedIn listed as "Connected" with the connected account name — the same flow works for X and Instagram
2. Publishing an approved content job to LinkedIn creates a real post visible at linkedin.com — the platform returns a post ID and the content job status changes to "published" with the post URL stored
3. Publishing a thread to X (3+ tweets) creates a real thread visible at x.com — all tweets are linked as a thread, not as separate posts
4. An OAuth token that expires within 24 hours is automatically refreshed before the next scheduled publish — the user never sees an "expired token" error on a scheduled post
5. A failed publish attempt (e.g., API rate limit) shows the error message in the content job detail view with a "Retry" button — the post status changes to "failed" (not "published") and Sentry receives the error event
   **Plans**: 4 plans
   Plans:
   - [x] 30-01-PLAN.md — Fix \_publish_to_platform (decrypt token, return dict) + store publish_results on content_jobs
   - [x] 30-02-PLAN.md — Proactive 24h token refresh in get_platform_token + Instagram \_refresh_token branch
   - [x] 30-03-PLAN.md — token_expiring_soon in /api/platforms/status + Connections.jsx warning + Fernet round-trip test
   - [x] 30-04-PLAN.md — LinkedIn registerUpload + X media/upload image attachment + Instagram media wiring verification + VALIDATION.md

### Phase 31: Smart Scheduling

**Goal**: The platform suggests AI-optimized posting times per platform based on the user's engagement history, the user can view all scheduled posts in a calendar view, and Celery Beat reliably publishes posts at their scheduled times
**Depends on**: Phase 30
**Requirements**: SCHD-01, SCHD-02, SCHD-03, SCHD-04
**Success Criteria** (what must be TRUE):

1. When scheduling a post, the user sees up to 3 "optimal time" suggestions per platform — the suggestions are based on the user's historical engagement data (or a sensible default if no data exists), not hardcoded times
2. User can view a calendar showing all scheduled posts across LinkedIn, X, and Instagram on a monthly grid — clicking a post in the calendar opens the content detail view
3. A post scheduled for a specific time publishes within 2 minutes of that time — verified by checking the published_at timestamp on the content job after the Celery Beat task fires
4. Rescheduling a post (changing the scheduled_at time) cancels the existing Celery task and creates a new one at the correct time — verified by rescheduling and confirming the old time is no longer active
   **Plans**: 4 plans
   Plans:
   - [x] 31-01-PLAN.md — Test scaffold for SCHD-01 through SCHD-04 (RED state before implementation)
   - [x] 31-02-PLAN.md — Fix planner.py: dual-write to scheduled_posts + wire optimal times from persona_engines
   - [x] 31-03-PLAN.md — Add /schedule/calendar and /schedule/{id}/reschedule endpoints to dashboard.py
   - [x] 31-04-PLAN.md — Frontend: ContentCalendar.jsx calendar endpoint + reschedule modal
         **UI hint**: yes

### Phase 32: Frontend Core Flows Polish

**Goal**: Every core frontend page (auth, dashboard home, ContentStudio, settings) is polished to production quality — loading, error, and empty states all work correctly, the layout is responsive at all breakpoints, and keyboard navigation works throughout
**Depends on**: Phase 28 (content generation complete), Phase 30 (publishing complete)
**Requirements**: FEND-01, FEND-02, FEND-03, FEND-04, FEND-05, FEND-06, FEND-07
**Success Criteria** (what must be TRUE):

1. Visiting /auth on a fresh session shows the login form — social login buttons (Google, LinkedIn, X) are visible and functional, inline validation shows password requirements before submission, and a failed login shows an error message without page reload
2. The dashboard home page shows the user's real stats (credits remaining, posts generated, posts scheduled) with correct numbers — if no content exists yet, an empty state with a "Create your first post" CTA appears instead of a blank page
3. Resizing the browser from 375px to 1440px on any core page (auth, dashboard, ContentStudio, settings) shows a properly laid-out page at every width — no horizontal scroll, no overlapping elements, no truncated text
4. A user can complete the full ContentStudio workflow (select platform → select format → type topic → generate → edit → approve → schedule) using only the keyboard — Tab, Enter, Space, and arrow keys are sufficient
5. Every page shows a skeleton loader during data fetching, a user-friendly error message with retry option on API failure, and an appropriate empty state on first use — no page ever shows a blank white screen or a raw JavaScript error
   **Plans**: 6 plans
   Plans:
   - [x] 32-01-PLAN.md — AuthPage: password validation, ARIA error, button types, focus-ring (FEND-01)
   - [x] 32-02-PLAN.md — DashboardHome: error+retry state, empty CTA, responsive grid fix (FEND-02, FEND-05, FEND-06)
   - [x] 32-03-PLAN.md — Settings: 4-tab layout (Radix Tabs), BillingTab skeleton/error, MSW handlers (FEND-04, FEND-05, FEND-07)
   - [x] 32-04-PLAN.md — ContentStudio: video toggle keyboard, responsive layout, AgentPipeline aria-live (FEND-03, FEND-06, FEND-07)
   - [x] 32-05-PLAN.md — ErrorBoundary: design token fixes, AlertTriangle icon, focus-ring (FEND-05, FEND-07)
   - [x] 32-06-PLAN.md — Test suite: AuthPage, DashboardHome, Settings test files (FEND-01/02/04/05/07)
         **UI hint**: yes

### Phase 33: Design System & Landing Page

**Goal**: A consistent design system (lime/violet/dark palette, Clash Display headings, component tokens) is applied across all pages, and the landing page is rebuilt to be conversion-optimized with hero, features, how-it-works, pricing, social proof, and footer sections
**Depends on**: Phase 32
**Requirements**: DSGN-01, DSGN-02, DSGN-03, DSGN-04, DSGN-05
**Success Criteria** (what must be TRUE):

1. Every page in the application uses the same color tokens (lime #D4FF00 for CTAs, violet #7000FF for secondary, #050505 background) — no page has hardcoded hex colors or conflicting palette choices
2. The landing page has a visible hero section, a features section, a how-it-works section, a pricing/plan-builder section, and a footer with legal links — all sections are present and fully populated (no "coming soon" placeholders)
3. On a 375px mobile screen, the landing page renders without horizontal scroll, the hero CTA button is easily tappable, and the navigation collapses into a mobile menu — verified in browser at 375px width
4. The landing page /meta title includes "ThookAI", the meta description is under 160 characters and describes the product, and the Open Graph og:image is set — verified with a curl of the page HTML or browser DevTools
5. A first-time visitor to the landing page can clearly understand what ThookAI does, see how it works in 3 steps, and find the pricing — measurable by a 5-second reading test: a person reading the hero + features sections can explain the product
   **Plans**: TBD
   Plans: [To be planned]
   **UI hint**: yes

### Phase 34: Security & GDPR

**Goal**: ThookAI is penetration-test ready — every input is validated and sanitized, CSRF is enforced everywhere, no secrets are in code, no stack traces leak in production errors, dependencies have zero critical/high CVEs, and GDPR compliance is implemented with data export, account deletion, cookie consent, and legal pages
**Depends on**: Phase 32
**Requirements**: SECR-01, SECR-02, SECR-03, SECR-04, SECR-05, SECR-06, SECR-07, SECR-08, SECR-09, SECR-10, SECR-11, SECR-12, SECR-13
**Success Criteria** (what must be TRUE):

1. Sending a POST request with a payload containing a MongoDB injection pattern (e.g., {"$where": "..."}) or an XSS payload (e.g., "<script>alert(1)</script>") to any endpoint returns 400 with the input rejected — verified with 10 payloads from the OWASP testing guide
2. Running "grep -r 'os.environ.get' backend/" and "grep -rE '(API_KEY|SECRET|PASSWORD)\s\*=' backend/" returns zero results outside of config.py — no hardcoded secrets exist in the codebase
3. A user can request their full data export at GET /api/auth/export and receive a JSON file containing all their content jobs, persona, scheduled posts, analytics, and billing history — the response is complete within 10 seconds
4. A user can delete their account at **POST /api/auth/delete-account** with body {"confirm": "DELETE"} — within 5 seconds, their email is anonymized in the users collection, and their persona/content/scheduled posts are removed — the user can no longer log in (Note: implementation uses POST with confirmation body, not bare DELETE, for safer UX — see SECR-10)
5. Visiting the site for the first time shows a GDPR cookie consent banner — PostHog tracking only initializes after the user clicks "Accept" — verified by checking PostHog events in an incognito session before and after consent
6. /privacy and /terms pages exist and are accessible without authentication — both pages contain real content (not Lorem Ipsum)
**Plans**: 9 plans
Plans:
- [ ] 34-01-PLAN.md — XSS sanitization layer (SECR-01, SECR-02, SECR-03)
- [ ] 34-02-PLAN.md — Secret audit + Sentry PII scrubbing (SECR-06, SECR-07)
- [ ] 34-03-PLAN.md — Rate limiting + CSRF verification (SECR-04, SECR-05)
- [ ] 34-04-PLAN.md — Dependency CVE audit (SECR-08)
- [ ] 34-05-PLAN.md — GDPR export + delete backend gaps (SECR-09, SECR-10)
- [ ] 34-06-PLAN.md — Settings Data tab GDPR frontend UI (SECR-09, SECR-10)
- [ ] 34-07-PLAN.md — PostHog consent gate (SECR-11)
- [ ] 34-08-PLAN.md — Privacy + Terms polish + routing verification (SECR-12, SECR-13)
- [ ] 34-09-PLAN.md — Security test suite (all SECR)

### Phase 35: Performance, Monitoring & Launch

**Goal**: Every API endpoint responds in under 500ms at p95, the frontend bundle is optimized with code splitting and lazy loading achieving Lighthouse >90, Sentry shows zero unresolved errors for 48 hours, PostHog confirms user flows are tracked, the full E2E smoke test passes, and a 50-user load test verifies the platform handles scale
**Depends on**: Phases 26-34 (all v3.0 features complete)
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06, PERF-07, PERF-08, PERF-09
**Success Criteria** (what must be TRUE):

1. Curling the 10 most-used API endpoints 100 times each and calculating p95 latency shows all 10 under 500ms — endpoints that exceed this threshold have their slow queries identified via MongoDB explain() and indexed
2. Running Lighthouse in Chrome DevTools on the landing page, dashboard home, and ContentStudio each score 90+ on Performance — bundle analysis shows no single chunk exceeds 500KB and the main dashboard loads with code splitting
3. The full E2E smoke test (register → onboard → generate content → add media → schedule → publish → view analytics) completes without errors in a fresh browser session against the live production URL
4. A Locust load test of 50 concurrent users running the standard content generation flow for 5 minutes shows p95 response time under 2 seconds and zero 5xx errors in the results
5. Sentry shows zero unresolved errors for 48 consecutive hours after the final deployment — all existing error events are reviewed and resolved before the clock starts
6. The pre-launch checklist is signed off: SSL verified, CORS configured, all env vars set in Railway and Vercel, Stripe in production mode, rate limiting active, monitoring active, backup strategy documented
   **Plans**: TBD
   Plans: [To be planned]

## Progress

**Execution Order:**
v3.0 phases execute in order: 26 → 27 → 28 → 29 → 30 → 31 → 32 → 33 → 34 → 35

| Phase                                | Plans Complete | Status      | Completed  |
| ------------------------------------ | -------------- | ----------- | ---------- |
| 26. Backend Endpoint Hardening       | 5/5            | Complete    | 2026-04-11 |
| 27. Onboarding Reimagination         | 5/5            | Complete    | 2026-04-12 |
| 28. Content Generation Multi-Format  | 5/5            | Complete    | 2026-04-12 |
| 29. Media Generation Pipeline        | 5/5            | Complete    | 2026-04-12 |
| 30. Social Publishing End-to-End     | 4/4            | Complete    | 2026-04-12 |
| 31. Smart Scheduling                 | 4/4            | Complete    | 2026-04-12 |
| 32. Frontend Core Flows Polish       | 7/7            | Complete    | 2026-04-13 |
| 33. Design System & Landing Page     | 6/6            | Complete    | 2026-04-13 |
| 34. Security & GDPR                  | 0/9            | Not started | -          |
| 35. Performance, Monitoring & Launch | 0/TBD          | Not started | -          |
