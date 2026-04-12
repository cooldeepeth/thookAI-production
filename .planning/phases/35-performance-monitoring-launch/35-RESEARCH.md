# Phase 35: Performance, Monitoring & Launch — Research

**Researched:** 2026-04-12
**Domain:** Performance engineering, observability, E2E testing, load testing, pre-launch readiness
**Confidence:** HIGH

---

## Summary

Phase 35 is the v3.0 ship gate. All preceding phases (26–34) are verified complete. The
codebase enters Phase 35 in a strong state: Sentry PII scrubbing is wired (Phase 34),
PostHog is gated behind cookie consent (Phase 34), Playwright E2E infrastructure is in
place with a full critical-path smoke test at `./e2e/critical-path.spec.ts`, and a Locust
load-test file exists at `backend/tests/load/locustfile.py`. Performance middleware
(compression, caching, timing) is deployed. MongoDB indexes for every hot-path collection
are defined in `db_indexes.py`.

The main work in Phase 35 is measurement and remediation, not construction. Three areas
require new code: (1) adding multi-browser projects to `playwright.config.ts` for
PERF-07, (2) adding `React.lazy()` code-splitting to the Dashboard router for PERF-02,
(3) producing `LAUNCH-CHECKLIST.md` for PERF-09. Everything else is tooling configuration,
metrics collection, and gate-keeping.

**Primary recommendation:** Run the measurement passes first (PERF-01 latency, PERF-02
bundle analysis, PERF-04 Locust), fix what fails, then run the gates (PERF-03 E2E on prod
URL, PERF-05 Sentry 48h, PERF-08 checklist). Two plans must be `autonomous: false` because
they require the human to confirm live production state before the clock starts.

---

## Phase Requirements

<phase_requirements>

| ID | Description | Research Support |
|----|-------------|------------------|
| PERF-01 | All API endpoints respond in <500ms (p95) | Performance middleware in place; `X-Response-Time` header emitted; curl + awk p95 script pattern documented below |
| PERF-02 | Frontend bundle optimized (code splitting, lazy loading, tree shaking) | No `React.lazy()` found in `App.js` or `Dashboard/index.jsx`; framer-motion, html2canvas bundled eagerly; `source-map-explorer` not in package.json |
| PERF-03 | Lighthouse performance score >90 on key pages | `@lhci/cli` 0.15.1 available via npx; CRA build + LHCI pattern documented |
| PERF-04 | Sentry monitoring active and clean (zero unresolved errors for 48 hours) | `sentry-sdk[fastapi]>=2.0.0` installed; `_scrub_pii` callback wired in `server.py` lines 99–120 |
| PERF-05 | PostHog analytics verified tracking user flows | PostHog loaded in `public/index.html`; consent gate in `CookieConsent.jsx`; no `posthog.capture()` calls found in React components — only auto-capture via SDK |
| PERF-06 | E2E smoke test passes: register → onboard → generate → schedule → publish | `e2e/critical-path.spec.ts` covers steps 1–7; missing publish step and analytics view against prod URL |
| PERF-07 | Load test passes: 50 concurrent users, <2s response time | `locustfile.py` ready; spawns 50 users with 10/s ramp; covers generate (weight 3), dashboard (weight 1), credits (weight 1) |
| PERF-08 | Cross-browser verified: Chrome, Firefox, Safari, Mobile Safari | `playwright.config.ts` has only chromium project; Firefox + webkit + mobile projects need adding |
| PERF-09 | Pre-launch checklist complete and signed off | All env vars catalogued from `config.py`; checklist items enumerated below |

</phase_requirements>

---

## Current State Audit

### Performance Middleware

`backend/middleware/performance.py` (verified): [VERIFIED: file read]

| Middleware | Class | Config in server.py | Status |
|------------|-------|---------------------|--------|
| `TimingMiddleware` | Emits `X-Response-Time: <ms>` header; logs WARN when > `slow_request_threshold_ms` | `slow_request_threshold_ms=2000` | Active |
| `CompressionMiddleware` | gzip level 6, min 500 bytes, skips SSE/StreamingResponse | `minimum_size=500, compression_level=6` | Active |
| `CacheMiddleware` | Redis-backed, TTL per endpoint; falls through gracefully when Redis is absent | `max_entries=1000` (8 endpoints cached) | Active |

**Cached endpoints:** `/api/templates/categories` (1h), `/api/billing/subscription/tiers` (1h),
`/api/billing/credits/costs` (1h), `/api/viral/patterns` (1h), `/api/content/image-styles` (1h),
`/api/content/series/templates` (1h), `/api/content/providers/summary` (5min),
`/api/persona/regional-english/options` (24h).

**Important:** The `TimingMiddleware` threshold is 2000ms. Slow-request warnings only fire
above 2s. For p95 < 500ms target, plan 35-01 must lower this to 500ms for measurement
purposes (and revert or leave at 500ms permanently).

### MongoDB Index Audit

`backend/db_indexes.py` (verified): [VERIFIED: file read]

All hot-path collections are indexed:

| Collection | Key Indexes for Hot Paths | Missing? |
|------------|--------------------------|---------|
| `content_jobs` | `(user_id, status)`, `(user_id, created_at)`, `(user_id, platform)`, `job_id` unique | None identified |
| `scheduled_posts` | `(status, scheduled_at)`, `user_id`, `scheduled_at` | None identified |
| `platform_tokens` | `(user_id, platform)` unique, `user_id`, `expires_at` | None identified |
| `users` | `user_id` unique, `email` unique, `subscription_tier`, `created_at` | None identified |
| `persona_engines` | `user_id` unique | None identified |
| `strategy_recommendations` | `(user_id, topic, status)` compound — MANDATORY for 14-day suppression | Present |
| `dashboard` (derived from aggregation of `content_jobs`) | Uses `(user_id, status)` compound | Covered |

**Dashboard `GET /api/dashboard/stats` is likely doing a MongoDB aggregation over
`content_jobs` filtered by `user_id`.** The compound index `idx_user_status` on
`(user_id, status)` covers this query pattern. If the dashboard also sorts by
`created_at`, the `idx_user_created` compound covers that too. No missing indexes
are immediately obvious from the defined index set, but the p95 measurement pass
(Plan 35-01) will confirm via `explain()`.

### Frontend Code Splitting

`frontend/src/App.js` (verified): [VERIFIED: file read]

```
ALL routes imported statically at module top:
  import Dashboard from "@/pages/Dashboard";
  import OnboardingWizard from "@/pages/Onboarding";
  import LandingPage from "@/pages/LandingPage";
  ... (all 10 page imports are static)
```

`frontend/src/pages/Dashboard/index.jsx` (verified):

```
ALL dashboard sub-pages imported statically:
  import DashboardHome from "./DashboardHome";
  import ContentStudio from "./ContentStudio";
  import Analytics from "./Analytics";
  import StrategyDashboard from "./StrategyDashboard";
  ... (all 17 sub-page imports are static)
```

**Finding:** Zero `React.lazy()` calls exist anywhere in the frontend. [VERIFIED: grep returned
empty] The entire app — including all 17 dashboard sub-pages, framer-motion, html2canvas,
and all Radix UI components — ships in one initial bundle. This is the highest-risk item
for the Lighthouse 90+ target and the 500KB chunk cap requirement.

### Bundle Size

No `source-map-explorer` or `webpack-bundle-analyzer` in `package.json`. [VERIFIED: file read]
Bundle size is currently unknown. CRA with all dependencies listed in `package.json` will
produce at minimum:

- `react` + `react-dom`: ~44KB min+gz
- `framer-motion` 12.38.0: ~100KB min+gz
- `@radix-ui` (33 packages): ~60–90KB combined min+gz
- `react-router-dom` 7.5.1: ~15KB min+gz
- `html2canvas` 1.4.1: ~50KB min+gz (loaded even when not needed)
- `lucide-react` 0.507.0 (tree-shakeable): ~varies per import
- `date-fns` 4.1.0 (tree-shakeable): ~varies per import

Without measuring: initial bundle is likely 500KB–1MB uncompressed. Splitting Dashboard
routes will save 30–50% of the initial load because the 17 sub-pages account for most
of the app-specific code.

### E2E Test Coverage

Playwright infrastructure: [VERIFIED: files read]

| File | What It Tests | Against Production? |
|------|--------------|---------------------|
| `e2e/smoke.spec.ts` | Frontend and backend reachable, health endpoint | No — localhost:3000/8001 |
| `e2e/critical-path.spec.ts` | Full 7-step journey (signup → strategy approve), 3 error scenarios | No — all API mocked via `page.route()` |
| `e2e/billing.spec.ts` | Billing flows (not read) | Unknown |
| `e2e/agency.spec.ts` | Agency workspace flows (not read) | Unknown |
| `e2e/export.spec.ts` | Content export (not read) | Unknown |

**Finding for PERF-06/PERF-03:** The critical-path smoke test uses mock API responses
via `page.route()` — it does NOT exercise the real backend. PERF-03 requires the full
smoke test to run against the live production URL with real API calls. A separate
`production-smoke.spec.ts` is needed that:
1. Sets `baseURL` to the production URL (via env var `PROD_URL`)
2. Uses real credentials (from env vars `SMOKE_TEST_EMAIL` / `SMOKE_TEST_PASSWORD`)
3. Does NOT mock any API routes
4. Covers: register → onboard → generate → schedule → analytics view

**Finding for PERF-07 (cross-browser):** `playwright.config.ts` has only one project
(`chromium`). Adding Firefox, webkit (Safari), and mobile projects is a 15-line config
change.

### Sentry State

`backend/server.py` lines 96–121 (verified): [VERIFIED: file read]

- `sentry-sdk[fastapi]>=2.0.0` installed per `requirements.txt` [VERIFIED]
- `sentry_sdk.init()` called at server startup when `SENTRY_DSN` is set
- `before_send=_scrub_pii` callback scrubs PII fields (Phase 34 requirement)
- `traces_sample_rate=0.1` in production, `profiles_sample_rate=0.1`
- `environment` set from `settings.app.environment`

**For PERF-05 (48h zero errors):** Sentry must be initialized with the production DSN
and must have been quiet for 48 consecutive hours. This requires:
1. Human grooming pass through Sentry dashboard to resolve stale/known errors
2. Recording the "clock start" timestamp
3. Human sign-off 48h later that no new unresolved errors appeared

This is a **manual gate** — it cannot be automated. Plan 35-05 must be `autonomous: false`.

### PostHog Event Coverage

`frontend/public/index.html` (verified): PostHog snippet loaded, `__thookai_init_posthog()`
function defined, gated on `localStorage["thookai_cookie_consent"] === "accepted"`. [VERIFIED]

`frontend/src/components/CookieConsent.jsx` (verified): `accept()` calls
`window.__thookai_init_posthog()` and `window.posthog.opt_in_capturing()`. `decline()`
calls `opt_out_capturing()`. [VERIFIED]

**PostHog event coverage audit:** No explicit `posthog.capture()` calls exist in any
React component. [VERIFIED: grep empty] PostHog relies entirely on **auto-capture**
(clicks, pageviews, form submissions) via the SDK snippet in `index.html`. This means:

- **Pageview events:** Automatically fired on route change — YES via `capturePerformance`
  config and SPA pageview tracking
- **Click events:** Auto-captured — YES
- **Custom events (content generated, persona created, etc.):** NONE

**For PERF-06:** The planner must decide whether auto-capture is sufficient for funnel
verification or whether explicit `posthog.capture()` calls should be added for the two
key funnels (auth funnel and content generation funnel). Recommendation: add
`posthog.capture("content_generated", { platform, job_id })` in ContentStudio after
successful job creation, and `posthog.capture("user_registered")` in the auth flow.
This satisfies PERF-06 more robustly than relying only on click auto-capture.

### Locust Load Test

`backend/tests/load/locustfile.py` (verified): [VERIFIED: file read]

The file is production-ready for the 50-user test as specified:
- Spawns a fresh registered user per worker (`on_start`)
- Tasks: `generate_content` (weight 3), `check_dashboard` (weight 1), `check_credits` (weight 1)
- Credit atomicity post-run check via `on_test_stop`
- Outputs `load-results_stats.csv` with 95th percentile column

**Gap vs. PERF-04 requirement:**
1. Current locust p95 target in the file is 500ms but PERF-04 requires p95 < 2s under load.
   The 500ms threshold is for individual endpoint p95 at low load (PERF-01). At 50 concurrent
   users, the pipeline (LLM call inside `generate_content`) will take 5–30s per call — this
   is expected. The p95 < 2s target applies to fast endpoints (dashboard, credits), not the
   LLM pipeline. The plan must configure separate p95 thresholds per endpoint type.
2. The locustfile connects to `localhost:8001` by default. For PERF-04 it must target the
   production URL. Add `--host` flag to the run command.

**Locust not installed** in current system Python. [VERIFIED: system check returned empty]
It must be added to `backend/requirements.txt` as `locust>=2.43.4` (already documented
in the file header but not in requirements.txt).

---

## Standard Stack

### Core Tools for Phase 35

| Tool | Version | Purpose | Availability |
|------|---------|---------|-------------|
| `locust` | >=2.43.4 | 50-user load test (PERF-04) | Not installed — add to requirements.txt |
| `@lhci/cli` | 0.15.1 | Lighthouse CI headless scoring (PERF-03) | Available via `npx @lhci/cli` |
| `source-map-explorer` | >=2.5.3 | Analyze CRA bundle chunk sizes (PERF-02) | Not installed — add to frontend devDependencies |
| `playwright` | Already installed (project root `package.json`) | Multi-browser E2E (PERF-07, PERF-03) | Available |
| `sentry-sdk[fastapi]` | >=2.0.0 | Error tracking (PERF-05) | Installed (requirements.txt) |
| PostHog snippet | SDK via CDN | Analytics funnel tracking (PERF-06) | Wired in index.html |
| `bash` + `awk` | system | p95 latency script via curl loop (PERF-01) | Available anywhere |

**Installation (backend):**
```bash
# Add to backend/requirements.txt
locust>=2.43.4,<3.0
```

**Installation (frontend):**
```bash
cd frontend && npm install --save-dev source-map-explorer
```

### p95 Latency Measurement Tool Selection

**Recommendation: `curl` + `bash` + `awk` script** — zero new tooling dependencies.

`hey`, `k6`, and `wrk` are not installed and require OS-level install. A bash loop over
curl with `X-Response-Time` header extraction from the server response is zero-dependency,
scriptable, and produces a CSV that matches the expected verification report format.

```bash
# Source: [VERIFIED: TimingMiddleware adds X-Response-Time header to every response]
# Pattern: curl 100 iterations, extract X-Response-Time header, compute p95 via awk

ENDPOINT="https://api.thook.ai/api/dashboard/stats"
AUTH="Authorization: Bearer $TEST_TOKEN"
TIMES=()
for i in $(seq 1 100); do
  T=$(curl -s -o /dev/null -D - -H "$AUTH" "$ENDPOINT" \
    | grep -i x-response-time | awk '{print $2}' | tr -d 'ms\r')
  TIMES+=($T)
done
# Sort and get p95
printf "%s\n" "${TIMES[@]}" | sort -n | awk 'NR==95{print "p95:", $1, "ms"}'
```

This works because `TimingMiddleware` emits `X-Response-Time: <float>ms` on every response.

---

## Architecture Patterns

### React.lazy Code Splitting Pattern (PERF-02)

The Dashboard router at `frontend/src/pages/Dashboard/index.jsx` has 17 static imports.
Lazy-loading all sub-pages is the highest-leverage change. The pattern is straightforward
with `React.lazy()` + `React.Suspense`:

```jsx
// Source: [ASSUMED - standard React pattern, verified in React 18 docs]
import { lazy, Suspense } from "react";

// Replace static imports with lazy imports
const DashboardHome = lazy(() => import("./DashboardHome"));
const ContentStudio  = lazy(() => import("./ContentStudio"));
const Analytics      = lazy(() => import("./Analytics"));
// ... (all 17 sub-pages)

// Wrap Routes in Suspense
function Dashboard() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#050505] flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-lime border-t-transparent rounded-full animate-spin" />
    </div>}>
      <Routes>
        <Route path="/" element={<DashboardHome />} />
        ...
      </Routes>
    </Suspense>
  );
}
```

**App.js lazy imports** (top-level routes): The same pattern applies to
`LandingPage`, `AuthPage`, `OnboardingWizard`, and `Dashboard` itself in `App.js`.
Priority order: Dashboard lazy-load first (biggest impact), then LandingPage (second
biggest since it contains framer-motion animations).

**CRA / CRACO chunk naming:** With CRACO, dynamic `import()` calls automatically
produce named chunks based on the file path. No webpack config changes are needed.

**framer-motion tree shaking:** `framer-motion` 12.x supports tree-shaking.
No change is needed unless a specific `motion` import pulls in the full bundle.
Verify with `source-map-explorer` after the lazy-load split.

### Playwright Multi-Browser Configuration (PERF-07)

```typescript
// Source: [VERIFIED: @playwright/test devices API, playwright.config.ts structure confirmed]
// Add to playwright.config.ts projects array:

projects: [
  { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  { name: "firefox",  use: { ...devices["Desktop Firefox"] } },
  { name: "webkit",   use: { ...devices["Desktop Safari"] } },
  {
    name: "mobile-chrome",
    use: { ...devices["Pixel 5"] },  // 393x851 viewport
  },
  {
    name: "mobile-safari",
    use: { ...devices["iPhone 13 Pro"] },  // 390x844 viewport
  },
],
```

**Note:** For PERF-07, the multi-browser run should use the **production URL** smoke test
(`production-smoke.spec.ts`), not the full mocked `critical-path.spec.ts` which would
require the test backends running locally on every browser worker.

### Production E2E Smoke Pattern (PERF-03)

A new `e2e/production-smoke.spec.ts` targeting the live URL:

```typescript
// Source: [ASSUMED: Playwright env var pattern for baseURL override]
// Run with: PROD_URL=https://thook.ai npx playwright test production-smoke.spec.ts

const BASE_URL = process.env.PROD_URL || "http://localhost:3000";

test.use({ baseURL: BASE_URL });

// Use real backend — NO page.route() mocks
// Credentials from env: SMOKE_USER_EMAIL, SMOKE_USER_PASSWORD
```

**Key decision:** The production smoke test must use a dedicated test account (not the
owner's personal account) to avoid polluting real analytics. The test should clean up
after itself by deleting generated content jobs and the test user via the API.

### Locust Configuration for PERF-04

The existing `locustfile.py` needs one change: the 5-minute run with the production URL:

```bash
# Source: [VERIFIED: locustfile.py header comment]
cd backend && locust \
  -f tests/load/locustfile.py \
  --headless \
  -u 50 \
  -r 5 \
  --run-time 5m \
  --host https://api.thook.ai \
  --csv=load-results \
  --html=load-results.html
```

**Spawn rate:** `-r 5` (5 users/sec) — ramps 50 users over 10 seconds, not all at once.
The original comment suggests `-r 10` but for a production test `-r 5` is safer.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lighthouse scoring | Manual DevTools runs | `@lhci/cli` (installed via npx) | Repeatable, CI-compatible, produces JSON report |
| Bundle analysis | `console.log` chunk sizes | `source-map-explorer` | Shows exact bytes per module, identifies megadeps |
| p95 measurement | Custom Python timing harness | `TimingMiddleware` `X-Response-Time` header + bash | Already instrumented; no new infra needed |
| Load testing | Custom concurrency script | `locust` (existing `locustfile.py`) | Handles 50-user orchestration, CSV output, credit atomicity check |
| Multi-browser testing | Separate browser installs | Playwright `projects` config | Single test run, single report, cross-browser matrix in one config |

---

## Common Pitfalls

### Pitfall 1: Cold Server p95 Inflation
**What goes wrong:** Running p95 measurements on a cold server (fresh deploy, no warm
connections) inflates latency by 3–10x due to MongoDB connection pool establishment,
JIT compilation of Python code, and Redis connection setup.
**Why it happens:** Motor async connection pool initializes lazily. The first 10–20 requests
after server start pay the pool-fill cost.
**How to avoid:** Before the 100-iteration curl loop, run 15 warmup requests that are
discarded from the p95 calculation.
**Warning signs:** First 5 requests are all >1000ms while subsequent ones are <100ms.

### Pitfall 2: Locust Hitting the LLM Pipeline
**What goes wrong:** The `generate_content` task calls the real LLM pipeline. Under 50
concurrent users, 50 simultaneous Anthropic API calls will: (a) exhaust the API rate limit
causing 429s, (b) produce p95 > 30s (LLM is inherently slow), which inflates the overall
p95 stats and makes the load test appear to fail.
**Why it happens:** The locustfile generates real content (not mocked).
**How to avoid:** For PERF-04, measure p95 on the FAST endpoints only (dashboard, credits,
auth/me). The `generate_content` task should be present but its latency should be reported
separately (expected to be 5–30s). The PERF-04 requirement "p95 < 2s" applies to the
p95 of the fast-endpoint requests, not the LLM pipeline requests. Confirm this
interpretation with the user before running.
**Warning signs:** The `load-results_stats.csv` row for `/api/content/generate` shows
p95 > 10000ms — this is expected, not a failure.

### Pitfall 3: React.lazy() Breaking the Dashboard Layout
**What goes wrong:** After wrapping Dashboard sub-page imports in `React.lazy()`, the
initial render shows a loading spinner on every navigation, causing layout shift.
**Why it happens:** Each lazy chunk is fetched on demand. If the Suspense fallback is
a full-page spinner, the sidebar and topbar disappear on every route change.
**How to avoid:** The Suspense fallback must be placed INSIDE the layout (inside the
`<div className="flex-1 md:ml-64">` content area), not wrapping the entire Dashboard
component. The sidebar and TopBar should render immediately; only the content area shows
the loading spinner.
**Warning signs:** Dashboard sidebar flashes away on every navigation click.

### Pitfall 4: Stripe sk_test_ Keys in Production
**What goes wrong:** If `STRIPE_SECRET_KEY` is set to a `sk_test_*` value in Railway
production env vars, live payments fail silently — Stripe accepts test charges but does
not process real money. Webhooks for test keys are also separate from live webhooks.
**Why it happens:** Developers copy `.env.example` to Railway without switching to live keys.
**How to avoid:** The pre-launch checklist MUST include a grep check: if
`STRIPE_SECRET_KEY` starts with `sk_test_`, fail the checklist with a CRITICAL warning.
The `StripeConfig.is_fully_configured()` method does not currently check for `sk_test_`
vs `sk_live_` prefix. Add this check.
**Warning signs:** Stripe dashboard shows revenue in "Test mode" view.

### Pitfall 5: CORS Wildcard on Production
**What goes wrong:** If `CORS_ORIGINS` env var is unset or `*` in Railway, the server
falls back to the hardcoded allow-list in `server.py` (lines 351–358). This is actually
the safe behavior — but if a developer adds `CORS_ORIGINS=*` explicitly to Railway, the
server rejects it at middleware level (since `allow_credentials=True` + `allow_origins=["*"]`
is rejected by CORSMiddleware).
**Why it happens:** Confusion between "unset CORS_ORIGINS" (safe fallback) vs. explicit `*`.
**How to avoid:** Pre-launch checklist: verify `CORS_ORIGINS` in Railway is either unset
(uses safe hardcoded list) or explicitly set to `https://thook.ai,https://www.thook.ai`.
**Warning signs:** CORS errors in browser console on production, especially for preflight OPTIONS.

### Pitfall 6: sentry-sdk v2 PII Scrub API Surface
**What goes wrong:** Bumping `sentry-sdk` to v3+ (if released) changes the `before_send`
callback signature or the `event["request"]["data"]` structure, breaking the PII scrub
implemented in Phase 34.
**Why it happens:** The `before_send` API surface changed between major Sentry SDK versions.
**How to avoid:** Pin `sentry-sdk[fastapi]>=2.0.0,<3.0` in `requirements.txt` (already done).
Do not bump the major version without reading the v2→v3 migration guide.
**Warning signs:** PII data appearing in Sentry breadcrumbs after an SDK upgrade.

### Pitfall 7: PostHog Not Firing Because Consent Not Set
**What goes wrong:** E2E and load tests create accounts programmatically. The
`localStorage["thookai_cookie_consent"]` key is never set in automated sessions, so
PostHog never initializes. PostHog funnel verification in PERF-06 would show zero events.
**Why it happens:** Automated browsers start with empty localStorage; the consent banner
delay (1500ms) never fires.
**How to avoid:** For the PostHog funnel verification test, use a real browser session
where the human manually accepts cookies, or run a brief Playwright session that explicitly
sets the consent key before navigating to the app.
**Warning signs:** PostHog dashboard shows zero events from the test session.

### Pitfall 8: Lighthouse Fails Because Build Includes Source Maps
**What goes wrong:** `GENERATE_SOURCEMAP=true` (CRA default) produces `.js.map` files
that bloat the `build/` folder and can cause Lighthouse to report higher transfer sizes.
**Why it happens:** CRA includes source maps in the build by default.
**How to avoid:** Run Lighthouse against the Vercel-deployed production URL (which strips
source maps from CDN responses), not the local `build/` folder served with `serve`.
**Warning signs:** Lighthouse reports 2x the expected bundle sizes.

---

## Code Examples

### p95 Measurement Script (PERF-01)

```bash
# Source: [VERIFIED: TimingMiddleware emits X-Response-Time header, server.py line 270-271]
# Usage: ENDPOINT_URL=https://api.thook.ai/api/dashboard/stats \
#        AUTH_HEADER="Bearer <token>" \
#        bash measure_p95.sh

#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${ENDPOINT_URL}"
ITERATIONS=100
WARMUP=15
TOKEN="${AUTH_HEADER}"
TIMES_FILE=$(mktemp)

echo "Warming up ($WARMUP requests, discarded)..."
for i in $(seq 1 $WARMUP); do
  curl -s -o /dev/null -H "Authorization: $TOKEN" "$ENDPOINT"
done

echo "Measuring p95 ($ITERATIONS requests)..."
for i in $(seq 1 $ITERATIONS); do
  TIME=$(curl -s -o /dev/null -D - \
    -H "Authorization: $TOKEN" \
    -H "Accept-Encoding: gzip" \
    "$ENDPOINT" \
    | grep -i "x-response-time:" \
    | awk '{print $2}' \
    | tr -d 'ms\r\n')
  echo "$TIME" >> "$TIMES_FILE"
done

P95=$(sort -n "$TIMES_FILE" | awk 'NR==95{print $1}')
MEAN=$(awk '{sum+=$1} END{printf "%.1f", sum/NR}' "$TIMES_FILE")
MAX=$(sort -n "$TIMES_FILE" | tail -1)

echo "Results for: $ENDPOINT"
echo "  p95:  ${P95}ms  (target: <500ms)"
echo "  mean: ${MEAN}ms"
echo "  max:  ${MAX}ms"
echo "  PASS: $([ "${P95%.*}" -lt 500 ] && echo YES || echo FAIL)"
rm "$TIMES_FILE"
```

### Playwright Multi-Browser Project Config (PERF-07)

```typescript
// Source: [VERIFIED: playwright.config.ts confirmed; devices import confirmed]
// Replace the single `projects` array in playwright.config.ts

projects: [
  {
    name: "chromium",
    use: { ...devices["Desktop Chrome"] },
  },
  {
    name: "firefox",
    use: { ...devices["Desktop Firefox"] },
  },
  {
    name: "webkit",
    use: { ...devices["Desktop Safari"] },
  },
  {
    name: "mobile-chrome",
    use: { ...devices["Pixel 5"] },
  },
  {
    name: "mobile-safari",
    use: { ...devices["iPhone 13 Pro"] },
  },
],
```

### Lighthouse CI Run Pattern (PERF-03)

```bash
# Source: [VERIFIED: @lhci/cli 0.15.1 available; CRA build output in frontend/build/]
# Run against production URL (recommended) or serve local build

# Option A: Against live production URL
npx @lhci/cli collect \
  --url="https://thook.ai" \
  --url="https://thook.ai/auth" \
  --numberOfRuns=3

npx @lhci/cli assert \
  --assert.preset=lighthouse:recommended \
  --assert.assertions.performance=["error", {"minScore": 0.9}] \
  --assert.assertions.accessibility=["warn", {"minScore": 0.9}]

# Option B: Against local production build
cd frontend && npm run build
npx serve -s build -p 5000 &
npx @lhci/cli collect --url="http://localhost:5000" --numberOfRuns=3
```

---

## Runtime State Inventory

This phase is performance measurement and tooling only. No data migrations, renames, or
refactors.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no collection renames | None |
| Live service config | Sentry DSN must be set in Railway for PERF-05 | Manual: verify `SENTRY_DSN` in Railway env vars |
| OS-registered state | None | None |
| Secrets/env vars | `STRIPE_SECRET_KEY` must be `sk_live_*` not `sk_test_*` | Manual: verify in Railway |
| Build artifacts | None — no package rename | None |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Playwright, LHCI | Yes | v20.15.0 | — |
| `@lhci/cli` | PERF-03 Lighthouse | Yes (npx) | 0.15.1 | Manual DevTools (slower) |
| `locust` | PERF-04 load test | No — not installed | — | Add `locust>=2.43.4` to requirements.txt |
| `source-map-explorer` | PERF-02 bundle analysis | No — not in package.json | — | Add to devDependencies |
| Playwright browsers | PERF-07 cross-browser | Yes (project root) | Already configured | — |
| `curl` + `bash` + `awk` | PERF-01 p95 measurement | Yes (system) | System | — |

**Missing dependencies with fallback:**
- `locust`: Add to `requirements.txt` before Plan 35-04 runs
- `source-map-explorer`: Add to `frontend/package.json` devDependencies before Plan 35-02 runs

---

## Suggested Plan Breakdown

The planner should produce exactly these 7 plans in 3 waves.

### Wave 1: Measurement (can run in parallel)

**35-01: Backend p95 latency measurement + index audit (PERF-01)**
- Requirements: PERF-01
- Goal: Write `backend/scripts/measure_p95.sh`; run against the 10 most-used endpoints;
  capture JSON report; run MongoDB `explain()` on any endpoint > 500ms p95; add indexes
  if needed.
- Files touched: `backend/scripts/measure_p95.sh` (new), `backend/db_indexes.py` (if new
  index needed), `backend/middleware/performance.py` (lower slow-request threshold to 500ms)
- Dependencies: Production URL + auth token required
- Autonomous: true (measurement is not destructive)

**35-02: Frontend bundle optimization — React.lazy + code splitting (PERF-02)**
- Requirements: PERF-02
- Goal: Add `source-map-explorer` to devDependencies; add `React.lazy()` to all Dashboard
  sub-page imports in `frontend/src/pages/Dashboard/index.jsx`; add `React.lazy()` to
  top-level routes in `App.js`; wrap routes in `<Suspense>`; verify no chunk > 500KB via
  `source-map-explorer`.
- Files touched: `frontend/src/pages/Dashboard/index.jsx`, `frontend/src/App.js`,
  `frontend/package.json`
- Dependencies: None
- Autonomous: true

**35-03: Lighthouse CI scoring — key pages pass 90 (PERF-03)**
- Requirements: PERF-03
- Goal: Run `@lhci/cli` against the three required pages (landing, dashboard home,
  ContentStudio) on the production URL; verify all score >= 90 on Performance; document
  results in `35-03-SUMMARY.md`.
- Files touched: None (measurement only); `.lighthouserc.json` (new, if using LHCI config)
- Dependencies: Must run AFTER 35-02 (bundle split) is deployed to Vercel
- Autonomous: true

### Wave 2: Load + Cross-Browser (after Wave 1 fixes deployed)

**35-04: Locust 50-user load test (PERF-07)**
- Requirements: PERF-07 (load test — note: PERF-07 in REQUIREMENTS.md is "load test
  passes: 50 concurrent users, <2s response time"; cross-browser is PERF-08)
- Goal: Add `locust>=2.43.4` to `requirements.txt`; verify locustfile.py targets the
  production URL via `--host`; run 50-user 5-minute test; capture `load-results_stats.csv`;
  verify p95 < 2s on fast endpoints (dashboard/stats, auth/me, billing/credits); verify
  zero 5xx errors.
- Files touched: `backend/requirements.txt`, `backend/tests/load/locustfile.py` (minor
  update: separate p95 thresholds for LLM vs fast endpoints)
- Dependencies: Production URL available
- Autonomous: true

**35-05: Multi-browser E2E smoke + production smoke test (PERF-03, PERF-08)**
- Requirements: PERF-03 (production E2E), PERF-08 (cross-browser)
- Goal: (a) Add Firefox, webkit, mobile-chrome, mobile-safari projects to
  `playwright.config.ts`; (b) Write `e2e/production-smoke.spec.ts` that hits the live
  production URL with real credentials; (c) Run both smoke tests on all 5 browser
  projects.
- Files touched: `playwright.config.ts`, `e2e/production-smoke.spec.ts` (new)
- Dependencies: Production URL + smoke test account credentials
- Autonomous: false — requires human to provide production URL and smoke test credentials

### Wave 3: Gates + Sign-Off

**35-06: Sentry grooming + PostHog event audit (PERF-04, PERF-05)**
- Requirements: PERF-04 (Sentry 48h), PERF-05 (PostHog funnel verified)
- Goal: (a) Add explicit `posthog.capture()` calls for content generation and auth funnel;
  (b) Document the Sentry grooming process and record the 48h clock start timestamp;
  (c) Verify PostHog events flow in an accepted-consent incognito session.
- Files touched: `frontend/src/pages/Dashboard/ContentStudio/index.jsx` (posthog.capture),
  `frontend/src/pages/AuthPage.jsx` (posthog.capture), `frontend/src/context/AuthContext.jsx`
  (posthog.identify after login)
- Dependencies: None for code changes; Sentry grooming requires human
- Autonomous: false — 48h clock MUST be started by a human after reviewing Sentry dashboard

**35-07: Pre-launch checklist + final sign-off (PERF-06, PERF-09)**
- Requirements: PERF-06 (pre-launch checklist), PERF-09 (signed off)
- Goal: Write `LAUNCH-CHECKLIST.md` at repo root; validate all env vars in Railway and
  Vercel; verify Stripe production mode; verify CORS allow-list; verify SSL; verify n8n
  workflows active; sign off.
- Files touched: `LAUNCH-CHECKLIST.md` (new), `backend/services/stripe_service.py`
  (add `sk_test_` prefix guard), `backend/config.py` (add Stripe production mode validation)
- Dependencies: 35-01 through 35-06 all PASS; Sentry 48h elapsed
- Autonomous: false — final sign-off is a human gate

---

## Plans Requiring `autonomous: false`

The following plans must include `autonomous: false` in their frontmatter. The executor
must stop and wait for human confirmation before proceeding.

| Plan | Why `autonomous: false` | What Human Must Confirm |
|------|------------------------|------------------------|
| 35-05 | Production E2E requires live URL + real smoke-test credentials | Provide `PROD_URL`, `SMOKE_USER_EMAIL`, `SMOKE_USER_PASSWORD`; confirm which URL is production |
| 35-06 | Sentry 48h clock is a manual gate — cannot be automated | Review Sentry dashboard, resolve all stale errors, record the start timestamp. Sign off when 48h have elapsed with zero new unresolved errors. |
| 35-07 | Final launch sign-off requires human verification of live production state | Confirm all checklist items are green: SSL, CORS, env vars, Stripe live mode, n8n active, monitoring active |

---

## Pre-Launch Checklist Items (for PERF-09)

The executor for Plan 35-07 should produce `LAUNCH-CHECKLIST.md` containing these items.

### SSL & DNS
- [ ] `https://thook.ai` resolves and cert is valid (TLS 1.2+)
- [ ] `https://www.thook.ai` redirects to `https://thook.ai`
- [ ] `https://api.thook.ai` (or Railway URL) resolves and cert is valid
- [ ] `GET /health` on production backend returns `{"status": "ok"}`

### CORS
- [ ] `CORS_ORIGINS` in Railway is NOT set to `*` (either unset or explicit allow-list)
- [ ] Preflight OPTIONS request from `https://thook.ai` to `https://api.thook.ai/api/auth/me` succeeds

### Environment Variables — Railway (backend)
**Required always:**
- [ ] `MONGO_URL` — MongoDB Atlas connection string (not `mongodb://localhost`)
- [ ] `DB_NAME` — production database name
- [ ] `JWT_SECRET_KEY` — ≥ 32 random characters, not `change_this_to...`
- [ ] `FERNET_KEY` — valid Fernet key (`from cryptography.fernet import Fernet; Fernet.generate_key()`)
- [ ] `ENVIRONMENT=production`
- [ ] `REDIS_URL` — Redis Cloud / ElastiCache URL

**LLM (at least one):**
- [ ] `ANTHROPIC_API_KEY` — starts with `sk-ant-`, not placeholder
- [ ] `OPENAI_API_KEY` (optional fallback)
- [ ] `PERPLEXITY_API_KEY` (optional, scout agent)

**Billing:**
- [ ] `STRIPE_SECRET_KEY` — starts with `sk_live_`, NOT `sk_test_`
- [ ] `STRIPE_WEBHOOK_SECRET` — webhook endpoint registered in Stripe dashboard for prod URL
- [ ] Stripe webhook endpoint URL in Stripe dashboard points to `https://api.thook.ai/api/billing/webhook`

**Media:**
- [ ] `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`

**OAuth:**
- [ ] `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- [ ] `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`
- [ ] `META_APP_ID`, `META_APP_SECRET`
- [ ] `TWITTER_API_KEY`, `TWITTER_API_SECRET`
- [ ] `ENCRYPTION_KEY` — Fernet key for platform OAuth tokens

**Email:**
- [ ] `RESEND_API_KEY`, `FROM_EMAIL`

**Monitoring:**
- [ ] `SENTRY_DSN` — production Sentry project DSN
- [ ] `BACKEND_URL=https://api.thook.ai`
- [ ] `FRONTEND_URL=https://thook.ai`

**Optional:**
- [ ] `FAL_KEY` (image generation)
- [ ] `ELEVENLABS_API_KEY` (voice)
- [ ] `N8N_URL`, `N8N_WEBHOOK_SECRET` (scheduled workflows)

### Environment Variables — Vercel (frontend)
- [ ] `REACT_APP_BACKEND_URL=https://api.thook.ai`
- [ ] No `sk_*` or `*_SECRET` vars in frontend env (secrets must not leak to browser)

### Rate Limiting
- [ ] `RATE_LIMIT_PER_MINUTE=60` (or configured value) active in production
- [ ] `RATE_LIMIT_AUTH_PER_MINUTE=10` active (protects login endpoint)
- [ ] Verified with: `curl -X POST https://api.thook.ai/api/auth/login -d '{}' × 15` — 16th request returns 429

### Monitoring
- [ ] Sentry dashboard shows `environment: production` events
- [ ] PostHog dashboard shows pageview events from production URL
- [ ] Health endpoint at `/health` returns `{"status": "ok"}` (not `"unhealthy"`)

### Backup Strategy
- [ ] MongoDB Atlas automated backup enabled (6-hour interval, 7-day retention)
- [ ] R2 object versioning enabled on `thookai-media` bucket
- [ ] Sentry error retention policy documented (90 days on free plan, configurable)

### n8n Workflow Status
- [ ] `n8n` deployed on Railway (or confirmed not required at launch)
- [ ] If deployed: scheduled-posts workflow active, credit-reset workflow active

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest 8.x + pytest-asyncio |
| Framework (frontend) | Jest (via react-scripts) + RTL |
| E2E framework | Playwright (project root `playwright.config.ts`) |
| Config file | `pytest.ini` (backend), `craco.config.js` (frontend jest), `playwright.config.ts` (E2E) |
| Quick run (backend) | `cd backend && pytest tests/ -x -q` |
| Quick run (E2E) | `npx playwright test e2e/smoke.spec.ts` |
| Full E2E | `npx playwright test --project=chromium` |
| Lighthouse | `npx @lhci/cli collect --url=<URL> --numberOfRuns=3` |
| Load test | `cd backend && locust -f tests/load/locustfile.py --headless -u 50 -r 5 --run-time 5m --host <URL> --csv=load-results` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | p95 < 500ms on 10 endpoints | perf script | `bash backend/scripts/measure_p95.sh` | ❌ Wave 1 |
| PERF-02 | No chunk > 500KB, dashboard lazy-loaded | bundle analysis | `npm run analyze` (source-map-explorer) | ❌ Wave 1 |
| PERF-03 | Lighthouse > 90 on 3 pages | Lighthouse CI | `npx @lhci/cli collect --url=<PROD>` | ❌ Wave 2 |
| PERF-04 | Sentry clean 48h | manual | — (manual gate) | N/A |
| PERF-05 | PostHog funnels verified | manual + Playwright | `npx playwright test e2e/posthog-consent.spec.ts` | ❌ Wave 3 |
| PERF-06 | E2E full smoke on prod URL | Playwright E2E | `PROD_URL=<URL> npx playwright test e2e/production-smoke.spec.ts` | ❌ Wave 2 |
| PERF-07 | Load test 50 users p95 < 2s | Locust | `locust --headless -u 50 -r 5 --run-time 5m` | ✅ exists (update needed) |
| PERF-08 | Cross-browser Chrome/FF/Safari/Mobile | Playwright multi-project | `npx playwright test --project=chromium --project=firefox --project=webkit` | ❌ config update Wave 2 |
| PERF-09 | Pre-launch checklist signed off | manual + automated checks | `bash backend/scripts/launch-checklist-verify.sh` | ❌ Wave 3 |

### Wave 0 Gaps (files to create before implementation)

- [ ] `backend/scripts/measure_p95.sh` — PERF-01 measurement script
- [ ] `backend/scripts/launch-checklist-verify.sh` — automated portion of PERF-09
- [ ] `e2e/production-smoke.spec.ts` — real-backend smoke against prod URL (PERF-03, PERF-08)
- [ ] `e2e/helpers/production-auth.ts` — handles real login for production smoke
- [ ] `.lighthouserc.json` — LHCI configuration with 90+ assertion thresholds
- [ ] `LAUNCH-CHECKLIST.md` — human sign-off checklist (PERF-09)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `X-Response-Time` header format is `<float>ms` (e.g., `"123.45ms"`) as extracted by `awk '{print $2}'` | p95 measurement script | Script produces wrong output; use `curl -w "%{time_total}"` as fallback |
| A2 | Lazy-loading 17 Dashboard sub-pages will bring the initial bundle under 500KB | Bundle optimization | May need additional `framer-motion` dynamic import if the bundle is still over 500KB after splitting |
| A3 | PostHog auto-capture (pageviews + clicks) is sufficient for PERF-05 funnel verification | PostHog audit | PostHog project may require explicit events for funnel construction; verify in PostHog dashboard |
| A4 | The Locust "p95 < 2s" target applies only to fast endpoints, not the LLM pipeline | Locust load test | If the requirement literally means ALL endpoints including LLM pipeline, the test will fail and the requirement needs to be relaxed |
| A5 | Production backend URL is `https://api.thook.ai` | Pre-launch checklist | May be a Railway URL like `https://thookai-production.up.railway.app` — confirm before running smoke tests |
| A6 | `@lhci/cli` 0.15.1 works with `--assert.assertions.performance` flag for score assertions | Lighthouse CI | Flag syntax may differ between LHCI versions; fallback to manual DevTools if needed |

---

## Open Questions

1. **Production URL confirmation**
   - What we know: Backend deployed on Railway, frontend on Vercel
   - What's unclear: Whether `thook.ai` is live and pointing at current builds, or still
     pointing at an older deploy
   - Recommendation: Human confirms the production URL before Plans 35-05 and 35-07

2. **Locust p95 threshold for LLM endpoint**
   - What we know: PERF-07 in REQUIREMENTS.md says "p95 < 2s"; LLM pipeline takes 5–30s
   - What's unclear: Whether the 2s threshold applies to the LLM endpoint or only fast endpoints
   - Recommendation: Plan 35-04 should note this ambiguity and default to measuring fast
     endpoints only; owner confirms threshold for content generation endpoint separately

3. **n8n deployment status**
   - What we know: CLAUDE.md says "n8n not yet deployed" — scheduled publishing, daily
     limits, and credit resets are inactive
   - What's unclear: Whether n8n must be deployed for the v3.0 launch gate or is deferred
   - Recommendation: Pre-launch checklist should have an n8n section marked optional; owner
     confirms whether launch gate requires n8n

4. **Smoke test account creation**
   - What we know: Production smoke test needs a real account to test
   - What's unclear: Whether to create a dedicated smoke test account or reuse an existing
     one; whether test content created during smoke should be auto-deleted
   - Recommendation: Create a dedicated `smoke@thookai.com` account in production;
     Plan 35-05 should include cleanup after the smoke run

---

## Sources

### Primary (HIGH confidence)
- `backend/server.py` (lines 96–121) — Sentry init, PII scrubbing callback verified
- `backend/middleware/performance.py` — TimingMiddleware `X-Response-Time` header verified
- `backend/db_indexes.py` — All MongoDB indexes audited
- `backend/tests/load/locustfile.py` — Locust test verified; 50-user task weights confirmed
- `frontend/src/App.js` — Zero `React.lazy()` calls confirmed
- `frontend/src/pages/Dashboard/index.jsx` — 17 static imports confirmed
- `frontend/package.json` — No `source-map-explorer` confirmed
- `playwright.config.ts` — Single chromium project confirmed; `baseURL: localhost:3000`
- `e2e/smoke.spec.ts`, `e2e/critical-path.spec.ts` — E2E coverage audited
- `frontend/public/index.html` — PostHog gated init confirmed
- `frontend/src/components/CookieConsent.jsx` — Consent gate logic verified
- `backend/config.py` — All env vars catalogued from dataclasses
- `.planning/REQUIREMENTS.md` — PERF-01 through PERF-09 definitions confirmed
- `.planning/ROADMAP.md` (lines 585–599) — Phase 35 success criteria confirmed
- `backend/requirements.txt` — `sentry-sdk[fastapi]>=2.0.0` confirmed; `locust` absent

### Secondary (MEDIUM confidence)
- Node.js v20.15.0 confirmed available; `@lhci/cli` 0.15.1 confirmed via `npx --yes @lhci/cli --version`

### Tertiary (LOW confidence)
- Estimated bundle sizes for dependencies (framer-motion, html2canvas) from training knowledge — not measured [ASSUMED]
- Lighthouse 90+ achievability after React.lazy split — reasonable inference but not measured [ASSUMED]

---

## Project Constraints (from CLAUDE.md)

- **Branch strategy:** All work branches from `dev`, PRs target `dev`. Never commit to `main`.
- **Config pattern:** All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly.
- **Database pattern:** Always `from database import db` with Motor async.
- **LLM model:** `claude-sonnet-4-20250514`
- **Billing changes:** Flag for human review — `backend/services/stripe_service.py` changes need owner approval before merge
- **Agent pipeline:** After any change to `backend/agents/`, verify full pipeline flow
- **No new Python packages** without adding to `backend/requirements.txt`
- **No new npm packages** without noting in PR description

**Phase 35 specific application:**
- Adding `locust>=2.43.4` to `requirements.txt` is required for Plan 35-04 (new package — must be in PR description)
- Adding `source-map-explorer` to `frontend/package.json` is required for Plan 35-02 (new npm package — must be in PR description)
- Any STRIPE_SECRET_KEY validation changes touch `backend/services/stripe_service.py` indirectly via `backend/config.py` — flag the PR

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools verified against actual files
- Architecture: HIGH — current code state fully audited
- Pitfalls: HIGH — sourced from direct code findings (e.g., zero React.lazy, Stripe test-key gap)
- Plan breakdown: MEDIUM — count and scope correct; wave sequencing assumes Wave 1 deploys before Wave 2 runs

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable stack; npm/pip versions may drift after 30 days)
