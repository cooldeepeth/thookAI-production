# Phase 35: Performance, Monitoring & Launch — Validation

**Generated:** 2026-04-12
**Phase type:** Validation + sign-off (measurement-heavy, not feature-heavy)
**v3.0 ship gate:** YES — this is the final phase. All 9 PERF requirements must be PASS before launch.

---

## Decision Coverage Matrix

| Req ID | Plan | Task | Coverage | Notes |
|--------|------|------|----------|-------|
| PERF-01 | 35-01 | Task 1+2 | Full | Threshold lowered to 500ms; 10 endpoints measured; report produced |
| PERF-02 | 35-02 | Task 1+2 | Full | React.lazy() on Dashboard (17 sub-pages) + App.js top-level; source-map-explorer; bundle report |
| PERF-03 | 35-03 | Task 1 | Full | @lhci/cli against 3 pages; minScore 0.9; report produced. Depends on 35-02 deployed first |
| PERF-04 | 35-06 | Checkpoint | Full | Manual gate — Sentry grooming + 48h clock. Cannot be automated |
| PERF-05 | 35-06 | Task 1 | Full | posthog.capture x2 + posthog.identify; PostHog event verification in checkpoint |
| PERF-06 | 35-05 | Task 2+Checkpoint | Full | e2e/production-smoke.spec.ts with real API calls; no mocks; human confirms 20/20 pass |
| PERF-07 | 35-04 | Task 1+2 | Full | locust in requirements.txt; 50-user 5-min test; LLM endpoint excluded from 2s gate |
| PERF-08 | 35-05 | Task 1+Checkpoint | Full | 5-browser projects in playwright.config.ts; production-smoke.spec.ts runs on all 5 |
| PERF-09 | 35-07 | Task 1+Checkpoint | Full | LAUNCH-CHECKLIST.md at repo root; sk_test_ guard; human sign-off |

All 9 requirements: Full coverage. No partial coverage.

---

## Wave Map

```
Wave 1 (parallel — no dependencies):
  35-01  Backend p95 latency measurement + index audit          PERF-01
  35-02  Frontend bundle optimization — React.lazy()            PERF-02

Wave 2 (after Wave 1):
  35-03  Lighthouse CI scoring                                   PERF-03     depends: 35-02
  35-04  Locust 50-user load test                               PERF-07     depends: 35-01
  35-05  Multi-browser E2E + production smoke test              PERF-06,08  depends: 35-02

Wave 3 (after Wave 2 — gates):
  35-06  Sentry grooming + PostHog event audit                  PERF-04,05  depends: 35-05
  35-07  Pre-launch checklist + final sign-off                  PERF-09     depends: ALL
```

**Rationale for wave assignments:**
- 35-01 and 35-02 are fully independent measurement/code tasks — parallel Wave 1.
- 35-03 must run AFTER 35-02 because Lighthouse scores the post-split bundle; running it on the pre-split bundle would give artificially low scores that disappear after 35-02 is deployed.
- 35-04 must run AFTER 35-01 because the load test targets the same production infrastructure. Running both simultaneously inflates p95 measurements.
- 35-05 must run AFTER 35-02 because the production smoke spec (PERF-06) is measured on the same Vercel instance. Bundle optimization should be deployed before E2E is run.
- 35-06 and 35-07 are Wave 3 gates — they depend on all prior plans being complete. The Sentry 48h window starts in 35-06; 35-07 cannot be signed off until that window closes.

---

## Plans Requiring `autonomous: false`

| Plan | Why Manual | What Human Must Do |
|------|-----------|-------------------|
| 35-05 | Production E2E requires live URL + real credentials | Provide `PROD_URL`, `SMOKE_USER_EMAIL`, `SMOKE_USER_PASSWORD`; confirm 20/20 tests pass |
| 35-06 | Sentry 48h gate is a manual clock — cannot be automated | Review Sentry dashboard, resolve all stale errors, record clock start timestamp, return 48h later |
| 35-07 | Final launch sign-off requires human verification of live production state | Work through every item in LAUNCH-CHECKLIST.md against Railway + Vercel dashboards, sign off |

Plans 35-01, 35-02, 35-03, 35-04 are `autonomous: true`.

---

## Open Assumptions

1. **Production URL unknown at planning time.** Plans 35-01, 35-04, 35-05 accept `PROD_URL` / `PROD_API_URL` env vars. If not set, measurements fall back to localhost with a note in the report that they must be re-run against production.

2. **LLM endpoint excluded from p95 gates.** `/api/content/generate` is excluded from the 500ms (PERF-01) and 2s (PERF-07) gates. It is reported separately. This is documented in perf-01-p95-results.md and perf-07-load-test-results.md.

3. **Dashboard Lighthouse score measured on /auth redirect.** Unauthenticated Lighthouse on `/dashboard` redirects to `/auth`. The `/auth` score is used for the dashboard page gate. A manual authenticated DevTools run is recommended for the authenticated dashboard score — this is documented in 35-03 as a conditional pass.

4. **n8n deployment status unknown.** The pre-launch checklist has an n8n section that allows `[N/A — deferred to post-launch]`. n8n is not a launch blocker for v3.0.

5. **Stripe billing files touched in 35-07.** `backend/services/stripe_service.py` is modified to add a read-only sk_test_ logging guard. CLAUDE.md Rule 7 (flag billing changes for human review) is satisfied by the `autonomous: false` checkpoint in 35-07 which explicitly calls out the stripe_service.py change for review.

6. **locust in requirements.txt is dev-only.** The file does not have a separate dev-requirements.txt. locust is added with a comment marking it dev/CI-only. If the production build system installs all requirements.txt packages, locust will be included — it is a passive dependency (CLI tool, not imported by the server).

---

## File Ownership Map (no conflicts within waves)

| Plan | Files Modified |
|------|---------------|
| 35-01 | backend/scripts/measure_p95.sh (NEW), backend/middleware/performance.py, backend/db_indexes.py (if needed), reports/phase-35/perf-01-p95-results.md (NEW) |
| 35-02 | frontend/src/App.js, frontend/src/pages/Dashboard/index.jsx, frontend/package.json, reports/phase-35/perf-02-bundle-analysis.md (NEW) |
| 35-03 | .lighthouserc.json (NEW), reports/phase-35/perf-03-lighthouse-results.md (NEW) |
| 35-04 | backend/requirements.txt, backend/tests/load/locustfile.py, reports/phase-35/perf-07-load-test-results.md (NEW) |
| 35-05 | playwright.config.ts, e2e/production-smoke.spec.ts (NEW) |
| 35-06 | frontend/src/pages/Dashboard/ContentStudio/index.jsx, frontend/src/pages/AuthPage.jsx, frontend/src/context/AuthContext.jsx |
| 35-07 | LAUNCH-CHECKLIST.md (NEW), backend/services/stripe_service.py, backend/config.py |

Zero file conflicts within each wave. No file appears in two plans of the same wave.

---

_Generated by GSD Planner for Phase 35 — 2026-04-12_
