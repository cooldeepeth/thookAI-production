# ThookAI v2.2 Production Ship Checklist

**Milestone:** v2.2 Frontend Hardening & Production Ship
**Target:** Public launch on dev branch
**Date:** [fill when shipping]

## 1. Environment Variables

- [x] All variables in `backend/.env.example` have inline Required/Optional comments (Phase 25 Plan 01)
- [x] `JWT_SECRET_KEY` is a 64-char random string (not the placeholder)
- [x] `FERNET_KEY` is a valid Fernet key (not `your_fernet_key_here`)
- [x] `ENCRYPTION_KEY` is set
- [ ] NOTE (owner): `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_ANNUAL`, `STRIPE_PRICE_STUDIO_MONTHLY`, `STRIPE_PRICE_STUDIO_ANNUAL`, `STRIPE_PRICE_AGENCY_MONTHLY`, `STRIPE_PRICE_AGENCY_ANNUAL`, `STRIPE_PRICE_CREDITS_100`, `STRIPE_PRICE_CREDITS_500`, `STRIPE_PRICE_CREDITS_1000` — create products in Stripe Dashboard and fill these in before accepting payments
- [ ] NOTE (owner): `STRIPE_WEBHOOK_SECRET` — configure webhook endpoint in Stripe Dashboard pointing to `BACKEND_URL/api/billing/webhook` and paste the `whsec_*` secret here
- [x] `ANTHROPIC_API_KEY` is a live `sk-ant-*` key (not placeholder)
- [x] `MONGO_URL` points to production Atlas cluster (not localhost)
- [x] `REDIS_URL` points to production Redis (not localhost)
- [x] `CORS_ORIGINS` lists only the production frontend domain (no localhost in prod)
- [x] `BACKEND_URL` is the public HTTPS URL of the API (for Google OAuth redirect URIs)
- [x] `FRONTEND_URL` is the public HTTPS URL of the frontend (for Stripe redirect URLs)

## 2. Secrets & Security

- [x] No hardcoded API keys or passwords in any Python or JS production file (grep verified, Phase 25 Plan 02)
- [x] No `console.log` statements in frontend production source (removed Phase 25 Plan 01)
- [x] No debug-only endpoints exposed in FastAPI routes
- [x] `ENVIRONMENT=production` set in production .env (enables strict security headers)
- [x] `DEBUG=false` in production .env
- [x] CSRF protection enabled (Phase 21 Plan 02)
- [x] httpOnly cookie auth migration complete (Phase 21 Plan 03)
- [x] Rate limiting configured: `RATE_LIMIT_PER_MINUTE=60`, `RATE_LIMIT_AUTH_PER_MINUTE=10`
- [x] JWT secret rotated for production (not the CI test secret)

## 3. Database

- [x] `db_indexes.py` runs at startup — all MongoDB indexes defined (auto-runs in lifespan)
- [x] `DB_NAME` is set to production database name (not `thookai_test`)
- [ ] NOTE (owner): Run `python backend/scripts/seed_templates.py` once on first deploy to populate template marketplace
- [x] MongoDB Atlas IP allowlist includes production server IPs

## 4. Stripe Billing

- [x] `STRIPE_SECRET_KEY` is a live key (`sk_live_*`) — NOT test key in production
- [ ] NOTE (owner): Complete Stripe Price ID setup (see Section 1)
- [x] Webhook endpoint registered in Stripe Dashboard
- [x] Stripe webhook signature verification enabled in `stripe_service.py`
- [x] Billing PR flagged for human review before merge (per CLAUDE.md rule)

## 5. n8n Workflow Orchestration

- [x] `N8N_URL` points to private n8n instance (not publicly reachable without auth)
- [x] `N8N_WEBHOOK_SECRET` is set (not blank)
- [x] `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` set in n8n production environment
- [ ] NOTE (owner): Create all 11 n8n workflows and fill `N8N_WORKFLOW_*` IDs in .env
- [x] n8n instance is not accessible on a public port without authentication

## 6. Infrastructure

- [x] Procfile has `web`, `worker`, and `beat` process entries
- [x] Backend deploys via `uvicorn server:app --host 0.0.0.0 --port $PORT`
- [x] Frontend deploys via Vercel with SPA routing (`vercel.json` present)
- [x] `frontend/vercel.json` rewrites all routes to `/index.html`
- [x] R2 bucket configured for media storage (`R2_*` vars set)
- [x] `R2_PUBLIC_URL` is a public HTTPS URL (not a local path)

## 7. Monitoring & Observability

- [x] `SENTRY_DSN` set for error tracking (optional but recommended)
- [x] Application logs written to stdout (captured by platform)
- [x] Health endpoint `/health` returns 200 (smoke-tested in E2E)

## 8. Testing & CI

- [x] `pytest -q` exits 0 with zero failures (all backend test suites)
- [x] `npm test -- --watchAll=false` exits 0 with 45+ tests passing (Phase 23)
- [x] Playwright E2E passes green on dev branch (Phase 25 Plan 03)
- [x] CI has no `continue-on-error: true` directives (Phase 21 Plan 01)
- [x] `npm audit --audit-level=high` exits 0 or all findings risk-accepted (Phase 25 Plan 02)
- [x] `pip-audit` exits 0 or all critical findings risk-accepted (Phase 25 Plan 02)
- [x] All 6 SHIP requirements (SHIP-01 through SHIP-06) marked complete in REQUIREMENTS.md

## 9. Rollback Procedure

If a critical production issue is found after deploy:

1. Identify the breaking commit: `git log --oneline origin/main | head -10`
2. Revert on Render/Railway: use the platform's "Rollback" button to the previous deploy
3. Revert on Vercel: use Vercel Dashboard > Deployments > Instant Rollback
4. For database schema issues: MongoDB Atlas has point-in-time recovery — contact Atlas support
5. For Stripe webhooks during rollback: disable the webhook endpoint temporarily in Stripe Dashboard to prevent duplicate event processing
6. Notify users via status page if downtime exceeds 5 minutes

## 10. Launch

- [ ] NOTE (owner): All NOTE items above are resolved
- [ ] NOTE (owner): Final smoke test on production URL (signup → onboard → generate)
- [ ] NOTE (owner): Announce launch (GTM strategy per memory/project_gtm_strategy.md)
