# Roadmap: ThookAI Stabilization

## Overview

ThookAI has 30 merged PRs and every feature written in code, but bugs marked fixed are still broken
in the actual codebase. This milestone works through the full stack in dependency order: clean up
the git chaos, restore infrastructure, fix the user entry point (auth + onboarding), repair the
content pipeline, wire up publishing and billing, verify media generation and analytics, then
confirm every auxiliary feature and the frontend quality layer. When complete, a user can sign up,
onboard, generate, schedule, publish, pay, and manage their account without hitting a broken flow.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Git & Branch Cleanup** - Establish a single clean baseline before any code changes
- [ ] **Phase 2: Infrastructure & Celery** - Restore the task queue and supporting services that everything depends on
- [x] **Phase 3: Auth, Onboarding & Email** - Fix the user entry point and persona generation (core product value) (completed 2026-03-31)
- [x] **Phase 4: Content Pipeline** - Verify and repair the 5-agent generation pipeline end-to-end (completed 2026-03-31)
- [x] **Phase 5: Publishing, Scheduling & Billing** - Wire real publishing dispatch and restore the credit/billing loop (completed 2026-03-31)
- [x] **Phase 6: Media Generation & Analytics** - Verify credit-gated media features and real social metrics (completed 2026-03-31)
- [ ] **Phase 7: Platform Features, Admin & Frontend Quality** - Confirm all auxiliary features and frontend polish

## Phase Details

### Phase 1: Git & Branch Cleanup
**Goal**: A single, conflict-free dev branch exists as the canonical baseline for all stabilization work
**Depends on**: Nothing (first phase)
**Requirements**: GIT-01, GIT-02, GIT-03, GIT-04
**Success Criteria** (what must be TRUE):
  1. All worktree-agent-* branches are gone from local and remote — `git branch -a` shows none
  2. PR #30 (custom plan builder) is merged into dev with no conflicts
  3. `git log --oneline dev` shows a clean linear history with no unresolved merge artifacts
  4. main is updated from dev and matches dev HEAD for production deploy readiness
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Delete worktree-agent-* and merged stale branches
- [ ] 01-02-PLAN.md — Merge feat/post-launch-sprint into dev, advance main, push clean

### Phase 2: Infrastructure & Celery
**Goal**: The Celery worker and beat scheduler are running, all services are reachable, and the environment is fully documented and validated at startup
**Depends on**: Phase 1
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07
**Success Criteria** (what must be TRUE):
  1. `celery -A celery_app worker` starts without errors and all 4 queues (default, media, content, video) appear in the worker log
  2. Celery beat starts and logs that it is scheduling its registered tasks (process_scheduled_posts, reset_daily_limits, refresh_monthly_credits, cleanup_old_jobs, cleanup_expired_shares, aggregate_daily_analytics)
  3. `GET /health` returns 200 with green status for MongoDB, Redis, R2, and LLM connectivity
  4. `docker-compose up` brings all 6 services up with no container exit errors
  5. Starting the backend with a missing required env var prints a clear error naming the missing variable and exits — not a silent crash
  6. All 59 baseline tests pass (zero regressions from Phase 1 work)
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Fix test suite and verify Celery configuration
- [x] 02-02-PLAN.md — Env var validation, .env.example completion, health endpoint
- [x] 02-03-PLAN.md — Docker setup, CORS centralization, rate limiting verification


### Phase 3: Auth, Onboarding & Email
**Goal**: Users can register, log in, reset passwords, and complete onboarding — receiving a real personalized Persona Engine, not a mock fallback
**Depends on**: Phase 2
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. A new user can register with email/password, receives 200 starter credits, and is redirected to onboarding
  2. A returning user can log in and their session survives a full browser refresh
  3. Google OAuth login completes and either creates a new account or links to an existing one
  4. A user who clicks "Forgot password" receives an email via Resend with a working reset link
  5. Completing the 7-question onboarding interview produces a persona card with real personalized voice fingerprint fields — not the generic mock fallback (verifiable by checking the LLM model used in logs: must be claude-sonnet-4-20250514)
  6. Agency workspace invitation emails send via Resend with correct join links
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Auth core: registration with credits, login, session persistence, Google OAuth
- [x] 03-02-PLAN.md — Email service verification and password reset flow
- [x] 03-03-PLAN.md — Onboarding model fix verification and persona generation quality

### Phase 4: Content Pipeline
**Goal**: The 5-agent generation pipeline runs reliably end-to-end, producing personalized drafts using real user context — with fatigue awareness and past content memory
**Depends on**: Phase 3
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06
**Success Criteria** (what must be TRUE):
  1. A content generation request returns a draft within 180 seconds — job reaches "reviewing" status and content is visible in the UI
  2. The Thinker stage receives fatigue shield patterns from persona_refinement and uses them as explicit avoidance instructions (verifiable in Thinker prompt logs)
  3. The Writer stage queries Pinecone for similar past approved content and injects style examples into its prompt (verifiable in Writer prompt logs — Pinecone is called, not skipped)
  4. Jobs stuck in "processing" for more than 10 minutes are automatically cleaned up by Celery beat and marked as failed — they do not stay stuck forever
  5. UOM behavioral inference fields from the persona engine are present in the job context passed to agents
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Pipeline integration tests: orchestrator, UOM, fatigue shield, vector store
- [x] 04-02-PLAN.md — End-to-end pipeline execution and stale job cleanup verification

### Phase 5: Publishing, Scheduling & Billing
**Goal**: Scheduled posts actually reach social platforms, the credit/billing loop is end-to-end functional, and Celery beat handles all time-driven billing tasks
**Depends on**: Phase 4
**Requirements**: PUB-01, PUB-02, PUB-03, PUB-04, PUB-05, BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, BILL-06
**Success Criteria** (what must be TRUE):
  1. A post approved for immediate publish sends an actual API request to LinkedIn/X/Instagram (not a simulated log line) — verifiable by real post appearing on the platform or OAuth call appearing in network logs
  2. A post scheduled for a future time publishes via Celery beat within 2 minutes of its scheduled_at timestamp
  3. OAuth connect and disconnect flow completes for all three platforms (LinkedIn, X, Instagram) and platform_tokens collection reflects the change
  4. Stripe checkout session creates and a completed test-mode payment upgrades the user's subscription_tier and credits in the database
  5. Credits are atomically deducted before the pipeline starts — concurrent requests cannot produce a negative credit balance
  6. Starter tier hard caps are enforced: attempting a 3rd video or 6th carousel returns a 402 with a clear message; LinkedIn-only restriction blocks non-LinkedIn posts for free tier
  7. Monthly credit refresh runs on schedule via Celery beat and resets user credits to the correct tier amount
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — Publishing dispatch and platform OAuth verification tests
- [x] 05-02-PLAN.md — Atomic credit deduction fix and starter tier restrictions
- [x] 05-03-PLAN.md — Stripe billing flow verification and monthly credit refresh tests

### Phase 6: Media Generation & Analytics
**Goal**: Credit-gated media features (image, voice, video) run correctly and asynchronously, file uploads land in R2, and the analytics dashboard shows real platform metrics
**Depends on**: Phase 5
**Requirements**: MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, ANAL-01, ANAL-02, ANAL-03, ANAL-04
**Success Criteria** (what must be TRUE):
  1. Requesting AI image generation does not block the FastAPI event loop — other API endpoints remain responsive during a running image generation job
  2. Voice clone sample upload completes and ElevenLabs returns a voice_id stored in the user's media assets
  3. A file uploaded via the upload endpoint is stored in Cloudflare R2 — the URL returned resolves to the actual file; uploading without R2 configured returns HTTP 503 (not a silent /tmp save)
  4. Media assets in db.media_assets have valid R2 URLs that resolve (no dead links from /tmp fallback)
  5. The analytics dashboard shows engagement metrics sourced from real LinkedIn/X/Instagram API data for posts published in previous phases — not fabricated from job counts
  6. Optimal posting times in performance_intelligence reflect real engagement patterns from published posts (populated, not empty {})
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Async media generation verification (image, voice, video agents)
- [x] 06-02-PLAN.md — R2 upload path and media asset storage verification
- [x] 06-03-PLAN.md — Social analytics polling, optimal times, and real-data dashboard verification

### Phase 7: Platform Features, Admin & Frontend Quality
**Goal**: Every auxiliary feature (templates, exports, campaigns, sharing, webhooks, notifications) and admin/agency tooling works end-to-end, and the frontend has no broken states
**Depends on**: Phase 6
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-07, FEAT-08, FEAT-09, ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04, UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. The template marketplace displays at least 20 seed templates browsable by category; selecting one pre-fills the content generation form
  2. Content export produces a downloadable CSV with correct date-range filtering; copy export copies formatted text to clipboard
  3. The persona share link generates a URL that renders the public persona card without requiring login; the /discover viral card analyzes pasted posts and generates a shareable card
  4. The admin dashboard shows real platform stats (user count, active subscriptions, recent jobs) — not placeholder data
  5. SSE notifications fire in the browser for job completion and publish events — the notification bell updates without a page reload
  6. All five frontend pages load without JavaScript console errors; 401 responses redirect to /auth; the mobile hamburger sidebar opens and closes correctly
**UI hint**: yes
**Plans**: 4 plans

Plans:
- [ ] 07-01-PLAN.md — Platform features verification: repurpose, campaigns, templates, export, import
- [ ] 07-02-PLAN.md — Persona sharing, viral card, SSE notifications, outbound webhooks verification
- [ ] 07-03-PLAN.md — Admin dashboard and agency workspace verification
- [x] 07-04-PLAN.md — Frontend quality: mobile sidebar, error boundary, empty states, 401 handling

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Git & Branch Cleanup | 0/2 | Not started | - |
| 2. Infrastructure & Celery | 3/3 | Complete |  |
| 3. Auth, Onboarding & Email | 3/3 | Complete   | 2026-03-31 |
| 4. Content Pipeline | 2/2 | Complete   | 2026-03-31 |
| 5. Publishing, Scheduling & Billing | 3/3 | Complete   | 2026-03-31 |
| 6. Media Generation & Analytics | 3/3 | Complete   | 2026-03-31 |
| 7. Platform Features, Admin & Frontend Quality | 1/4 | In Progress|  |
