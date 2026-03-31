# CLAUDE.md — ThookAI Agent Briefing

> This file is the authoritative briefing for every Claude Code agent session.
> Read this entire file before touching any code. Do not skip sections.

---

## 1. Platform Overview

**ThookAI** is an AI-powered content creation platform for creators, founders,
and agencies. Users build a "Persona Engine" (their voice fingerprint) through
an onboarding interview, then generate platform-specific content (LinkedIn, X,
Instagram) via a 5-agent AI pipeline. The platform handles scheduling,
repurposing, analytics, billing, and multi-user workspaces.

**Production stack:**
- Backend: FastAPI (Python 3.11) — entry point is `backend/server.py`
- Frontend: React (CRA + CRACO), TailwindCSS, shadcn/ui — lives in `frontend/`
- Database: MongoDB via Motor (async) — accessed via `from database import db`
- Task queue: Celery + Redis — tasks in `backend/tasks/`
- Media storage: Cloudflare R2 (S3-compatible) — service in `backend/services/media_storage.py`
- LLM: Anthropic Claude (primary), OpenAI (fallback) — via `backend/services/llm_client.py`
- Email: Resend — `RESEND_API_KEY` + `FROM_EMAIL` in env (not yet implemented)
- Payments: Stripe — `backend/services/stripe_service.py`
- Vector store: Pinecone — `backend/services/vector_store.py` (implemented, not wired)
- Video: Remotion service — lives in `remotion-service/` directory
- Deployment: Backend on Render/Railway (Procfile: `uvicorn server:app`), Frontend on Vercel

---

## 2. Absolute Rules — Never Break These

1. **NEVER commit directly to `main`**. Always create a branch from `dev` and open a PR targeting `dev`.
2. **Branch naming**: `fix/short-description`, `feat/short-description`, `infra/short-description`
3. **Never hardcode secrets, API keys, or credentials** in any file. Use `settings.*` from `backend/config.py`.
4. **Never introduce a new Python package** without adding it to `backend/requirements.txt`.
5. **Never introduce a new npm package** without noting it in the PR description.
6. **After any change to `backend/agents/`**, manually verify the content pipeline still flows: Commander → Scout → Thinker → Writer → QC.
7. **After any change to `backend/services/stripe_service.py` or `backend/routes/billing.py`**, flag the PR for human review — do not merge billing changes without owner approval.
8. **Config pattern**: All settings come from `backend/config.py` dataclasses which read from `.env`. Never use `os.environ.get()` directly in route/agent/service files — always import `from config import settings`.
9. **Database access pattern**: Always use `from database import db` and Motor async methods (`await db.collection.find_one(...)`). Never use synchronous PyMongo calls.
10. **Do not delete or modify `backend/db_indexes.py`** — it is auto-run on startup and defines all MongoDB indexes.

---

## 3. Directory Structure
thookAI-production/
├── backend/
│ ├── server.py # FastAPI app + all router registrations + middleware
│ ├── config.py # All settings dataclasses (DatabaseConfig, LLMConfig, etc.)
│ ├── database.py # MongoDB Motor client — exports db and client
│ ├── db_indexes.py # MongoDB index definitions — runs at startup
│ ├── auth_utils.py # JWT auth — exports get_current_user dependency
│ ├── Procfile # Production start: uvicorn server:app
│ ├── requirements.txt # Python dependencies
│ ├── .env.example # All required environment variables documented here
│ │
│ ├── agents/ # AI pipeline agents
│ │ ├── pipeline.py # Orchestrates the full generation pipeline
│ │ ├── commander.py # Parses user intent, builds job spec
│ │ ├── scout.py # Research agent (uses Perplexity API)
│ │ ├── thinker.py # Strategy + angle selection
│ │ ├── writer.py # Content generation (Claude primary)
│ │ ├── qc.py # Quality control + compliance check
│ │ ├── publisher.py # Platform publishing (LinkedIn, X, Instagram)
│ │ ├── analyst.py # Analytics + insights generation
│ │ ├── learning.py # User feedback learning loop
│ │ ├── repurpose.py # Cross-platform content repurposing
│ │ ├── series_planner.py # Multi-post series planning
│ │ ├── anti_repetition.py # Content diversity / hook fatigue detection
│ │ ├── viral_predictor.py # Hook scoring + virality prediction
│ │ ├── designer.py # AI image generation (fal.ai / DALL-E)
│ │ ├── video.py # Video generation (Luma, Kling, Runway, HeyGen)
│ │ ├── voice.py # Voice/TTS generation (ElevenLabs)
│ │ └── visual.py # Visual brief + brand asset management
│ │
│ ├── routes/ # FastAPI routers — all mounted in server.py under /api
│ │ ├── auth.py # /api/auth — email/password register + login
│ │ ├── auth_google.py # /api/auth/google — Google OAuth (Authlib)
│ │ ├── password_reset.py # /api/reset-password — token-based reset (email NOT sent yet)
│ │ ├── onboarding.py # /api/onboarding — 7-question interview + persona generation
│ │ ├── persona.py # /api/persona — CRUD, sharing, export
│ │ ├── content.py # /api/content — generation, approval, editing, scheduling
│ │ ├── dashboard.py # /api/dashboard — stats, feed, recommendations
│ │ ├── platforms.py # /api/platforms — OAuth connect for LinkedIn/X/Instagram
│ │ ├── repurpose.py # /api/content/repurpose + /api/content/series
│ │ ├── analytics.py # /api/analytics — overview, trends, persona evolution
│ │ ├── billing.py # /api/billing — Stripe checkout, webhooks, portal
│ │ ├── viral.py # /api/viral — hook scoring, A/B variations
│ │ ├── agency.py # /api/agency — workspaces, members, invitations
│ │ ├── templates.py # /api/templates — community template marketplace
│ │ ├── media.py # /api/media — generated media asset management
│ │ └── uploads.py # /api/uploads — file + URL upload for content context
│ │
│ ├── services/ # Shared business logic services
│ │ ├── llm_client.py # LlmChat class — wraps Anthropic/OpenAI/Gemini
│ │ ├── llm_keys.py # Helper: anthropic_available(), chat_constructor_key()
│ │ ├── credits.py # Credit deduction, tier configs, TIER_CONFIGS dict
│ │ ├── stripe_service.py # Stripe checkout, webhook handling, subscription mgmt
│ │ ├── subscriptions.py # Subscription status, tier enforcement
│ │ ├── persona_refinement.py # Persona evolution, fatigue shield, voice analysis
│ │ ├── vector_store.py # Pinecone wrapper — store/search content embeddings
│ │ ├── media_storage.py # R2 upload/download helpers
│ │ └── creative_providers.py # fal.ai, ElevenLabs, image/video provider abstraction
│ │
│ ├── tasks/ # Celery async tasks
│ │ ├── content_tasks.py # Pipeline, scheduled posts, daily limits, analytics, cleanup
│ │ └── media_tasks.py # Async media generation tasks
│ │
│ └── middleware/ # FastAPI middleware
│ ├── security.py # SecurityHeadersMiddleware, RateLimitMiddleware, InputValidationMiddleware
│ └── performance.py # CompressionMiddleware, CacheMiddleware, TimingMiddleware
│
├── frontend/
│ ├── src/ # React source — components, pages, hooks, api client
│ ├── craco.config.js # CRA override config
│ ├── tailwind.config.js # TailwindCSS config
│ ├── components.json # shadcn/ui config
│ └── vercel.json # Vercel deployment config (SPA routing)
│
├── remotion-service/ # Separate Node.js service for Remotion video rendering
├── memory/ # Agent memory/context files (do not auto-delete)
└── docs/ # Documentation files

text

---

## 4. Content Generation Pipeline — How It Works

Every content generation request flows through this pipeline in `backend/agents/pipeline.py`:
User Request (POST /api/content/generate)
↓
Commander Agent (commander.py)
- Parses raw_input, platform, content_type
- Loads user's Persona Engine from db.persona_engines
- Builds structured job spec
↓
Scout Agent (scout.py)
- Optional: searches Perplexity for topic research
- Returns enriched context for the Thinker
↓
Thinker Agent (thinker.py)
- Selects content angle, hook strategy, structure
- Applies anti-repetition check via agents/anti_repetition.py
↓
Writer Agent (writer.py)
- Generates final content using Claude (claude-sonnet-4-20250514)
- Applies persona voice fingerprint from db.persona_engines
↓
QC Agent (qc.py)
- Checks compliance, quality, brand consistency
- Returns scored draft
↓
Job saved to db.content_jobs with status "reviewing"
WebSocket / polling returns result to frontend

text

**Job statuses**: `pending` → `processing` → `reviewing` → `approved` → `scheduled` or `published`

**LLM model to always use**: `claude-sonnet-4-20250514` (Anthropic primary)
⚠️ `backend/routes/onboarding.py` incorrectly uses `"claude-4-sonnet-20250514"` — this is a known bug causing silent fallback to mock persona generation.

---

## 5. Database Collections Reference

| Collection | Purpose | Key fields |
|---|---|---|
| `users` | User accounts | `user_id`, `email`, `subscription_tier`, `credits`, `onboarding_completed` |
| `persona_engines` | User persona cards | `user_id`, `card{}`, `voice_fingerprint{}`, `content_identity{}`, `performance_intelligence{}`, `learning_signals{}`, `uom{}` |
| `content_jobs` | All content generation jobs | `job_id`, `user_id`, `platform`, `status`, `draft`, `final_content`, `was_edited` |
| `scheduled_posts` | Posts queued for publishing | `schedule_id`, `user_id`, `platform`, `scheduled_at`, `status` |
| `platform_tokens` | OAuth tokens for social platforms | `user_id`, `platform`, `access_token`, `refresh_token`, `expires_at` |
| `workspaces` | Agency workspaces | `workspace_id`, `owner_id`, `name`, `settings{}` |
| `workspace_members` | Workspace membership | `workspace_id`, `user_id`, `role`, `status` |
| `templates` | Community template marketplace | `template_id`, `author_id`, `category`, `hook_type`, `upvotes`, `uses_count` |
| `media_assets` | Generated images/videos | `asset_id`, `user_id`, `type`, `url`, `job_id` |
| `uploads` | User-uploaded context files | `upload_id`, `user_id`, `url`, `context_type` |
| `password_reset_tokens` | Reset tokens | `user_id`, `token`, `expires_at`, `used` |
| `persona_shares` | Shareable persona links | `share_token`, `user_id`, `expires_at`, `is_active` |

**Subscription tiers**: `free` → `pro` → `studio` → `agency`
**Credit system**: defined in `backend/services/credits.py` → `TIER_CONFIGS` dict

---

## 6. Known Bugs & Broken Systems (Priority Order)

These are confirmed broken. Fix in this order due to dependencies.

### 🔴 CRITICAL — Blocks Core Functionality

**[BUG-1] Wrong Claude model name in onboarding.py**
- File: `backend/routes/onboarding.py` lines ~95 and ~110
- Bug: `"claude-4-sonnet-20250514"` should be `"claude-sonnet-4-20250514"`
- Effect: Every onboarding call fails silently and falls back to the dumb mock persona generator. All users get generic personas, destroying the core product value.
- Fix: Replace both incorrect model strings with `"claude-sonnet-4-20250514"`

**[BUG-2] Celery app not configured — ALL scheduled tasks are dead**
- Missing files: `backend/celery_app.py` and `backend/celeryconfig.py`
- Effect: All `@shared_task` decorators in `backend/tasks/content_tasks.py` and `backend/tasks/media_tasks.py` are orphaned. Nothing in `tasks/` ever runs automatically.
- Broken tasks: `process_scheduled_posts` (posts never publish), `reset_daily_limits` (users stay credit-capped forever), `refresh_monthly_credits`, `cleanup_old_jobs`, `cleanup_expired_shares`, `aggregate_daily_analytics`
- Fix: Create `backend/celery_app.py` with Redis broker from `settings.app.redis_url`. Create `backend/celeryconfig.py` with a `beat_schedule` dict for all 6 tasks. Update `Procfile` to add `worker: celery -A celery_app worker` and `beat: celery -A celery_app beat`.

**[BUG-3] `_publish_to_platform()` in content_tasks.py is a placeholder**
- File: `backend/tasks/content_tasks.py` — `_publish_to_platform()` function
- Bug: The function logs `"[SIMULATED] Publishing to {platform}"` and returns `True`. It never calls `agents/publisher.py`.
- Effect: Scheduled posts appear to "publish" in the DB (status set to `published`) but nothing is actually sent to LinkedIn/X/Instagram.
- Fix: Replace the placeholder body with a call to the appropriate method in `backend/agents/publisher.py`, passing the platform, content, and OAuth token.

**[BUG-4] No email service — password reset and agency invites are silent**
- Missing: No email sending implementation anywhere in the codebase
- `RESEND_API_KEY` and `FROM_EMAIL` are declared in `.env.example` and `config.py` but never used
- Affected: `backend/routes/password_reset.py` (generates token, never emails it), `backend/routes/agency.py` invite endpoint (logs "invitation sent", sends nothing)
- Fix: Create `backend/services/email_service.py` using the `resend` Python package (already in `requirements.txt`). Implement `send_password_reset_email(to_email, reset_link)` and `send_workspace_invite_email(to_email, workspace_name, invite_link)`. Call these from the respective routes.

### 🟡 HIGH — Platform Quality Degraded

**[BUG-5] Analytics data is fabricated — no real social data**
- Files: `backend/agents/analyst.py`, `backend/routes/analytics.py`
- Bug: All metrics (engagement, reach, impressions) are derived from internal DB job counts, not actual post performance from LinkedIn/X/Instagram APIs.
- `performance_intelligence` in `db.persona_engines` is always initialised as `{}` and never populated.
- `optimal_posting_times` is always `{}`.
- Fix: Add a background task that, after a post is published, polls the platform API for performance metrics after 24h and 7d, and writes results back to `db.content_jobs.performance_data` and aggregates into `persona_engines.performance_intelligence`.

**[BUG-6] Vector store implemented but never called**
- File: `backend/services/vector_store.py` — full Pinecone wrapper exists
- Bug: `agents/learning.py` stores approved content as raw strings in MongoDB, NOT as embeddings in Pinecone. `agents/writer.py` does not query similar past content before writing.
- Fix: In `agents/learning.py`, after storing approval, also call `vector_store.store_content_embedding(user_id, content, metadata)`. In `agents/writer.py`, call `vector_store.find_similar_content(user_id, topic)` at the start to fetch style examples and inject them into the writer prompt.

**[BUG-7] Media upload falls back to /tmp in production (data loss)**
- File: `backend/routes/uploads.py`
- Bug: If `R2_ACCESS_KEY_ID` is not set, files are saved to `/tmp/thookai_uploads/` and the local path is stored as the URL in MongoDB. On cloud deployments, `/tmp` is ephemeral — files vanish on restart, all media URLs become dead links.
- Fix: Add a startup check in `server.py` lifespan that warns loudly if R2 is not configured. In `uploads.py`, if R2 is unavailable, raise HTTP 503 with message "Media storage not configured" rather than silently falling back to /tmp.

**[BUG-8] Stripe billing has no Price IDs — checkout will fail**
- File: `backend/services/stripe_service.py`
- Bug: `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_STUDIO_MONTHLY`, etc. are all blank in `.env.example`. `create_checkout_session` will throw a Stripe `InvalidRequest` error for any upgrade attempt.
- Also: `STRIPE_WEBHOOK_SECRET` being missing causes all webhooks to fail signature verification — subscription upgrades from Stripe won't propagate to the DB.
- Fix (config-level, not code): Document in PR description that owner must create Stripe products and fill in all `STRIPE_PRICE_*` env vars. Code fix: Add explicit check at startup that logs `ERROR: Stripe Price IDs not configured` if any are blank when `ENVIRONMENT=production`.

**[BUG-9] Pattern Fatigue Shield and Anti-Repetition are duplicate + disconnected systems**
- Files: `backend/services/persona_refinement.py` (`get_pattern_fatigue_shield`), `backend/agents/anti_repetition.py`
- Bug: Two separate systems do the same job but don't share data. The Commander calls `anti_repetition.py` during generation. The Fatigue Shield in `persona_refinement.py` is only exposed via `GET /analytics/fatigue-shield` but never fed back into the generation pipeline.
- Fix: In `backend/agents/pipeline.py` (Thinker step), before angle selection, call `get_pattern_fatigue_shield(user_id)` and inject any flagged patterns into the Thinker prompt as explicit avoidance instructions. Deprecate the duplicate logic in `anti_repetition.py` gradually.

### 🟠 MEDIUM — Features Built But Unreachable

**[BUG-10] Template marketplace has no seed data**
- File: `backend/routes/templates.py`
- Bug: `db.templates` collection is empty on a fresh deployment. The marketplace page will show nothing.
- Fix: Create `backend/scripts/seed_templates.py` with 20–30 curated starter templates across all categories (`thought_leadership`, `storytelling`, `how_to`, `contrarian`, etc.) for LinkedIn, X, and Instagram. Run once on deploy.

**[BUG-11] Persona sharing feature is complete but hidden**
- File: `backend/routes/persona.py` — full implementation exists
- Bug: No frontend routes or UI components reference the persona share endpoints. Users cannot discover or use the feature.
- Fix: Add a "Share Persona" button in the Persona page in the frontend. Wire it to `POST /api/persona/share` and display the returned link.

**[BUG-12] Designer agent image generation blocks event loop**
- File: `backend/agents/designer.py`
- Bug: Image generation polling loop runs synchronously when Celery is not configured. This blocks FastAPI's async event loop during 5-minute timeouts, freezing the entire server under concurrent load.
- Fix: Wrap the polling loop in `asyncio.wait_for()` with a 60s timeout. If Celery is available, always use the async task path.

---

## 7. Features Not Yet Implemented (from Product Roadmap)

These are missing entirely — no backend or frontend code exists yet:

| Feature | Where to build | Notes |
|---|---|---|
| Post export (copy/CSV/PDF) | `backend/routes/content.py` + frontend | Simple endpoint returning formatted content |
| Real social analytics ingestion | New: `backend/services/social_analytics.py` | Poll LinkedIn UGC API, X v2 tweet metrics, IG insights 24h/7d after publish |
| Notification system | New: SSE endpoint in `backend/routes/notifications.py` | Job completion, scheduled post published, billing events |
| Voice cloning upload flow | `backend/agents/voice.py` + frontend | User uploads sample audio → ElevenLabs clone creation |
| Post history bulk import | New: `backend/routes/onboarding.py` or new route | Batch upload past posts for persona training |
| Campaign/project grouping | New: `backend/routes/campaigns.py` | Group content jobs under a campaign umbrella |
| Celery beat config | `backend/celery_app.py` (create new) | See BUG-2 above |
| Avatar creation flow | `backend/agents/video.py` | User photo → HeyGen avatar ID creation |
| Webhook/Zapier outbound | New: `backend/services/webhook_service.py` | Fire on job completion events |
| Admin dashboard | New: `backend/routes/admin.py` | Guarded by admin role — view daily_stats, user counts |

---

## 8. Environment Variables Reference

All config lives in `backend/config.py`. Required variables for full functionality:
Core (required always)
MONGO_URL, DB_NAME, JWT_SECRET_KEY, FERNET_KEY

LLM (at least one required)
ANTHROPIC_API_KEY # Primary — use model: claude-sonnet-4-20250514
OPENAI_API_KEY # Fallback
PERPLEXITY_API_KEY # Scout agent research

Media storage (required in production)
R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL

Task queue (required for scheduled features)
REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND

Email (required for password reset + agency invites)
RESEND_API_KEY, FROM_EMAIL

Billing (required for paid plans)
STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
STRIPE_PRICE_PRO_MONTHLY, STRIPE_PRICE_PRO_ANNUAL
STRIPE_PRICE_STUDIO_MONTHLY, STRIPE_PRICE_STUDIO_ANNUAL
STRIPE_PRICE_AGENCY_MONTHLY, STRIPE_PRICE_AGENCY_ANNUAL
STRIPE_PRICE_CREDITS_100, STRIPE_PRICE_CREDITS_500, STRIPE_PRICE_CREDITS_1000

OAuth platforms
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, BACKEND_URL

Vector memory
PINECONE_API_KEY, PINECONE_INDEX_NAME

Media generation (optional, feature-gated)
FAL_KEY, LUMA_API_KEY, ELEVENLABS_API_KEY

text

---

## 9. Testing

- Test files live in `backend/tests/`
- Run tests with: `cd backend && pytest`
- After fixing any agent file, test the full pipeline:
POST /api/content/generate {platform: "linkedin", content_type: "post", raw_input: "test"}

text
and confirm the job reaches `reviewing` status within 60 seconds.
- After fixing billing, always test with Stripe test mode keys (`sk_test_*`), never live keys.

---

## 10. Team Agent Orchestration

ThookAI uses a team-based agent orchestration layer on top of GSD for autonomous development.

**Your role:** When the user discusses features, architecture, or priorities, act as their **CTO-level technical partner** — brainstorm, challenge assumptions, help decompose work into phases, and identify risks.

**Team commands:**
- `/team:deploy <phase>` — Full pipeline: specialist analysis → plan → execute → verify → report
- `/team:brief <phase>` — Run specialists only (review before committing to execution)
- `/team:status [phase]` — Show deployment status and artifacts
- `/team:autonomous` — Run all remaining phases with specialist analysis

**Domain specialists** (spawned in parallel before planning):
- **Backend specialist** — APIs, database, auth, server architecture analysis
- **Frontend specialist** — Components, state, UX, responsive design analysis
- **AI/Data specialist** — LLM integration, prompts, embeddings, pipeline analysis

**How it works:** Specialists produce BRIEF.md files → GSD planner reads them as extra context → executor builds → verifier checks → TEAM-REPORT.md compiles results.

**When to suggest team commands:**
- User says "let's build this" or "implement this feature" → suggest `/team:deploy`
- User wants to review approach first → suggest `/team:brief`
- User says "ship it" or "execute everything" → suggest `/team:autonomous`

---

## 11. PR Checklist (include in every PR description)

- [ ] Branch targets `dev`, not `main`
- [ ] No secrets or API keys in code
- [ ] `requirements.txt` updated if new packages added
- [ ] No new `os.environ.get()` calls — used `settings.*` instead
- [ ] Tested locally with `uvicorn server:app --reload` from `backend/`
- [ ] Pipeline smoke test passed (if agent files modified)
- [ ] Described what was broken and how it is now fixed

<!-- GSD:project-start source:PROJECT.md -->
## Project

**ThookAI — Stabilization & Production Readiness**

ThookAI is an AI-powered content creation platform for creators, founders, and agencies. Users build a "Persona Engine" (voice fingerprint) through an onboarding interview, then generate platform-specific content (LinkedIn, X, Instagram) via a 5-agent AI pipeline. The platform handles scheduling, repurposing, analytics, billing, media generation, and multi-user workspaces. Currently deployed to Render (backend) and Vercel (frontend) but not publicly launched — multiple features are broken or partially implemented.

**Core Value:** Every feature that exists in the codebase must actually work end-to-end — a user can sign up, onboard, generate content, schedule, publish, pay, and manage their account without hitting broken flows.

### Constraints

- **Branch strategy**: All work branches from `dev`, PRs target `dev`. Never commit to `main` directly.
- **Branch naming**: `fix/short-description`, `feat/short-description`, `infra/short-description`
- **Config pattern**: All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly.
- **Database pattern**: Always `from database import db` with Motor async. Never synchronous PyMongo.
- **LLM model**: `claude-sonnet-4-20250514` (Anthropic primary)
- **Billing changes**: Flag for human review — no auto-merge on billing code
- **Agent pipeline**: After any change to `backend/agents/`, verify full pipeline flow
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11.11 - Backend API, agents, task processing
- JavaScript/React 18.3.1 - Frontend application (CRA + CRACO)
- TypeScript - Frontend tooling (with ESLint plugin support)
- HTML/CSS - Frontend via TailwindCSS 3.4.17
- SQL/MongoDB Query Language - Database operations via Motor async driver
## Runtime
- Python 3.11.11 (specified in `backend/runtime.txt`)
- Node.js 18+ (frontend uses `react-scripts` 5.0.1)
- pip (Python) - `backend/requirements.txt` with 52 dependencies
- npm (JavaScript) - `frontend/package.json` with 99 dependencies
- Lockfiles: package-lock.json (frontend), pip freeze equivalent in requirements.txt
## Frameworks
- FastAPI 0.110.1 - REST API framework, async request handling
- Uvicorn 0.25.0 - ASGI server for FastAPI
- React 18.3.1 - UI framework
- React Router DOM 7.5.1 - Client-side routing
- React Hook Form 7.56.2 - Form state management
- Zod 3.24.4 - TypeScript-first schema validation
- Radix UI (33 components) - Headless component library (accordion, dialog, dropdown, etc.)
- shadcn/ui - Composable React components built on Radix UI (referenced via `components.json`)
- TailwindCSS 3.4.17 - Utility-first CSS framework
- Lucide React 0.507.0 - Icon library
- Framer Motion 12.38.0 - Animation library
- Embla Carousel React 8.6.0 - Carousel component
- Sonner 2.0.3 - Toast notification system
- Celery 5.3.0 - Distributed task queue
- Redis 7+ - Message broker and result backend
- pytest 8.0.0 - Python test framework
- pytest-asyncio 0.23.0 - Async test support
- No frontend test framework detected in package.json
- Craco 7.1.0 - CRA configuration override (webpack)
- Black 24.1.1 - Python code formatter
- isort 5.13.2 - Python import sorter
- flake8 7.0.0 - Python linter
- mypy 1.8.0 - Python type checker
- ESLint 8.57.1 - JavaScript linter
- TypeScript ESLint (5.62.0) - TS-aware linting
- PostCSS 8.4.49 - CSS preprocessor (with autoprefixer)
- Jest (via react-scripts) - JavaScript test runner (CRA default)
## Key Dependencies
- motor 3.3.1 - Async MongoDB driver (uses PyMongo 4.5.0 under the hood)
- anthropic 0.34.0 - Anthropic Claude API client (primary LLM)
- openai 1.40.0 - OpenAI API client (fallback LLM)
- boto3 1.34.129+ - AWS S3 / Cloudflare R2 client
- stripe 8.0.0 - Payment processing
- google-generativeai 0.8.0 - Google Gemini support (optional)
- langgraph 0.2.0 - LangChain-based agent orchestration
- langchain-core 0.3.0 - LangChain framework
- fal-client 0.10.0 - FAL.ai image generation
- lumaai 1.0.0 - Luma Dream Machine video API
- elevenlabs 1.50.0 - ElevenLabs voice/TTS API
- pinecone 5.0.0 - Vector database for embeddings
- redis 5.0.0 - Redis Python client with hiredis speedup
- kombu 5.6.0 - Celery message transport
- billiard 4.2.1 - Celery task execution backend
- authlib 1.3.2 - OAuth client for Google, LinkedIn, Twitter, Instagram
- pyjwt 2.10.1 - JWT token creation/verification
- python-jose 3.3.0 - JOSE token support
- bcrypt 4.1.3 - Password hashing
- passlib 1.7.4 - Password utilities
- cryptography 42.0.8 - Encryption (Fernet for token encryption)
- itsdangerous 2.2.0 - Secure signing for tokens
- pydantic 2.6.4+ - Data validation and settings management
- email-validator 2.2.0 - Email format validation
- python-multipart 0.0.9 - Multipart form data parsing
- httpx 0.28.1 - HTTP client (sync+async)
- requests 2.31.0 - HTTP client (synchronous)
- pandas 2.2.0 - Data manipulation
- numpy 1.26.0 - Numerical computing
- typer 0.9.0 - CLI utilities
- jq 1.6.0 - JSON query tool
- python-dotenv 1.0.1 - .env file loading
- sentry-sdk 2.0.0+ - Error tracking and performance monitoring
- resend 2.0.0 - Transactional email service
- tzdata 2024.2 - Timezone database
- tzlocal 5.0 - Local timezone detection
## Configuration
- `DatabaseConfig` - MongoDB connection (MONGO_URL, DB_NAME, pool sizing)
- `SecurityConfig` - JWT, CORS, rate limiting
- `LLMConfig` - API keys for all LLM providers
- `R2Config` - Cloudflare R2 credentials
- `EmailConfig` - Resend email configuration
- `GoogleConfig` - Google OAuth
- `StripeConfig` - Stripe API keys and price IDs
- `VideoProviderConfig` - Video generation API keys (Runway, Kling, Luma, HeyGen, D-ID, FAL)
- `VoiceProviderConfig` - Voice/TTS API keys (Play.ht, Google TTS)
- `PlatformOAuthConfig` - LinkedIn, Meta/Instagram, Twitter OAuth
- `PineconeConfig` - Vector store configuration
- `AppConfig` - Environment, debug, logging, URLs
- Frontend: `frontend/tsconfig.json` (TypeScript config)
- Frontend: `frontend/tailwind.config.js` - TailwindCSS customization
- Frontend: `frontend/craco.config.js` - CRA webpack overrides
- Frontend: `frontend/postcss.config.js` - PostCSS plugins
- Frontend: `components.json` - shadcn/ui component configuration
- Backend: `backend/celeryconfig.py` - Celery task routing and beat schedule
- Backend: `pytest.ini` - Pytest configuration
- Docker: `docker-compose.yml` - Local development services
## Platform Requirements
- Python 3.11+
- Node.js 18+ (for frontend)
- MongoDB 7.0+ (local or Atlas)
- Redis 7+ (for Celery)
- Git
- API keys: At least one LLM provider (Anthropic preferred, OpenAI fallback)
- Deployment targets: Backend on Render/Railway/Heroku (via Procfile), Frontend on Vercel
- MongoDB Atlas (cloud managed)
- Redis Cloud or AWS ElastiCache
- Cloudflare R2 (media storage)
- All external API credentials (Stripe, Resend, video/voice providers)
- Backend: `uvicorn server:app --host 0.0.0.0 --port $PORT` (Procfile `web` process)
- Background worker: `celery -A celery_app:celery_app worker` (Procfile `worker` process)
- Beat scheduler: `celery -A celery_app:celery_app beat` (Procfile `beat` process)
- Frontend: `npm start` (Vercel or local development)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python: `snake_case.py` (e.g., `auth_utils.py`, `content_tasks.py`)
- React/Frontend: `PascalCase.jsx` for components (e.g., `AuthContext.jsx`), `camelCase.js` for utilities
- UI components from shadcn: `kebab-case.jsx` (e.g., `toggle-group.jsx`, `radio-group.jsx`)
- Python: `snake_case()` for all functions and methods
- React: `camelCase()` for all functions, `PascalCase()` for components and custom hooks
- Custom hooks: `useXxx()` pattern (e.g., `useAuth`, `checkAuth`)
- Handler functions: `handleXxx()` or `onXxx()` pattern in React components
- Python: `snake_case` for all variables and constants. Module-level constants in `UPPER_CASE`
- React/JS: `camelCase` for all variables, `UPPER_CASE` for constants
- Environment variables: `UPPER_CASE` with underscores (e.g., `REACT_APP_BACKEND_URL`, `MONGO_URL`)
- Python: Use type hints for all functions (PEP 484). Import from `typing` module
- React: No TypeScript — JSDoc comments used sparingly
- Dataclasses in Python: All config uses `@dataclass` decorator with field factories
- MongoDB collections referenced as `db.collection_name` throughout
- Query operations use Motor async methods: `await db.collection.find_one()`, `await db.collection.insert_one()`
- Fields in documents use `snake_case`
## Code Style
- Python: Black formatter (configured in `requirements.txt`)
- React/Frontend: No explicit formatter configured, uses React Scripts defaults
- Line length: Implicit 88-char limit (Black default)
- Python: 
- React/Frontend:
- Python order (per isort):
- React order:
- React: `@/*` maps to `src/*` (defined in `jsconfig.json`)
- Backend: No path aliases, relative imports from project root
## Error Handling
- Use explicit exception catching: `except SpecificException as e:`
- Always log before re-raising: `logger.warning(f"Issue: {e}")` then `raise`
- For API routes: raise `HTTPException(status_code=xxx, detail="message")`
- Use try/finally blocks to ensure cleanup (especially for database connections)
- Log at appropriate levels: `logger.warning()` for recoverable issues, `logger.error()` for failures, `logger.critical()` for severe startup issues
- Use bare `catch { }` blocks (no error object) in async operations
- Catch errors in useEffect/useCallback but don't necessarily rethrow — often just set UI state (e.g., `setUser(null)`)
- No formal error boundaries detected — errors logged to browser console
## Logging
- Python: `logging` module (standard library)
- React: No formal logging library — uses `console` (with TODO for Sentry)
- Python: Logger initialized per-module: `logger = logging.getLogger(__name__)`
- Log critical startup info in `server.py` lifespan context manager: `logger.info("Starting ThookAI API...")`
- Use structured logging with f-strings: `logger.info(f"User {user_id} registered")`
- Security-sensitive data (passwords, tokens) NEVER logged
- All database operations log at DEBUG level or on error at WARNING level
## Comments
- Comment non-obvious logic: why something is done, not what is being done
- Document complex algorithms with docstrings
- Mark known issues with `# TODO:` or `# FIXME:` (searchable)
- Mark important assumptions with `# NOTE:` or `# IMPORTANT:`
- Python: Triple-quoted docstrings on functions and classes
- Multiline docstrings preferred for public APIs and services
- React: JSDoc-style comments rare; prefer clear code over comments
## Function Design
- Python: Aim for functions under 50 lines
- React components: Aim for under 100 lines (split larger components)
- Complex logic extracted to helper functions
- Python: Use type hints for all parameters
- Python: Pass configuration via `settings` singleton, not function arguments
- React: Props validated by usage (no PropTypes), optional props have defaults
- Use dataclasses (Python) or objects (React) for multiple related parameters
- Python functions should return typed values: `-> str`, `-> dict`, `-> List[str]`, `-> Optional[dict]`
- React components return JSX
- Async functions return the same types wrapped in a coroutine
- Database queries return `dict` or `None` (single) or `List[dict]` (multiple)
## Module Design
- Python modules export functions/classes at module level (no `__all__` required but ok to use)
- React components export as named exports: `export function Button() { }`
- Services in `backend/services/` export a class or set of functions as the API
- Not used in Python backend
- React UI components in `src/components/ui/` are individual files, not re-exported from index
## Config Pattern (Critical)
## Database Pattern (Critical)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Multi-agent AI pipeline for content generation (Commander → Scout → Thinker → Writer → QC)
- FastAPI backend with Motor async MongoDB driver and Celery task queue
- React frontend with client-side context-based auth and REST API consumption
- Service layer abstraction for external integrations (LLM, media storage, billing, vector embeddings)
- Middleware-based cross-cutting concerns (security, rate limiting, performance optimization)
## Layers
- Purpose: Render user interfaces and handle user interactions
- Location: `frontend/src/pages/`, `frontend/src/components/`
- Contains: React page components (Dashboard, Onboarding, ContentStudio), UI components (shadcn/ui), page-level logic
- Depends on: AuthContext for user state, API services for HTTP calls, custom hooks for data fetching
- Used by: End users through the browser
- Purpose: Manage application-level state, authentication, and client-side routing
- Location: `frontend/src/context/AuthContext.jsx`, `frontend/src/App.js`, `frontend/src/hooks/`
- Contains: AuthProvider (JWT + localStorage token management), custom hooks (useAuth, useAPI), React Router setup
- Depends on: FastAPI auth endpoints, localStorage for token persistence
- Used by: All pages and components for auth checks, user context, API access
- Purpose: Abstract HTTP communication with the backend
- Location: `frontend/src/lib/` (likely contains API client utilities)
- Contains: HTTP client configuration, request/response interceptors, endpoint helpers
- Depends on: REACT_APP_BACKEND_URL environment variable, AuthContext token
- Used by: All components that need to call backend endpoints
- Purpose: Handle incoming HTTP requests and orchestrate business logic
- Location: `backend/server.py`
- Contains: Application instantiation, middleware registration, route mounting, lifespan management (startup/shutdown)
- Depends on: All middleware, all routers, database connection, config validation
- Used by: Frontend clients, external webhooks, scheduled tasks
- Purpose: Handle HTTP endpoints for specific business domains
- Location: `backend/routes/*.py` (auth.py, content.py, persona.py, billing.py, agency.py, etc.)
- Contains: Request validation, response serialization, authorization checks, delegation to services/agents
- Depends on: get_current_user auth dependency, database, services, agents, Celery tasks
- Used by: FastAPI application through router registration in server.py
- Purpose: Orchestrate multi-stage AI content generation through specialized agents
- Location: `backend/agents/pipeline.py`, `backend/agents/*.py` (commander, scout, thinker, writer, qc, etc.)
- Contains: 
- Depends on: LLM clients, vector store, database, external media providers
- Used by: Content generation routes and background tasks
- Purpose: Encapsulate reusable business logic and external integrations
- Location: `backend/services/*.py`
- Contains:
- Depends on: Config settings, external APIs (LLM, Stripe, R2, Pinecone, etc.), database
- Used by: Routes, agents, tasks
- Purpose: Handle cross-cutting concerns for all HTTP requests/responses
- Location: `backend/middleware/security.py`, `backend/middleware/performance.py`
- Contains:
- Depends on: Redis (optional for rate limiting), Starlette middleware base
- Used by: FastAPI application, applied globally to all routes
- Purpose: Database access abstraction and connection pooling
- Location: `backend/database.py`, `backend/db_indexes.py`, `backend/auth_utils.py`
- Contains:
- Depends on: MongoDB (async Motor driver), config settings, FERNET_KEY for encryption
- Used by: All routes, services, agents for data persistence
- Purpose: Async background processing for long-running and scheduled operations
- Location: `backend/tasks/content_tasks.py`, `backend/tasks/media_tasks.py`, `backend/celery_app.py`
- Contains:
- Depends on: Redis (Celery broker), database, agents, services
- Used by: Routes for async job submission, triggered by Celery beat for scheduled tasks
- Purpose: Centralized environment-driven configuration
- Location: `backend/config.py`
- Contains: Dataclass-based config objects (DatabaseConfig, SecurityConfig, LLMConfig, R2Config, StripeConfig, etc.)
- Depends on: Environment variables from .env
- Used by: All modules that need config (imports `from config import settings`)
## Data Flow
- **Frontend state:** User auth via AuthContext (JWT token in localStorage)
- **Backend session state:** JWT claims contain user_id, derived from `get_current_user()` dependency
- **Job state:** Stored in MongoDB (content_jobs collection) with status progression: pending → processing → reviewing → approved → scheduled/published
- **Persona state:** Stored in MongoDB (persona_engines collection), immutable until user explicitly creates new version
- **Credit state:** Stored in MongoDB (users.credits), updated transactionally on content generation
- **Scheduled posts state:** Stored in MongoDB (scheduled_posts collection), polled by Celery beat task
## Key Abstractions
- Purpose: Unified abstraction over multiple LLM providers (Anthropic, OpenAI, Gemini)
- Examples: `backend/services/llm_client.py`, used in all agent files
- Pattern: Constructor takes provider key, provider name, model name; provides `async generate()` method for streaming or full responses
- Purpose: Represents a single content generation request through its lifecycle
- Examples: Saved to and queried from `db.content_jobs`
- Pattern: Contains job_id, user_id, platform, status, draft, final_content, edited_content, performance_data, created_at, updated_at
- Purpose: Represents a user's voice fingerprint and content identity
- Examples: Saved to and queried from `db.persona_engines`
- Pattern: Contains user_id, card (persona descriptors), voice_fingerprint, content_identity, performance_intelligence, learning_signals, uom (Unit of Measure for success)
- Purpose: Standardize agent function signatures for pipeline composition
- Pattern: All agents export async function like `async def run_agent(input_data, context) -> dict`
- Examples: run_commander, run_scout, run_thinker, run_writer, run_qc in `backend/agents/*.py`
- Purpose: Uniform interface to external APIs (Stripe, R2, Pinecone, Resend)
- Pattern: Service classes initialize with config, expose async methods for operations
- Examples: StripeService.create_checkout_session(), R2Storage.upload(), PineconeVectorStore.store_embedding()
- Purpose: Composable request/response filtering
- Pattern: Each middleware inherits BaseHTTPMiddleware, implements dispatch() async method
- Examples: SecurityHeadersMiddleware, RateLimitMiddleware in `backend/middleware/`
## Entry Points
- Location: `backend/server.py` (main function, lifespan context manager)
- Triggers: `uvicorn server:app` from Procfile
- Responsibilities:
- Location: `backend/routes/content.py:create_content()` endpoint
- Triggers: `POST /api/content/create` from frontend
- Responsibilities:
- Location: Worker processes (defined in `backend/celery_app.py`)
- Triggers: Celery Beat scheduler (cron-based) or explicit task.delay() calls
- Responsibilities:
- Location: `frontend/src/App.js` (main component)
- Triggers: Browser navigation to frontend URL
- Responsibilities:
- Location: `frontend/src/context/AuthContext.jsx`
- Triggers: App mount, manual login, Google OAuth callback
- Responsibilities:
## Error Handling
- Catch request validation errors: Return `422 Unprocessable Entity` with field errors
- Catch auth errors: Return `401 Unauthorized` if no token or token invalid
- Catch permission errors: Return `403 Forbidden` if user lacks required role/workspace access
- Catch not-found errors: Return `404 Not Found` if resource doesn't exist
- Catch credit errors: Return `402 Payment Required` if insufficient credits
- Catch Stripe errors: Return `402 Payment Required` with specific error message
- Generic server errors: Return `500 Internal Server Error`, log full traceback with Sentry
- LLM API failures: Log error, return default/fallback response (e.g., mock persona in onboarding)
- Database failures: Raise exception caught by route handler, return `500`
- External API timeouts (Perplexity, R2, Stripe): Log, return partial data or skip enrichment
- Request too large: RateLimitMiddleware returns `429 Too Many Requests`
- Invalid JSON: InputValidationMiddleware returns `400 Bad Request`
- Missing security headers: SecurityHeadersMiddleware still returns OK but logs warning
- API call fails: useAPI hook catches error, sets error state, displays toast notification
- Auth token invalid: AuthContext logs user out, redirects to /auth
- Network timeout: Show retry button or "offline" message
- Form validation: Show field-level errors, disable submit until fixed
- Sentry DSN configured in server.py if `SENTRY_DSN` env var set
- Logs written to stdout with timestamp, level, module name, message
- Database errors logged to database error collection (if configured)
## Cross-Cutting Concerns
- Approach: Python logging module configured in `backend/server.py` with standard format
- Pattern: `logger = logging.getLogger(__name__)` at module level, log at appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Front-end: Browser console logging via window.console, no centralized logging yet
- Backend: Pydantic BaseModel for request validation (declared in route handler), custom validators for complex rules (password policy, credit sufficiency)
- Frontend: React Hook Form for form validation, client-side checks before submission
- Backend: JWT tokens (HS256 algorithm, configurable expiry days), validated by `get_current_user()` dependency in all protected routes
- Token payload: Contains user_id, issued_at, expiry
- Token storage: Frontend localStorage, passed as `Authorization: Bearer <token>` header
- Refresh: No refresh token flow yet; token expires based on JWT_EXPIRE_DAYS config
- Backend: Role-based checks (admin, user, workspace_member) in route handlers
- Workspace context: Some routes check user is member of workspace and has appropriate role
- API key checks: Some routes (webhooks) verify Stripe webhook signature
- Backend: Middleware-level compression (gzip), response caching headers
- Frontend: Code splitting by route, lazy loading of Dashboard components
- Database: MongoDB indexes created at startup (db_indexes.py)
- Connection pooling: Motor async client configured with minPoolSize=10, maxPoolSize=100
- Rate limiting: Configurable per-minute limits (RATE_LIMIT_PER_MINUTE=60, auth-specific lower limit)
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
