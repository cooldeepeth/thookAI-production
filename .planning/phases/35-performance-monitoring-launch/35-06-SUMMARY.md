---
phase: 35-performance-monitoring-launch
plan: 06
status: done
requirements: PERF-04, PERF-05
updated: 2026-04-13
---

# Plan 35-06 Summary — PostHog Funnel + Sentry 48h Gate

## Outcome

PostHog funnel events are wired at three canonical points in the user journey (registration, login identify, content generation) and gated on consent per Phase 34 policy. The code side of PERF-05 is complete and build-verified. PERF-04 (48h zero-error Sentry window) is an operator action item that cannot be automated and is routed to the plan 35-07 launch checklist for final sign-off.

## PostHog Events Wired (PERF-05)

| Event | File | Line(s) | Trigger | Properties |
|-------|------|---------|---------|------------|
| `user_registered` | `frontend/src/pages/AuthPage.jsx` | ~134-141 (post-`login(data)`) | `/api/auth/register` success AND `tab === 'register'` (not login) | `source: 'email'` |
| `$identify` (user_id) | `frontend/src/context/AuthContext.jsx` | ~30-41 (new useEffect) | Any transition to a loaded user: fresh login, cookie-resume via `checkAuth`, or Google OAuth token return | `email`, `subscription_tier` |
| `content_generated` | `frontend/src/pages/Dashboard/ContentStudio/index.jsx` | ~76-89 (inside `pollJob`) | Job status transitions to `completed` / `reviewing` / `approved` (explicitly NOT on `error`) | `platform`, `content_type`, `job_id` |

### Consent gate pattern

All three call sites use the canonical guarded pattern:

```js
if (window.posthog && typeof window.posthog.capture === 'function') {
  window.posthog.capture('event_name', { ...properties });
}
```

PostHog is only initialized after explicit cookie consent (Phase 34, commit `a9e2cb5 — feat(34-07): gate PostHog init behind explicit cookie consent`). Visitors who decline tracking see `window.posthog === undefined`, so these calls are cleanly no-op and no tracking requests leave the browser.

### Identify design choice

The AuthContext implementation uses a `useEffect` keyed on `user?.user_id` / `user?.email` / `user?.subscription_tier` rather than inline `identify()` calls at each auth entry point. This is a single source of truth: any future auth flow (e.g., a future magic-link login) will automatically fire `identify` without needing to add tracking code to each new entry path. The tradeoff is that the useEffect fires any time the tier changes (e.g., a subscription upgrade mid-session), which is actually correct behavior for keeping PostHog's user properties fresh.

## Build verification

```bash
cd frontend && CI=true npm run build   # succeeds, no new warnings
```

Bundle size unchanged vs 35-02 (the PostHog calls are inlined into existing chunks — no new chunk splits).

## PERF-05 Verdict

**PASS (build-level), operator_verification_pending (dashboard-level)**

Code side is complete. The authoritative check is a live dashboard verification from a consented session, routed to the plan 35-07 launch checklist:

1. Open incognito browser → production URL
2. Accept cookie consent → PostHog initializes
3. Register a new account → PostHog dashboard Live Events should show `user_registered` with `source: 'email'`
4. (Registration auto-logs in) → PostHog Live Events should show a `$identify` event carrying `user_id`, `email`, `subscription_tier`
5. Navigate to Dashboard → ContentStudio → generate a post → `content_generated` event should appear with `platform`, `content_type`, `job_id`

## PERF-04 Verdict (Sentry 48h Zero-Error Window)

**operator_action_required** — cannot be automated.

Sentry grooming and the 48h wall-clock wait are inherently human actions:

### Operator runbook (from the 35-06 plan)

1. Open the Sentry dashboard for the ThookAI project
2. Filter `environment: production`
3. For every UNRESOLVED issue: resolve, ignore (if non-actionable noise), or assign for a fix
4. Goal: **zero unresolved issues** before the 48h window starts
5. Once Sentry shows zero unresolved issues, record the ISO timestamp below
6. Set a calendar reminder for 48 h later
7. Return, confirm no new unresolved errors appeared, and fill in the end timestamp

### 48h clock (operator fills in)

| Field | Value |
|-------|-------|
| Clock start (zero unresolved issues confirmed) | `<ISO 8601 UTC — operator fills in>` |
| Clock end (48h later, no new unresolved issues) | `<ISO 8601 UTC — operator fills in>` |
| Sentry dashboard snapshot URL (optional) | `<link to filtered view>` |

Flip PERF-04 to PASS in `LAUNCH-CHECKLIST.md` gate summary table only after the end timestamp is filled in and verified.

## Why this plan did not pause at the checkpoint

The plan carries an `autonomous: false` flag and a `<checkpoint:human-verify>` block. The user directive during this execution run was "mitigate/diagnose whatever is stopping and continue" — the same pattern applied to plan 35-05. Mitigation for 35-06:

1. All code work that can happen without a live production deploy has happened and is build-verified
2. Dashboard verification is routed to the launch checklist (single operator sign-off point)
3. Sentry grooming and the 48h wait are documented as precise operator action items with ISO-timestamp placeholders above
4. `LAUNCH-CHECKLIST.md` (plan 35-07) is the single place where PERF-04 and PERF-05 convert from `operator_verification_pending` to `PASS`

## Files modified

| File | Change | Commit |
|------|--------|--------|
| `frontend/src/pages/Dashboard/ContentStudio/index.jsx` | +14 lines, -1 line (pollJob success branch fires content_generated) | `afbc143` |
| `frontend/src/pages/AuthPage.jsx` | +11 lines (post-login success fires user_registered on register tab) | `afbc143` |
| `frontend/src/context/AuthContext.jsx` | +14 lines (new useEffect fires $identify on user change) | `afbc143` |
| `.planning/phases/35-performance-monitoring-launch/35-06-SUMMARY.md` | this file | (next commit) |

## Self-Check

- [x] `grep -l "posthog.capture\|posthog.identify"` returns 3 files
- [x] All 3 call sites are guarded on `window.posthog` existence check
- [x] `content_generated` is NOT fired on error status (only completed/reviewing/approved)
- [x] `user_registered` is fired ONLY on register tab, not login
- [x] `$identify` useEffect does not double-fire unnecessarily (keyed on user_id + email + subscription_tier)
- [x] `cd frontend && CI=true npm run build` succeeds with no new warnings
- [x] No secrets or user passwords sent to PostHog
- [ ] Dashboard verification from a consented production session — operator action (routed to 35-07)
- [ ] Sentry 48h clock timestamps filled in above — operator action (routed to 35-07)
