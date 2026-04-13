---
doc: project-overview
audience: co-founder + investor (technical depth)
voice: company (third-person)
version: v3.0-pre-launch
date: 2026-04-13
companion: PITCH-DECK.md, USER-FLOWS.md
---

# ThookAI — Project Overview

> The complete picture of what ThookAI is, how it's built, what runs where, and how everything connects. Written for a reader who wants to understand the system end-to-end before joining or investing.

---

## 1. Mission

**Give every creator their own AI content team — one that learns their voice, knows their audience, and proactively recommends what to post next.**

Not "AI that writes posts." Not "ChatGPT for marketers." A complete, persona-aware, multi-format content operating system that takes a creator from blank cursor to published post on every major platform, with a learning loop that gets smarter every cycle.

---

## 2. Product in one paragraph

ThookAI is an AI Content Operating System. A user signs up, answers a 7-question persona interview, and receives a personalized voice fingerprint (the "Persona Engine"). From that point forward, every piece of content they generate flows through a 5-agent pipeline (Commander → Scout → Thinker → Writer → QC → Consigliere) that produces platform-native content for LinkedIn, X, and Instagram in 9 different formats. ThookAI auto-generates accompanying media (images, carousel slides, short-form video, voice narration), suggests optimal posting times based on real engagement history, schedules and publishes via official platform APIs, and feeds the resulting performance data back into a Strategist Agent that proactively recommends what to create next. The platform supports multi-user agency workspaces, billing via a Custom Plan Builder with volume tier pricing, GDPR compliance, and an extensive learning loop powered by a per-user LightRAG knowledge graph and Pinecone vector store.

---

## 3. Why this exists

### The pain

Modern creators face an impossible triangle: **quality**, **frequency**, and **time**. They can deliver any two but not all three. Generic AI tools (ChatGPT, Jasper, Copy.ai) solve frequency but produce content that sounds like everyone else. Hiring writers solves quality but is expensive and slow. Writing personally solves quality but kills frequency.

### The insight

Voice is a **data structure**, not a one-time setup. The longer a system spends with a creator, the better it can act on their behalf. No competing product treats voice as first-class data with its own schema, learning loop, and API.

### The bet

A platform that captures voice deeply, generates with persona-fidelity, and learns from real engagement will create a switching cost curve that compounds. Year 1, the user is amazed. Year 2, the user can't imagine going back to a generic tool. Year 3, the user's Persona Engine is more valuable than any individual subscription.

---

## 4. System architecture (layered view)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                              │
│  React 18 + TailwindCSS + shadcn/ui + Framer Motion                     │
│  Vercel deployment · 38 pages · 36 code-split bundles                   │
│  httpOnly cookie auth · CSRF double-submit · centralized apiFetch       │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ HTTPS (CORS allow-listed)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                               │
│  FastAPI 0.110 (Python 3.11) on Railway                                 │
│  Uvicorn ASGI server                                                    │
│  Middleware stack (outermost → innermost):                              │
│    CORS → CSRF → SecurityHeaders → RateLimit → InputValidation →        │
│    Compression → Cache → Timing → Session                               │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
            ┌──────────────────────┴──────────────────────┐
            │                                             │
            ▼                                             ▼
┌─────────────────────────────┐         ┌─────────────────────────────────┐
│       ROUTE LAYER           │         │       AGENT LAYER               │
│  26 router files, 70+       │         │  21 agents in backend/agents/   │
│  endpoints                  │         │                                 │
│                             │         │  Pipeline agents:               │
│  /api/auth                  │         │    Commander (parse intent)     │
│  /api/auth/google           │         │    Scout (research)             │
│  /api/auth/social           │         │    Thinker (strategy)           │
│  /api/onboarding            │         │    Writer (generation)          │
│  /api/persona               │         │    QC (compliance)              │
│  /api/content               │         │    Consigliere (risk review)    │
│  /api/dashboard             │         │                                 │
│  /api/platforms             │         │  Specialized agents:            │
│  /api/billing               │         │    Designer (image)             │
│  /api/analytics             │         │    Voice (TTS / clone)          │
│  /api/templates             │         │    Video (multi-provider)       │
│  /api/strategy              │         │    Visual (brand assets)        │
│  /api/notifications         │         │    Publisher (LI / X / IG)      │
│  /api/agency                │         │    Analyst (engagement)         │
│  /api/admin                 │         │    Learning (feedback loop)     │
│  /api/uploads               │         │    Strategist (proactive recs)  │
│  /api/media                 │         │    Repurpose (cross-platform)   │
│  ...                        │         │    Series Planner               │
│                             │         │    Anti-Repetition              │
│                             │         │    Viral Predictor              │
│                             │         │    Orchestrator (LangGraph)     │
└─────────────────────────────┘         └─────────────────────────────────┘
            │                                             │
            └──────────────────────┬──────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          SERVICE LAYER                                   │
│  18 services in backend/services/                                       │
│                                                                         │
│  llm_client          stripe_service       media_storage                 │
│  llm_keys            subscriptions        creative_providers            │
│  credits             social_analytics     vector_store                  │
│  email_service       persona_refinement   uom_service                   │
│  obsidian_service    notification_service lightrag_service              │
│  webhook_service     sanitize             agent_accuracy                │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐
│  PERSISTENCE     │   │  TASK QUEUE      │   │  EXTERNAL APIS       │
│                  │   │                  │   │                      │
│  MongoDB Atlas   │   │  Redis +         │   │  See "External       │
│  (Motor async)   │   │  Celery          │   │  Integrations" table │
│  27 collections  │   │  3 queues        │   │  (next section)      │
│                  │   │  Beat scheduler  │   │                      │
│  Cloudflare R2   │   │                  │   │                      │
│  (media)         │   │                  │   │                      │
│                  │   │                  │   │                      │
│  Pinecone        │   │                  │   │                      │
│  (vectors)       │   │                  │   │                      │
└──────────────────┘   └──────────────────┘   └──────────────────────┘
```

---

## 5. External integrations (complete list)

| Category                      | Provider                               | Purpose                                     | Status                                                                        |
| ----------------------------- | -------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------- |
| **LLM (primary)**             | Anthropic Claude Sonnet 4.5            | Writer agent (persona-fidelity)             | ✅ Wired, needs credit top-up                                                 |
| **LLM (secondary)**           | OpenAI GPT-4o + GPT-4o-mini            | Commander, Thinker, QC, fallback            | ✅ Wired                                                                      |
| **LLM (tertiary)**            | Google Gemini                          | Optional fallback                           | ✅ Wired                                                                      |
| **Research LLM**              | Perplexity sonar-pro                   | Scout agent web research                    | ✅ Wired                                                                      |
| **Knowledge graph**           | LightRAG sidecar                       | Per-user multi-hop retrieval                | ✅ Wired                                                                      |
| **Vector store**              | Pinecone                               | Persistent embeddings (1536-dim)            | ⚠️ Index dim mismatch (operator action H1)                                    |
| **Image generation**          | FAL.ai (Flux Pro, Seadance)            | Primary image generator                     | ✅ Wired, needs API key                                                       |
| **Image generation**          | OpenAI DALL-E                          | Fallback image                              | ✅ Wired                                                                      |
| **Video generation**          | Runway ML                              | Long-form video                             | ✅ Wired, needs API key                                                       |
| **Video generation**          | Luma Dream Machine                     | Short-form motion                           | ✅ Wired, needs API key                                                       |
| **Video generation**          | Kling AI                               | Cinematic clips                             | ✅ Wired, needs API key                                                       |
| **Video generation**          | Pika Labs                              | Stylized clips                              | ✅ Wired, needs API key                                                       |
| **Video generation**          | HeyGen                                 | Avatar / talking-head                       | ✅ Wired, needs API key                                                       |
| **Video generation**          | D-ID                                   | Talking-head from photo                     | ✅ Wired, needs API key                                                       |
| **Voice / TTS**               | ElevenLabs                             | Voice cloning + premium TTS                 | ✅ Wired, needs API key                                                       |
| **Voice / TTS**               | Play.ht                                | Alternative TTS                             | ✅ Wired                                                                      |
| **Voice / TTS**               | Google TTS                             | Cost-effective fallback                     | ✅ Wired                                                                      |
| **Video assembly**            | Remotion (self-hosted)                 | Carousel + composition templates            | ✅ Wired                                                                      |
| **Object storage**            | Cloudflare R2                          | Media storage (S3-compatible, no egress)    | ✅ Wired                                                                      |
| **Database**                  | MongoDB Atlas                          | Primary persistence                         | ✅ Wired                                                                      |
| **Cache + queue**             | Redis                                  | Celery broker + cache layer                 | ✅ Wired                                                                      |
| **Background jobs**           | Celery (workers + beat)                | Scheduled publishing, analytics polling     | ✅ Wired, beat schedule active                                                |
| **Email**                     | Resend                                 | Password reset, agency invites              | ⚠️ Domain DKIM verification needed (operator action H5)                       |
| **Payments**                  | Stripe                                 | Checkout, subscriptions, webhooks           | ⚠️ Verify `sk_live_` (operator action B3)                                     |
| **Auth (social)**             | Google OAuth                           | Sign in with Google                         | ✅ Wired                                                                      |
| **Auth (platform)**           | LinkedIn OAuth 2.0                     | Connect LinkedIn account for publishing     | ✅ Wired                                                                      |
| **Auth (platform)**           | X OAuth 2.0 PKCE                       | Connect X account for publishing            | ✅ Wired                                                                      |
| **Auth (platform)**           | Meta Graph (Instagram + Facebook)      | Connect Instagram business account          | ✅ Wired                                                                      |
| **Publishing**                | LinkedIn UGC API                       | Post to LinkedIn                            | ✅ Wired                                                                      |
| **Publishing**                | X v2 API                               | Post to X                                   | ✅ Wired                                                                      |
| **Publishing**                | Instagram Meta Graph API               | Post to Instagram business                  | ✅ Wired                                                                      |
| **Analytics in**              | LinkedIn UGC + organizational insights | Engagement metrics 24h+7d                   | ✅ Wired                                                                      |
| **Analytics in**              | X v2 tweet metrics                     | Engagement metrics                          | ✅ Wired                                                                      |
| **Analytics in**              | Instagram insights                     | Engagement metrics                          | ✅ Wired                                                                      |
| **Error tracking**            | Sentry                                 | Backend error capture + PII scrub           | ✅ Active in production                                                       |
| **Error tracking (frontend)** | Sentry React                           | Frontend error capture                      | 🔴 NOT WIRED — TODO comment in `frontend/src/index.js:1` (operator action H2) |
| **Product analytics**         | PostHog                                | User behavior, funnel events, feature flags | ⚠️ Wrong account key (operator action B4)                                     |
| **Personal vault**            | Obsidian Local REST API                | Scout enrichment from user's notes          | ✅ Wired (opt-in)                                                             |
| **Workflow automation**       | n8n (legacy)                           | Kept as bridge endpoints, not canonical     | ✅ Wired (Celery Beat is canonical)                                           |

**Total integrations: 35+ external services**, with multi-provider fallback in 3 categories (LLM, image, video) for resilience.

---

## 6. Database schema (27 collections)

### Core user data

- `users` — accounts, subscription tier, credits, onboarding status
- `persona_engines` — voice fingerprint, content identity, performance intelligence, learning signals, UOM
- `persona_shares` — shareable persona link tokens with expiry
- `password_resets` — password reset tokens with TTL
- `login_attempts` — account lockout state (TTL: 30 min)
- `user_sessions` — JWT session tokens with TTL

### Content & generation

- `content_jobs` — every content generation request with full pipeline output
- `content_series` — multi-post series (e.g. 5-part LinkedIn series)
- `templates` — community template marketplace
- `template_upvotes` — template community voting
- `template_usage` — which templates were used by whom
- `media_assets` — generated images / video / voice / carousel
- `media_pipeline_ledger` — per-stage credit tracking for partial-failure accounting
- `uploads` — context files uploaded by users for content generation

### Scheduling & publishing

- `scheduled_posts` — queued for publishing via Celery Beat
- `platform_tokens` — encrypted OAuth tokens per platform per user (LinkedIn, X, Instagram)
- `oauth_states` — CSRF-style state tokens for OAuth flows (TTL: 10 min)

### Strategy & intelligence

- `strategy_recommendations` — proactive cards from Strategist Agent
- `strategist_state` — per-user runner state (last run, cadence flags)
- `learning_signals` — explicit feedback signals
- `daily_briefs` — daily content opportunity briefs (TTL: 48h)
- `daily_brief_dismissals` — dismissed briefs (TTL: 48h)
- `viral_cards` — public persona cards (TTL: 30 days)

### Billing & monetization

- `credit_transactions` — every credit credit/debit
- `subscription_history` — subscription tier history
- `stripe_events` — webhook idempotency (TTL: 7 days)

### Workspaces (agency)

- `workspaces` — agency workspace metadata
- `workspace_members` — members with roles + invitation status

### Onboarding

- `onboarding_sessions` — in-progress onboarding state (TTL: 24h)

### Indexes

27 collections, 110+ indexes total. All indexes defined in `backend/db_indexes.py` and auto-created on startup. Recently hardened (PR #63) to be idempotent against rename migrations (handles MongoDB error codes 85/86).

---

## 7. The 5-agent content pipeline (technical detail)

Every content generation flows through this LangGraph orchestrator (`backend/agents/orchestrator.py`).

### Stage 1 — Commander

**File**: `backend/agents/commander.py`
**LLM**: OpenAI GPT-4o → Anthropic fallback
**Job**: Parse the user's raw_input + platform + content_type into a structured `JobSpec`. Loads the Persona Engine from MongoDB. Determines required credits, applies UOM directives.
**Output**: `{job_spec, persona, uom_directives, estimated_cost}`
**Timeout**: 15 seconds
**Fallback**: Returns a default JobSpec if LLM fails

### Stage 2 — Scout

**File**: `backend/agents/scout.py`
**LLM**: Perplexity sonar-pro → mock fallback
**Job**: Optional research enrichment for topics that need fresh data. Also queries the user's LightRAG knowledge graph for related concepts. Pulls from Obsidian vault if connected.
**Output**: `{research_summary, sources, knowledge_graph_hits}`
**Timeout**: 20 seconds
**Fallback**: Skips enrichment, pipeline continues

### Stage 3 — Thinker

**File**: `backend/agents/thinker.py`
**LLM**: OpenAI GPT-4o-mini → Anthropic fallback
**Job**: Selects the angle, hook strategy, structure. Runs anti-repetition check via `agents/anti_repetition.py` (TF-IDF cosine similarity over recent posts). Runs hook fatigue analysis. Optionally invokes "hook debate" sub-agent for variant generation.
**Output**: `{angle, hook_variants, structure, repetition_score, hook_fatigue_warning}`
**Timeout**: 12 seconds

### Stage 4 — Writer

**File**: `backend/agents/writer.py`
**LLM**: Anthropic Claude Sonnet 4.5 → mock fallback
**Job**: Generates the final content using the Persona Engine voice fingerprint, regional English variant, UOM directives, and the strategy from Thinker. Wraps in retry logic (1 attempt with 1s backoff). Stores embedding in Pinecone for future similarity checks.
**Output**: `{final_content, persona_match_score, hook_used, length, format}`
**Timeout**: 30 seconds
**Fallback**: Returns a deterministic mock with persona traces

### Stage 5 — QC

**File**: `backend/agents/qc.py`
**LLM**: OpenAI GPT-4o-mini → Anthropic fallback → mock
**Job**: Compliance check, slop detection, persona-match scoring. Runs anti-slop vision check on generated images. Returns scored draft.
**Output**: `{persona_match: 0-10, ai_risk: 0-100, platform_fit: 0-10, slop_pass: bool, suggestions}`
**Timeout**: 12 seconds

### Stage 6 — Consigliere (optional final review)

**File**: `backend/agents/consigliere.py`
**LLM**: OpenAI GPT-4o
**Job**: Final risk assessment — flags potentially harmful content, missing disclaimers, brand-safety issues.
**Output**: `{risk_assessment, action: "approve" | "warn" | "block"}`
**Timeout**: 10 seconds
**Fallback**: Pipeline continues without consigliere review (non-fatal)

### Wall-clock performance

- **Average end-to-end**: 8-15 seconds for text-only post
- **With anti-repetition + hook debate**: 15-25 seconds
- **With image generation added**: 25-40 seconds
- **With video generation added**: 60-180 seconds (provider-dependent)

### Cost economics

- **Text-only pipeline cost**: ~$0.05 (Commander + Thinker + Writer + QC, summed across providers)
- **With image**: +$0.04-0.08 (FAL.ai Flux Pro or DALL-E)
- **With short video**: +$0.10-0.50 (depends on provider)
- **With voice narration**: +$0.05-0.15 (ElevenLabs)

### Credit pricing

- **Text post**: 10 credits ($0.60 at Starter tier) → 92% gross margin
- **Image**: 8 credits ($0.48) → 70% margin
- **Carousel (5 slides)**: 15 credits ($0.90) → 65% margin
- **Short video**: 25 credits ($1.50) → 50% margin
- **Voice narration**: 12 credits ($0.72) → 60% margin

---

## 8. Technology stack (full)

### Backend

| Component           | Choice                              | Version                   |
| ------------------- | ----------------------------------- | ------------------------- |
| Language            | Python                              | 3.11.11                   |
| Web framework       | FastAPI                             | 0.110.1                   |
| ASGI server         | Uvicorn                             | 0.25.0                    |
| Database driver     | Motor (async MongoDB)               | 3.3.1                     |
| Validation          | Pydantic                            | 2.6.4+                    |
| Task queue          | Celery                              | 5.3.0                     |
| Message broker      | Redis                               | 5.0.0 (client) + Redis 7+ |
| Auth                | python-jose, PyJWT, bcrypt, passlib | latest                    |
| Encryption          | cryptography (Fernet)               | 42.0.8                    |
| HTTP client         | httpx + requests                    | latest                    |
| LLM SDK (Anthropic) | anthropic                           | 0.34.0                    |
| LLM SDK (OpenAI)    | openai                              | 1.40.0                    |
| LLM framework       | LangGraph + LangChain Core          | 0.2.0                     |
| Vector store        | pinecone                            | 5.0.0                     |
| Image SDK           | fal-client                          | 0.10.0                    |
| Video SDK           | lumaai                              | 1.0.0                     |
| Voice SDK           | elevenlabs                          | 1.50.0                    |
| Object storage      | boto3 (S3-compatible for R2)        | 1.34.129+                 |
| Email               | resend                              | 2.0.0                     |
| Payments            | stripe                              | 8.0.0                     |
| Auth (social)       | authlib                             | 1.3.2                     |
| Error tracking      | sentry-sdk                          | 2.0.0+                    |
| Test                | pytest, pytest-asyncio              | 8.0.0                     |
| Lint                | flake8, mypy, black, isort          | latest                    |

### Frontend

| Component         | Choice                          | Version         |
| ----------------- | ------------------------------- | --------------- |
| Language          | JavaScript (no TS in app code)  | ES2022          |
| Framework         | React                           | 18.3.1          |
| Bundler           | Create React App + CRACO        | 7.1.0           |
| Routing           | React Router DOM                | 7.5.1           |
| Styling           | TailwindCSS                     | 3.4.17          |
| Component library | shadcn/ui (47 components)       | New York style  |
| Headless UI       | Radix UI (33 primitives)        | latest          |
| Forms             | React Hook Form + Zod           | 7.56.2 + 3.24.4 |
| Animation         | Framer Motion                   | 12.38.0         |
| Icons             | Lucide React                    | 0.507.0         |
| Toasts            | Sonner                          | 2.0.3           |
| Carousel          | Embla Carousel React            | 8.6.0           |
| Test              | Jest (CRA default) + Playwright | latest          |
| Lint              | ESLint + TypeScript ESLint      | 8.57.1          |

### Infrastructure

| Component       | Choice                             |
| --------------- | ---------------------------------- |
| Backend host    | Railway (asia-southeast1-eqsg3a)   |
| Frontend host   | Vercel                             |
| Database        | MongoDB Atlas                      |
| Cache + queue   | Redis Cloud (or equivalent)        |
| Object storage  | Cloudflare R2                      |
| CDN             | Cloudflare (R2) + Vercel edge      |
| Domain          | thook.ai (apex → www redirect)     |
| TLS             | Let's Encrypt via Vercel + Railway |
| Local dev       | Docker Compose                     |
| CI/CD           | GitHub Actions                     |
| Knowledge graph | LightRAG self-hosted sidecar       |

---

## 9. Security posture

### Authentication

- Email/password with bcrypt hashing
- Google OAuth via Authlib
- LinkedIn / X / Instagram OAuth for platform connection (separate from auth)
- JWT signed with HS256, stored in **httpOnly** cookies
- CSRF protection via double-submit token pattern (token in non-httpOnly cookie + X-CSRF-Token header)
- Account lockout after 5 failed attempts (15-min cooldown)
- Session token rotation on logout

### API security

- Pydantic body validation on every POST endpoint (no `dict[Any, Any]` accepted)
- XSS sanitization via `backend/services/sanitize.py` (stdlib `html.escape`) on all free-text fields before storage
- MongoDB injection prevention (no f-string queries, parameterized everywhere)
- CORS allow-list (no wildcards in production — verified via OPTIONS preflight)
- Rate limiting: 60/min global + 10/min auth-specific via `RateLimitMiddleware`
- Input validation middleware blocks malformed payloads at the edge

### Headers

All responses include:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (camera, microphone, geolocation, etc. all blocked)
- `X-XSS-Protection: 1; mode=block`

### Token storage

- OAuth platform tokens encrypted at rest via Fernet (`backend/routes/platforms.py:_encrypt_token`)
- Encryption key from `ENCRYPTION_KEY` env var (Fernet 32-byte base64)
- Tokens auto-refreshed proactively (24h before expiry) if a refresh_token is available
- For Instagram (no refresh_token), uses `fb_exchange_token` flow

### Sentry PII scrubbing

- Custom `before_send` callback strips PII from event payloads
- Configured in `backend/server.py` lifespan setup

### GDPR

- `/api/auth/export` — full user data export across 12 collections (users, persona, content, transactions, platforms (redacted), feedback, uploads, scheduled posts, media, workspaces, templates)
- `/api/auth/delete-account` — anonymizes user record, deletes persona, revokes platform tokens, anonymizes content jobs, deletes uploads, clears auth cookies
- Cookie consent gate (currently dev-only; main deployment has it pending)
- Privacy policy and Terms of Service pages live

### Verified by 700+ tests

- Billing module: 95%+ coverage gate (mandatory in CI)
- Security module: 85%+ coverage gate
- Pipeline & agents: 85%+ coverage gate
- OWASP Top 10 parametrized test suite (10/10 pass)

---

## 10. Background jobs & scheduling

All scheduled tasks run through Celery Beat (`backend/celeryconfig.py`). The earlier n8n bridge endpoints are kept for compatibility but Celery Beat is canonical.

| Task                        | Schedule               | Purpose                                               |
| --------------------------- | ---------------------- | ----------------------------------------------------- |
| `process-scheduled-posts`   | Every 5 min            | Pick up due `scheduled_posts` and publish to platform |
| `cleanup-stale-jobs`        | Every 10 min           | Mark hung pipeline jobs as errored after timeout      |
| `reset-daily-limits`        | Daily 00:00 UTC        | Reset per-user daily content creation counters        |
| `refresh-monthly-credits`   | 1st of month 00:00 UTC | Refresh subscription credit allowances                |
| `cleanup-old-jobs`          | Weekly                 | Remove failed/cancelled jobs older than 30 days       |
| `aggregate-daily-analytics` | Daily                  | Compute platform-wide daily stats                     |
| `cleanup-expired-shares`    | Daily                  | Remove expired persona share tokens                   |

Celery worker queues are split by load profile:

- `content` queue → text generation pipeline
- `media` queue → image / voice generation
- `video` queue → long-running video generation (separated to prevent slow video jobs from blocking text generation)

---

## 11. Frontend page inventory (38 pages)

### Public

- Landing page (Hero, Features, HowItWorks, DiscoverBanner, SocialProof, AgentCouncil, PricingSection, Footer)
- Auth page (login + register + Google OAuth + LinkedIn + X)
- Reset password
- Privacy policy
- Terms of service
- Persona Card public viewer
- Discover (viral persona card showcase)

### Onboarding

- Onboarding wizard (3-phase: Welcome → Voice Sample Analysis → Persona Card Reveal)

### Dashboard (13 sub-views inside Dashboard layout shell)

- DashboardHome (stats, daily brief, recent activity, recommendations)
- ContentStudio (text + media generation hub)
- ContentLibrary (all generated content)
- ContentCalendar (month grid view of scheduled posts)
- ContentOutput (single-job detail view with media + edit + approve)
- StrategyDashboard (Strategist Agent recommendations feed)
- Persona Engine (view + edit persona)
- Repurpose Agent (cross-platform repurposing)
- Templates (community template marketplace)
- Connections (LinkedIn / X / Instagram OAuth status)
- Analytics (engagement, trends, insights, persona evolution)
- Settings (account, billing, data export, account deletion)
- Agency Workspace (multi-user team management)

### Admin

- Admin dashboard (admin role only)
- Admin Users (admin role only)

### Experimental / specialized

- Viral Card (analyze any post URL)
- ComingSoon (placeholder for v4 features)

---

## 12. Backend route inventory (26 router files, 70+ endpoints)

| Router file         | Mount prefix                                     | Endpoint count | Notes                                                                                  |
| ------------------- | ------------------------------------------------ | -------------- | -------------------------------------------------------------------------------------- |
| `auth.py`           | `/api/auth`                                      | 11             | register, login, me, logout, csrf-token, export, delete-account                        |
| `auth_google.py`    | `/api/auth/google`                               | 2              | OAuth init + callback                                                                  |
| `auth_social.py`    | `/api/auth`                                      | 4              | LinkedIn + X social login                                                              |
| `password_reset.py` | `/api/auth`                                      | 2              | forgot, reset                                                                          |
| `onboarding.py`     | `/api/onboarding`                                | 5              | questions, analyze-posts, generate-persona, import-history, save-step                  |
| `persona.py`        | `/api/persona`                                   | 11             | CRUD, share, public, regional-english, avatar, voice-clone                             |
| `content.py`        | `/api/content`                                   | 14             | create, job, jobs, status, export, regenerate, repurpose, series                       |
| `dashboard.py`      | `/api/dashboard`                                 | 9              | stats, activity, brief, schedule (calendar/upcoming/optimal), publish                  |
| `platforms.py`      | `/api/platforms`                                 | 8              | status, connect/{platform}, callback/{platform}, disconnect/{platform}                 |
| `billing.py`        | `/api/billing`                                   | 14             | config, checkout, plan/preview, credits, subscription, payments, webhook               |
| `analytics.py`      | `/api/analytics`                                 | 10             | overview, trends, insights, learning, optimal-times, fatigue-shield, persona evolution |
| `viral.py`          | `/api/viral-card`                                | 1              | analyze                                                                                |
| `agency.py`         | `/api/agency`                                    | 6              | workspaces, members, invitations                                                       |
| `templates.py`      | `/api/templates`                                 | 6              | list, detail, upvote, use, categories                                                  |
| `repurpose.py`      | `/api/content/repurpose` + `/api/content/series` | 6              | repurpose, series CRUD                                                                 |
| `media.py`          | `/api/media`                                     | 4              | upload-url, confirm, list, delete                                                      |
| `uploads.py`        | `/api/uploads`                                   | 3              | file, url, list                                                                        |
| `notifications.py`  | `/api/notifications`                             | 4              | list, count, mark-read, SSE feed                                                       |
| `webhooks.py`       | `/api/webhooks`                                  | 3              | list, create, events                                                                   |
| `strategy.py`       | `/api/strategy`                                  | 5              | recommendations, accept, dismiss, feedback                                             |
| `campaigns.py`      | `/api/campaigns`                                 | 5              | CRUD                                                                                   |
| `obsidian.py`       | `/api/obsidian`                                  | 4              | config, sync, search                                                                   |
| `admin.py`          | `/api/admin`                                     | 6              | users, daily_stats, system_health                                                      |
| `n8n_bridge.py`     | `/api/n8n`                                       | 7              | execute/{task} (compatibility — Celery Beat is canonical)                              |
| `uom.py`            | `/api/uom`                                       | 4              | get, directives/{agent}, update                                                        |

**Total: ~70 endpoints across 26 router files.**

---

## 13. Phase / milestone history

### v1.0 ThookAI Stabilization (Phases 1-8) — Shipped 2026-04-01

Initial production-readiness sprint. Built or hardened: git/branch hygiene, Celery + Redis infra, auth + onboarding + email, content pipeline, publishing/scheduling/billing, media generation + analytics, admin + frontend quality, gap closure.

### v2.0 Intelligent Content OS (Phases 9-16) — Shipped 2026-04-01

The "intelligent" layer that defines ThookAI's category. Added:

- n8n bridge infrastructure (later replaced by Celery Beat as canonical)
- LightRAG knowledge graph with per-user isolation
- Multi-model media orchestration (8 formats via Remotion)
- Strategist Agent (nightly proactive recommendations)
- Analytics feedback loop (24h + 7d social metrics polling)
- Strategy Dashboard with SSE feed + one-click approve
- Obsidian vault integration
- E2E security hardening + critical-path smoke testing

### v2.1 Production Hardening — 50x Testing Sprint (Phases 17-20) — Shipped 2026-04-03

Test debt sprint. 700+ tests added across 4 coverage-gated suites. 4 P0 bugs found and fixed via TDD: JWT secret fallback, atomic credit decrement, webhook deduplication, LightRAG lambda race condition.

### v2.2 Frontend Hardening (Phases 21-25) — Shipped 2026-04-04

Frontend quality + production posture:

- CI strictness (removed all `continue-on-error`)
- httpOnly cookie auth migration (replaced localStorage JWT) + CSRF
- Centralized `apiFetch` with timeout / retry / error handling (replaced 41 raw `fetch()` calls)
- Frontend unit test suite (45+ tests in CI)
- Content download (text/images/zip) + redirect-to-platform compose URLs
- Full Playwright E2E verification

### v3.0 Distribution-Ready (Phases 26-35) — In Progress (9/10 done)

The current milestone. Goal: transform "code exists" → "every feature works perfectly end-to-end with zero errors against real production."

| Phase | Title                            | Status                                                          |
| ----- | -------------------------------- | --------------------------------------------------------------- |
| 26    | Backend endpoint hardening       | ✅ Complete (70 endpoints audited)                              |
| 27    | Onboarding reimagination         | ✅ Complete                                                     |
| 28    | Multi-format content generation  | ✅ Complete (9 platform-format combos)                          |
| 29    | Media generation pipeline        | ✅ Complete (4/5 SUMMARY files; code complete)                  |
| 30    | Social publishing end-to-end     | ✅ Complete (LI / X / IG)                                       |
| 31    | Smart scheduling                 | ✅ Complete (4 manual UI checks pending)                        |
| 32    | Frontend core flows polish       | ✅ Complete                                                     |
| 33    | Design system & landing page     | 🟡 Partial (landing page rebuilt; system documentation pending) |
| 34    | Security & GDPR                  | ✅ Complete (13 SECR requirements verified)                     |
| 35    | Performance, monitoring & launch | ✅ Complete (operator gate is the only blocker)                 |

### v4.0 Post-launch (proposed)

- Multi-language engine (Sarvam AI + regional Indian languages)
- Native mobile apps (React Native shells)
- Real-time collaboration in Content Studio
- Advanced video editing (auto B-roll suggestions)
- API marketplace (Persona Engine as a service)

### v5.0 Vision

- White-label enterprise deployments
- ThookAI Voice Mode (talk to your strategist)
- Cross-creator persona graph (agency-level intelligence)

---

## 14. What's currently in production vs. dev

### Deployed to production (main branch → Railway + Vercel)

- All v1.0, v2.0, v2.1, v2.2 work
- Phase 1-17 of "v3 rebuild" track (a parallel rebuild that ran in parallel with GSD phases 26-35)

### Sitting on `dev` branch (192 unpushed commits + 35+ shipped phases)

- All GSD phases 26-35 work
- Hotfix PR #63 (datetime aware comparison + idx_email idempotency) sitting on a separate `hotfix/datetime-naive-aware-prod` branch off main, ready to merge

### What needs to ship to converge

1. Push 192 unpushed `dev` commits to `origin/dev` (operator action B5)
2. Merge `hotfix/datetime-naive-aware-prod` PR #63 to `main`
3. Open PR `dev` → `main` to bring all phase 26-35 work to production
4. Deploy

---

## 15. Engineering principles (how this codebase is built)

### 1. Configuration is centralized

Every environment variable is read in `backend/config.py` via `@dataclass` settings classes. NO route, agent, service, or middleware ever calls `os.environ.get()` directly. Verified: 0 violations across 200+ files.

### 2. Database access is uniform

Every database access uses `from database import db` and Motor async methods. NO synchronous PyMongo calls. Indexes defined declaratively in `backend/db_indexes.py` and auto-created on startup.

### 3. Errors are explicit

Every `try` block has a specific `except`. Empty `except: pass` is allowed only for best-effort cleanup paths (lockout records, optional webhooks, non-fatal feature toggles). Sampled 14 files; all defensible.

### 4. Logging not printing

Zero `print()` statements in routes/agents/services/middleware. Every log goes through Python's `logging` module.

### 5. Test-driven on critical modules

Billing has a 95%+ coverage gate in CI. Security and Pipeline & Agents have 85%+ gates. Coverage is enforced (PR #63 met both gates).

### 6. Atomic commits with intent

Every commit explains the **why**, not just the what. Example: "fix: CompressionMiddleware duplicate Content-Length causing 502" includes 3 paragraphs of root cause and reasoning.

### 7. Phase-based development

Every feature ships through a documented phase: research → plan → execute → verify → summary. Each phase has a `VERIFICATION.md` with auditable evidence.

### 8. AI-augmented engineering

The codebase is built using Claude Code as a pair programmer with structured agent orchestration. Specific agents for backend, frontend, AI/data, code review, debugging, and verification. Workflows like `/team:deploy` and `/gsd-execute-phase` parallelize work across multiple specialized sub-agents.

### 9. Production-first

Staging is for major launches only. Most commits land on `dev`, run through CI, and merge to `main` only when all gates are green. Operator-action checks (LAUNCH-CHECKLIST.md) catch anything CI cannot.

### 10. Documentation as code

Every milestone has a verifiable artifact. The `.planning/` directory has phase plans, summaries, verifications, and audit reports — all version-controlled with the code.

---

## 16. Codebase metrics (snapshot)

| Metric                                  | Count     |
| --------------------------------------- | --------- |
| Backend Python files                    | 200+      |
| Backend lines of code (excl. tests)     | ~25,000   |
| Backend tests                           | 700+      |
| Backend test coverage (billing)         | 95%+      |
| Backend test coverage (security)        | 85%+      |
| Backend test coverage (pipeline)        | 85%+      |
| Frontend pages                          | 38        |
| Frontend components (custom + shadcn)   | 50+       |
| Frontend bundle (main.js gzipped)       | 107.51 kB |
| Frontend code-split chunks              | 36        |
| Frontend lazy-loaded routes             | 26        |
| API endpoints                           | 70+       |
| Database collections                    | 27        |
| Database indexes                        | 110+      |
| External service integrations           | 35+       |
| Specialized AI agents                   | 21        |
| Backend services                        | 18        |
| Phases shipped (v1.0 → v3.0)            | 35+       |
| GitHub PRs merged                       | 60+       |
| Git commits (lifetime)                  | ~2000+    |
| Commits unpushed (dev → origin/dev)     | 192       |
| Total integrations with API key support | 24        |

---

## 17. Glossary (technical terms used above)

| Term                         | Plain English                                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Persona Engine**           | The data structure storing a user's voice fingerprint, content preferences, and learning signals             |
| **5-agent pipeline**         | The sequence of AI agents (Commander → Scout → Thinker → Writer → QC → Consigliere) that produces every post |
| **LangGraph**                | A framework for building multi-agent AI workflows with state passing and conditional routing                 |
| **LightRAG**                 | An open-source per-user knowledge graph for multi-hop retrieval                                              |
| **Pinecone**                 | A vector database that stores AI embeddings for fast similarity search                                       |
| **Motor**                    | The async Python driver for MongoDB                                                                          |
| **Celery Beat**              | A scheduler that runs Python tasks on cron-like schedules                                                    |
| **Remotion**                 | A React-based video composition framework for programmatic video                                             |
| **httpOnly cookie**          | A cookie that JavaScript cannot read — defends against XSS-based session theft                               |
| **CSRF double-submit**       | A pattern where a token is sent in both a non-httpOnly cookie AND a request header — both must match         |
| **Fernet**                   | Symmetric encryption used to encrypt OAuth tokens at rest                                                    |
| **CORS**                     | Cross-Origin Resource Sharing — the policy that says "frontend X can call backend Y"                         |
| **Pydantic**                 | Python data validation library used for API request/response schemas                                         |
| **OAuth 2.0 PKCE**           | A security extension to OAuth used by single-page apps; Twitter requires it                                  |
| **UGC API**                  | LinkedIn's User Generated Content API for posting on behalf of authenticated users                           |
| **Meta Graph API**           | The API for posting to Instagram business accounts (via Facebook's Graph API)                                |
| **R2**                       | Cloudflare's S3-compatible object storage with no egress fees                                                |
| **Sentry**                   | Error tracking platform — every backend exception lands here                                                 |
| **PostHog**                  | Product analytics platform — tracks user behavior and funnel events                                          |
| **Resend**                   | Modern transactional email API                                                                               |
| **Stripe webhook**           | Stripe sends our backend HTTP POSTs when events happen (payment success, subscription change)                |
| **TF-IDF cosine similarity** | An algorithm to measure text similarity — used to detect repetition in generated content                     |
| **JWT**                      | JSON Web Token — a signed token used for stateless authentication                                            |
| **LangChain**                | A framework for building LLM-powered applications                                                            |
| **Embedding**                | A high-dimensional numerical representation of text used for similarity search                               |
| **Volume tier pricing**      | Per-credit cost decreases as the user buys more credits                                                      |
| **Code splitting**           | Breaking a large frontend bundle into smaller chunks loaded on demand                                        |
| **Lazy loading**             | Loading code only when it's needed (e.g., when a route is visited)                                           |

---

## 18. Where to look in the codebase

| If you want to understand...      | Read this file                                                          |
| --------------------------------- | ----------------------------------------------------------------------- |
| The product vision                | `.planning/PROJECT.md`                                                  |
| The phase-by-phase build history  | `.planning/ROADMAP.md`                                                  |
| The launch checklist              | `LAUNCH-CHECKLIST.md`                                                   |
| The current operator action items | `.planning/audit/OPERATOR-ACTIONS.md`                                   |
| The architecture                  | This file (`docs/pitch/PROJECT-OVERVIEW.md`)                            |
| The pitch                         | `docs/pitch/PITCH-DECK.md`                                              |
| User flows                        | `docs/pitch/USER-FLOWS.md`                                              |
| The 5-agent pipeline              | `backend/agents/orchestrator.py`                                        |
| The persona schema                | `backend/services/persona_refinement.py` + `backend/agents/onboarding/` |
| Database schema                   | `backend/db_indexes.py`                                                 |
| Configuration                     | `backend/config.py`                                                     |
| Auth flow                         | `backend/routes/auth.py`, `auth_google.py`, `auth_social.py`            |
| Content generation flow           | `backend/routes/content.py` → `backend/agents/orchestrator.py`          |
| Publishing flow                   | `backend/routes/dashboard.py` → `backend/agents/publisher.py`           |
| Strategist Agent                  | `backend/agents/strategist.py`                                          |
| Frontend entry                    | `frontend/src/App.js`                                                   |
| Frontend API client               | `frontend/src/lib/api.js`                                               |
| Auth context                      | `frontend/src/context/AuthContext.jsx`                                  |
| Landing page                      | `frontend/src/pages/LandingPage.jsx` and `frontend/src/pages/Landing/*` |
| Dashboard                         | `frontend/src/pages/Dashboard/index.jsx`                                |

---

## 19. What this product needs next (after v3.0 launch)

1. **Real users.** The product is built. The data is the next moat. We need 100 hand-picked design partners to flow through the system and start generating learning signals.

2. **Distribution velocity.** A co-founder dedicated to GTM. The founder has shipped 35+ phases solo with AI augmentation; the next bottleneck is not engineering throughput, it's distribution throughput.

3. **Design polish on the visual surfaces.** Phase 33 (design system + landing page) is partial. The landing page works but isn't conversion-optimized for cold traffic. Worth a 2-week design sprint after v3.0 ships.

4. **Native mobile.** v4.0. Once we have 1000+ active users, the mobile experience becomes important.

5. **Localization.** v4.0. Indian creator market is huge and underserved. Sarvam AI integration is in the v4.0 plan.

6. **Enterprise mode.** v5.0. Self-hosted ThookAI for Fortune 500 marketing teams.

---

_This document is the canonical project overview for ThookAI v3.0. Pair it with `PITCH-DECK.md` (narrative) and `USER-FLOWS.md` (UX) for a complete picture._

_Last updated: 2026-04-13_
