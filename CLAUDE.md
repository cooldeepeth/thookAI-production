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

## 10. PR Checklist (include in every PR description)

- [ ] Branch targets `dev`, not `main`
- [ ] No secrets or API keys in code
- [ ] `requirements.txt` updated if new packages added
- [ ] No new `os.environ.get()` calls — used `settings.*` instead
- [ ] Tested locally with `uvicorn server:app --reload` from `backend/`
- [ ] Pipeline smoke test passed (if agent files modified)
- [ ] Described what was broken and how it is now fixed