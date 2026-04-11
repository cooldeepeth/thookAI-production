# ThookAI Production Deployment Guide

> Deploy ThookAI to production on thook.ai
> Backend: Railway | Frontend: Vercel | DB: MongoDB Atlas | Cache: Redis Cloud | Media: Cloudflare R2

---

## Prerequisites Checklist

Before starting, confirm you have:

- [ ] thook.ai domain with DNS access
- [ ] GitHub repo: github.com/cooldeepeth/thookAI-production
- [ ] MongoDB Atlas cluster (M10+ recommended for production)
- [ ] Redis Cloud or Upstash instance
- [ ] Cloudflare R2 bucket created
- [ ] Stripe account with products and prices created
- [ ] At least one LLM API key (Anthropic recommended)
- [ ] Railway account (railway.app)
- [ ] Vercel account (vercel.com)

---

## Step 1: Generate Security Keys

Run these locally ONCE. Save the output securely (password manager, not plaintext):

```bash
# JWT Secret (64+ chars)
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Fernet Key (for encryption)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Encryption Key (for OAuth token storage — separate from Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# n8n Webhook Secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# n8n Encryption Key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 2: Create Stripe Products & Prices

In your Stripe Dashboard (test mode first, then switch to live):

### Credit Packages (one-time payments)
1. Create Product: "100 Credits" → Create Price: $6.00 one-time → copy `price_xxx`
2. Create Product: "500 Credits" → Create Price: $25.00 one-time → copy `price_xxx`
3. Create Product: "1000 Credits" → Create Price: $40.00 one-time → copy `price_xxx`

### Subscription Plans (if using legacy tier pricing)
4. "Pro Monthly" → $29/mo recurring → copy `price_xxx`
5. "Pro Annual" → $290/yr recurring → copy `price_xxx`
6. "Studio Monthly" → $79/mo → copy `price_xxx`
7. "Studio Annual" → $790/yr → copy `price_xxx`
8. "Agency Monthly" → $199/mo → copy `price_xxx`
9. "Agency Annual" → $1990/yr → copy `price_xxx`

Note: ThookAI v2.0 uses a custom plan builder with dynamic pricing. The fixed-tier prices are fallback/legacy. The plan builder uses `price_data` for dynamic Stripe prices.

### Webhook Endpoint
10. Go to Stripe Dashboard → Developers → Webhooks
11. Add endpoint: `https://api.thook.ai/api/billing/webhook/stripe`
12. Select events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`
13. Copy the Webhook Signing Secret (`whsec_xxx`)

---

## Step 3: Deploy Backend on Railway

### 3a. Create Railway Project

1. Go to railway.app → New Project → Deploy from GitHub Repo
2. Select `cooldeepeth/thookAI-production`
3. Railway auto-detects the Dockerfile in `backend/`
4. Set the **Root Directory** to `backend/`

### 3b. Configure Railway Services

You need **3 services** in Railway:

**Service 1: Web (FastAPI API)**
- Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`
- Generate Domain: `thookai-api-production.up.railway.app` (temporary)

**Service 2: Worker (Celery)**
- Start Command: `celery -A celery_app:celery_app worker --loglevel=info --concurrency=2 -Q default,media,content,video`
- No port needed (background process)

**Service 3: n8n (Workflow Orchestration)**
- Docker Image: `n8nio/n8n:stable`
- Port: 5678
- Note: We'll configure this in Step 6

### 3c. Set ALL Environment Variables

In Railway → Web Service → Variables, set:

```env
# === CORE (REQUIRED) ===
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# === DATABASE ===
MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
DB_NAME=thook_production

# === SECURITY ===
JWT_SECRET_KEY=<your-64-char-key-from-step-1>
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7
FERNET_KEY=<your-fernet-key-from-step-1>
ENCRYPTION_KEY=<your-encryption-key-from-step-1>

# === CORS (CRITICAL — no wildcards) ===
CORS_ORIGINS=https://thook.ai,https://www.thook.ai,https://api.thook.ai

# === RATE LIMITING ===
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_AUTH_PER_MINUTE=10

# === REDIS ===
REDIS_URL=redis://default:<password>@<host>:<port>
CELERY_BROKER_URL=redis://default:<password>@<host>:<port>/0
CELERY_RESULT_BACKEND=redis://default:<password>@<host>:<port>/1

# === LLM PROVIDERS (at least one required) ===
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
PERPLEXITY_API_KEY=pplx-xxx

# === MEDIA STORAGE (Cloudflare R2) ===
R2_ACCOUNT_ID=<your-account-id>
R2_ACCESS_KEY_ID=<your-access-key>
R2_SECRET_ACCESS_KEY=<your-secret-key>
R2_BUCKET_NAME=thookai-media
R2_PUBLIC_URL=https://pub-xxx.r2.dev

# === STRIPE BILLING ===
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_CREDITS_100=price_xxx
STRIPE_PRICE_CREDITS_500=price_xxx
STRIPE_PRICE_CREDITS_1000=price_xxx
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_ANNUAL=price_xxx
STRIPE_PRICE_STUDIO_MONTHLY=price_xxx
STRIPE_PRICE_STUDIO_ANNUAL=price_xxx
STRIPE_PRICE_AGENCY_MONTHLY=price_xxx
STRIPE_PRICE_AGENCY_ANNUAL=price_xxx

# === GOOGLE OAUTH ===
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
BACKEND_URL=https://api.thook.ai

# === SOCIAL PLATFORM OAUTH ===
LINKEDIN_CLIENT_ID=xxx
LINKEDIN_CLIENT_SECRET=xxx
META_APP_ID=xxx
META_APP_SECRET=xxx
TWITTER_API_KEY=xxx
TWITTER_API_SECRET=xxx

# === EMAIL ===
RESEND_API_KEY=re_xxx
FROM_EMAIL=noreply@thook.ai

# === URLS ===
FRONTEND_URL=https://thook.ai
BACKEND_URL=https://api.thook.ai

# === MONITORING ===
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# === n8n ORCHESTRATION ===
N8N_URL=http://<n8n-railway-internal-url>:5678
N8N_WEBHOOK_SECRET=<your-n8n-webhook-secret-from-step-1>
N8N_API_KEY=<generate-in-n8n-ui>
N8N_BACKEND_CALLBACK_URL=https://api.thook.ai

# === VECTOR DB ===
PINECONE_API_KEY=xxx
PINECONE_INDEX_NAME=thookai-personas
PINECONE_ENVIRONMENT=us-east-1

# === MEDIA GENERATION (optional — feature-gated) ===
FAL_KEY=xxx
LUMA_API_KEY=xxx
ELEVENLABS_API_KEY=xxx
HEYGEN_API_KEY=xxx

# === LIGHTRAG (if deploying knowledge graph) ===
LIGHTRAG_URL=http://<lightrag-railway-internal-url>:9621
LIGHTRAG_EMBEDDING_MODEL=text-embedding-3-small
LIGHTRAG_EMBEDDING_DIM=1536
```

### 3d. Custom Domain for Backend

1. Railway → Web Service → Settings → Custom Domain
2. Add: `api.thook.ai`
3. Railway gives you a CNAME target (e.g., `xxx.up.railway.app`)
4. In your DNS (Cloudflare/registrar): add CNAME record `api` → `xxx.up.railway.app`
5. Railway auto-provisions SSL certificate

---

## Step 4: Deploy Frontend on Vercel

### 4a. Import Project

1. Go to vercel.com → New Project → Import Git Repository
2. Select `cooldeepeth/thookAI-production`
3. Set **Root Directory** to `frontend/`
4. Framework Preset: Create React App
5. Build Command: `npm run build` (vercel.json overrides this)
6. Output Directory: `build`

### 4b. Set Environment Variables

```env
REACT_APP_BACKEND_URL=https://api.thook.ai
```

That's it for the frontend. All configuration comes from the backend via API calls.

### 4c. Custom Domain for Frontend

1. Vercel → Project → Settings → Domains
2. Add: `thook.ai` and `www.thook.ai`
3. Vercel gives you A/AAAA records or CNAME
4. In your DNS: add the records Vercel provides
5. Vercel auto-provisions SSL

---

## Step 5: DNS Configuration

In your domain registrar or Cloudflare DNS:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | `api` | `xxx.up.railway.app` (from Railway) | Auto |
| A | `@` (root) | Vercel IP (76.76.21.21) | Auto |
| CNAME | `www` | `cname.vercel-dns.com` | Auto |

If using Cloudflare:
- Proxy status: DNS only (not proxied) for `api` — Railway handles SSL
- Proxy status: DNS only for root/www — Vercel handles SSL

---

## Step 6: Deploy n8n on Railway

### 6a. Create n8n Service

1. Railway → New Service → Docker Image
2. Image: `n8nio/n8n:stable`
3. Port: 5678

### 6b. n8n Environment Variables

```env
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=<postgres-host>
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=<password>

EXECUTIONS_MODE=queue
QUEUE_BULL_REDIS_HOST=<redis-host>
QUEUE_BULL_REDIS_PORT=<redis-port>
QUEUE_BULL_REDIS_PASSWORD=<redis-password>

N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<strong-password>

N8N_BLOCK_ENV_ACCESS_IN_NODE=true
EXECUTIONS_DATA_MAX_AGE=336

WEBHOOK_URL=https://n8n.thook.ai
N8N_ENCRYPTION_KEY=<from-step-1>
```

### 6c. Configure n8n Workflows

After n8n is running:
1. Access n8n UI (Railway public URL or via tunnel)
2. Import workflow JSON templates from `backend/n8n-workflows/` if they exist
3. Create 10 scheduled workflows matching the N8N_WORKFLOW_* IDs in your backend env:
   - `process-scheduled-posts` (every 1 min)
   - `reset-daily-limits` (midnight UTC)
   - `refresh-monthly-credits` (daily check)
   - `cleanup-old-jobs` (daily)
   - `cleanup-expired-shares` (daily)
   - `aggregate-daily-analytics` (2am UTC)
   - `cleanup-stale-jobs` (every 15 min)
   - `run-nightly-strategist` (3am UTC)
   - `poll-analytics-24h` (hourly)
   - `poll-analytics-7d` (daily)
4. Each workflow: HTTP Request node → POST `https://api.thook.ai/api/n8n/execute/{task-name}`
5. Set X-ThookAI-Signature header with HMAC-SHA256 of request body using N8N_WEBHOOK_SECRET
6. Copy workflow IDs to backend env vars

---

## Step 7: Deploy LightRAG (Optional — Knowledge Graph)

### Option A: Railway Service

1. New Service → Docker Image: `ghcr.io/hkuds/lightrag:latest`
2. Set env vars:
```env
OPENAI_API_KEY=<your-openai-key>
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```
3. Internal URL becomes your LIGHTRAG_URL

### Option B: Skip for Launch

LightRAG is non-fatal — if LIGHTRAG_URL is not set, the system gracefully degrades. The Thinker agent works without knowledge graph data. You can add this post-launch.

---

## Step 8: Deploy Remotion Service (Optional — Video)

### Option A: Railway Service

1. New Service → Deploy from GitHub repo, root directory: `remotion-service/`
2. Set env vars: R2 credentials + REMOTION_LICENSE_KEY (if you have one)
3. Internal URL becomes your REMOTION_SERVICE_URL

### Option B: Skip for Launch

Remotion is feature-gated. If not configured, video generation simply isn't available. Text + image content still works fully.

---

## Step 9: Post-Deployment Verification

### 9a. Health Check

```bash
curl https://api.thook.ai/health
```

Expected response:
```json
{"status": "healthy", "services": {"mongo": "ok", "redis": "ok", ...}}
```

### 9b. API Smoke Test

```bash
# Register a test user
curl -X POST https://api.thook.ai/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@thook.ai", "password": "TestPass123!"}'

# Login
curl -X POST https://api.thook.ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@thook.ai", "password": "TestPass123!"}'
# Copy the token from response

# Check auth
curl https://api.thook.ai/api/auth/me \
  -H "Authorization: Bearer <token>"

# Check billing config (public)
curl https://api.thook.ai/api/billing/config
```

### 9c. Frontend Verification

1. Open https://thook.ai in browser
2. Register a new account
3. Complete onboarding (3 phases)
4. Generate content (verify pipeline works)
5. Check billing page (Stripe checkout redirect works)
6. Connect a social platform (OAuth flow works)

### 9d. Stripe Webhook Test

1. Stripe Dashboard → Webhooks → Send test event
2. Send `checkout.session.completed`
3. Verify backend logs show successful processing
4. Check MongoDB: `db.stripe_events` has the event ID (idempotency working)

### 9e. n8n Verification

1. Check n8n UI — all workflows active
2. Trigger a test: POST to `/api/n8n/execute/cleanup-stale-jobs`
3. Verify callback received by backend (check logs)

---

## Step 10: Pre-Launch Testing Strategy

### Stage 1: Private Alpha (You Only) — 1-2 Days

1. Create your real account on thook.ai
2. Complete full onboarding
3. Generate 10+ pieces of content across all platforms
4. Test ALL billing flows with Stripe test keys:
   - Credit purchase (all 3 packages)
   - Custom plan builder (try different credit combos)
   - Plan modification (upgrade/downgrade)
   - Cancellation
5. Connect LinkedIn (real OAuth)
6. Schedule a post → verify it publishes
7. Check analytics after 24h → verify real metrics poll
8. Test strategy recommendations (wait for nightly run or trigger manually)
9. Test error states: disconnect platform, exhaust credits, generate with bad input

### Stage 2: Stripe Live Mode Switch — 30 Minutes

1. Stripe Dashboard → switch from Test to Live mode
2. Update ALL Stripe env vars in Railway:
   - `STRIPE_SECRET_KEY` → `sk_live_xxx`
   - `STRIPE_PUBLISHABLE_KEY` → `pk_live_xxx`
   - `STRIPE_WEBHOOK_SECRET` → new live webhook signing secret
   - All `STRIPE_PRICE_*` → live price IDs (recreate products in live mode)
3. Register a new webhook endpoint (live mode has separate endpoints)
4. Test with a real $6 credit purchase (refund immediately after)
5. Verify webhook fires and credits are added

### Stage 3: Closed Beta (5-10 Trusted Users) — 1 Week

1. Invite 5-10 friends/colleagues
2. Monitor Sentry for errors in real-time
3. Watch Railway logs for any 500 errors
4. Check MongoDB for data integrity:
   ```
   db.users.countDocuments()
   db.content_jobs.countDocuments({status: "error"})
   db.credit_transactions.countDocuments()
   ```
5. Monitor Redis memory usage (should stay stable)
6. Track API response times in Railway metrics

### Stage 4: Public Soft Launch

1. Announce on LinkedIn/X with your personal account
2. Monitor metrics for first 48 hours
3. Set up Railway alerting for CPU > 80%, memory > 80%
4. Have rollback ready: Railway supports instant rollbacks to previous deploy

---

## Complete API Credential Checklist

Every external API ThookAI integrates with, grouped by criticality:

### Tier 1: Required for Basic Functionality
| Service | API Key Env Var | Dashboard URL | What It Does |
|---------|----------------|---------------|--------------|
| MongoDB Atlas | `MONGO_URL` | cloud.mongodb.com | All data storage |
| Redis Cloud | `REDIS_URL` | app.redislabs.com | Cache, rate limits, Celery broker |
| Anthropic | `ANTHROPIC_API_KEY` | console.anthropic.com | Primary LLM (content generation) |
| Stripe | `STRIPE_SECRET_KEY` + 9 more | dashboard.stripe.com | Payments, subscriptions |

### Tier 2: Required for Core Features
| Service | API Key Env Var | Dashboard URL | What It Does |
|---------|----------------|---------------|--------------|
| Cloudflare R2 | `R2_ACCOUNT_ID` + 4 more | dash.cloudflare.com | Media file storage |
| Google OAuth | `GOOGLE_CLIENT_ID/SECRET` | console.cloud.google.com | Social login |
| Resend | `RESEND_API_KEY` | resend.com/emails | Password reset emails |
| Sentry | `SENTRY_DSN` | sentry.io | Error tracking |
| OpenAI | `OPENAI_API_KEY` | platform.openai.com | LLM fallback + LightRAG embeddings |

### Tier 3: Required for Social Publishing
| Service | API Key Env Var | Dashboard URL | What It Does |
|---------|----------------|---------------|--------------|
| LinkedIn | `LINKEDIN_CLIENT_ID/SECRET` | linkedin.com/developers | Post to LinkedIn |
| Meta/Instagram | `META_APP_ID/SECRET` | developers.facebook.com | Post to Instagram |
| X/Twitter | `TWITTER_API_KEY/SECRET` | developer.twitter.com | Post to X |
| Perplexity | `PERPLEXITY_API_KEY` | perplexity.ai | Scout agent research |

### Tier 4: Optional Premium Features
| Service | API Key Env Var | Dashboard URL | What It Does |
|---------|----------------|---------------|--------------|
| fal.ai | `FAL_KEY` | fal.ai/dashboard | Image generation |
| ElevenLabs | `ELEVENLABS_API_KEY` | elevenlabs.io | Voice cloning/TTS |
| Luma AI | `LUMA_API_KEY` | lumalabs.ai | Video generation |
| HeyGen | `HEYGEN_API_KEY` | heygen.com | Avatar videos |
| Pinecone | `PINECONE_API_KEY` | app.pinecone.io | Vector similarity search |

### Tier 5: Self-Hosted Services (Railway)
| Service | Config | What It Does |
|---------|--------|--------------|
| n8n | `N8N_URL` + workflow IDs | Scheduled tasks, publishing, analytics |
| LightRAG | `LIGHTRAG_URL` | Knowledge graph for content intelligence |
| Remotion | `REMOTION_SERVICE_URL` | Video composition/rendering |

---

## Things to Be Cautious About

### Security
- **NEVER commit .env files** — they contain all your secrets
- **Rotate JWT_SECRET_KEY** if you suspect it was exposed — all existing tokens become invalid
- **FERNET_KEY and ENCRYPTION_KEY** — if lost, ALL encrypted OAuth tokens become unreadable. Back these up securely.
- **Stripe webhook secret** — if wrong, all payment events silently fail. Test with Stripe CLI first.
- **CORS_ORIGINS** — must be exact domain list, NO wildcards in production

### Data
- **MongoDB Atlas**: Enable M10+ cluster for production. M0 (free) has 500MB limit and no backups.
- **Backup strategy**: Atlas continuous backup + point-in-time recovery. Test restore before launch.
- **LightRAG embedding model is FROZEN** — if you change it, you must rebuild the entire index

### Billing
- **Test with Stripe test keys first** — always. Never test billing with live keys.
- **Webhook idempotency** — ThookAI deduplicates by event_id. If you replay webhooks, they're safely skipped.
- **Credit refunds** — if a user requests refund, you must manually add credits back via MongoDB or admin endpoint

### Monitoring
- **Sentry** — set it up before launch, not after. First real user error = you get notified instantly.
- **Railway logs** — check daily for first week. Look for 500 errors, slow requests (>2s), Redis connection issues.
- **MongoDB Atlas Performance Advisor** — enable it. Shows slow queries that need indexes.

### Scaling
- **Railway**: Start with 1 web instance + 1 worker. Scale horizontally if response times increase.
- **MongoDB Atlas**: Auto-scaling available on M10+. Watch for connection pool exhaustion (currently max 100).
- **Redis**: Watch memory usage. Rate limit data + Celery tasks accumulate. Set maxmemory-policy.

---

## Rollback Plan

If something goes wrong after launch:

1. **Railway**: Instant rollback to previous deployment (1 click in dashboard)
2. **Vercel**: Instant rollback to previous deployment
3. **Database**: MongoDB Atlas point-in-time recovery (if data corruption)
4. **Stripe**: Refund any charges via Stripe dashboard
5. **n8n**: Disable all workflows to stop automated publishing

---

## Post-Launch Monitoring Checklist (First 48 Hours)

- [ ] Check Sentry — any new errors?
- [ ] Check Railway metrics — CPU/memory within limits?
- [ ] Check MongoDB Atlas — connection count normal? Slow queries?
- [ ] Check Redis — memory stable? No OOM?
- [ ] Check Stripe webhooks — all events processed? Any failures?
- [ ] Check n8n — all workflows executing? Any failures?
- [ ] Test a content generation as a real user
- [ ] Verify a scheduled post actually published
- [ ] Check analytics polling worked (24h after first publish)
- [ ] Verify credit deduction is accurate
- [ ] Test Google OAuth login
- [ ] Verify frontend loads < 3 seconds
