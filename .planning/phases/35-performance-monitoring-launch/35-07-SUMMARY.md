---
phase: 35-performance-monitoring-launch
plan: 07
status: done
requirements: PERF-09
updated: 2026-04-13
---

# Plan 35-07 Summary — v3.0 Launch Checklist + Stripe Guard (PERF-09)

## Outcome

`LAUNCH-CHECKLIST.md` is now at the repo root as the single authoritative pre-launch gate for ThookAI v3.0. It consolidates all 9 PERF requirement verdicts from plans 35-01 through 35-06, enumerates every Railway / Vercel env var that matters, and routes the remaining operator action items (Lighthouse re-run, locust run, Playwright cross-browser, PostHog dashboard verify, Sentry 48 h grooming) to a single sign-off point. The Stripe test-key launch guard is live in `validate_stripe_config()` — startup now logs CRITICAL if `STRIPE_SECRET_KEY` is not a `sk_live_*` key in production.

PERF-09 flips to PASS the moment the founder fills in the Sign-Off section of `LAUNCH-CHECKLIST.md` with a name, date, and the `SIGNED OFF — ThookAI v3.0 — <date>` declaration.

## Artifacts

| File | Change | Purpose |
|------|--------|---------|
| `LAUNCH-CHECKLIST.md` | **new** (repo root) | 9-row gate table, env var catalog (Railway + Vercel), SSL/DNS/CORS checks, rate limit verification, monitoring (Sentry 48 h + PostHog), backup strategy, n8n status, operator action index, sign-off section |
| `backend/config.py` | +8 lines | `StripeConfig.is_live_mode()` method — returns True only for `sk_live_*` keys, used by stripe_service startup guard |
| `backend/services/stripe_service.py` | +16 lines (new branch in `validate_stripe_config()`) | `logger.critical("LAUNCH-BLOCKER: ...")` when `settings.app.is_production and not settings.stripe.is_live_mode()`. Reports the detected prefix (sk_test_ or unknown) so operators can triage Railway env fast. |

## ⚠ CLAUDE.md Rule 7 — Billing file flagged

`backend/services/stripe_service.py` was touched. Per CLAUDE.md Rule 7, any change to `stripe_service.py` or `backend/routes/billing.py` must be flagged for human review. The PR message at commit `9c73972` includes the explicit flag and documents the scope:

- **Only `validate_stripe_config()` was modified** — a new conditional branch at the top of the function
- **No payment-flow logic changed**:
  - No new API calls to Stripe
  - No changes to checkout, webhook handling, subscription management, or refund logic
  - The existing `is_stripe_configured()` initialization gate is unchanged
  - The existing credit-price and webhook-secret validation branches are unchanged
- **Effect is a startup log line**, nothing else — the server still boots, Stripe still initializes, payments still route through the existing code paths

This is the lowest-risk billing-adjacent change possible: a boot-time warning that fires when the operator has forgotten to swap the Stripe key from test to live. It does not alter billing behavior; it alerts the operator to a configuration bug that would otherwise silently break every real checkout.

## Stripe guard behavior by scenario

| Environment | `STRIPE_SECRET_KEY` prefix | Log level | Startup effect |
|-------------|---------------------------|-----------|----------------|
| `development` | any | (no new log) | Unchanged |
| `development` | `sk_test_` | (no new log) | Unchanged — test keys are expected in dev |
| `production` | `sk_live_` | (no new log) | Unchanged — correct state, silent pass |
| `production` | `sk_test_` | **CRITICAL** `LAUNCH-BLOCKER ... detected: sk_test_ (test mode)` | Server still boots, Stripe initializes in test mode, but the boot log shouts |
| `production` | unset / placeholder | CRITICAL (existing `is_stripe_configured()` warning, unchanged) | Existing behavior |
| `production` | unknown prefix | **CRITICAL** `LAUNCH-BLOCKER ... detected: unknown / missing live key` | Server still boots, log flags the misconfiguration |

## 9 PERF requirement final verdicts (written into the checklist)

| # | Requirement | Plan | Status at end of Phase 35 | Gates for PASS |
|---|-------------|------|---------------------------|----------------|
| PERF-01 | API p95 < 500 ms | 35-01 | instrumentation_ready | operator runs `measure_p95.sh` against production |
| PERF-02 | Bundle optimized + code splitting | 35-02 | **PASS** | (none — build-level gates all green) |
| PERF-03 | Lighthouse ≥ 90 | 35-03 | CONDITIONAL PASS | operator re-runs LHCI against Vercel URL |
| PERF-04 | Sentry 48 h zero-error | 35-06 | operator_action_required | operator grooms dashboard + waits 48 h |
| PERF-05 | PostHog funnel verified | 35-06 | PASS (build), dashboard pending | operator verifies 3 events in Live Events |
| PERF-06 | E2E smoke test | 35-05 | config_verified | operator runs with production creds |
| PERF-07 | 50-user load test | 35-04 | script_ready | operator runs locust against production |
| PERF-08 | Cross-browser smoke | 35-05 | config_verified | same as PERF-06 (shared spec) |
| PERF-09 | Launch checklist signed off | 35-07 | **code_done / founder_sign_off_pending** | founder fills Sign-Off section |

2 of 9 requirements are hard PASS at build/code level (PERF-02, PERF-05 build side). The remaining 7 are **config-verified / operator-executable** — the code and tooling are complete, and every one of them has a precise runbook in its plan report. The launch checklist is the single place where these flip to final PASS.

## Why the founder sign-off cannot be automated

The 35-07 plan carries an explicit `autonomous: false` flag because the founder sign-off is the product owner making a conscious decision to ship. Claude can write the checklist, add the guard, wire the pipelines, and run every gate that can be automated. Claude **cannot** and should not sign the checklist — the signature is a liability declaration ("I have verified production state") that belongs to a human.

The checklist's sign-off block intentionally has `<founder name>` / `<YYYY-MM-DD>` placeholders for the operator to fill in. No orchestration layer will generate a date or identity there.

## Self-Check

- [x] `LAUNCH-CHECKLIST.md` exists at repo root
- [x] 9 PERF rows in the gate summary table (`grep -c "^| PERF-0" LAUNCH-CHECKLIST.md` → 9)
- [x] `SIGNED OFF` marker present in the sign-off section
- [x] `backend/config.py` has `is_live_mode()` method on `StripeConfig`
- [x] `backend/services/stripe_service.py` has the `sk_test_` production guard
- [x] `python3 ast.parse` passes on both Python files
- [x] Commit message at `9c73972` carries explicit CLAUDE.md Rule 7 billing flag
- [x] No payment logic modified — only `validate_stripe_config()` startup validation
- [ ] Founder sign-off in `LAUNCH-CHECKLIST.md` — operator action
- [ ] PERF-01 / 03 / 04 / 05 (dashboard) / 06 / 07 / 08 remaining operator actions per respective runbooks

## v3.0 Ship Declaration

**Phase 35 code side: COMPLETE — 7 / 7 plans have SUMMARY files.**

ThookAI v3.0 is **code-ready to ship**. The remaining work is:

1. Deploy `dev` branch → Vercel production (automatic on push) and Railway production (automatic on merge)
2. Founder works through `LAUNCH-CHECKLIST.md` top-to-bottom
3. Operator runs the 6 pending runbooks (see checklist "Operator Actions Still Pending" table) against the deployed environment
4. Groom Sentry and start the 48 h clock
5. 48 h later, confirm no new errors
6. Founder signs `LAUNCH-CHECKLIST.md`
7. Merge `dev` → `main`
8. 🚀

Phase 35 is **done from an execution standpoint**. PERF-09 flips to PASS with the founder signature.
