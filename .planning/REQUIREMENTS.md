# Requirements: ThookAI Stabilization

**Defined:** 2026-03-31
**Core Value:** Every feature that exists in the codebase must actually work end-to-end — a user can sign up, onboard, generate content, schedule, publish, pay, and manage their account without hitting broken flows.

## v1 Requirements

Requirements for stabilization release. Each maps to roadmap phases.

### Git & Branch Cleanup

- [ ] **GIT-01**: All worktree-agent-* branches deleted from local and remote
- [ ] **GIT-02**: PR #30 (custom plan builder) merged into dev cleanly
- [ ] **GIT-03**: dev branch is the single clean baseline with no conflicts
- [ ] **GIT-04**: main updated from dev for production deploy

### Authentication & Onboarding

- [ ] **AUTH-01**: User can register with email/password and receives 200 starter credits
- [ ] **AUTH-02**: User can log in and session persists across browser refresh
- [ ] **AUTH-03**: Google OAuth login completes and creates/links user account
- [x] **AUTH-04**: Password reset email sends via Resend and reset link works
- [ ] **AUTH-05**: Onboarding interview uses correct Claude model (claude-sonnet-4-20250514, not mock fallback)
- [ ] **AUTH-06**: Persona Engine generated from onboarding is personalized with real voice fingerprint

### Content Pipeline

- [ ] **PIPE-01**: Content generation request completes within 180s timeout and returns draft
- [ ] **PIPE-02**: LangGraph orchestrator runs with debate protocol and quality loops
- [ ] **PIPE-03**: UOM behavioral inference steers agent behavior per user profile
- [ ] **PIPE-04**: Unified fatigue shield feeds avoidance patterns into Thinker during generation
- [ ] **PIPE-05**: Pinecone vector store enriches Writer with past approved content examples
- [ ] **PIPE-06**: Stale jobs (stuck in processing >10min) cleaned up automatically by Celery beat

### Publishing & Scheduling

- [ ] **PUB-01**: Content publishes to LinkedIn via real OAuth token dispatch (not simulated)
- [ ] **PUB-02**: Content publishes to X via real OAuth token dispatch
- [ ] **PUB-03**: Content publishes to Instagram via real OAuth token dispatch
- [ ] **PUB-04**: Scheduled posts execute via Celery beat at the correct scheduled time
- [ ] **PUB-05**: Platform OAuth connect and disconnect flow works for LinkedIn/X/Instagram

### Billing & Credits

- [ ] **BILL-01**: Custom plan builder preview endpoint returns correct credit count and price
- [ ] **BILL-02**: Stripe checkout session creates successfully and processes payment
- [ ] **BILL-03**: Stripe webhook updates subscription status and credits in DB
- [ ] **BILL-04**: Credits are deducted before pipeline starts (not check-only)
- [ ] **BILL-05**: Starter tier hard caps enforced (max 2 videos, 5 carousels, LinkedIn only)
- [ ] **BILL-06**: Monthly credit refresh runs via Celery beat and resets user credits

### Media Generation

- [ ] **MEDIA-01**: AI image generation runs async (does not block FastAPI event loop)
- [ ] **MEDIA-02**: Voice clone sample upload and ElevenLabs clone creation works
- [ ] **MEDIA-03**: Video generation pipeline and HeyGen avatar creation works
- [ ] **MEDIA-04**: File uploads go to Cloudflare R2 (HTTP 503 if R2 unavailable in production, no /tmp fallback)
- [ ] **MEDIA-05**: Media assets stored in DB with valid R2 URLs that resolve

### Analytics & Intelligence

- [ ] **ANAL-01**: Social analytics service polls LinkedIn/X/Instagram APIs 24h and 7d after publish
- [ ] **ANAL-02**: Performance intelligence calculates real optimal posting times from engagement data
- [ ] **ANAL-03**: Analytics dashboard displays real metrics (not fabricated from job counts)
- [ ] **ANAL-04**: Persona evolution and refinement cycles tracked over time

### Platform Features

- [ ] **FEAT-01**: Content repurposing generates adapted content for target platform
- [ ] **FEAT-02**: Campaign grouping creates/lists/manages campaign umbrellas
- [ ] **FEAT-03**: Template marketplace displays 30 seed templates with browse/filter/use
- [ ] **FEAT-04**: Content export produces copy/CSV/bulk download with date range filter
- [ ] **FEAT-05**: Post history import accepts batch uploads and uses them for persona training
- [ ] **FEAT-06**: Persona sharing generates link and public view page renders persona card
- [ ] **FEAT-07**: Viral persona card at /discover analyzes pasted posts and generates shareable card
- [ ] **FEAT-08**: SSE notifications fire for job completion and publish events
- [ ] **FEAT-09**: Outbound webhooks fire on configurable events (Zapier integration)

### Admin & Agency

- [ ] **ADMIN-01**: Admin dashboard shows real platform stats and user management
- [ ] **ADMIN-02**: Agency workspace creation, joining, and member management works
- [ ] **ADMIN-03**: Workspace invitation emails send via Resend with correct links
- [ ] **ADMIN-04**: Member roles (owner/admin/member) and permissions enforced

### Infrastructure

- [x] **INFRA-01**: Celery worker starts with all queues (default, media, content, video) and beat runs scheduled tasks
- [x] **INFRA-02**: All existing tests pass (baseline 59, expected to grow)
- [x] **INFRA-03**: Docker/docker-compose builds and runs all 6 services successfully
- [x] **INFRA-04**: Health endpoint at /health checks MongoDB, Redis, R2, LLM connectivity
- [x] **INFRA-05**: All 35 env vars documented in .env.example and validated at startup with clear error messages
- [x] **INFRA-06**: CORS config centralized via settings.security.cors_origins
- [x] **INFRA-07**: Rate limiting works (Redis-backed primary, in-memory fallback)

### Frontend Quality

- [ ] **UI-01**: Mobile responsive sidebar with hamburger menu works
- [ ] **UI-02**: Error boundary catches render crashes and shows recovery UI
- [ ] **UI-03**: Empty states show friendly CTAs on ContentLibrary, Campaigns, Templates
- [ ] **UI-04**: Expired sessions (401) redirect to /auth automatically
- [ ] **UI-05**: All frontend pages load without JavaScript console errors

## v2 Requirements

Deferred to next milestone (M4-M11). Tracked but not in current scope.

### M4: Interactive Onboarding
- **M4-01**: Social profile batch analysis (connect accounts, analyze 90+ posts)
- **M4-02**: Visual preference test ("Swipe & Pick" content styles)
- **M4-03**: Voice sample analysis (60s recording → Whisper extraction)
- **M4-04**: Brand identity canvas (colors, fonts, pillars, exclusions)
- **M4-05**: Animated persona card reveal

### M5: Persona Refinement & Content DNA
- **M5-01**: Content DNA fingerprinting (rhythm, emotional arc, vocabulary clusters)
- **M5-02**: 4-cycle refinement (real-time, micro, weekly, monthly)
- **M5-03**: Per-channel persona variants

### M6-M11: Future Features
- **M6**: Trend Prediction Engine with Multi-Agent Debate Arena
- **M7**: Full Media Pipeline (LTX, Higgsfield, Remotion, Sound Agent)
- **M8**: Multi-Language Engine (20+ languages, Sarvam AI for Indian languages)
- **M9**: Intelligence & Analytics v2 (Algorithm Pulse, Audience Simulation)
- **M10**: Platform-Native UX Shells (rich composers)
- **M11**: Extraordinary Features (Content Twin, Cross-Creator Intelligence)

## Out of Scope

| Feature | Reason |
|---------|--------|
| New feature development | Stabilize existing features first — no new code until everything works |
| UI/UX redesign | Stabilize current UI, aesthetic changes deferred |
| Performance optimization | Get it working first, optimize later |
| Migration to different tech stack | Stabilize what exists |
| Mobile app | Web-first, mobile deferred to future milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GIT-01 | Phase 1 | Pending |
| GIT-02 | Phase 1 | Pending |
| GIT-03 | Phase 1 | Pending |
| GIT-04 | Phase 1 | Pending |
| INFRA-01 | Phase 2 | Complete |
| INFRA-02 | Phase 2 | Complete |
| INFRA-03 | Phase 2 | Complete |
| INFRA-04 | Phase 2 | Complete |
| INFRA-05 | Phase 2 | Complete |
| INFRA-06 | Phase 2 | Complete |
| INFRA-07 | Phase 2 | Complete |
| AUTH-01 | Phase 3 | Pending |
| AUTH-02 | Phase 3 | Pending |
| AUTH-03 | Phase 3 | Pending |
| AUTH-04 | Phase 3 | Complete |
| AUTH-05 | Phase 3 | Pending |
| AUTH-06 | Phase 3 | Pending |
| PIPE-01 | Phase 4 | Pending |
| PIPE-02 | Phase 4 | Pending |
| PIPE-03 | Phase 4 | Pending |
| PIPE-04 | Phase 4 | Pending |
| PIPE-05 | Phase 4 | Pending |
| PIPE-06 | Phase 4 | Pending |
| PUB-01 | Phase 5 | Pending |
| PUB-02 | Phase 5 | Pending |
| PUB-03 | Phase 5 | Pending |
| PUB-04 | Phase 5 | Pending |
| PUB-05 | Phase 5 | Pending |
| BILL-01 | Phase 5 | Pending |
| BILL-02 | Phase 5 | Pending |
| BILL-03 | Phase 5 | Pending |
| BILL-04 | Phase 5 | Pending |
| BILL-05 | Phase 5 | Pending |
| BILL-06 | Phase 5 | Pending |
| MEDIA-01 | Phase 6 | Pending |
| MEDIA-02 | Phase 6 | Pending |
| MEDIA-03 | Phase 6 | Pending |
| MEDIA-04 | Phase 6 | Pending |
| MEDIA-05 | Phase 6 | Pending |
| ANAL-01 | Phase 6 | Pending |
| ANAL-02 | Phase 6 | Pending |
| ANAL-03 | Phase 6 | Pending |
| ANAL-04 | Phase 6 | Pending |
| FEAT-01 | Phase 7 | Pending |
| FEAT-02 | Phase 7 | Pending |
| FEAT-03 | Phase 7 | Pending |
| FEAT-04 | Phase 7 | Pending |
| FEAT-05 | Phase 7 | Pending |
| FEAT-06 | Phase 7 | Pending |
| FEAT-07 | Phase 7 | Pending |
| FEAT-08 | Phase 7 | Pending |
| FEAT-09 | Phase 7 | Pending |
| ADMIN-01 | Phase 7 | Pending |
| ADMIN-02 | Phase 7 | Pending |
| ADMIN-03 | Phase 7 | Pending |
| ADMIN-04 | Phase 7 | Pending |
| UI-01 | Phase 7 | Pending |
| UI-02 | Phase 7 | Pending |
| UI-03 | Phase 7 | Pending |
| UI-04 | Phase 7 | Pending |
| UI-05 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after roadmap creation — traceability populated*
