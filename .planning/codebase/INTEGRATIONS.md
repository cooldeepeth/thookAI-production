# External Integrations

**Analysis Date:** 2026-03-31

## APIs & External Services

**LLM / AI Generation:**
- Anthropic Claude (primary) - Content generation
  - SDK/Client: `anthropic 0.34.0`
  - Auth: `ANTHROPIC_API_KEY` (format: `sk-ant-*`)
  - Model: `claude-sonnet-4-20250514` (primary, per CLAUDE.md)
  - Usage: `backend/services/llm_client.py`, `backend/agents/writer.py`
  
- OpenAI (fallback) - Text completion, embeddings, image generation
  - SDK/Client: `openai 1.40.0`
  - Auth: `OPENAI_API_KEY` (format: `sk-*`)
  - Usage: `backend/services/llm_client.py`, embeddings in `backend/services/vector_store.py`
  
- Google Gemini (optional) - Alternative text generation
  - SDK/Client: `google-generativeai 0.8.0`
  - Auth: `GEMINI_API_KEY`
  - Usage: `backend/services/llm_client.py`

- Perplexity API - Research/web search for Scout agent
  - Auth: `PERPLEXITY_API_KEY` (format: `pplx-*`)
  - Usage: `backend/agents/scout.py`, `backend/routes/dashboard.py`
  - Endpoint: `https://api.perplexity.ai/chat/completions`

**Image Generation:**
- FAL.ai (FLUX, SDXL Lightning)
  - SDK/Client: `fal-client 0.10.0`
  - Auth: `FAL_KEY`
  - Usage: `backend/agents/designer.py`, `backend/services/creative_providers.py`

**Video Generation:**
- Luma Dream Machine
  - SDK/Client: `lumaai 1.0.0`
  - Auth: `LUMA_API_KEY`
  - Usage: `backend/agents/video.py`, `backend/services/creative_providers.py`

- Kling AI
  - Auth: `KLING_API_KEY`
  - Usage: `backend/agents/video.py`

- Runway
  - Auth: `RUNWAY_API_KEY`
  - Usage: `backend/agents/video.py`

- HeyGen
  - Auth: `HEYGEN_API_KEY`
  - Usage: `backend/agents/video.py` (avatar creation)

- D-ID
  - Auth: `DID_API_KEY`
  - Usage: `backend/agents/video.py`

**Voice / TTS Generation:**
- ElevenLabs (primary TTS)
  - SDK/Client: `elevenlabs 1.50.0`
  - Auth: `ELEVENLABS_API_KEY`
  - Usage: `backend/agents/voice.py`, `backend/services/creative_providers.py`

- Play.ht (alternative TTS)
  - Auth: `PLAYHT_API_KEY`, `PLAYHT_USER_ID`
  - Usage: `backend/services/creative_providers.py`

- Google Cloud Text-to-Speech
  - Auth: `GOOGLE_TTS_API_KEY`
  - Usage: `backend/services/creative_providers.py`

## Data Storage

**Databases:**
- MongoDB 7.0+
  - Connection: `MONGO_URL` (default: `mongodb://localhost:27017`)
  - Client: Motor (async) via `from database import db`
  - Collections: users, persona_engines, content_jobs, scheduled_posts, platform_tokens, workspaces, workspace_members, templates, media_assets, uploads, password_reset_tokens, persona_shares
  - See `backend/db_indexes.py` for auto-created indexes at startup

**File Storage:**
- Cloudflare R2 (S3-compatible object storage)
  - Endpoint: `https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com`
  - Client: boto3 (configured in `backend/services/media_storage.py`)
  - Credentials: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`
  - Supported file types: video (500MB), audio (25MB), image (20MB), document (50MB)
  - Fallback: None (explicit 503 error if R2 not configured, per BUG-7)
  - Usage: `backend/routes/uploads.py`, `backend/services/media_storage.py`

**Caching / Task Queue:**
- Redis 7+
  - Connection: `REDIS_URL` (default: `redis://localhost:6379/0`)
  - Purpose: Celery message broker and result backend
  - Config: Separate brokers/backends via `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`
  - Usage: `backend/celery_app.py`, all scheduled tasks in `backend/tasks/`

**Vector Database:**
- Pinecone (vector embeddings for persona learning)
  - API Key: `PINECONE_API_KEY`
  - Index: `PINECONE_INDEX_NAME` (default: `thookai-personas`)
  - Dimension: 1536 (OpenAI text-embedding-3-small)
  - Usage: `backend/services/vector_store.py`, embeddings generated via OpenAI API
  - Status: Implemented but not wired into generation pipeline (BUG-6)

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based
  - Implementation: `backend/auth_utils.py`
  - Secrets: `JWT_SECRET_KEY` (HS256 algorithm), `JWT_EXPIRE_DAYS` (default: 7)
  - Token encryption: `FERNET_KEY` for sensitive token data
  - Dependency: `get_current_user` in `backend/auth_utils.py`

**OAuth Integrations:**
- Google OAuth 2.0
  - SDK: `authlib 1.3.2`
  - Credentials: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
  - Redirect URI: `{BACKEND_URL}/api/auth/google/callback`
  - Implementation: `backend/routes/auth_google.py`
  - Usage: User registration/login via Google

- LinkedIn OAuth (user-facing, not implemented in code yet)
  - Auth: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`
  - Purpose: Connect user's LinkedIn account for publishing
  - Implementation placeholder: `backend/routes/platforms.py`

- Meta/Instagram OAuth (user-facing)
  - Auth: `META_APP_ID`, `META_APP_SECRET`
  - Purpose: Instagram publishing
  - Implementation placeholder: `backend/routes/platforms.py`

- Twitter/X OAuth (user-facing)
  - Auth: `TWITTER_API_KEY`, `TWITTER_API_SECRET`
  - Purpose: Twitter/X publishing
  - Implementation placeholder: `backend/routes/platforms.py`

## Monitoring & Observability

**Error Tracking:**
- Sentry (optional)
  - SDK: `sentry-sdk 2.0.0+` with FastAPI integration
  - Config: `SENTRY_DSN` (optional, no-op if not set)
  - Initialized in `backend/server.py` lifespan if `sentry_dsn` present
  - Sample rate: 0.1 in production, 1.0 in development

**Logs:**
- Approach: Python `logging` module with configurable level via `LOG_LEVEL` (default: INFO)
- Formatted: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Stdout to container/platform logs (no file persistence)
- Celery worker logs go to stdout with `--loglevel=info`

## CI/CD & Deployment

**Hosting:**
- Backend: Render, Railway, or Heroku (supports Procfile with Python 3.11 buildpack)
- Frontend: Vercel (deployed from `frontend/` directory)
- Database: MongoDB Atlas
- Cache: Redis Cloud or AWS ElastiCache

**CI Pipeline:**
- GitHub Actions (.github/workflows - present but not inspected)
- No explicit CI configuration in provided files
- Manual testing: `cd backend && pytest` for Python tests

**Deployment Configuration:**
- Backend: `backend/Procfile` defines three processes:
  - `web: uvicorn server:app --host 0.0.0.0 --port $PORT`
  - `worker: celery -A celery_app:celery_app worker --loglevel=info --concurrency=2 -Q default,media,content,video`
  - `beat: celery -A celery_app:celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler`
- Frontend: `frontend/vercel.json` for Vercel SPA routing
- Docker: `docker-compose.yml` for local development with MongoDB, Redis, Celery worker, and Celery beat services

## Environment Configuration

**Required env vars for full functionality:**

*Core:*
- `MONGO_URL` - MongoDB connection string
- `DB_NAME` - Database name (default: `thook_database`)
- `JWT_SECRET_KEY` - Minimum 32 chars, used for access token signing
- `FERNET_KEY` - Generated via `cryptography.fernet.Fernet.generate_key()`

*LLM (at least one required):*
- `ANTHROPIC_API_KEY` - Primary LLM (format: `sk-ant-*`)
- `OPENAI_API_KEY` - Fallback LLM (format: `sk-*`)
- `PERPLEXITY_API_KEY` - Scout agent research (format: `pplx-*`)

*Media Storage (required in production):*
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`

*Task Queue (required for scheduled posts, daily limits):*
- `REDIS_URL` - Redis connection (default: `redis://localhost:6379/0`)
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (can be same as REDIS_URL)

*Email (required for password reset + agency invites):*
- `RESEND_API_KEY` - Resend API key
- `FROM_EMAIL` - Sender email address (default: `noreply@thookai.com`)
- `FRONTEND_URL` - Frontend base URL for reset/invite links

*Billing (required for paid plans):*
- `STRIPE_SECRET_KEY` - Stripe API key (format: `sk_test_*` or `sk_live_*`)
- `STRIPE_WEBHOOK_SECRET` - Webhook signing key
- `STRIPE_PRICE_*` - All tier and credit price IDs (currently empty, blocking checkout)

*OAuth:*
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - Google OAuth
- `BACKEND_URL` - Redirect URI base (default: `http://localhost:8001`)

*Optional:*
- `SENTRY_DSN` - Error tracking (optional)
- `GEMINI_API_KEY` - Google Gemini (optional)
- `FAL_KEY`, `LUMA_API_KEY`, `ELEVENLABS_API_KEY` - Creative providers (optional/feature-gated)
- `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` - Vector store (optional, not wired)

**Secrets location:**
- `.env` file at `backend/.env` (gitignored, loaded via `python-dotenv`)
- Production: Managed by deployment platform (Render/Railway env vars, or .env file in container)
- Never commit `.env` to git; use `.env.example` as template

## Webhooks & Callbacks

**Incoming:**
- Stripe webhooks
  - Endpoint: `/api/billing/webhook` (implementation in `backend/routes/billing.py`)
  - Secret: `STRIPE_WEBHOOK_SECRET` (for signature verification)
  - Events: Payment success, subscription updates, refunds
  - Status: Webhook signature verification fails if secret not set (BUG-8)

**Outgoing:**
- None implemented yet
- Planned: `backend/services/webhook_service.py` exists but unused (see roadmap in CLAUDE.md)
- Future: Zapier/custom webhook firing on job completion events

## Integration Status Summary

| System | Status | Blocker | Notes |
|--------|--------|---------|-------|
| Anthropic Claude | Implemented | None | Primary LLM, uses model claude-sonnet-4-20250514 |
| OpenAI | Implemented | None | Fallback LLM, embeddings |
| Perplexity | Implemented | None | Scout agent research |
| Stripe | Implemented | BUG-8 | Price IDs empty, webhook secret needed |
| Resend | Implemented | None | Password reset, workspace invites |
| Cloudflare R2 | Implemented | None | Media storage, falls back to /tmp if unconfigured |
| MongoDB | Implemented | None | Primary data store, async via Motor |
| Redis | Implemented | Celery config | Task queue, scheduler |
| Google OAuth | Implemented | None | User auth |
| FAL.ai | Implemented | Config | Image generation |
| Luma | Implemented | Config | Video generation |
| ElevenLabs | Implemented | Config | Voice/TTS |
| Pinecone | Implemented | BUG-6 | Vector store not called from writer/learning |
| LinkedIn OAuth | Stub only | Full impl | Publishing integration incomplete |
| Meta OAuth | Stub only | Full impl | Instagram publishing incomplete |
| Twitter OAuth | Stub only | Full impl | X publishing incomplete |
| Social Analytics | Not implemented | Not applicable | Post performance polling missing |
| Email (general) | Stub only | Full impl | Only password reset implemented |
| Notifications | Stub only | Full impl | SSE endpoint missing |

---

*Integration audit: 2026-03-31*
