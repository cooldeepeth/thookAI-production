# ThookAI — Production Ready

## What This Is

ThookAI is an AI-powered content operating system for creators, founders, and agencies. Users build a "Persona Engine" (voice fingerprint) through an interactive onboarding experience, then generate platform-specific multi-format content (LinkedIn, X, Instagram) via a 5-agent AI pipeline with proactive strategy recommendations. The platform handles scheduling, repurposing, analytics, billing, multi-model media orchestration (8 formats via Remotion), knowledge graph intelligence (LightRAG), and multi-user workspaces. Deployed to Railway (backend) and Vercel (frontend) at thook.ai. v2.2 shipped — httpOnly auth, centralized apiFetch, CI strictness, 16 production fixes.

## Core Value

Proactive, personalized content creation at scale — the platform recommends what to create, generates multi-format media, and learns from real social performance data to improve every cycle.

## Requirements

### Validated

<!-- These capabilities exist in the codebase (code written, PRs merged to dev). "Validated" here means code exists — NOT that it works correctly. This milestone's job is to verify and fix each one. -->

- ✓ User auth (email/password register + login) — existing (PR #1+)
- ✓ Google OAuth login — existing (PR #3)
- ✓ Password reset with email via Resend — existing (PR #5)
- ✓ 7-question onboarding interview + persona generation — existing (PR #20 model fix)
- ✓ Content generation pipeline (Commander → Scout → Thinker → Writer → QC) — existing
- ✓ LangGraph orchestrator with debate protocol + quality loops — existing (PR #25 M2)
- ✓ UOM behavioral inference steering agents — existing (PR #25 M3)
- ✓ Content scheduling + real publishing to LinkedIn/X/Instagram — existing (PR #2, #26)
- ✓ Celery task queue + beat scheduler — existing (PR #2, #20)
- ✓ Custom plan builder pricing (replaces 4-tier) — existing (PR #30)
- ✓ Starter credits (200 free) with hard caps — existing (PR #30)
- ✓ Stripe checkout + webhook handling + subscription management — existing (PR #8)
- ✓ Content repurposing across platforms — existing
- ✓ Series planning (multi-post) — existing
- ✓ Campaign/project grouping — existing (PR #18)
- ✓ Template marketplace with 30 seed templates — existing (PR #12, #13)
- ✓ Persona sharing (share links + public view) — existing (PR #11)
- ✓ Viral persona card at /discover — existing (PR #29)
- ✓ Content export (copy/CSV/bulk download with date range) — existing (PR #16)
- ✓ Post history import for persona training — existing (PR #15)
- ✓ Real social analytics ingestion (LinkedIn/X/Instagram APIs) — existing (PR #9)
- ✓ Performance intelligence (optimal posting times) — existing (PR #10)
- ✓ Pinecone vector store wired into learning + writer — existing (PR #7)
- ✓ Fatigue shield unified with anti-repetition — existing (PR #6)
- ✓ Voice clone flow (ElevenLabs) — existing (PR #21)
- ✓ Video pipeline + avatar creation (HeyGen) — existing (PR #22)
- ✓ AI image generation (fal.ai/DALL-E) — existing
- ✓ SSE notification system — existing (PR #19)
- ✓ Outbound webhooks (Zapier) — existing (PR #17)
- ✓ Agency workspaces + members + invitations — existing
- ✓ Admin dashboard — existing (PR #23)
- ✓ Cloudflare R2 media storage (no /tmp fallback) — existing (PR #4)
- ✓ Security middleware (rate limiting, CSP, input validation) — existing
- ✓ Error boundary + empty states + 401 handling — existing (PR #26)
- ✓ Mobile responsive sidebar — existing (PR #26)
- ✓ CI/CD (GitHub Actions, 59 tests, Docker/docker-compose) — existing
- ✓ Production deployment guide — existing (PR #28)
- ✓ n8n infrastructure replacing Celery beat for task orchestration — v2.0 Phase 9
- ✓ Real publishing to social platforms via n8n workflows — v2.0 Phase 9
- ✓ LightRAG knowledge graph with per-user isolation — v2.0 Phase 10
- ✓ Multi-model media orchestration (8 formats, Remotion assembly) — v2.0 Phase 11
- ✓ Strategist Agent (nightly proactive recommendations, cadence controls) — v2.0 Phase 12
- ✓ Analytics feedback loop (real social metrics 24h+7d) — v2.0 Phase 13
- ✓ Strategy Dashboard with SSE feed + one-click approve — v2.0 Phase 14
- ✓ Obsidian vault integration (Scout enrichment + Strategist signal) — v2.0 Phase 15
- ✓ E2E audit + security hardening + production ship — v2.0 Phase 16

- ✓ Billing & payments test suite (324 tests) + 3 P0 TDD fixes — v2.1 Phase 17
- ✓ Security & auth test suite (126 tests) — JWT, OAuth, OWASP Top 10, RBAC — v2.1 Phase 18
- ✓ Core features test suite (240 tests) + LightRAG lambda TDD fix — v2.1 Phase 19
- ✓ Frontend E2E + integration tests (74+ tests) — Playwright, Locust, Docker smoke — v2.1 Phase 20
- ✓ 95%+ billing coverage, 85%+ core coverage achieved — v2.1 Phase 17-19
- ✓ 4 P0 bugs fixed via TDD (JWT fallback, atomic credits, webhook dedup, LightRAG lambda) — v2.1

- ✓ CI strictness — removed all continue-on-error from ci.yml and e2e.yml — v2.2 Phase 21
- ✓ httpOnly cookie auth migration (replaced localStorage JWT) + CSRF protection — v2.2 Phase 21
- ✓ Centralized apiFetch replacing raw fetch() calls with timeout, retry, error handling — v2.2 Phase 22
- ✓ Content download (text/images/zip) + redirect-to-platform compose URLs — v2.2 Phase 24
- ✓ Playwright E2E verification (critical path, billing, agency, download/redirect) — v2.2 Phase 25
- ✓ 16 production fixes shipped (compression auth fix, bcrypt, CORS, OAuth, Celery Beat, security) — v2.2 deployment

### Active

<!-- v3.0: Distribution-Ready Platform Rebuild -->

- [ ] Backend endpoint hardening — every route tested, validated, error-handled against production
- [ ] Interactive onboarding reimagination — voice samples, writing analysis, visual identity
- [ ] Multi-format content generation — LinkedIn (post/article/carousel), X (tweet/thread), Instagram (feed/reel/story)
- [ ] Media generation pipeline — auto-images, carousels, video, voice narration via Remotion
- [ ] Real social publishing end-to-end — LinkedIn UGC, X v2, Instagram Meta Graph with media
- [ ] Smart scheduling — AI-optimized posting times, calendar view
- [ ] Frontend core flows polish — auth, dashboard, content studio, settings
- [ ] Design system & landing page — consistent design, conversion-optimized landing
- [ ] Security & GDPR — penetration-ready, data export/deletion, cookie consent, privacy/terms
- [ ] Performance, monitoring & launch checklist — API profiling, bundle optimization, E2E smoke test

### Out of Scope

- M5: Content DNA Fingerprinting — subsumed by Strategist Agent + LightRAG
- M8: Multi-Language Engine (Sarvam AI, regional languages) — deferred to v4.0
- M10: Platform-Native UX Shells (mobile apps) — deferred to v4.0
- M11: Extraordinary Features — deferred to future milestone
- Real-time collaboration — not needed for solo creators / small agencies yet
- A-roll / B-roll video editing — no codebase support, deferred to v4.0
- Meme generation — no codebase support, deferred to v4.0
- Platform-specific workspaces — agency workspaces exist but platform-specific deferred

## Current Milestone: v3.0 Distribution-Ready Platform Rebuild

**Goal:** Transform ThookAI from "code exists" to "every feature works perfectly end-to-end" — a new user can register, onboard interactively, generate multi-format content, schedule, and publish to real social accounts with zero errors. Ready for real users at scale.

**Target features:**

- Backend endpoint hardening (every route tested against production)
- Interactive onboarding reimagination (voice, writing samples, visual identity)
- Multi-format content generation (text, image, carousel, video, voice per platform)
- Media generation pipeline (auto-images, Remotion compositions, voice narration)
- Real social publishing (LinkedIn, X, Instagram with media)
- Smart scheduling (AI-optimized times, calendar view)
- Frontend core flows polish (auth, dashboard, content studio, settings)
- Design system & conversion-optimized landing page
- Security & GDPR compliance
- Performance optimization & launch readiness

## Context

- **v1.0-v2.2 shipped** — 25 phases, 81+ plans, 1000+ tests, platform deployed and live
- **Platform live** at thook.ai (Vercel) + Railway backend with MongoDB Atlas, Redis, R2, Stripe sandbox
- **16 production fixes shipped** April 10 — auth, CORS, compression, bcrypt, OAuth, Celery Beat, security
- **Tech stack**: FastAPI + Motor + Celery Beat + Redis + React + TailwindCSS + shadcn/ui + Remotion
- **Working E2E**: register, login, onboarding, content generation, billing, templates, R2 uploads
- **Needs verification/fixing**: frontend auth flow, persona generation, content quality, media generation, social publishing, many frontend pages
- **Existing media providers**: fal.ai, Luma, Runway, HeyGen, ElevenLabs, DALL-E — all to be tested and wired
- **Existing Remotion compositions**: ImageCarousel, Infographic, ShortFormVideo, StaticImageCard, TalkingHeadOverlay

## Constraints

- **Branch strategy**: All work branches from `dev`, PRs target `dev`. Never commit to `main` directly.
- **Branch naming**: `fix/short-description`, `feat/short-description`, `infra/short-description`
- **Config pattern**: All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly.
- **Database pattern**: Always `from database import db` with Motor async. Never synchronous PyMongo.
- **LLM model**: `claude-sonnet-4-20250514` (Anthropic primary)
- **Billing changes**: Flag for human review — no auto-merge on billing code
- **Agent pipeline**: After any change to `backend/agents/`, verify full pipeline flow

## Key Decisions

| Decision                                               | Rationale                                                                         | Outcome                                                                  |
| ------------------------------------------------------ | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Stabilize before building new features                 | Previous rapid development created unreliable foundation                          | ✓ Good — all 57 requirements verified                                    |
| Include custom plan builder (PR #30) in stabilization  | Pricing pivot is final direction, not experimental                                | ✓ Good — atomic credits + custom tiers working                           |
| Start from dev branch                                  | Has all 28 merged PRs — better to audit and fix than reapply from main            | ✓ Good — avoided rebase complexity                                       |
| GSD workflow for granular task decomposition           | Previous approach shipped fast but without per-fix verification                   | ✓ Good — 22 plans with verification loops caught real bugs               |
| TDD-first approach for phases 3-8                      | Write failing tests → fix code → verify                                           | ✓ Good — 319+ tests, 0 failures, caught JWT bug and race condition       |
| Parallel agent execution per wave                      | Independent plans run simultaneously                                              | ✓ Good — significant time savings, merge conflicts minimal               |
| Replace Celery with n8n                                | Celery was fragile, n8n provides visual workflow orchestration + webhook triggers | ⚠️ Revisit — Celery Beat restored in production (10 tasks), n8n deferred |
| Multi-model orchestration over single-model generation | Professional production approach — intelligence in planning/assembly              | — Pending                                                                |
| LightRAG complements Pinecone                          | Vector store for similarity, knowledge graph for relationships                    | — Pending                                                                |
| Strategist Agent as breakthrough differentiator        | No competitor has proactive content intelligence from user's own vault            | — Pending                                                                |
| Celery Beat restored over n8n                          | n8n deployment complexity; Celery Beat simpler for 10 scheduled tasks             | ✓ Good — running in production with 10 tasks                             |
| Deploy to Railway (not Render)                         | Railway handles Python + worker processes better, $PORT auto-binding              | ✓ Good — backend stable on Railway                                       |
| httpOnly cookies over localStorage JWT                 | Security best practice, prevents XSS token theft                                  | ✓ Good — cookie auth + CSRF working in production                        |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):

1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):

1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

_Last updated: 2026-04-12 after v3.0 milestone start — Distribution-Ready Platform Rebuild. 10 phases (26-35), transforming existing code into production-quality MVP._
