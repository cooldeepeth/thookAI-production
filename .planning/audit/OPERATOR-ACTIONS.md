---
doc: operator-stake-list
date: 2026-04-13
companion: AUDIT-2026-04-13.md
---

# OPERATOR ACTIONS — v3.0 Ship-Ready Stake List

> Everything below is **YOUR hands**. I cannot do these without secrets, account access, or destructive operations on shared infra.
> Companion: `.planning/audit/AUDIT-2026-04-13.md` for the full audit.
> Order matters — top to bottom is the recommended sequence.

---

## 🔴 BLOCKING (5 items, ~35 min active + Anthropic billing wait)

### B5. Push 192 unpushed dev commits to origin (5 min) — DO FIRST

Local `dev` is **192 commits ahead** of `origin/dev`. All Phase 26-35 work is at risk of disk-loss.

```bash
cd /Users/kuldeepsinhparmar/thookAI-production
git checkout dev
git push origin dev
```

- [ ] Pushed

---

### B2. Merge PR #63 to main (5 min)

**URL:** https://github.com/cooldeepeth/thookAI-production/pull/63

**What it fixes:**

- PYTHON-R (19 events: TypeError on `/api/platforms/status`)
- PYTHON-Q (TypeError on `/api/analytics/trends`)
- PYTHON-P (TypeError on `/api/analytics/fatigue-shield`)
- Future db_indexes idempotency (no more IndexOptionsConflict noise on rename migrations)

**CI shape**: 5 ✅ + 4 ❌ — IDENTICAL to your last 5 merged PRs to main (Backend Tests Security/General/Pipeline coverage gates + flaky playwright are all pre-existing and tolerated).

**After merge**: Railway auto-deploys (~3 min). Sentry datetime errors stop within 10 min.

- [ ] PR #63 reviewed
- [ ] Merged
- [ ] Railway redeploy succeeded (check Railway dashboard)
- [ ] Confirm: hit `https://gallant-intuition-production-698a.up.railway.app/api/platforms/status` with a Bearer (any auth'd user) and verify 200, no TypeError in Sentry within 10 min

---

### B3. Verify Stripe key prefix in Railway (5 min)

The PERF-09 launch guard (`backend/services/stripe_service.py:37+ validate_stripe_config`) is on dev only — NOT yet deployed to main. Until that lands, there is no automatic check at boot.

**Manually verify in Railway dashboard:**

- Service: backend (gallant-intuition-production-698a)
- Variables tab → search `STRIPE_SECRET_KEY`
- Confirm value starts with `sk_live_` — NOT `sk_test_`

If wrong:

- [ ] Get live key from https://dashboard.stripe.com/apikeys (top-right toggle: "Viewing live data")
- [ ] Update `STRIPE_SECRET_KEY` in Railway
- [ ] Update `STRIPE_WEBHOOK_SECRET` from https://dashboard.stripe.com/webhooks (the live webhook endpoint)
- [ ] Redeploy

Also verify in Stripe dashboard: webhook endpoint = `https://gallant-intuition-production-698a.up.railway.app/api/billing/webhook/stripe` (or `https://api.thook.ai/...` if you wire H4).

- [ ] Stripe key prefix verified `sk_live_`
- [ ] Webhook secret matches live endpoint
- [ ] Stripe dashboard shows "Viewing live data" not "Test data"

---

### B1. Top up Anthropic API credits (10 min)

**Evidence**: 7 unresolved Sentry events in last 2 days:

```
BadRequestError: Error code: 400 - Your credit balance is too low to access the Anthropic API.
Please go to Plans & Billing to upgrade or purchase credits.
```

**Affected endpoints right now**:

- `POST /api/content/create` (3 events, PYTHON-J)
- `POST /api/onboarding/generate-persona` (2 events, PYTHON-H)
- `POST /api/viral-card/analyze` (2 events, PYTHON-M)
- "AI reasoning failed" downstream (1 event, PYTHON-S)

**Action**:

1. Go to https://console.anthropic.com → Settings → Plans & Billing
2. Identify which API key is in Railway: `echo $ANTHROPIC_API_KEY | head -c 20` from Railway shell, or check the workspace name in console
3. Add credits (recommended: $50 minimum to cover smoke testing + early users)
4. Confirm: `curl -X POST https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'` → expect 200

- [ ] Anthropic billing topped up
- [ ] Direct API test returns 200
- [ ] No new Sentry events from `/api/content/create` after 30 min

**WHY THIS IS BLOCKING**: PERF-04 needs a Sentry zero-error window. Until Anthropic is funded, the 4 unresolved issues from credit exhaustion will keep firing on every content_create call.

---

### B4. PostHog key — production sends to a different account (15 min, decision needed)

**Discovery**: The production frontend bundle has `phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs` hardcoded directly in `frontend/public/index.html:119`. This key is **NOT in your `Thook` PostHog org** — your Thook org has only one project (`Default project 375540`) with key `phc_qRfW8FoHgKvhvCBeR3XsRbapx9woHkegVNbWPKyrUSt7`.

**3 options** — pick one:

**Option A**: You have a second PostHog account that holds the production key.

- [ ] Tell me which account/email so I can configure PostHog MCP to query that project
- [ ] Confirm your funnel events `user_registered`, `$identify`, `content_generated` are flowing in that account's Live Events

**Option B**: Replace the key with your Thook org key (recommended — single source of truth).

- [ ] I'll edit `frontend/public/index.html:119` to use `phc_qRfW8FoHgKvhvCBeR3XsRbapx9woHkegVNbWPKyrUSt7`
- [ ] Commit + push to dev → Vercel rebuilds frontend
- [ ] After deploy, verify funnel events appear in the Thook org Default project
- [ ] PERF-05 unblocked

**Option C**: Move the key out of HTML into a Vercel env var (long-term clean).

- [ ] I'll change `index.html` to read from an injected `__POSTHOG_KEY__` token replaced at build time, OR move the init into a React component that reads `process.env.REACT_APP_POSTHOG_KEY`
- [ ] You set `REACT_APP_POSTHOG_KEY` in Vercel env
- [ ] Vercel redeploy
- [ ] Funnel events appear

**Recommendation**: B for speed, C for cleanliness. Tell me which.

- [ ] Decision made
- [ ] Key updated
- [ ] PERF-05 funnel events visible in PostHog Live Events

---

## 🟠 HIGH (6 items, ~70 min)

### H1. Pinecone index dimension mismatch (10-30 min, depends on choice)

**Sentry**: PYTHON-N (4 events), PYTHON-K (1 event). `Vector dimension 1536 does not match the dimension of the index 1024`.

Code expects 1536 (`backend/services/vector_store.py:19 EMBEDDING_DIMENSION = 1536` — OpenAI text-embedding-3-small). Deployed Pinecone index is 1024.

**Choose**:

**Option A** (recommended, 10 min, destructive): Recreate index at 1536 dims.

1. Pinecone dashboard → your project → Indexes → delete existing index
2. Create new index: name `thookai-personas`, dimension `1536`, metric `cosine`, region `us-east-1` (or whatever your env uses)
3. Confirm `PINECONE_INDEX_NAME` and `PINECONE_ENVIRONMENT` in Railway match
4. Restart backend (Railway redeploy)
5. **Loses existing embeddings** — they'll regenerate next time content_create runs

**Option B** (30 min, code change): Switch to 1024-dim model.

- Change `vector_store.py:19` to `EMBEDDING_DIMENSION = 1024`
- Switch the embedding model to Voyage AI `voyage-3` (1024 dims) — needs `VOYAGE_API_KEY` env var + new SDK
- Existing 1024-dim index works as-is

**Recommendation**: A. Faster, no SDK change.

- [ ] Choice made
- [ ] Pinecone aligned
- [ ] Test: `POST /api/content/create` doesn't throw `Similarity query failed` in Sentry

---

### H2. Frontend Sentry DSN missing (20 min — I do code, you do env)

`frontend/src/index.js:1` is literally:

```js
// TODO: Add Sentry error tracking
// npm install @sentry/react
// Then initialize with REACT_APP_SENTRY_DSN env var
```

**Action**:

1. **You**: Get the frontend project DSN from Sentry → Settings → Projects → create or find a "javascript-react" project → copy DSN
2. **You**: Add `REACT_APP_SENTRY_DSN=https://...@o123456.ingest.sentry.io/...` to Vercel env vars (Production + Preview)
3. **Me (when you say go)**: `npm install --save @sentry/react` in `frontend/`, edit `frontend/src/index.js` to wire `Sentry.init({dsn: process.env.REACT_APP_SENTRY_DSN, environment, integrations: [Sentry.browserTracingIntegration(), Sentry.replayIntegration()], tracesSampleRate: 0.1, replaysSessionSampleRate: 0.0, replaysOnErrorSampleRate: 0.1})`
4. **You**: Vercel redeploy
5. **Verify**: Throw a test error from frontend devtools, check Sentry frontend project for the event

- [ ] Frontend Sentry project created
- [ ] DSN copied
- [ ] `REACT_APP_SENTRY_DSN` added to Vercel
- [ ] Tell me to wire the init code

---

### H3. PostHog consent gate not on production (depends on dev→main merge)

The Phase 34-07 fix `feat(34-07): gate PostHog init behind explicit cookie consent` is on dev only. Production runs PostHog init immediately on page load. GDPR exposure for EU traffic.

**Action**: After PR #63 merges, plan a dev→main merge that brings ALL of Phase 26-35 forward. This is a meta-action, not a single env var.

- [ ] PR #63 merged first
- [ ] Decide: full dev→main merge OR cherry-pick just the consent gate commit
- [ ] Vercel redeploy after frontend changes land

---

### H4. `api.thook.ai` DNS record missing (10 min)

`dig api.thook.ai` returns no record. LAUNCH-CHECKLIST.md assumes it exists. Real backend is `gallant-intuition-production-698a.up.railway.app`.

**Choose**:

**Option A** (10 min, recommended): Wire CNAME at your DNS provider.

- DNS provider for `thook.ai` (Cloudflare? Vercel? Other?)
- Add CNAME: `api` → `gallant-intuition-production-698a.up.railway.app`
- TTL: 300 (low so propagation is fast)
- After propagation: `dig api.thook.ai` returns the Railway target
- Then in Railway: backend service → Settings → Domains → add custom domain `api.thook.ai` → Railway issues TLS cert via ACME
- Update `BACKEND_URL` in Railway env vars: `https://api.thook.ai`
- Update `REACT_APP_BACKEND_URL` in Vercel env vars: `https://api.thook.ai`
- Redeploy frontend

**Option B** (5 min): Accept Railway URL and update LAUNCH-CHECKLIST.md.

- Edit `LAUNCH-CHECKLIST.md` to replace every `api.thook.ai` reference with `gallant-intuition-production-698a.up.railway.app`
- Less professional-looking but functional

**Recommendation**: A for v3.0. Worth the 10 minutes.

- [ ] DNS choice made
- [ ] CNAME added (if A)
- [ ] Railway custom domain configured (if A)
- [ ] BACKEND_URL + REACT_APP_BACKEND_URL updated
- [ ] Curl `https://api.thook.ai/health` returns 200

---

### H5. Resend domain verification (10 min)

`RESEND_API_KEY` is set + `FROM_EMAIL=noreply@thookai.com`. But the `thookai.com` domain (or your final domain) needs DKIM/SPF/DMARC records verified in Resend dashboard, otherwise password-reset emails will land in spam or bounce.

**Action**:

1. https://resend.com/domains → check status of `thookai.com` (or whichever domain you're using for FROM_EMAIL)
2. If "Not verified": Resend shows the 3 DNS records you need to add (TXT for SPF + 2 CNAMEs for DKIM)
3. Add them at your DNS provider
4. Click "Verify" in Resend → wait for green checkmarks
5. Test: trigger a password-reset email from the live site → check inbox + spam

- [ ] Resend domain status verified
- [ ] Test email delivers to inbox (not spam)

---

### H6. Phase 31 needs human verification (4 manual checks, ~30 min)

From `.planning/phases/31-smart-scheduling/31-VERIFICATION.md`:

1. **Calendar UI**: Open `https://thook.ai/dashboard/calendar` → verify calendar grid loads from `/api/dashboard/schedule/calendar` (check Network tab) → click month ChevronLeft/Right → verify new API call → confirm scheduled-post cards show 3 buttons (Now, Edit, Trash).
2. **DB write**: Schedule a post from ContentStudio → in MongoDB Atlas, query `db.scheduled_posts.find({user_id: "<your_uid>"})` → expect docs with `schedule_id` starting `sch_`, `status: "scheduled"`.
3. **Live Celery Beat**: Run `celery -A celery_app:celery_app beat` (or confirm it's running on Railway worker process) → schedule a post 5-10 min in the future → wait → verify `status` flips to `published` and `published_at` is within 2 min of `scheduled_at`.
4. **Reschedule modal**: Open a scheduled card → click Edit → change date/time → click Reschedule → toast "Rescheduled" appears → calendar refreshes with new time.

- [ ] Calendar UI passes
- [ ] DB write confirmed
- [ ] Celery Beat publishes a real post
- [ ] Reschedule modal flow works

---

## 🟡 MEDIUM (4 items, ~60 min total — accept or schedule)

### M1. Phase 29-05 SUMMARY missing

- [ ] Write `.planning/phases/29-media-generation-pipeline/29-05-SUMMARY.md` OR accept doc gap

### M2. Phase 34 per-plan SUMMARY files missing (9)

- [ ] Decide: keep VERIFICATION.md as the single source OR retroactively write the 9 summaries

### M3. PR #63 backport to dev

- [ ] After PR #63 merges, I'll handle: `git checkout dev && git merge main` and resolve the conflict on `platforms.py` (dev has the 24h refresh feature too — keep both)

### M4. `/api/billing/health` endpoint missing

- [ ] Optional: I can add a `/api/billing/health` that calls `stripe.Account.retrieve()` to confirm key validity at runtime

---

## 🟢 LOW (4 items, ~30 min — pure cleanup)

- [ ] **L1** Drop 16 obsolete worktree branches: `git worktree list` → `git worktree remove <path>`
- [ ] **L2** Mark `EMERGENT_LLM_KEY` as deprecated in `backend/.env.example` line 33 (Emergent was removed in commit `bc61bdf`)
- [ ] **L3** Remove `EMERGENT_LLM_KEY` from `backend/config.py:66` — no remaining caller
- [ ] **L4** Either delete `backend/routes/n8n_bridge.py` (38 KB dead code) or document as compatibility shim

---

## What I'm waiting on you for (smoke testing — separate ask)

These are the items from the original Phase 35 launch sequence that I cannot do without your hands:

- [ ] **PERF-01 measure_p95**: I need a smoke account (email + password OR a long-lived JWT). Once available, I run `backend/scripts/measure_p95.sh` against all 10 endpoints with `DELAY_MS=1000` for ~20 minutes and populate `reports/phase-35/perf-01-p95-results.md`.
- [ ] **PERF-06/08 cross-browser smoke**: Same smoke account. I run `npx playwright install firefox webkit` then `npx playwright test e2e/production-smoke.spec.ts` for the 20-test matrix (4 tests × 5 browsers) against `https://thook.ai`.
- [ ] **PERF-04 48h zero-error window**: After the BLOCKING items above are cleared, the 48h Sentry clock starts wall-time.

---

## Final ship sequence (when everything above is green)

```bash
# 1. Update LAUNCH-CHECKLIST sign-off section
vim LAUNCH-CHECKLIST.md   # fill in founder name + date

# 2. Final smoke test (optional but recommended)
curl -sI https://thook.ai
curl -s https://api.thook.ai/health   # or Railway URL

# 3. Final Sentry check — should be 0 unresolved
# (use Sentry MCP or dashboard)

# 4. Type the sign-off line
echo "SIGNED OFF — ThookAI v3.0 — $(date +%Y-%m-%d)" >> LAUNCH-CHECKLIST.md
git add LAUNCH-CHECKLIST.md
git commit -m "feat(launch): v3.0 sign-off"
git push origin main

# 5. Tag the release
git tag -a v3.0.0 -m "ThookAI v3.0 — Distribution-Ready Platform"
git push origin v3.0.0

# 🚀
```

---

_Total estimated active time: ~3 hours + 48h Sentry wall clock + Anthropic billing wait._

_Companion: see `.planning/audit/AUDIT-2026-04-13.md` for the full code-level findings + verification matrices._
