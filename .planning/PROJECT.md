# ThookAI — Production Ready

## What This Is

ThookAI is an AI-powered content creation platform for creators, founders, and agencies. Users build a "Persona Engine" (voice fingerprint) through an onboarding interview, then generate platform-specific content (LinkedIn, X, Instagram) via a 5-agent AI pipeline. The platform handles scheduling, repurposing, analytics, billing, media generation, and multi-user workspaces. Deployed to Render (backend) and Vercel (frontend). v1.0 stabilization complete — all features verified end-to-end with 319+ tests.

## Core Value

Personalized content creation at scale — every user gets a unique voice fingerprint that drives all content generation, with real social platform publishing and analytics feedback loops.

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

### Active

<!-- v2.0: Intelligent Content Operating System -->

- [ ] n8n infrastructure replacing Celery for task orchestration and automation
- [ ] Real publishing to LinkedIn/X/Instagram via platform APIs through n8n
- [ ] LightRAG knowledge graph with entity/relationship extraction from approved content
- [ ] Multi-hop retrieval for Thinker agent via LightRAG
- [ ] Multi-model media orchestration engine (Designer plans → Orchestrator decomposes → best model per task → Remotion assembles)
- [ ] Static image with typography generation pipeline
- [ ] Image carousel generation pipeline
- [ ] Talking-head with overlays generation pipeline
- [ ] Short-form video (15-60s) generation pipeline
- [ ] Strategist Agent for proactive content recommendations
- [ ] Strategy Dashboard with recommendation cards and one-click approve
- [ ] SSE notifications via n8n (job completion, trending topics, scheduled post published)
- [ ] Analytics feedback loop (real social metrics 24h + 7d after publish)
- [ ] Performance intelligence from real data (optimal_posting_times)
- [ ] Obsidian vault integration via obsidian-cli into Scout agent
- [ ] E2E audit, security hardening, and production ship

### Out of Scope

- M4: Interactive Onboarding redesign — deferred to future milestone
- M5: Content DNA Fingerprinting — subsumed by Strategist Agent + LightRAG
- M8: Multi-Language Engine (Sarvam AI, regional languages) — deferred to v3.0
- M10: Platform-Native UX Shells (mobile apps) — deferred to v3.0
- M11: Extraordinary Features — deferred to future milestone
- Full UI/UX redesign — incremental improvements only (Strategy Dashboard is new, rest evolves)
- Real-time collaboration — not needed for solo creators / small agencies yet

## Current Milestone: v2.0 Intelligent Content Operating System

**Goal:** Transform ThookAI from a reactive content generation tool into a proactive content operating system with multi-model orchestrated media generation.

**Target features:**
- n8n infrastructure replacing Celery for task orchestration + real publishing
- LightRAG knowledge graph for entity/relationship extraction and multi-hop retrieval
- Multi-model media orchestration engine (Designer plans → best model per task → Remotion assembles)
- Strategist Agent for proactive content recommendations (Obsidian + LightRAG + n8n + persona)
- Strategy Dashboard with recommendation cards, SSE notifications, one-click approve
- Analytics feedback loop (real social metrics → Strategist + persona intelligence)
- Obsidian vault integration into Scout agent for research-grounded content
- E2E audit + security hardening + production ship

**Key architectural principle:** Intelligence is in planning and assembly, not single-model generation. Anti-generic, anti-AI-slop content by design.

## Context

- **v1.0 Stabilization shipped** — 8 phases, 22 plans, 57 requirements, all verified, 319+ tests
- **Stable foundation**: Auth, onboarding, content pipeline, publishing, billing, media, analytics, workspaces all working E2E
- **Tech stack evolving**: FastAPI + Motor + n8n (replacing Celery) + Redis + React + TailwindCSS + shadcn/ui
- **New integrations for v2.0**: n8n (self-hosted), LightRAG, Obsidian CLI, Remotion (compositor), multi-model routing
- **Deployed** to Render (backend) and Vercel (frontend)
- **Existing media providers**: fal.ai, Luma, Runway, HeyGen, ElevenLabs, DALL-E — all to be orchestrated

## Constraints

- **Branch strategy**: All work branches from `dev`, PRs target `dev`. Never commit to `main` directly.
- **Branch naming**: `fix/short-description`, `feat/short-description`, `infra/short-description`
- **Config pattern**: All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly.
- **Database pattern**: Always `from database import db` with Motor async. Never synchronous PyMongo.
- **LLM model**: `claude-sonnet-4-20250514` (Anthropic primary)
- **Billing changes**: Flag for human review — no auto-merge on billing code
- **Agent pipeline**: After any change to `backend/agents/`, verify full pipeline flow

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Stabilize before building new features | Previous rapid development created unreliable foundation | ✓ Good — all 57 requirements verified |
| Include custom plan builder (PR #30) in stabilization | Pricing pivot is final direction, not experimental | ✓ Good — atomic credits + custom tiers working |
| Start from dev branch | Has all 28 merged PRs — better to audit and fix than reapply from main | ✓ Good — avoided rebase complexity |
| GSD workflow for granular task decomposition | Previous approach shipped fast but without per-fix verification | ✓ Good — 22 plans with verification loops caught real bugs |
| TDD-first approach for phases 3-8 | Write failing tests → fix code → verify | ✓ Good — 319+ tests, 0 failures, caught JWT bug and race condition |
| Parallel agent execution per wave | Independent plans run simultaneously | ✓ Good — significant time savings, merge conflicts minimal |
| Replace Celery with n8n | Celery was fragile, n8n provides visual workflow orchestration + webhook triggers | — Pending |
| Multi-model orchestration over single-model generation | Professional production approach — intelligence in planning/assembly | — Pending |
| LightRAG complements Pinecone | Vector store for similarity, knowledge graph for relationships | — Pending |
| Strategist Agent as breakthrough differentiator | No competitor has proactive content intelligence from user's own vault | — Pending |

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
*Last updated: 2026-04-01 after v2.0 milestone initialization — Intelligent Content Operating System. 8 target phases: n8n, LightRAG, media orchestration, Strategist, dashboard, analytics loop, Obsidian, E2E audit.*
