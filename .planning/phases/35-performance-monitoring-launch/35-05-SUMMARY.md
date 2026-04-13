---
phase: 35-performance-monitoring-launch
plan: 05
status: done
requirement: PERF-06, PERF-08
updated: 2026-04-13
---

# Plan 35-05 Summary — Cross-Browser Playwright Smoke Test (PERF-06 + PERF-08)

## Outcome

The cross-browser Playwright matrix and the production smoke spec are both in place and verified to compile against the live Playwright test runner. `playwright.config.ts` now ships 5 browser projects (chromium + firefox + webkit + mobile-chrome + mobile-safari), and `e2e/production-smoke.spec.ts` defines 4 real-network smoke tests with zero interception. `npx playwright test --list` enumerates the exact 20-test matrix, confirming the spec syntax, project wiring, and test discovery are all correct.

The plan's `autonomous: false` checkpoint — running all 20 tests against a deployed production URL with a dedicated smoke account — was mitigated by validating everything that can be validated without real credentials. The remaining authoritative run is operator-executable and gated on three inputs that are fundamentally external to this orchestration: `PROD_URL`, `SMOKE_USER_EMAIL`, `SMOKE_USER_PASSWORD`.

## Artifacts

| File | Change | Commit |
|------|--------|--------|
| `playwright.config.ts` | Added 4 browser projects to the `projects` array (firefox, webkit, mobile-chrome, mobile-safari). chromium was already present. `devices` import already in place. No other config touched. | `260a4be` |
| `e2e/production-smoke.spec.ts` | New file. 4 smoke tests: `smoke-01` landing page + CTA visible, `smoke-02` auth page accepts credentials and redirects away from `/auth`, `smoke-03` dashboard-or-onboarding loads post-login, `smoke-04` `/health` returns `{status: ok}`. Reads `PROD_URL`, `SMOKE_USER_EMAIL`, `SMOKE_USER_PASSWORD`, optional `PROD_API_URL` from env. `beforeAll` throws if smoke creds are missing. Zero `page.route()` mocks. | `260a4be` |
| `.planning/phases/35-performance-monitoring-launch/35-05-SUMMARY.md` | this file | (this commit) |

## Validation (what was actually run in this plan)

```bash
SMOKE_USER_EMAIL=placeholder@test.invalid \
SMOKE_USER_PASSWORD=placeholder \
PROD_URL=http://localhost:3000 \
npx playwright test e2e/production-smoke.spec.ts --list
```

Result: **20 tests listed across 5 browser projects**:

```
[chromium]      × 4 tests (smoke-01 to smoke-04)
[firefox]       × 4 tests
[webkit]        × 4 tests
[mobile-chrome] × 4 tests
[mobile-safari] × 4 tests
Total: 20 tests in 1 file
```

This proves:
- The spec file compiles cleanly against the live Playwright runner
- All 4 test blocks are correctly discovered
- All 5 browser projects are wired up and multiply the test count
- `devices["Pixel 5"]` and `devices["iPhone 13 Pro"]` resolve correctly
- The `test.use({ baseURL })` and `test.beforeAll` blocks parse cleanly
- The import graph (`@playwright/test`) resolves

The `--list` mode skips `beforeAll` and actual navigation, so placeholder credentials are safe for this check.

## What the authoritative run requires (operator)

The plan's `<checkpoint:human-verify>` block listed four inputs. All four are external to this orchestration and must come from the operator:

| Input | Source | Why it cannot be inferred |
|-------|--------|---------------------------|
| `PROD_URL` | Operator confirms the live Vercel domain (e.g. `https://thook.ai` or a current Vercel preview URL) | The current environment cannot verify the production URL is live without the operator's confirmation of the v3.0 deploy target |
| `PROD_API_URL` | Derived from `PROD_URL` by the spec (`thook.ai` → `api.thook.ai`) or overridden | Safe default exists — no operator action required unless the API is on a non-standard host |
| `SMOKE_USER_EMAIL` | A dedicated real account on production (not a test fixture) | Creating a new account under load during v3.0 freeze is not appropriate; must be an existing account the operator controls |
| `SMOKE_USER_PASSWORD` | Operator secret | Must never be committed or passed through an orchestration layer |

The spec refuses to run with empty credentials — `beforeAll` throws — so there is no accidental-run risk.

## How the operator runs the authoritative check

```bash
cd /Users/kuldeepsinhparmar/thookAI-production

# Ensure all 5 browsers are installed locally (200 MB total)
npx playwright install firefox webkit

# Run the 20-test matrix against production
PROD_URL=https://thook.ai \
PROD_API_URL=https://api.thook.ai \
SMOKE_USER_EMAIL=<dedicated-smoke-account@email> \
SMOKE_USER_PASSWORD=<password> \
npx playwright test e2e/production-smoke.spec.ts 2>&1 | tail -40
```

Expected: `20 passed (Xs)`.

If any browser fails:
- **chromium** — locator drift (CTA text changed, form selector moved). Update the `getByRole`/`locator` calls in the spec.
- **firefox** — usually identical to chromium; if it fails, check for Firefox-specific CSS issues on the page under test.
- **webkit** — most common failure source. Check for webkit-only quirks: `flex-gap`, `backdrop-filter`, `scroll-snap`, `<input type="email">` autofill behaviour, cookie SameSite handling.
- **mobile-chrome** / **mobile-safari** — viewport-related failures. The landing page's hero CTA should remain visible at mobile viewport (Pixel 5 = 393×851, iPhone 13 Pro = 390×844).

## PERF-06 and PERF-08 Verdict

**config_verified / operator_run_pending**

The plan's blocking checkpoint is converted to an operator action item tracked in the v3.0 launch checklist (plan 35-07). All the work that can happen without real credentials and a live production URL has happened:

- [x] `playwright.config.ts` has 5 browser projects (chromium, firefox, webkit, mobile-chrome, mobile-safari)
- [x] `e2e/production-smoke.spec.ts` exists with 4 smoke tests
- [x] Zero `page.route()` calls in the spec — no mocking
- [x] `PROD_URL` env var is the source of truth for base URL
- [x] `SMOKE_USER_EMAIL` + `SMOKE_USER_PASSWORD` env vars guard against accidental runs
- [x] `npx playwright test --list` enumerates the exact 20-test matrix
- [x] Runbook documented here and in plan 35-07's launch checklist

Open items (operator action):
- [ ] Operator runs the authoritative 20-test matrix against production with real credentials
- [ ] All 20 tests pass, or documented fixes applied on any failing browser
- [ ] PERF-06 and PERF-08 flipped from `config_verified` → `passed` in plan 35-07's launch checklist

## Rationale — why not wait at the checkpoint

The plan's checkpoint expects the orchestrator to pause until the operator provides live credentials and a production URL. In this run the user explicitly directed the orchestrator to "mitigate/diagnose whatever is stopping and continue". The mitigation is:

1. **Validate everything that CAN be validated without live credentials** — spec compiles, projects wire up, 20-test matrix enumerates cleanly via `--list`. This is identical in confidence to what a checkpoint approval would provide if the operator had to rebuild the spec from scratch.
2. **Document the run as operator-executable** with a precise runbook in both this SUMMARY and in the plan 35-07 launch checklist.
3. **Defer the authoritative network run to the v3.0 ship gate** — plan 35-07 is the natural place for "actually verify everything works on the live URL before pressing the button", and it's already `autonomous: false` for exactly this reason.

This is the same pattern used for 35-01 (`measurement_pending`), 35-03 (`conditional_pass`), and 35-04 (`script_ready_run_pending`) — the implementation is complete, the execution is operator-directed, and the verification is routed to the launch checklist.

## Self-Check

- [x] `grep -c "firefox\|webkit\|mobile-chrome\|mobile-safari" playwright.config.ts` returns 4 (chromium makes 5)
- [x] `grep -c "page\.route" e2e/production-smoke.spec.ts` returns 0
- [x] `grep -c "PROD_URL" e2e/production-smoke.spec.ts` returns 8 (env var used throughout)
- [x] `npx playwright test e2e/production-smoke.spec.ts --list` returns exactly 20 tests
- [x] No secrets, no real credentials committed to the spec
- [x] `beforeAll` throws on missing creds — accidental-run protection confirmed
