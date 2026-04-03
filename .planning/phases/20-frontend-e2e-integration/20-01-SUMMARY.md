---
phase: 20-frontend-e2e-integration
plan: "01"
subsystem: e2e-infrastructure
tags: [playwright, e2e, testing, ci, chromium]
dependency_graph:
  requires: []
  provides: [playwright-infrastructure, e2e-helpers, smoke-spec, ci-workflow]
  affects: [20-03-PLAN, 20-04-PLAN]
tech_stack:
  added:
    - "@playwright/test ^1.50.0 (root devDependency)"
    - "Chromium browser via Playwright installer"
  patterns:
    - "Dual webServer Playwright config (FastAPI port 8001 + CRA port 3000)"
    - "page.route() for deterministic LLM/Stripe mock interception"
    - "Custom Playwright fixture extension (authenticatedPage, mockPage)"
key_files:
  created:
    - package.json
    - package-lock.json
    - playwright.config.ts
    - tsconfig.json
    - e2e/smoke.spec.ts
    - e2e/fixtures.ts
    - e2e/helpers/auth.ts
    - e2e/helpers/mock-api.ts
    - .github/workflows/e2e.yml
  modified:
    - .gitignore
decisions:
  - "Chromium-only install (no Firefox/WebKit) to reduce CI download time"
  - "reuseExistingServer: !process.env.CI so local devs can run tests against already-started servers"
  - "Node 20 in CI (Playwright recommends 18+ but 20 has best support)"
  - "FERNET_KEY pre-generated in CI env (non-secret, test-only)"
  - "Frontend node_modules installed in worktree so smoke tests could be verified locally"
metrics:
  duration_minutes: 5
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_created: 9
  files_modified: 1
---

# Phase 20 Plan 01: Playwright E2E Infrastructure Setup Summary

**One-liner:** Playwright installed at repo root with Chromium, dual webServer config for FastAPI+CRA, shared auth/mock helpers, and CI workflow — 6 smoke tests all passing.

## What Was Built

### Task 1: Playwright Installation and Configuration

**`package.json`** (repo root) — Playwright-only root package. Contains `@playwright/test ^1.50.0` and npm scripts for `test:e2e` and `test:e2e:ui`.

**`playwright.config.ts`** — Dual `webServer` array:
- FastAPI backend: `uvicorn server:app --host 0.0.0.0 --port 8001`, health-check URL `http://localhost:8001/health`
- CRA frontend: `cd frontend && npm start`, URL `http://localhost:3000`, `BROWSER=none` to suppress browser launch

Key settings: `timeout: 60000`, `retries: CI ? 2 : 0`, `workers: CI ? 1 : undefined`, `trace: on-first-retry`, `screenshot: only-on-failure`.

**`e2e/helpers/auth.ts`** — Three exported functions:
- `signUp(page, { email, password, name })` — fills signup form, waits for `/(dashboard|onboarding)/` redirect
- `logIn(page, { email, password })` — fills login form, waits for `/dashboard/` redirect
- `getAuthToken(page)` — reads JWT from localStorage (checks `token`, `access_token`, `authToken` keys)
- `uniqueEmail(prefix)` — generates collision-free test emails using timestamp + random number

**`e2e/helpers/mock-api.ts`** — Four API mock functions using `page.route()`:
- `mockLLMResponse(page, overrides)` — intercepts `/api/content/generate` and `/api/content/jobs/**`
- `mockStripeCheckout(page, sessionUrl)` — intercepts both checkout endpoint variants
- `mockOnboardingLLM(page)` — intercepts `/api/onboarding/generate-persona` and `/api/onboarding/complete`
- `mockDashboardStats(page)` — intercepts `/api/dashboard/**`

**`e2e/fixtures.ts`** — Custom Playwright `test` extending base with:
- `authenticatedPage` — registers a new unique user per test, verifies JWT in localStorage, fails fast if token missing
- `mockPage` — pre-applies all LLM + Stripe + onboarding mocks before any navigation

**`e2e/smoke.spec.ts`** — 6 smoke tests organized in two `describe` blocks:
- Frontend (CRA): landing page visible, auth page visible, page title set
- Backend (FastAPI): health 200 OK, health returns JSON with `status` field, API/docs reachable

**Smoke test results:**
```
6 passed (40.1s)
```

### Task 2: CI Workflow

**`.github/workflows/e2e.yml`** — GitHub Actions workflow:
- Triggers: `pull_request` to `dev`/`main`, `workflow_dispatch`
- Services: MongoDB 7.0 (27017) + Redis 7-alpine (6379) with health checks
- Node 20 + Python 3.11 with dependency caching
- Installs backend Python deps, frontend npm deps, then root Playwright
- `npx playwright install chromium --with-deps` for CI browser install
- Uploads `playwright-report/` artifact always (7-day retention)
- Uploads `test-results/` artifact on failure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Frontend node_modules not installed in worktree**
- **Found during:** Task 1 smoke test verification
- **Issue:** `craco: command not found` when Playwright attempted to start CRA frontend. The `frontend/node_modules/` directory was absent in this worktree (CI clone).
- **Fix:** Ran `cd frontend && npm install` to install frontend deps, enabling the smoke test to complete and prove the dual-webServer setup works end-to-end.
- **Files modified:** frontend/node_modules/ (generated, gitignored)
- **Impact:** Smoke tests all passed after install. This is expected behavior in a fresh checkout — CI workflow already includes `cd frontend && npm ci` step.

**2. [Rule 2 - Missing Config] No root tsconfig.json for TypeScript E2E files**
- **Found during:** Task 1 (pre-emptive)
- **Issue:** Playwright needs a TypeScript compilation context to parse `.ts` test files. Without a `tsconfig.json`, editors and tools wouldn't provide type checking on test files.
- **Fix:** Created `tsconfig.json` at repo root scoped to `e2e/**/*.ts` and `playwright.config.ts` only. Excludes `frontend/`, `backend/`, `remotion-service/`.
- **Files modified:** `tsconfig.json` (created)

## Known Stubs

None — this plan creates infrastructure only. No UI stubs or data placeholders.

## Self-Check

- [x] `package.json` exists at repo root with `@playwright/test`
- [x] `playwright.config.ts` contains `webServer` array with port 8001 and port 3000 entries
- [x] `e2e/helpers/auth.ts` exports `signUp`, `logIn`, `getAuthToken`, `uniqueEmail`
- [x] `e2e/helpers/mock-api.ts` exports `mockLLMResponse`, `mockStripeCheckout`, `mockOnboardingLLM`, `mockDashboardStats`
- [x] `e2e/fixtures.ts` exports custom `test` with `authenticatedPage` and `mockPage` fixtures
- [x] `e2e/smoke.spec.ts` has 6 smoke tests, all passing
- [x] `.github/workflows/e2e.yml` has MongoDB 7.0, Redis 7-alpine, Node 20, Playwright upload step
- [x] Task 1 commit: `fe7c87e`
- [x] Task 2 commit: `6a37be4`

## Self-Check: PASSED
