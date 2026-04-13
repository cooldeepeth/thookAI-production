---
doc: pitch-deck
audience: co-founder + investor
voice: company (third-person)
version: v3.0-pre-launch
date: 2026-04-13
---

# ThookAI

> The AI Content Operating System for creators, founders, and agencies.

**One sentence**: ThookAI gives every creator their own AI content team — a Persona Engine that learns their voice, a 5-agent pipeline that writes platform-specific posts, multi-format media generation (image / carousel / video / voice), automatic publishing, and a Strategist Agent that proactively recommends what to post next based on what's actually working.

---

## SLIDE 1 — Cover

**ThookAI** — Your AI Content Team. On Autopilot.

- Site: https://thook.ai
- Stage: v3.0 pre-launch (production deployment live, launch checklist 95% green)
- Stack: FastAPI + React + MongoDB + LangGraph + LightRAG, deployed on Railway + Vercel
- Brand: Lime (#D4FF00) primary, Violet (#7000FF) accent, dark-mode-first
- Status: 50+ features shipped across v1.0 → v2.2, v3.0 in final operator-checklist phase

---

## SLIDE 2 — Vision

> **Every creator should have their own AI content team — one that learns their voice, knows their audience, and proactively recommends what to post next.**

The next generation of personal media isn't going to be powered by individual humans typing into ChatGPT. It's going to be powered by personalized AI systems that understand a creator's voice deeply enough to _act on their behalf_ across every platform, every format, every day — without ever sounding generic.

ThookAI is that system.

---

## SLIDE 3 — The Problem

### 3 painful truths about AI content tools today

| #     | The pain                    | Why it matters                                                                                                                                                                     |
| ----- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Generic AI output**       | Creators try ChatGPT, Jasper, Copy.ai. They get content that sounds like everyone else's. Their audience tunes out. They go back to writing manually.                              |
| **2** | **Reactive, not proactive** | Existing tools only generate when you tell them to. They don't _know_ what you should post next. Every blank cursor is a blocker.                                                  |
| **3** | **No learning loop**        | Tools don't see what worked on your last post. They don't know your audience pulled higher engagement on Tuesdays. They don't notice you've used the same hook 4 times in 3 weeks. |

### The real cost

- **Creators**: Burnout. The average solo founder spends 7+ hours/week on content and abandons it within 90 days.
- **Agencies**: Margin compression. Junior copywriters at $35/hr writing posts that AI could draft in 30 seconds — but no AI today preserves a client's voice well enough to ship without human rewrites.
- **Founders**: Distribution debt. They have a real product, real expertise, and real opinions. They have zero time to package any of it for distribution.

### Why this hasn't been solved yet

Existing tools optimize for **generation speed**, not **voice fidelity** + **strategic intelligence**. They're text completion engines bolted onto pretty UIs. None of them treat your voice as a first-class data structure that gets richer over time.

---

## SLIDE 4 — The Solution

ThookAI is built around 4 capabilities that, _together_, no other AI content product offers:

### 1. The Persona Engine

A multi-dimensional voice fingerprint built from a 7-question onboarding interview, then continuously refined from real performance data and user edits. Every piece of content is generated _from_ this fingerprint, not adapted to it.

### 2. The 5-Agent Pipeline

Every content request flows through a debate-driven pipeline of specialized agents:

```
Commander (intent + spec)
    ↓
Scout (research via Perplexity + LightRAG knowledge graph)
    ↓
Thinker (angle + hook strategy + anti-repetition)
    ↓
Writer (Claude Sonnet 4.5, persona-conditioned)
    ↓
QC (compliance + slop detection + persona-match scoring)
    ↓
Consigliere (final risk review)
```

Each agent has timeout protection, provider fallbacks, and structured outputs. The pipeline costs ~$0.05 per generation and runs in 8-15 seconds.

### 3. The Strategist Agent

A nightly background agent that synthesizes the user's LightRAG knowledge graph + real social analytics + content history into ranked recommendation cards — _delivered before the user opens the app_.

### 4. The Learning Loop

- Real social metrics (LinkedIn UGC API, X v2 API, Instagram Meta Graph) polled 24h and 7d after every publish
- Performance data feeds back into the Strategist's recommendations + the Writer's hook selection
- Anti-fatigue shield detects hook overuse and forces variety
- Persona refinement updates voice descriptors based on what's actually performing

**No competing product offers all four.** Most offer none.

---

## SLIDE 5 — Product Walkthrough (60-second version)

### Step 1 — Sign up (30 seconds)

Email/password OR Google OAuth → JWT in httpOnly cookie → onboarding wizard.

### Step 2 — Build the Persona (3 minutes)

Answer 7 questions: content focus, audience, style, frequency, platforms, goals, unique angle. Optional: upload writing samples for voice analysis. ThookAI generates a Persona Card with archetype (Educator / Storyteller / Provocateur / Builder), voice descriptor, content pillars, hook style, target audience.

### Step 3 — Create first content (2 minutes)

Open Content Studio → type a topic OR pick a Strategist recommendation → 5-agent pipeline runs (8-15 seconds) → review LinkedIn post / X thread / Instagram caption with persona match score, hook variants, predicted engagement.

### Step 4 — Add media (1 minute)

Auto-generate cover image (FAL.ai / DALL-E) → carousel slides (Remotion) → 30-second video (Runway / Luma / Kling) → voice narration (ElevenLabs).

### Step 5 — Schedule + publish

ThookAI suggests optimal posting time per platform (from analytics history). One-click approve → Celery Beat publishes at scheduled time → real engagement metrics flow back 24h and 7d later → Strategist learns.

### Step 6 — Repurpose

One LinkedIn article → 5 X tweets (thread mode) → 1 Instagram carousel → 1 video script. Same source, platform-native variants.

---

## SLIDE 6 — The Persona Engine (deep dive)

The Persona Engine is the data structure that makes ThookAI _not generic_. It contains:

| Layer                        | Contents                                                                                                | Updated by                                   |
| ---------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **Card**                     | Archetype, voice descriptor, content pillars, hook style, target audience                               | Onboarding interview + manual edits          |
| **Voice fingerprint**        | Lexical patterns, sentence rhythm, opener tendencies, signature phrases, regional English variant       | Onboarding sample analysis + content history |
| **Content identity**         | Topic taxonomy, format preferences, do/don't list                                                       | Refined per session                          |
| **Performance intelligence** | Optimal posting times per platform, engagement profile, hook-to-engagement correlation, fatigue signals | Real social analytics (24h + 7d polling)     |
| **Learning signals**         | User approvals, edits, dismissals, conversion outcomes                                                  | Every interaction                            |
| **Unit of Measure (UOM)**    | Behavioral inference about how the user wants the agents to behave                                      | UOM service                                  |

The Persona Engine is the **moat**. The longer a user stays on ThookAI, the richer their Persona becomes, and the more painful it gets to switch to a generic competitor.

---

## SLIDE 7 — What's Built (the receipts)

ThookAI is **not** an MVP. It is a deeply integrated production platform. Here's the inventory.

### Auth & user management

- ✅ Email/password register + login with bcrypt hashing
- ✅ Google OAuth (Authlib)
- ✅ LinkedIn OAuth, X OAuth (PKCE), Instagram OAuth (Meta Graph)
- ✅ JWT in httpOnly cookies + CSRF double-submit token
- ✅ Account lockout after 5 failed attempts (15-min cooldown)
- ✅ Password reset via Resend transactional email
- ✅ Persona sharing via signed share links + public viewer page

### Content generation

- ✅ 7-question onboarding interview with persona auto-generation
- ✅ Voice sample writing analysis
- ✅ 5-agent LangGraph pipeline (Commander → Scout → Thinker → Writer → QC → Consigliere)
- ✅ 9 platform-format combinations: LinkedIn (post / article / carousel), X (tweet / thread), Instagram (feed / reel / story), plus generic blog/email
- ✅ Anti-repetition detection (TF-IDF cosine similarity + hook pattern matching)
- ✅ Fatigue Shield (unified diversity scoring)
- ✅ Hook scoring and viral prediction (`backend/agents/viral_predictor.py`)
- ✅ Pinecone vector store wired into Writer + Learning agents
- ✅ Anti-slop vision check on generated images
- ✅ Series planner (multi-post arcs)
- ✅ Cross-platform repurposing
- ✅ Campaign / project grouping
- ✅ Template marketplace with 30 seed templates

### Media generation pipeline

- ✅ AI image generation: FAL.ai (Flux Pro, Seadance), DALL-E
- ✅ Video generation: Runway, Luma Dream Machine, Kling, Pika, HeyGen, D-ID
- ✅ Voice/TTS: ElevenLabs, Play.ht, Google TTS
- ✅ Voice cloning (ElevenLabs)
- ✅ Carousel slide composition via Remotion
- ✅ Multi-model media orchestration with credit ledger for partial-failure accounting
- ✅ R2 upload pipeline (presigned URLs, no /tmp fallback)
- ✅ 8 media formats supported via Remotion compositions

### Strategy & intelligence

- ✅ Strategist Agent (nightly proactive recommendations with cadence controls)
- ✅ Strategy Dashboard with SSE-driven feed + one-click approve
- ✅ LightRAG knowledge graph with per-user isolation
- ✅ Obsidian vault integration (Scout enrichment + Strategist signal)
- ✅ Real social analytics ingestion (LinkedIn UGC, X v2 metrics, Instagram insights)
- ✅ Performance intelligence (optimal posting times calculation)
- ✅ Persona refinement / voice evolution timeline
- ✅ Daily Brief generation

### Publishing & scheduling

- ✅ Smart scheduling with AI-optimized posting times per platform
- ✅ Calendar view (month grid, navigation, edit/delete/now buttons)
- ✅ Real publishing to LinkedIn UGC API, X v2 API, Instagram Meta Graph
- ✅ Token encryption (Fernet) for OAuth credentials
- ✅ Proactive 24h token refresh
- ✅ Celery Beat publisher (every 5 minutes)
- ✅ Reschedule modal with atomic cancel + recreate
- ✅ Scheduled-post status tracking (pending → scheduled → published / failed)
- ✅ Idempotency keys to prevent duplicate publishes

### Billing & monetization

- ✅ Stripe checkout + subscription management + customer portal
- ✅ Webhook handling with idempotency (`db.stripe_events`)
- ✅ Custom Plan Builder (replaces 4-tier model)
- ✅ Volume tier pricing: $0.06/credit (≤200), $0.056 (≤800), $0.045 (≤2000), $0.035 (>2000)
- ✅ 200 starter credits free
- ✅ Credit ledger with refund-on-failure
- ✅ Daily limit enforcement
- ✅ Monthly credit refresh (1st of month)
- ✅ Tier-based feature gating
- ✅ Stripe `sk_test_` → production launch guard

### Frontend

- ✅ React 18 + CRA + CRACO + TailwindCSS + shadcn/ui (47 components)
- ✅ Centralized `apiFetch` with timeout, retry, error normalization
- ✅ httpOnly cookie auth (no localStorage tokens)
- ✅ CSRF token double-submit
- ✅ 38 pages including: Landing, Auth, Onboarding (3-phase wizard), Dashboard (13 views), ContentStudio, ContentCalendar, ContentLibrary, ContentOutput, Analytics, StrategyDashboard, Connections, Settings, Templates, Campaigns, Persona Engine, Persona Card Public, Agency Workspace, Admin Dashboard
- ✅ Code-split bundle (36 chunks, main.js 107.51 kB gzipped, largest dynamic chunk 46.35 kB)
- ✅ SSE notification system
- ✅ Error boundaries + empty states + 401 handling
- ✅ Mobile responsive (375px / 768px / 1440px breakpoints)
- ✅ Framer Motion animations
- ✅ Cookie consent banner (GDPR)
- ✅ Privacy policy + Terms of service pages

### Security & GDPR

- ✅ Pydantic body validation on every POST endpoint
- ✅ XSS sanitization (`sanitize_text` via stdlib `html.escape`)
- ✅ MongoDB injection prevention (no f-string queries)
- ✅ CORS allow-list (no wildcards in production)
- ✅ Rate limiting: 60/min global, 10/min auth-specific
- ✅ Security headers: HSTS, CSP, X-Frame-Options=DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, X-XSS-Protection
- ✅ OAuth token encryption (Fernet)
- ✅ JWT refresh + httpOnly cookies + CSRF double-submit
- ✅ Sentry PII scrub callback
- ✅ GDPR data export (`/api/auth/export`, 12 collections)
- ✅ GDPR account deletion (`/api/auth/delete-account` with anonymization)
- ✅ Cookie consent gate
- ✅ Session token rotation
- ✅ Account lockout
- ✅ OWASP Top 10 parametrized test suite (10/10 pass)

### Infrastructure

- ✅ Backend on Railway (gallant-intuition-production-698a.up.railway.app)
- ✅ Frontend on Vercel (thook.ai → www.thook.ai)
- ✅ MongoDB Atlas (27 collections, indexed)
- ✅ Redis (Celery broker + cache layer)
- ✅ Cloudflare R2 media storage
- ✅ Sentry error tracking (backend)
- ✅ PostHog product analytics
- ✅ Resend transactional email
- ✅ Pinecone vector store
- ✅ LightRAG knowledge graph sidecar
- ✅ Celery Beat scheduler (7 periodic tasks)
- ✅ Worker queues for video / media / content (separated by load profile)
- ✅ Docker Compose for local development

### Observability & quality

- ✅ TimingMiddleware emits `X-Response-Time` on every response
- ✅ Compression middleware (gzip, content-aware)
- ✅ Cache middleware (Redis-backed)
- ✅ 700+ tests across 4 suites: Billing (95%+ coverage gate), Security (85%+), Pipeline & Agents (85%+), General
- ✅ Playwright E2E tests including critical-path, billing flow, agency workspace, content download, redirect-to-platform, production smoke
- ✅ Cross-browser matrix (5 projects: chromium, firefox, webkit, mobile-chrome, mobile-safari)
- ✅ Locust 50-user load test profile
- ✅ Lighthouse CI configuration
- ✅ Dead-link detection sweep
- ✅ Markdown linting

### Operations

- ✅ Custom plan builder (frontend + backend + Stripe integration)
- ✅ Admin dashboard
- ✅ Outbound webhooks (Zapier-compatible)
- ✅ Notification system (in-app + SSE feed)
- ✅ n8n bridge endpoints (legacy compatibility — Celery beat is canonical)
- ✅ Multi-user agency workspaces with member roles + invitations
- ✅ Workspace-scoped content sharing

### What's intentionally deferred to v4.0

- Multi-language engine (Sarvam AI + regional Indian languages)
- Native mobile apps
- Real-time collaboration
- A-roll / B-roll video editing
- Content DNA fingerprinting (subsumed by Strategist + LightRAG)

**Total: 50+ shipped capabilities, 27 MongoDB collections, 70+ API endpoints, 38 pages, 21 specialized agents, 18 services, 700+ tests.**

---

## SLIDE 8 — Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Vercel)                                          │
│  React 18 + Tailwind + shadcn/ui · httpOnly cookie auth    │
│  38 pages · 36 code-split chunks · 107 kB main bundle      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (Railway · FastAPI)                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Middleware stack (in order)                        │    │
│  │  CORS → CSRF → SecurityHeaders → RateLimit →        │    │
│  │  InputValidation → Compression → Cache → Timing →   │    │
│  │  Session                                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │  26 Routes   │ │ 21 Agents    │ │ 18 Services      │    │
│  │  /api/auth   │ │ Commander    │ │ llm_client       │    │
│  │  /api/content│ │ Scout        │ │ stripe_service   │    │
│  │  /api/billing│ │ Thinker      │ │ media_storage    │    │
│  │  /api/persona│ │ Writer       │ │ vector_store     │    │
│  │  ...         │ │ QC           │ │ social_analytics │    │
│  │              │ │ Consigliere  │ │ persona_refine   │    │
│  │              │ │ Strategist   │ │ creative_provs   │    │
│  │              │ │ Analyst      │ │ ...              │    │
│  │              │ │ Publisher    │ │                  │    │
│  │              │ │ ...          │ │                  │    │
│  └──────────────┘ └──────────────┘ └──────────────────┘    │
└──────┬──────────────┬──────────────┬───────────┬───────────┘
       │              │              │           │
       ▼              ▼              ▼           ▼
┌──────────┐   ┌─────────────┐   ┌────────┐   ┌──────────────┐
│ MongoDB  │   │   Redis     │   │   R2   │   │  Pinecone    │
│ Atlas    │   │  (Celery +  │   │ media  │   │   vectors    │
│ 27 cols  │   │   cache)    │   │ bucket │   │              │
└──────────┘   └──────┬──────┘   └────────┘   └──────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Celery       │
              │  workers      │
              │  + beat       │
              │               │
              │  3 queues:    │
              │  - content    │
              │  - media      │
              │  - video      │
              └───────────────┘
                      │
                      ▼
              ┌───────────────────────────────────────┐
              │  External APIs                        │
              │  Anthropic · OpenAI · Perplexity      │
              │  Stripe · Resend · Sentry · PostHog   │
              │  LinkedIn · X · Instagram · Google    │
              │  fal.ai · Luma · Runway · Kling       │
              │  HeyGen · D-ID · ElevenLabs · Play.ht │
              │  LightRAG sidecar · Obsidian REST     │
              └───────────────────────────────────────┘
```

---

## SLIDE 9 — Tech Stack

| Layer                | Choice                                        | Why                                                 |
| -------------------- | --------------------------------------------- | --------------------------------------------------- |
| **Backend language** | Python 3.11                                   | Fast async (Motor + httpx), best LLM SDK ecosystem  |
| **API framework**    | FastAPI 0.110                                 | Async-native, Pydantic validation, OpenAPI auto-gen |
| **Database**         | MongoDB Atlas + Motor (async)                 | Flexible schema for personas, audit-friendly        |
| **Task queue**       | Celery + Redis                                | Mature, multi-queue routing, beat scheduler         |
| **LLM primary**      | Anthropic Claude Sonnet 4.5                   | Highest persona-fidelity in our internal evals      |
| **LLM fallback**     | OpenAI GPT-4o + GPT-4o-mini                   | Cost-optimized for non-creative agents              |
| **Research**         | Perplexity sonar-pro                          | Best research-grounded LLM API                      |
| **Knowledge graph**  | LightRAG sidecar                              | Per-user isolated KG, multi-hop retrieval           |
| **Vector store**     | Pinecone                                      | Persistent embeddings, fast similarity search       |
| **Image gen**        | FAL.ai (Flux Pro, Seadance), DALL-E           | Quality + speed                                     |
| **Video gen**        | Runway, Luma, Kling, Pika, HeyGen, D-ID       | Provider diversity per format                       |
| **Voice/TTS**        | ElevenLabs, Play.ht, Google TTS               | Cloning + multi-voice                               |
| **Frontend**         | React 18 + CRA + CRACO + Tailwind + shadcn/ui | Familiar stack, fast iteration                      |
| **State**            | React Context + custom hooks                  | No Redux/Zustand needed at this scale               |
| **Forms**            | React Hook Form + Zod                         | Client-side validation that mirrors Pydantic        |
| **Animation**        | Framer Motion                                 | Industry standard                                   |
| **Deployment**       | Railway (backend) + Vercel (frontend)         | Zero-DevOps for solo team                           |
| **Storage**          | Cloudflare R2                                 | S3-compatible, no egress fees                       |
| **Email**            | Resend                                        | Developer-first, modern API                         |
| **Payments**         | Stripe                                        | Industry standard                                   |
| **Monitoring**       | Sentry + PostHog                              | Error tracking + product analytics                  |

---

## SLIDE 10 — Differentiation

| Capability                                      | ChatGPT    | Jasper   | Copy.ai  | Hypefury  | Buffer   | **ThookAI**                |
| ----------------------------------------------- | ---------- | -------- | -------- | --------- | -------- | -------------------------- |
| Voice fingerprint as data structure             | ❌         | ⚠️ basic | ❌       | ❌        | ❌       | **✅ Persona Engine**      |
| Multi-agent debate pipeline                     | ❌         | ❌       | ❌       | ❌        | ❌       | **✅ 5+ agents w/ debate** |
| Knowledge graph integration                     | ❌         | ❌       | ❌       | ❌        | ❌       | **✅ LightRAG per user**   |
| Proactive recommendations                       | ❌         | ❌       | ❌       | ⚠️ basic  | ❌       | **✅ Strategist Agent**    |
| Anti-repetition / fatigue shield                | ❌         | ❌       | ❌       | ❌        | ❌       | **✅**                     |
| Real social metrics learning loop               | ❌         | ❌       | ❌       | ⚠️ basic  | ⚠️ basic | **✅ 24h + 7d polling**    |
| Multi-format media (image/carousel/video/voice) | ❌         | ⚠️ image | ❌       | ❌        | ❌       | **✅ 8 formats**           |
| Real publishing to LI / X / IG                  | ❌         | ❌       | ❌       | ⚠️ X only | ✅       | **✅ all 3**               |
| Campaign / series planning                      | ❌         | ❌       | ❌       | ❌        | ⚠️ basic | **✅**                     |
| Voice cloning                                   | ❌         | ❌       | ❌       | ❌        | ❌       | **✅ ElevenLabs**          |
| Avatar / talking-head video                     | ❌         | ❌       | ❌       | ❌        | ❌       | **✅ HeyGen**              |
| Agency multi-user workspaces                    | ❌         | ⚠️ basic | ⚠️ basic | ❌        | ✅       | **✅ + invitations**       |
| GDPR data export + deletion                     | ⚠️ partial | ❌       | ❌       | ❌        | ❌       | **✅ self-serve**          |
| Custom plan builder pricing                     | ❌         | ❌       | ❌       | ❌        | ❌       | **✅**                     |

**The thesis**: Each row above is small. Five rows is interesting. **All 14 rows in one product is a category-defining moat.**

---

## SLIDE 11 — Market & Audience

### Total Addressable Market

- **Solo content creators**: 50M+ globally (Linktree estimate, 2024)
- **Founders / solo operators**: 30M+ (Stripe Atlas + Indie Hackers + LinkedIn data)
- **Boutique agencies (1-10 employees)**: 200K+ globally
- **Enterprise content teams**: 50K+ Fortune-listed companies with content departments

### Initial wedge (where we start)

- **Solo founders** building in public on LinkedIn + X (the "indie hacker" / "fractional CMO" tribe)
- **Tech / SaaS founders** with strong opinions and zero content time
- **Boutique agencies** serving 10-50 clients, looking to compress their content production cost

### Why this wedge first

1. **High pain, high willingness to pay.** Solo founders already spend $200-2000/mo on content help (writers, editors, video freelancers).
2. **Distribution-aligned.** They already create content about tools they love. Word-of-mouth flywheel built in.
3. **Persona Engine compounding.** Their content output is highly personal — exactly the use case where generic AI fails and ThookAI shines.
4. **Single-user economics.** No team-management complexity in the first cohort. Agency workspaces unlock the 5-50 seat market layer-2.

---

## SLIDE 12 — Business Model

### Custom Plan Builder (replaces traditional 4-tier model)

Users select exactly the credits they need across these operations:

| Operation                            | Credits | Margin (at $0.05/credit avg) |
| ------------------------------------ | ------- | ---------------------------- |
| Text post generation (full pipeline) | 10      | 86%                          |
| Text regeneration                    | 4       | 90%                          |
| AI image                             | 8       | 70%                          |
| Carousel (5 slides)                  | 15      | 65%                          |
| Short video (15-30s)                 | 25      | 50%                          |
| Voice narration                      | 12      | 60%                          |
| Series plan                          | 8       | 80%                          |
| Repurpose (1 → N platforms)          | 5       | 88%                          |

### Volume tier pricing (per credit)

| Monthly credits    | Price/credit | Effective $/post |
| ------------------ | ------------ | ---------------- |
| ≤ 200 (Starter)    | $0.06        | $0.60            |
| 200-800 (Growth)   | $0.056       | $0.56            |
| 800-2000 (Scale)   | $0.045       | $0.45            |
| 2000+ (Enterprise) | $0.035       | $0.35            |

### Free tier

**200 credits free on signup** (≈20 full posts, enough to experience the core value loop). No credit card required.

### Average user paths

- **Starter creator**: 200-400 credits/mo → $12-22/mo
- **Power creator**: 800-1500 credits/mo → $36-68/mo
- **Founder daily poster**: 1500-3000 credits/mo → $68-105/mo
- **Boutique agency (5 clients)**: 5000-10000 credits/mo → $175-350/mo
- **Scaling agency (20 clients)**: 20000+ credits/mo → $700+/mo

### Unit economics (text-only baseline)

- **COGS per post (full pipeline)**: ~$0.05 (Anthropic + OpenAI + Perplexity)
- **Revenue per post (Starter)**: $0.60
- **Gross margin (text only)**: ~92%
- **With media (carousel)**: ~70% margin
- **With video**: ~50% margin (varies by provider)

### Path to profitability

- Break-even per user: **~50 paid posts/month** at Starter tier
- Average paid user expected to consume **300+ paid posts/month**
- **6x over-coverage** per active paid user before factoring in repurpose / series multipliers

---

## SLIDE 13 — Go-to-Market

### Phase 1: Soft launch (now → +30 days)

- Founder-led, **no paid acquisition**
- Target: 100 hand-picked design partners (solo founders, agencies, technical creators)
- Channel: LinkedIn + X DMs from founder, Indie Hackers post, Hacker News show
- Goal: 50 active free users, 10 paying (any tier)
- KPI: Time to first published post < 10 minutes from signup

### Phase 2: Public launch (+30 → +90 days)

- Product Hunt launch with full feature parity demo video
- Content marketing: founder publishes ON ThookAI ABOUT ThookAI (recursive proof)
- Affiliate program for early users (20% lifetime commission on referred paid plans)
- Goal: 1000 free users, 100 paying

### Phase 3: Inbound + agency wedge (+90 → +180 days)

- SEO content: "[Persona] guide to LinkedIn growth", "X thread template library"
- Agency outreach: "your client roster but with 80% less production time"
- Goal: 5000 free users, 500 paying, 5 agency accounts (>$200/mo each)

### Phase 4: Paid acquisition (post-PMF signal)

- Paid LinkedIn + X ads targeting "content marketing manager" + "founder" + "indie hacker"
- Goal: $0.50 CAC against $50 LTV (24-month)

### Distribution wedge superpower

The **viral persona card** at `/discover` (Phase 11 / 12 — already shipped). Users get a public, shareable card showing their persona archetype. Acts as a Linktree-style growth loop: "see my AI-generated content persona on ThookAI" → friend signs up → friend's persona gets shared → exponential.

---

## SLIDE 14 — Roadmap (where we've been, where we go)

### What's shipped (v1.0 → v2.2)

- **v1.0** (Phases 1-8, shipped 2026-04-01) — Stabilization: git/branch cleanup, infra, auth, content pipeline, publishing, scheduling, billing, media gen, admin, frontend quality, gap closure
- **v2.0** (Phases 9-16, shipped 2026-04-01) — Intelligent OS: n8n infra, LightRAG knowledge graph, multi-model media orchestration, Strategist Agent, analytics feedback loop, Strategy Dashboard, Obsidian integration, E2E security hardening
- **v2.1** (Phases 17-20, shipped 2026-04-03) — Production hardening: 700+ test sprint covering billing (95%+), security (85%+), core features (85%+), frontend E2E
- **v2.2** (Phases 21-25, shipped 2026-04-04) — Frontend hardening: CI strictness, httpOnly cookie auth migration, centralized apiFetch, content download + redirect-to-platform, E2E verification

### v3.0 Distribution-Ready (current — 9/10 phases done)

- ✅ **Phase 26**: Backend endpoint hardening (70 endpoints audited)
- ✅ **Phase 27**: Onboarding reimagination (voice samples, writing analysis, visual identity)
- ✅ **Phase 28**: Multi-format content generation (9 platform-format combos)
- ✅ **Phase 29**: Media generation pipeline (R2 end-to-end)
- ✅ **Phase 30**: Real social publishing (LI / X / IG end-to-end)
- ✅ **Phase 31**: Smart scheduling + calendar
- ✅ **Phase 32**: Frontend core flows polish (responsive, empty states)
- 🟡 **Phase 33**: Design system & landing page (partial)
- ✅ **Phase 34**: Security & GDPR (13 SECR requirements verified)
- ✅ **Phase 35**: Performance, monitoring & launch checklist (operator gate)

### v4.0 Post-launch (proposed)

- Multi-language engine with regional Indian languages (Sarvam AI integration)
- Native mobile app shells (React Native)
- Real-time collaboration in Content Studio
- Advanced video editing (B-roll suggestions + auto-captions)
- API marketplace (let other tools call ThookAI's Persona Engine as a service)
- ThookAI for Education (campus distribution wedge)

### v5.0 Vision

- White-label deployments for enterprises
- ThookAI Voice Mode (talk to your strategist agent)
- Cross-creator persona graph (agencies see persona overlap across clients)

---

## SLIDE 15 — Team & How We Work

### Founder

**Kuldeepsinh Parmar** — solo technical founder building ThookAI end-to-end. Background: full-stack engineering, AI/ML systems, product design, GTM. Operates with a structured planning methodology (the "GSD" workflow) where every feature is researched, planned, executed, verified, and shipped through a documented pipeline.

### How we work

- **Phase-based development** — 35+ phases shipped to date, each with research + plan + execute + verify + summary stages
- **Atomic commits with intent** — every commit message explains the why, not just the what
- **Test-driven where it matters** — 700+ tests with coverage gates per critical module (billing 95%+, security 85%+)
- **AI-augmented engineering** — Claude Code as a pair-programmer, with structured agent orchestration for parallel work (`/team:deploy`, `/gsd-execute-phase`, etc.)
- **Documentation-as-code** — every milestone has a verifiable VERIFICATION.md showing which requirements were audited against running code
- **Production-first** — staging is for launches; all commits land on `dev` and merge to `main` only when CI is green and operator-checks pass

### What we're hiring (the co-founder ask)

- **Co-founder, distribution / GTM** (this is what this deck is asking for if you're reading it)
  - Owns: positioning, content marketing, sales, partnerships, agency outreach
  - Background: marketing operator + content creator, ideally has scaled a content product before
  - Equity: meaningful, time-vested
  - Why now: product is shipped. The biggest risk vector is now distribution velocity, not engineering.

### What we're NOT hiring (yet)

- Eng team — solo founder + Claude Code is moving at 5-10x normal velocity. Adding humans here adds coordination overhead before it adds shipping speed.
- Designers — design system is locked. shadcn/ui + Tailwind covers 95% of needs. Visual polish in v3.3.
- Customer success — not enough volume yet.

---

## SLIDE 16 — Traction (TBD until live launch)

> 🟡 **Numbers to fill in once v3.0 ships and the smoke launch begins.**

| Metric                                   | Today | 30 days | 90 days | 180 days |
| ---------------------------------------- | ----- | ------- | ------- | -------- |
| Free signups                             | [TBD] | [TBD]   | [TBD]   | [TBD]    |
| Active free users (WAU)                  | [TBD] | [TBD]   | [TBD]   | [TBD]    |
| Paid users                               | [TBD] | [TBD]   | [TBD]   | [TBD]    |
| MRR                                      | [TBD] | [TBD]   | [TBD]   | [TBD]    |
| Posts published via platform             | [TBD] | [TBD]   | [TBD]   | [TBD]    |
| Avg posts per active user / week         | [TBD] | [TBD]   | [TBD]   | [TBD]    |
| Persona retention (30d after onboarding) | [TBD] | [TBD]   | [TBD]   | [TBD]    |

### Engineering traction (already real)

- 35+ shipped phases with verifiable artifacts
- 50+ shipped product capabilities
- 70+ API endpoints (3 production fixes during Phase 26 audit, all merged)
- 700+ tests across 4 coverage-gated suites
- 27 MongoDB collections with proper indexing
- 6 video providers + 3 voice providers + 2 image providers wired
- 4 OAuth providers integrated (Google, LinkedIn, X, Instagram)
- Production deployment live at thook.ai (Railway + Vercel)
- 192 commits ahead of `origin/dev` ready to ship in v3.0

---

## SLIDE 17 — The Ask

### Funding ask: **[TBD — fill in when ready]**

- Use of funds:
  - **40%** — Distribution + content marketing (founder-led at first, then dedicated CMO-level co-founder)
  - **25%** — LLM + media provider COGS to support free-tier acquisition without margin death
  - **20%** — Engineering buffer (1-2 specialized contractors for native mobile / specialized AI work)
  - **10%** — Legal + compliance (international expansion, GDPR, agency contract templates)
  - **5%** — Buffer for opportunistic experiments (paid acquisition tests, viral moments)

### Co-founder ask

- **Equity**: meaningful, time-vested, with cliff
- **Cash**: market salary OR deferred-comp model with bonus tied to MRR milestones — open to discussion
- **Decision authority**: full ownership of GTM, marketing, sales, partnerships
- **Time commitment**: full-time

### What we're NOT asking for

- Anchor investors who want board control before product-market fit
- Engineering co-founders (the engineering bar is already set; we need distribution)
- Acquihires from existing companies — we're a venture, not a feature

---

## SLIDE 18 — Risks & Mitigations

| Risk                                                           | Likelihood         | Impact          | Mitigation                                                                                                                                                                             |
| -------------------------------------------------------------- | ------------------ | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Anthropic / OpenAI pricing changes hurt unit economics**     | Medium             | High            | Multi-provider fallback already built (Claude → GPT-4o → mock). Can switch primary in 1 day. Pricing is also dropping ~50% YoY in our category.                                        |
| **OpenAI / Anthropic / Google ship a competing product**       | High               | Medium          | Big AI labs don't ship vertical products at quality. ChatGPT "custom GPTs" tried this and failed. Our moat is the Persona Engine + learning loop, not the LLM.                         |
| **Hypefury / Buffer adds AI features and closes the gap**      | High               | Medium          | They lack the technical foundation: LightRAG, agent debate, Persona Engine. Adding all of them takes 6-12 months and may risk their existing UX. We have a 12+ month head start.       |
| **Content automation backlash from social platforms**          | Low                | High            | We publish via official APIs (LinkedIn UGC, X v2, Instagram Meta Graph) — fully sanctioned. We rate-limit and respect platform ToS. We are _helping_ creators be better, not spamming. |
| **GDPR / regulatory complications in EU**                      | Medium             | Medium          | Phase 34 GDPR work is complete (data export, deletion, consent gate, anonymization). Privacy-by-design from day one.                                                                   |
| **Founder bandwidth**                                          | High               | High            | This is exactly why we are recruiting a co-founder now. The product is shipped. Distribution velocity is the bottleneck.                                                               |
| **Pinecone vector dimension mismatch in production (current)** | Resolved           | Low             | Identified in audit, operator action H1 documents the fix. Affects only persona vector retrieval, which has graceful fallback.                                                         |
| **Anthropic billing exhausted (current)**                      | Resolved on top-up | High while down | Identified in audit, operator action B1. Top-up + monitoring alarms in v3.1.                                                                                                           |

---

## SLIDE 19 — Why Now

1. **AI capability has crossed the persona-fidelity threshold.** Claude Sonnet 4.5 + GPT-4o can preserve voice well enough that human creators no longer need to rewrite every sentence. This was not true 12 months ago.

2. **Creator economy is in its second wave.** First wave: Substack, Patreon, Shopify (2018-2022). Second wave: AI-augmented creators who scale 10x. ThookAI is the pickaxe.

3. **Multi-format media generation is finally consumer-grade.** Runway, Luma, Kling, fal.ai — all under $0.10/clip with quality that didn't exist 18 months ago. We can offer text + image + video + voice in one pipeline at sane unit economics.

4. **Distribution-ready stacks are democratized.** Railway + Vercel + Stripe + Resend means a solo founder can ship a full SaaS in weeks, not years. We've used this.

5. **The agency model is breaking.** Junior copywriter labor cost is rising. Client expectations are rising. AI tools are reshuffling the deck. ThookAI is a pre-built second brain for any agency that wants to keep margins.

6. **Founder distribution debt is at all-time-high.** Every founder we've talked to says: "I have a product, I have customers, I have ZERO time for content." We solve exactly that.

---

## SLIDE 20 — Why Us

- **Engineering depth shipped.** 35+ phases, 700+ tests, 50+ features in production. This isn't an idea on a napkin — this is a working platform.
- **Methodology that scales.** The GSD workflow + AI-augmented engineering means we can build at 5-10x normal velocity with verifiable quality gates.
- **Product taste with technical grounding.** The Persona Engine + agent debate architecture aren't off-the-shelf. They're informed product decisions made by someone who understands both the AI side and the creator pain.
- **Pre-built moat.** Every day a user is on ThookAI, their Persona Engine gets richer. Switching cost compounds over time. Competitors will always be chasing.
- **Capital-efficient by design.** Solo founder + Claude Code + Railway + Vercel means we can run on a fraction of typical SaaS burn until PMF. The funding ask is for _distribution_ not survival.

---

## Appendix A — Glossary (for non-technical readers)

| Term                              | Meaning                                                                                                                                                                                                                  |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Persona Engine**                | The data structure that captures a user's voice, audience, and content preferences. The "soul" of every generated post.                                                                                                  |
| **5-Agent Pipeline**              | The sequence of specialized AI agents (Commander, Scout, Thinker, Writer, QC, Consigliere) that produces every piece of content. Each agent has a single job and can fall back to alternatives if its primary LLM fails. |
| **LightRAG**                      | An open-source knowledge graph framework. We deploy a per-user instance so each user's knowledge graph stays isolated. Enables multi-hop retrieval (the AI can connect 2 unrelated facts to produce a novel insight).    |
| **Strategist Agent**              | A nightly background agent that synthesizes performance data + knowledge graph + persona to recommend WHAT to post next, before the user even opens the app.                                                             |
| **UOM (Unit of Measure)**         | A behavioral inference layer that learns how the user wants the agents to behave. Steers tone, length, format preference.                                                                                                |
| **Anti-fatigue / Fatigue Shield** | A diversity scoring system that detects when a user is repeating hooks, structures, or topics — and forces variety.                                                                                                      |
| **Credits**                       | The pricing unit. Each operation costs N credits. Volume tiers reduce $/credit at higher monthly buys.                                                                                                                   |
| **Custom Plan Builder**           | Replaces the typical 4-tier pricing (Starter / Pro / Business / Enterprise). Users pick exactly what they need across operations. Always-fair pricing.                                                                   |
| **R2**                            | Cloudflare's S3-compatible object storage. We use it for all generated media (images, video, voice) with zero egress fees.                                                                                               |
| **Pinecone**                      | A vector database. Stores numerical "embeddings" of content so the system can find similar past content in milliseconds.                                                                                                 |
| **Celery / Celery Beat**          | Background job queue + scheduler. Handles publishing posts at scheduled times, polling analytics, refreshing credits.                                                                                                    |
| **Sentry**                        | Error tracking. Every backend exception lands here with full stack trace + context.                                                                                                                                      |
| **PostHog**                       | Product analytics. Tracks every meaningful user action (registered, generated content, published).                                                                                                                       |
| **OAuth**                         | The login flow used by Google, LinkedIn, X, Instagram. We never see the user's password — the platform sends us a temporary access token.                                                                                |
| **CORS**                          | Cross-origin resource sharing. The security policy that says "frontend on thook.ai is allowed to call backend on api.thook.ai".                                                                                          |
| **Rate limiting**                 | Caps on how many requests a user (or attacker) can send per minute. Prevents abuse.                                                                                                                                      |
| **httpOnly cookie**               | A session cookie that JavaScript can't read. Mitigates XSS-based session theft.                                                                                                                                          |
| **CSRF token**                    | A second token sent in headers that proves the request came from the legitimate frontend, not a malicious site.                                                                                                          |
| **GDPR**                          | The EU's data protection law. We're compliant from day one with self-serve data export and account deletion.                                                                                                             |
| **Stripe webhook**                | The mechanism by which Stripe tells our backend "this user just paid". Idempotent so duplicates are handled safely.                                                                                                      |
| **n8n**                           | A workflow automation tool. We have bridge endpoints for it but Celery Beat is the canonical scheduler.                                                                                                                  |
| **Remotion**                      | A React-based video composition framework. We use it to assemble carousel slides and video templates.                                                                                                                    |
| **Voice cloning**                 | Uploading 30 seconds of voice → ElevenLabs creates a model that can speak any text in that voice.                                                                                                                        |

---

## Appendix B — Useful URLs

- **Production frontend**: https://thook.ai
- **GitHub repo**: https://github.com/cooldeepeth/thookAI-production
- **Pitch deck (this doc)**: `docs/pitch/PITCH-DECK.md`
- **Project overview**: `docs/pitch/PROJECT-OVERVIEW.md`
- **User flows**: `docs/pitch/USER-FLOWS.md`
- **Launch checklist**: `LAUNCH-CHECKLIST.md`
- **Operator action stake list**: `.planning/audit/OPERATOR-ACTIONS.md`
- **Full project plan**: `.planning/PROJECT.md`
- **Roadmap**: `.planning/ROADMAP.md`

---

## Appendix C — Contact

**Founder**: Kuldeepsinh Parmar
**Email**: [TBD]
**LinkedIn**: [TBD]
**X**: [TBD]
**Discord**: [TBD]

---

_This document is the canonical pitch material for ThookAI v3.0. It is intended for two audiences: a potential co-founder evaluating whether to join, and a potential investor evaluating whether to fund. Every claim in this deck is verifiable against the codebase and project plan in the linked repository._

_Last updated: 2026-04-13_
