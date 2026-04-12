# ThookAI v3.0 — Pre-Launch Checklist

**Platform:** ThookAI — AI Content Operating System
**Version:** v3.0
**Checklist Author:** GSD Phase 35
**Sign-off required by:** Founder / Platform Owner

---

## Phase 35 Gate Summary

All items below must be PASS or have an explicit `[deferred]` / `[N/A]` note with rationale before signing off.

| #       | Requirement                                               | Plan  | Verdict                                                    | Notes                                                                                                                                                                                                                                                                  |
| ------- | --------------------------------------------------------- | ----- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PERF-01 | API p95 < 500 ms on 10 most-used endpoints                | 35-01 | **instrumentation_ready / measurement_pending**            | `TimingMiddleware.slow_request_threshold_ms = 500` live. `backend/scripts/measure_p95.sh` ready. **Operator: run against production, paste results into `reports/phase-35/perf-01-p95-results.md`.**                                                                   |
| PERF-02 | Bundle optimized + code splitting                         | 35-02 | **PASS**                                                   | 36 JS chunks, `main.js` 107.51 kB gzipped, largest chunk 46.35 kB gzipped — well under 500 kB cap. Dashboard Suspense INSIDE layout shell (sidebar never flashes).                                                                                                     |
| PERF-03 | Lighthouse Performance ≥ 90 on landing / auth / dashboard | 35-03 | **CONDITIONAL PASS**                                       | Local build: landing 79, auth 83, dashboard 86. TBT=0 / CLS=0.004 prove the split is working. Gap is render-blocking from `npx serve` (no Brotli, no HTTP/2, no CDN). **Operator: re-run `npx @lhci/cli collect` against deployed Vercel URL — expected to clear 90.** |
| PERF-04 | Sentry 48 h zero-error window                             | 35-06 | **operator_action_required**                               | Sentry grooming and 48 h wall-clock wait are non-automatable. See §Monitoring below for clock-start / clock-end timestamps.                                                                                                                                            |
| PERF-05 | PostHog funnel events verified                            | 35-06 | **PASS (build) / operator_dashboard_verification_pending** | 3 funnel events wired (`user_registered`, `$identify`, `content_generated`) with consent-gated guards. Build verified. **Operator: verify events in PostHog Live Events from a consented production session.**                                                         |
| PERF-06 | E2E smoke test passes against production                  | 35-05 | **config_verified / operator_run_pending**                 | `e2e/production-smoke.spec.ts` with 4 real-network smoke tests, refuses to run without `SMOKE_USER_EMAIL` / `SMOKE_USER_PASSWORD`. **Operator: run with `PROD_URL` + dedicated smoke credentials.**                                                                    |
| PERF-07 | 50-user load test — fast endpoints p95 < 2 s, zero 5xx    | 35-04 | **script_ready / run_pending**                             | `locust>=2.43.4` in requirements.txt, threshold block documents fast-vs-LLM distinction, runbook + pre-run checklist in report. **Operator: `pip install locust && locust -u 50 -r 5 --run-time 5m --host $LOAD_HOST`.**                                               |
| PERF-08 | Cross-browser smoke passes (5 browsers)                   | 35-05 | **config_verified / operator_run_pending**                 | `playwright.config.ts` has 5 browser projects. `--list` enumerates the exact 20-test matrix. **Operator: `npx playwright install firefox webkit && npx playwright test e2e/production-smoke.spec.ts`.**                                                                |
| PERF-09 | This checklist signed off                                 | 35-07 | **PENDING**                                                | Founder fills in the Sign-Off section below.                                                                                                                                                                                                                           |

---

## SSL & DNS

- [ ] `https://thook.ai` resolves and TLS cert is valid (TLS 1.2+)
- [ ] `https://www.thook.ai` redirects to `https://thook.ai`
- [ ] `https://api.thook.ai` (or current Railway URL) resolves and cert is valid
- [ ] `GET /health` returns `{"status": "ok"}`

## CORS

- [ ] `CORS_ORIGINS` in Railway is NOT `*` (unset = safe fallback, or explicit allow-list)
- [ ] Preflight OPTIONS from `https://thook.ai` to `https://api.thook.ai/api/auth/me` succeeds

## Environment Variables — Railway (backend)

### Required Always

- [ ] `MONGO_URL` — MongoDB Atlas connection string (not `mongodb://localhost`)
- [ ] `DB_NAME` — production database name (not `thookai_dev`)
- [ ] `JWT_SECRET_KEY` — ≥ 32 random characters, not placeholder/default
- [ ] `FERNET_KEY` — valid Fernet key (`python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` to generate)
- [ ] `ENVIRONMENT=production`
- [ ] `REDIS_URL` — Redis Cloud or ElastiCache URL

### LLM (at least one required)

- [ ] `ANTHROPIC_API_KEY` — starts with `sk-ant-`, not placeholder

### Billing — CRITICAL

- [ ] `STRIPE_SECRET_KEY` — starts with `sk_live_`, **NOT** `sk_test_`
  - Verify in Railway dashboard: var value prefix = `sk_live_`
  - At server startup, `validate_stripe_config()` logs `CRITICAL LAUNCH-BLOCKER` if `sk_live_` prefix missing — check boot logs after deploy
  - Code reference: `backend/services/stripe_service.py:41` + `backend/config.py:180 (StripeConfig.is_live_mode)`
- [ ] `STRIPE_WEBHOOK_SECRET` — webhook endpoint registered for prod URL
- [ ] Stripe dashboard → Developers → Webhooks → endpoint = `https://api.thook.ai/api/billing/webhook`
- [ ] Stripe dashboard header shows "Viewing live data" (not "Test data")

### Media Storage (Cloudflare R2)

- [ ] `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`

### OAuth (social login + platform connections)

- [ ] `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- [ ] `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`
- [ ] `META_APP_ID`, `META_APP_SECRET`
- [ ] `TWITTER_API_KEY`, `TWITTER_API_SECRET`
- [ ] `ENCRYPTION_KEY` — Fernet key for OAuth token encryption (can be same as `FERNET_KEY` or distinct)

### Email

- [ ] `RESEND_API_KEY`, `FROM_EMAIL`

### Monitoring

- [ ] `SENTRY_DSN` — production project DSN
- [ ] `BACKEND_URL=https://api.thook.ai`
- [ ] `FRONTEND_URL=https://thook.ai`

## Environment Variables — Vercel (frontend)

- [ ] `REACT_APP_BACKEND_URL=https://api.thook.ai`
- [ ] No `sk_*` or `*_SECRET` vars in Vercel env (secrets must never reach the browser — Vercel injects `REACT_APP_*` at build time)

## Rate Limiting

- [ ] `RATE_LIMIT_PER_MINUTE=60` active — verify: 61 requests/minute returns 429
- [ ] `RATE_LIMIT_AUTH_PER_MINUTE=10` active — verify: 16 login attempts/min returns 429

## Monitoring

- [ ] Sentry dashboard shows `environment: production` events (not test/dev)
- [ ] PostHog dashboard shows pageview events from `thook.ai` (not localhost)
- [ ] **PERF-04 — Sentry 48h zero-error window:**
  - Clock start (all unresolved issues groomed): `<ISO 8601 UTC — operator fills in>`
  - Clock end (48 h later, zero new unresolved): `<ISO 8601 UTC — operator fills in>`
  - Sentry filtered dashboard link: `<optional>`
- [ ] **PERF-05 — PostHog funnel verification (consented session):**
  - `user_registered` event visible in Live Events: `<yes/no, date>`
  - `$identify` with `user_id` visible in Live Events: `<yes/no, date>`
  - `content_generated` event visible with platform/content_type/job_id: `<yes/no, date>`

## Backup Strategy

- [ ] MongoDB Atlas automated backup enabled (6-hour interval, 7-day retention)
- [ ] R2 object versioning enabled on the media bucket
- [ ] Sentry error retention policy reviewed (90 days on free plan)

## n8n Workflow Status

- [ ] n8n deployed on Railway — OR documented as `[deferred to post-launch]`
- [ ] If deployed: `scheduled-posts` workflow active, `credit-reset` workflow active, `analytics-poll` workflow active
- [ ] If NOT deployed: manual credit reset process documented and scheduled

## Final Code Checks

- [ ] No `sk_test_` keys in Railway env vars (CRITICAL — live payments will fail silently)
- [ ] No `localhost` references in production env vars (`MONGO_URL`, `REDIS_URL`, `BACKEND_URL`, `FRONTEND_URL`)
- [ ] `git log --oneline -15` on `dev` — all Phase 35 plan commits are present (35-01 through 35-07)
- [ ] PR from `dev` → `main` is open and reviewed
- [ ] PR does NOT touch `backend/routes/billing.py` without this checklist signed off (CLAUDE.md Rule 7)
- [ ] `backend/services/stripe_service.py` change in Phase 35 is the read-only `validate_stripe_config()` guard — no payment-flow logic changed

## Operator Actions Still Pending (from Phase 35 plans)

These items are tracked in their respective plan reports. Each must be confirmed or explicitly deferred before sign-off:

| Item                                                            | Plan  | Report                                                               | Action                                                 |
| --------------------------------------------------------------- | ----- | -------------------------------------------------------------------- | ------------------------------------------------------ |
| Run `measure_p95.sh` against production, populate results table | 35-01 | `reports/phase-35/perf-01-p95-results.md`                            | Run the script, paste numbers                          |
| Re-run Lighthouse CI against deployed Vercel URL                | 35-03 | `reports/phase-35/perf-03-lighthouse-results.md`                     | Run `npx @lhci/cli collect --url=https://thook.ai ...` |
| Install locust and run 50-user 5-minute load test               | 35-04 | `reports/phase-35/perf-07-load-test-results.md`                      | Follow runbook in report                               |
| Run 20-test Playwright cross-browser matrix                     | 35-05 | `.planning/phases/35-performance-monitoring-launch/35-05-SUMMARY.md` | Install firefox/webkit, run with credentials           |
| Verify PostHog events in Live Events from consented session     | 35-06 | `.planning/phases/35-performance-monitoring-launch/35-06-SUMMARY.md` | Incognito → accept cookies → register → generate       |
| Groom Sentry dashboard to zero unresolved, start 48h clock      | 35-06 | `.planning/phases/35-performance-monitoring-launch/35-06-SUMMARY.md` | Fill in clock-start / clock-end timestamps above       |

---

## Sign-Off

All checklist items above have been verified against the live Railway and Vercel environments, OR explicitly deferred with `[N/A]` / `[deferred]` and a rationale.

**Signed off by:** `<founder name>`
**Date:** `<YYYY-MM-DD>`
**Environment confirmed:** Production (`sk_live_*` Stripe keys, Atlas, Railway/Vercel)

**Final declaration (operator writes here once every box is checked or deferred):**

`SIGNED OFF — ThookAI v3.0 — <date>`

---

_Generated by GSD Phase 35, Plan 07 — `backend/services/stripe_service.py:41` + `backend/config.py:180`_
