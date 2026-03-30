# ThookAI Production Deployment Guide

Step-by-step guide to deploy ThookAI to production. Backend on Render, Frontend on Vercel.

---

## Step 1: Provision Infrastructure

### 1.1 MongoDB Atlas (Database)

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a free/M10 cluster
3. Set database user + password
4. Whitelist `0.0.0.0/0` (for Render IP access) or use Render static IPs
5. Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/thook_database`
6. Save as `MONGO_URL`

### 1.2 Redis (Upstash or Render Redis)

**Option A: Upstash (recommended — free tier, serverless)**
1. Go to [upstash.com](https://upstash.com)
2. Create a Redis database (select region closest to your Render region)
3. Copy the connection string: `rediss://default:xxx@xxx.upstash.io:6379`
4. Save as `REDIS_URL`

**Option B: Render Redis**
1. In Render dashboard → New → Redis
2. Copy internal URL: `redis://red-xxx:6379`
3. Save as `REDIS_URL`

### 1.3 Cloudflare R2 (Media Storage)

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → R2
2. Create bucket: `thookai-media`
3. Go to R2 → Manage R2 API tokens → Create API token
4. Save: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
5. Enable public access on bucket → get public URL (e.g., `https://pub-xxx.r2.dev`)
6. Save as `R2_PUBLIC_URL`

---

## Step 2: Get API Keys

### REQUIRED (app won't function without these)

| Service | Env Variable | Where to Get | Cost |
|---------|-------------|--------------|------|
| **Anthropic** (Claude — primary LLM) | `ANTHROPIC_API_KEY` | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) | Pay per token |
| **OpenAI** (GPT-4o — fallback + agents) | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Pay per token |
| **Perplexity** (Scout research) | `PERPLEXITY_API_KEY` | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) | Pay per query |
| **Resend** (transactional email) | `RESEND_API_KEY` | [resend.com/api-keys](https://resend.com/api-keys) | Free tier: 3K/month |
| **Google OAuth** (social login) | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials → OAuth 2.0 | Free |
| **Stripe** (billing) | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` | [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys) | 2.9% + 30c per transaction |

### REQUIRED FOR PUBLISHING (social platform posting)

| Service | Env Variables | Where to Get | Notes |
|---------|-------------|--------------|-------|
| **LinkedIn** | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | [linkedin.com/developers](https://www.linkedin.com/developers/apps) → Create app → Auth tab | Requires "Share on LinkedIn" + "Sign In with LinkedIn" products |
| **X / Twitter** | `TWITTER_API_KEY`, `TWITTER_API_SECRET` | [developer.x.com](https://developer.x.com/en/portal/dashboard) → Project → Keys & tokens | Requires Basic or Pro tier ($100/mo for posting) |
| **Meta / Instagram** | `META_APP_ID`, `META_APP_SECRET` | [developers.facebook.com](https://developers.facebook.com/apps/) → Create app → Settings → Basic | Requires Instagram Basic Display API + permissions review |

### OPTIONAL (feature-gated, can add later)

| Service | Env Variable | Where to Get | Feature |
|---------|-------------|--------------|---------|
| **ElevenLabs** | `ELEVENLABS_API_KEY` | [elevenlabs.io/app/api-key](https://elevenlabs.io/app/api-key) | Voice narration + cloning |
| **fal.ai** | `FAL_KEY` | [fal.ai/dashboard](https://fal.ai/dashboard) → API Keys | Image generation (Flux Pro) |
| **Luma** | `LUMA_API_KEY` | [lumalabs.ai](https://lumalabs.ai/dream-machine/api) | AI video generation |
| **Kling** | `KLING_API_KEY` | [klingai.com](https://klingai.com) | AI video (alternative) |
| **Pinecone** | `PINECONE_API_KEY` | [app.pinecone.io](https://app.pinecone.io) | Content memory / vector search |
| **Sentry** | `SENTRY_DSN` | [sentry.io](https://sentry.io) → Create project → DSN | Error tracking |

---

## Step 3: Create Stripe Products

1. Go to [dashboard.stripe.com/products](https://dashboard.stripe.com/products)
2. Create 3 products with monthly + annual prices:

| Product | Monthly Price | Annual Price |
|---------|-------------|-------------|
| **Pro** | $19/mo | $190/yr ($15.83/mo) |
| **Studio** | $49/mo | $490/yr ($40.83/mo) |
| **Agency** | $129/mo | $1,290/yr ($107.50/mo) |

3. Also create 3 credit pack products:

| Pack | Price |
|------|-------|
| **100 Credits** | $10 |
| **500 Credits** | $45 |
| **1000 Credits** | $80 |

4. Copy each Price ID (starts with `price_`) into env vars:
   - `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_ANNUAL`
   - `STRIPE_PRICE_STUDIO_MONTHLY`, `STRIPE_PRICE_STUDIO_ANNUAL`
   - `STRIPE_PRICE_AGENCY_MONTHLY`, `STRIPE_PRICE_AGENCY_ANNUAL`
   - `STRIPE_PRICE_CREDITS_100`, `STRIPE_PRICE_CREDITS_500`, `STRIPE_PRICE_CREDITS_1000`

---

## Step 4: Generate Secrets

Run these locally to generate required secrets:

```bash
# JWT Secret (64 random chars)
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Fernet Key (for general encryption)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Encryption Key (for OAuth token encryption — DIFFERENT from Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save these — you'll need them in Step 5.

---

## Step 5: Deploy Backend on Render

### 5.1 Create Web Service

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo: `cooldeepeth/thookAI-production`
3. Settings:
   - **Name:** `thookai-api`
   - **Branch:** `dev`
   - **Root Directory:** `backend`
   - **Runtime:** Docker (uses `backend/Dockerfile`)
   - **Instance Type:** Starter ($7/mo) or Standard ($25/mo)
   - **Health Check Path:** `/health`

### 5.2 Create Background Worker (Celery)

1. Render → New → Background Worker
2. Settings:
   - **Name:** `thookai-worker`
   - **Branch:** `dev`
   - **Root Directory:** `backend`
   - **Runtime:** Docker
   - **Docker Command:** `celery -A celery_app:celery_app worker --loglevel=info --concurrency=2 -Q default,media,content,video`

### 5.3 Create Background Worker (Celery Beat)

1. Render → New → Background Worker
2. Settings:
   - **Name:** `thookai-beat`
   - **Branch:** `dev`
   - **Root Directory:** `backend`
   - **Runtime:** Docker
   - **Docker Command:** `celery -A celery_app:celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler`

### 5.4 Set Environment Variables

Add these to ALL 3 services (web + worker + beat). In Render → Service → Environment:

```env
# App
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/thook_database
DB_NAME=thook_database

# Security (paste your generated values from Step 4)
JWT_SECRET_KEY=<your_64_char_secret>
FERNET_KEY=<your_fernet_key>
ENCRYPTION_KEY=<your_encryption_key>
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_AUTH_PER_MINUTE=10

# Redis / Celery
REDIS_URL=<your_redis_url>
CELERY_BROKER_URL=<your_redis_url>
CELERY_RESULT_BACKEND=<your_redis_url>

# LLM
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
PERPLEXITY_API_KEY=pplx-xxx

# Media Storage
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=thookai-media
R2_PUBLIC_URL=https://pub-xxx.r2.dev

# Email
RESEND_API_KEY=re_xxx
FROM_EMAIL=noreply@yourdomain.com

# OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
BACKEND_URL=https://thookai-api.onrender.com
FRONTEND_URL=https://yourdomain.com

# Billing
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_ANNUAL=price_xxx
STRIPE_PRICE_STUDIO_MONTHLY=price_xxx
STRIPE_PRICE_STUDIO_ANNUAL=price_xxx
STRIPE_PRICE_AGENCY_MONTHLY=price_xxx
STRIPE_PRICE_AGENCY_ANNUAL=price_xxx
STRIPE_PRICE_CREDITS_100=price_xxx
STRIPE_PRICE_CREDITS_500=price_xxx
STRIPE_PRICE_CREDITS_1000=price_xxx

# Platform OAuth (add when ready to enable publishing)
LINKEDIN_CLIENT_ID=xxx
LINKEDIN_CLIENT_SECRET=xxx
TWITTER_API_KEY=xxx
TWITTER_API_SECRET=xxx
META_APP_ID=xxx
META_APP_SECRET=xxx

# Monitoring (optional)
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

### 5.5 Deploy

Click "Deploy" on each service. Wait for health check to pass on the web service.

Verify: `curl https://thookai-api.onrender.com/health`

Expected response:
```json
{"status": "ok", "mongodb": "connected", "redis": "connected", "r2_storage": "configured", "llm_provider": "configured", "timestamp": "..."}
```

---

## Step 6: Deploy Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → New Project
2. Import GitHub repo: `cooldeepeth/thookAI-production`
3. Settings:
   - **Framework Preset:** Create React App
   - **Root Directory:** `frontend`
   - **Build Command:** `CI=false npm run build`
   - **Output Directory:** `build`
4. Environment Variables:
   - `REACT_APP_BACKEND_URL` = `https://thookai-api.onrender.com` (your Render URL)
5. Deploy

---

## Step 7: Configure OAuth Redirect URIs

### Google OAuth
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials
2. Edit your OAuth 2.0 client
3. Add Authorized redirect URI: `https://thookai-api.onrender.com/api/auth/google/callback`
4. Add Authorized JavaScript origin: `https://yourdomain.com`

### LinkedIn
1. In your LinkedIn app → Auth tab
2. Add redirect URL: `https://thookai-api.onrender.com/api/platforms/linkedin/callback`

### X / Twitter
1. In your X developer app → Settings → User authentication
2. Callback URL: `https://thookai-api.onrender.com/api/platforms/x/callback`

### Meta / Instagram
1. In your Facebook app → Settings → Basic
2. Add platform → Website: `https://yourdomain.com`
3. Facebook Login → Settings → Valid OAuth Redirect URIs: `https://thookai-api.onrender.com/api/platforms/instagram/callback`

---

## Step 8: Configure Stripe Webhook

1. Go to [dashboard.stripe.com/webhooks](https://dashboard.stripe.com/webhooks)
2. Add endpoint: `https://thookai-api.onrender.com/api/billing/webhook/stripe`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the Signing Secret (`whsec_xxx`) → set as `STRIPE_WEBHOOK_SECRET` in Render

---

## Step 9: Configure Custom Domain (Optional)

### Frontend (Vercel)
1. Vercel → Project → Settings → Domains
2. Add `yourdomain.com`
3. Add DNS records per Vercel instructions (CNAME or A record)

### Backend (Render)
1. Render → Web Service → Settings → Custom Domains
2. Add `api.yourdomain.com`
3. Add CNAME record: `api.yourdomain.com` → `thookai-api.onrender.com`

After DNS propagation, update:
- `BACKEND_URL` → `https://api.yourdomain.com`
- `FRONTEND_URL` → `https://yourdomain.com`
- `CORS_ORIGINS` → `https://yourdomain.com`
- `REACT_APP_BACKEND_URL` → `https://api.yourdomain.com`
- Update all OAuth redirect URIs to use new domain

---

## Step 10: Post-Deploy Verification

Run through each flow manually:

| # | Test | How |
|---|------|-----|
| 1 | Health check | `curl https://api.yourdomain.com/health` → all "connected" |
| 2 | Register | Create account on frontend → verify JWT returned |
| 3 | Google OAuth | Click "Sign in with Google" → verify redirect + login |
| 4 | Onboarding | Complete 7 questions → verify persona card generated |
| 5 | Generate content | Create a LinkedIn post → verify pipeline completes |
| 6 | Approve content | Approve generated content → verify status changes |
| 7 | Connect LinkedIn | OAuth flow → verify token stored |
| 8 | Schedule post | Schedule for 5 min → verify Celery processes it |
| 9 | Billing | Start Stripe checkout → complete with test card `4242 4242 4242 4242` |
| 10 | Password reset | Request reset → check email arrives → reset password |

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| 503 on `/health` | MongoDB or Redis not connected | Check MONGO_URL and REDIS_URL |
| CORS errors in browser | CORS_ORIGINS doesn't match frontend domain | Update CORS_ORIGINS env var |
| Google OAuth fails | Redirect URI mismatch | Check BACKEND_URL matches Google Cloud config |
| Stripe checkout fails | Missing Price IDs | Verify all STRIPE_PRICE_* vars are set |
| Pipeline stuck on "running" | Agent timeout or Celery not running | Check worker logs; stale cleanup runs every 10 min |
| Uploads return 503 | R2 not configured | Check R2_* env vars |
| Emails not sending | Resend not configured | Check RESEND_API_KEY |
| Token decryption fails | Wrong ENCRYPTION_KEY | Never change ENCRYPTION_KEY after deployment |
