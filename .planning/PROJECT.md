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

<!-- Next milestone: features, growth, and polish -->

(To be defined in next milestone via `/gsd:new-milestone`)

### Out of Scope

- M4: Interactive Onboarding redesign — deferred to next milestone
- M5: Content DNA Fingerprinting — deferred to next milestone
- M6: Trend Prediction Engine — deferred to next milestone
- M7: Full Media Pipeline expansion — deferred to next milestone
- M8: Multi-Language Engine — deferred to next milestone
- M9: Intelligence & Analytics v2 — deferred to next milestone
- M10: Platform-Native UX Shells — deferred to next milestone
- M11: Extraordinary Features — deferred to next milestone
- New feature development — no new features until existing ones work
- UI/UX redesign — stabilize current UI, don't redesign

## Context

- **v1.0 Stabilization shipped** — 8 phases, 22 plans, 57 requirements, all verified
- **319+ tests** across auth, pipeline, publishing, billing, media, analytics, platform features, frontend quality
- **Key fixes in v1.0**: JWT secret mismatch, atomic credit deduction, real HTTP dispatch to social platforms, MEDIA-05 integration gap, frontend env var syntax
- **54 files changed**, 10,110 insertions, 508 deletions across backend and frontend
- **Deployed** to Render (backend) and Vercel (frontend) — ready for soft launch
- **Tech stack stable**: FastAPI + Motor + Celery + Redis + React + TailwindCSS + shadcn/ui

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
*Last updated: 2026-04-01 after v1.0 milestone — ThookAI Stabilization shipped. 8 phases, 22 plans, 57 requirements, 319+ tests. Ready for next milestone.*
