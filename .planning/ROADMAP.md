# Roadmap: ThookAI

## Milestones

- v1.0 ThookAI Stabilization — Phases 1-8 (shipped 2026-04-01) — [archive](milestones/v1.0-ROADMAP.md)
- v2.0 Intelligent Content Operating System — Phases 9-16 (in progress)

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

### v2.0 Intelligent Content Operating System (In Progress)

**Milestone Goal:** Transform ThookAI from a reactive content generation tool into a proactive content operating system — n8n orchestrates all workflows, LightRAG builds a living knowledge graph of each user's content history, a Strategist Agent synthesizes signals into ranked daily recommendations, and a multi-model media orchestrator produces professional-grade visuals and video.

- [x] **Phase 9: n8n Infrastructure + Real Publishing** - Replace Celery beat with n8n for all scheduled/external-API tasks; establish webhook bridge; hard cutover with idempotency keys (completed 2026-03-31)
- [x] **Phase 10: LightRAG Knowledge Graph** - Deploy per-user knowledge graph sidecar; wire Thinker agent with multi-hop retrieval; lock embedding model before first insert (completed 2026-03-31)
- [x] **Phase 11: Multi-Model Media Orchestration** - Media Orchestrator service routing to best provider per asset type; Remotion compositions for all formats; credit ledger for partial-failure accounting (completed 2026-04-01)
- [x] **Phase 12: Strategist Agent** - Nightly n8n-triggered agent synthesizing LightRAG + persona + analytics into ranked recommendation cards with cadence controls (completed 2026-04-01)
- [ ] **Phase 13: Analytics Feedback Loop** - Real social metrics polling 24h + 7d post-publish via n8n; performance data feeds Strategist and persona intelligence
- [ ] **Phase 14: Strategy Dashboard + Notifications** - New React page with SSE-driven recommendation feed; one-click approve; dismissed cards archived; strategy API routes
- [ ] **Phase 15: Obsidian Vault Integration** - Scout enrichment from personal vault; Strategist uses vault as recommendation signal; opt-in with explicit path sandboxing
- [ ] **Phase 16: E2E Audit + Security Hardening + Production Ship** - Full critical-path smoke testing; n8n security config; per-user graph isolation verified; load testing; dead link detection

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
**Plans**: TBD

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
**Plans**: TBD
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
  1. The full critical path (signup → onboard → generate → schedule → publish → analytics → strategy recommend → one-click approve → publish again) completes without errors in a smoke test run
  2. The n8n instance is not publicly accessible — direct HTTP requests to the n8n URL from outside the private network return 401 or connection refused; `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` is confirmed in production env
  3. LightRAG per-user graph isolation is verified: authenticated as User A, a direct query to the LightRAG API with User B's user_id returns zero results
  4. Remotion render queue handles 5 concurrent render requests without timeout or OOM — load test results documented in audit report
  5. All Stripe billing flows, OAuth platform connections, and API rate limits work correctly under concurrent load — no silent failures
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
| 9. n8n Infrastructure + Real Publishing | v2.0 | 3/3 | Complete   | 2026-03-31 |
| 10. LightRAG Knowledge Graph | v2.0 | 3/3 | Complete    | 2026-03-31 |
| 11. Multi-Model Media Orchestration | v2.0 | 5/5 | Complete    | 2026-04-01 |
| 12. Strategist Agent | v2.0 | 4/4 | Complete   | 2026-04-01 |
| 13. Analytics Feedback Loop | v2.0 | 0/TBD | Not started | - |
| 14. Strategy Dashboard + Notifications | v2.0 | 0/TBD | Not started | - |
| 15. Obsidian Vault Integration | v2.0 | 0/TBD | Not started | - |
| 16. E2E Audit + Security Hardening + Production Ship | v2.0 | 0/TBD | Not started | - |
