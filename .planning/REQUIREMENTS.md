# Requirements: ThookAI v2.0 — Intelligent Content Operating System

**Defined:** 2026-04-01
**Core Value:** Personalized content creation at scale — every user gets a unique voice fingerprint that drives all content generation, with real social platform publishing and analytics feedback loops.

## v2.0 Requirements

Requirements for v2.0 milestone. Each maps to roadmap phases.

### n8n Infrastructure

- [x] **N8N-01**: n8n self-hosted deployment with Docker (`stable` tag) + PostgreSQL 15 queue mode
- [x] **N8N-02**: n8n webhook bridge — FastAPI triggers n8n workflows via POST, n8n calls back via HMAC-SHA256 authenticated endpoint (`POST /api/n8n/callback`)
- [x] **N8N-03**: Celery beat tasks migrated to n8n workflows — publishing, analytics polling, credit resets, cleanup jobs, strategist trigger
- [x] **N8N-04**: Hard Celery→n8n cutover protocol with idempotency keys on all publish operations (no dual execution)
- [x] **N8N-05**: Celery retained only for Motor-coupled media generation tasks (image/video rendering)
- [ ] **N8N-06**: User can see workflow status for in-progress operations (publishing countdown, analytics polling status)

### LightRAG Knowledge Graph

- [ ] **LRAG-01**: LightRAG sidecar service deployed as separate container with MongoDB storage (`thookai_lightrag` database)
- [ ] **LRAG-02**: Per-user namespace isolation — each user's knowledge graph is strictly separated at storage level
- [ ] **LRAG-03**: Domain-specific entity extraction prompt (topic domains, hook archetypes, emotional tones, named entities) tested on 10+ real posts before production ingestion
- [ ] **LRAG-04**: Embedding model (`text-embedding-3-small`) locked in config before first document insert with startup assertion on vector dimension
- [ ] **LRAG-05**: Thinker agent enhanced with multi-hop LightRAG retrieval — "what angles have I NOT used on topic X?"
- [ ] **LRAG-06**: Learning agent writes to both Pinecone (similarity) and LightRAG (relationships) on content approval
- [ ] **LRAG-07**: Strict retrieval routing contract — Thinker calls LightRAG only, Writer calls Pinecone only (no context bleeding)

### Multi-Model Media Orchestration

- [ ] **MEDIA-01**: Media Orchestrator service (`backend/services/media_orchestrator.py`) — decomposes MediaBrief into per-asset tasks, routes to best provider, assembles via Remotion
- [ ] **MEDIA-02**: Remotion render service expanded with Express API (`POST /render`, `GET /render/:id/status`) and R2 upload
- [ ] **MEDIA-03**: Pipeline credit ledger (`media_pipeline_ledger` collection) — per-stage credit tracking, cost caps per job, partial-failure accounting
- [ ] **MEDIA-04**: Static image with typography — brand-consistent social images via fal.ai/DALL-E + Remotion text overlay
- [ ] **MEDIA-05**: Quote cards — styled text-on-background with persona branding, dynamic font/color from persona theme
- [ ] **MEDIA-06**: Meme format — image + top/bottom text overlay with trending template support
- [ ] **MEDIA-07**: Image carousel — multi-slide compositions (up to 10 slides) for LinkedIn/Instagram via Remotion
- [ ] **MEDIA-08**: Infographic — data-driven visual with stats, icons, and structured layout via Remotion composition
- [ ] **MEDIA-09**: Talking-head with overlays — HeyGen avatar + text/graphic overlays via Remotion composition
- [ ] **MEDIA-10**: Short-form video (15-60s) — strategic reel with A-roll (talking-head), B-roll (stock/generated), typography overlays, voice narration (ElevenLabs), music bed
- [ ] **MEDIA-11**: Text-on-video — animated text overlays on user-uploaded or generated video clips
- [ ] **MEDIA-12**: Designer agent plans composition by format — selects optimal content type per platform and content angle
- [ ] **MEDIA-13**: All external assets pre-downloaded to R2 before Remotion render (timeout prevention)
- [ ] **MEDIA-14**: QC agent checks brand consistency, anti-AI-slop detection, and platform-specific specs on all media output

### Strategist Agent

- [ ] **STRAT-01**: Strategist Agent (`backend/agents/strategist.py`) — nightly n8n-triggered, synthesizes LightRAG + analytics + Obsidian + persona memory
- [ ] **STRAT-02**: Recommendation cards written to `db.strategy_recommendations` with `status: "pending_approval"` — never triggers generation directly
- [ ] **STRAT-03**: Every card includes "Why now: [signal]" rationale explaining the recommendation source
- [ ] **STRAT-04**: Cadence controls — max 3 new cards per user per day, hard cap enforced
- [ ] **STRAT-05**: Dismissal tracking — 14-day topic suppression on dismiss, dismissal rate monitored per user
- [ ] **STRAT-06**: If 5 consecutive dismissals, halve generation rate and surface "calibrate preferences" prompt
- [ ] **STRAT-07**: Recommendation cards include pre-filled `generate_payload` for one-click content generation

### Analytics Feedback Loop

- [ ] **ANLYT-01**: Real social metrics polling (24h + 7d after publish) via n8n workflows for LinkedIn, X, and Instagram
- [ ] **ANLYT-02**: Performance data written to `content_jobs.performance_data` with engagement, reach, impressions per platform
- [ ] **ANLYT-03**: Aggregated performance intelligence updates `persona_engines.performance_intelligence` with real optimal_posting_times
- [ ] **ANLYT-04**: Analytics data feeds into Strategist Agent for smarter recommendations (each publish cycle improves output)

### Strategy Dashboard

- [ ] **DASH-01**: New React page with SSE-driven recommendation card feed (max 3 active cards shown)
- [ ] **DASH-02**: One-click "Approve" button fires `POST /api/content/generate` with pre-filled payload from card
- [ ] **DASH-03**: Dismissed cards archived to History tab (not deleted)
- [ ] **DASH-04**: SSE notifications for job completion, trending topic alerts, scheduled post published
- [ ] **DASH-05**: Strategy routes (`GET /api/strategy`, `POST /api/strategy/:id/approve`, `POST /api/strategy/:id/dismiss`)

### Obsidian Vault Integration

- [ ] **OBS-01**: Scout agent enriched with Obsidian vault search results during content research phase
- [ ] **OBS-02**: Strategist uses recent vault files as recommendation trigger signal (new notes → new content ideas)
- [ ] **OBS-03**: `ObsidianConfig` dataclass in `backend/config.py` with `OBSIDIAN_BASE_URL` and `OBSIDIAN_API_KEY`
- [ ] **OBS-04**: Feature fully degrades when Obsidian not configured — Scout falls back to Perplexity only
- [ ] **OBS-05**: Strict path sandboxing — user designates specific subdirectory, all reads validated against vault root
- [ ] **OBS-06**: Opt-in UI with explicit "ThookAI will read files from: [path]" display before activation

### E2E Audit + Security Hardening

- [ ] **E2E-01**: Full E2E smoke testing across all user flows (signup → onboard → generate → schedule → publish → analytics → strategy)
- [ ] **E2E-02**: n8n instance behind private VPC or basic auth, `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` in production
- [ ] **E2E-03**: LightRAG per-user graph namespace enforcement verified (no cross-user data leakage)
- [ ] **E2E-04**: SSE event user-id scoping verified (no cross-user notification leakage)
- [ ] **E2E-05**: Load test confirming Remotion render queue handles 5+ concurrent requests
- [ ] **E2E-06**: Stripe billing verification with test keys across all plan types
- [ ] **E2E-07**: OAuth flow testing for all connected platforms (LinkedIn, X, Instagram, Google)
- [ ] **E2E-08**: API rate limit verification under concurrent load
- [ ] **E2E-09**: n8n execution history pruning configured (`EXECUTIONS_DATA_MAX_AGE=336`, `EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000`)
- [ ] **E2E-10**: Dead link detection across all media URLs and API endpoints

## Future Requirements

Deferred beyond v2.0. Tracked but not in current roadmap.

### Advanced Media

- **MEDIA-F01**: Multi-language voiceover via Sarvam AI (v3.0)
- **MEDIA-F02**: Real-time collaboration on media compositions (v3.0)
- **MEDIA-F03**: Custom Remotion template marketplace (v3.0)

### Platform Expansion

- **PLAT-F01**: Platform-native mobile apps (iOS/Android) (v3.0)
- **PLAT-F02**: TikTok publishing integration (v2.x)
- **PLAT-F03**: YouTube Shorts publishing integration (v2.x)

### Intelligence

- **INTEL-F01**: Content DNA Fingerprinting — deep voice analysis beyond persona cards (v2.x)
- **INTEL-F02**: Trend Prediction Engine — predict viral topics before they peak (v2.x)
- **INTEL-F03**: Automatic Obsidian write-back (anti-feature per research — offer explicit export only)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full auto-post without review | Brand safety requires human-in-the-loop — make approve fast, never remove it |
| General-purpose "write anything" mode | Bypasses Commander agent quality controls, degrades output |
| Bulk AI-generate full month unreviewed | Quality erosion, reputation risk for users |
| Multi-language engine (Sarvam AI) | Explicitly deferred to v3.0 per project constraints |
| Mobile native apps | Web-first, mobile deferred to v3.0 |
| Interactive onboarding redesign | Deferred — current onboarding works, polish later |
| Real-time collaboration | Small agencies handled by sequential review |
| Automatic Obsidian write-back | User trust risk — offer explicit export only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| N8N-01 | Phase 9 | Complete |
| N8N-02 | Phase 9 | Complete |
| N8N-03 | Phase 9 | Complete |
| N8N-04 | Phase 9 | Complete |
| N8N-05 | Phase 9 | Complete |
| N8N-06 | Phase 9 | Pending |
| LRAG-01 | Phase 10 | Pending |
| LRAG-02 | Phase 10 | Pending |
| LRAG-03 | Phase 10 | Pending |
| LRAG-04 | Phase 10 | Pending |
| LRAG-05 | Phase 10 | Pending |
| LRAG-06 | Phase 10 | Pending |
| LRAG-07 | Phase 10 | Pending |
| MEDIA-01 | Phase 11 | Pending |
| MEDIA-02 | Phase 11 | Pending |
| MEDIA-03 | Phase 11 | Pending |
| MEDIA-04 | Phase 11 | Pending |
| MEDIA-05 | Phase 11 | Pending |
| MEDIA-06 | Phase 11 | Pending |
| MEDIA-07 | Phase 11 | Pending |
| MEDIA-08 | Phase 11 | Pending |
| MEDIA-09 | Phase 11 | Pending |
| MEDIA-10 | Phase 11 | Pending |
| MEDIA-11 | Phase 11 | Pending |
| MEDIA-12 | Phase 11 | Pending |
| MEDIA-13 | Phase 11 | Pending |
| MEDIA-14 | Phase 11 | Pending |
| STRAT-01 | Phase 12 | Pending |
| STRAT-02 | Phase 12 | Pending |
| STRAT-03 | Phase 12 | Pending |
| STRAT-04 | Phase 12 | Pending |
| STRAT-05 | Phase 12 | Pending |
| STRAT-06 | Phase 12 | Pending |
| STRAT-07 | Phase 12 | Pending |
| ANLYT-01 | Phase 13 | Pending |
| ANLYT-02 | Phase 13 | Pending |
| ANLYT-03 | Phase 13 | Pending |
| ANLYT-04 | Phase 13 | Pending |
| DASH-01 | Phase 14 | Pending |
| DASH-02 | Phase 14 | Pending |
| DASH-03 | Phase 14 | Pending |
| DASH-04 | Phase 14 | Pending |
| DASH-05 | Phase 14 | Pending |
| OBS-01 | Phase 15 | Pending |
| OBS-02 | Phase 15 | Pending |
| OBS-03 | Phase 15 | Pending |
| OBS-04 | Phase 15 | Pending |
| OBS-05 | Phase 15 | Pending |
| OBS-06 | Phase 15 | Pending |
| E2E-01 | Phase 16 | Pending |
| E2E-02 | Phase 16 | Pending |
| E2E-03 | Phase 16 | Pending |
| E2E-04 | Phase 16 | Pending |
| E2E-05 | Phase 16 | Pending |
| E2E-06 | Phase 16 | Pending |
| E2E-07 | Phase 16 | Pending |
| E2E-08 | Phase 16 | Pending |
| E2E-09 | Phase 16 | Pending |
| E2E-10 | Phase 16 | Pending |

**Coverage:**
- v2.0 requirements: 59 total (6 N8N + 7 LRAG + 14 MEDIA + 7 STRAT + 4 ANLYT + 5 DASH + 6 OBS + 10 E2E)
- Mapped to phases: 59
- Unmapped: 0

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after roadmap creation — all 59 requirements mapped to Phases 9-16*
