---
phase: 34-security-gdpr
type: validation
created: 2026-04-13
---

# Phase 34: Security & GDPR — Plan Validation

## Summary

9 plans across 3 waves. All 13 SECR requirements covered. Zero conflicts in file ownership across same-wave plans.

---

## Dependency Graph

```
Wave 1 (4 plans — all independent, run in parallel):
  34-01: XSS Sanitization Layer
  34-02: Secret Audit + Error Hardening
  34-03: Rate Limiting + CSRF Verification
  34-04: Dependency CVE Audit

Wave 2 (5 plans — some have Wave 1 dependencies for context):
  34-05: GDPR Export + Delete Backend Gaps  (depends_on: 34-03 for rate limit context)
  34-06: Settings Data Tab Frontend         (depends_on: 34-05 for API contract)
  34-07: PostHog Consent Gate               (independent of other Wave 2 plans)
  34-08: Privacy + Terms Polish + ROADMAP fix (independent of other Wave 2 plans)
  Note: 34-07 and 34-08 touch different files — run in parallel with 34-05 and 34-06

Wave 3 (1 plan):
  34-09: Security Test Suite                (depends_on: all 8 prior plans)
```

```
     [34-01] ──────────────────────────────────────────────────┐
     [34-02] ──────────────────────────────────────────────────┤
     [34-03] ──→ [34-05] ──→ [34-06] ──────────────────────────┤──→ [34-09]
     [34-04] ──────────────────────────────────────────────────┤
                 [34-07] ────────────────────────────────────────┤
                 [34-08] ────────────────────────────────────────┘
```

---

## Wave Map

| Wave | Plans | Files Modified | Autonomous | Notes |
|------|-------|---------------|------------|-------|
| 1 | 34-01, 34-02, 34-03, 34-04 | backend/services/sanitize.py, 5 route files, backend/server.py, backend/middleware/security.py, backend/requirements.txt, frontend/package.json, SECURITY-EXCEPTIONS.md | All true | Zero file conflicts across Wave 1 plans |
| 2 | 34-05, 34-06, 34-07, 34-08 | backend/routes/auth.py, frontend/src/pages/Dashboard/Settings.jsx, frontend/public/index.html, frontend/src/components/CookieConsent.jsx, frontend/src/pages/PrivacyPolicy.jsx, frontend/src/App.js, .planning/ROADMAP.md | All true | 34-05 and 34-06 share auth.py conceptually but 34-06 only modifies Settings.jsx — no actual file conflict |
| 3 | 34-09 | backend/tests/security/test_input_validation.py, backend/tests/security/test_gdpr.py, frontend/src/__tests__/components/CookieConsent.test.jsx | true | Depends on all prior plans |

---

## Requirement Coverage Matrix

| Requirement | Plan | Task | Coverage | Notes |
|-------------|------|------|----------|-------|
| SECR-01 | 34-01 | Task 2 | Full | SECR-01 audit during sanitize_text wiring — flag any missing Pydantic bodies with TODO comments |
| SECR-02 | 34-01 | Task 1+2 | Full | sanitize.py created + wired into 5 route files |
| SECR-03 | 34-01 | Task 2 | Full | Verified CLEAN in research; executor confirms during file reads; documented in summary |
| SECR-04 | 34-03 | Task 1 | Full | CSRFMiddleware verified as already complete; audit documented in summary |
| SECR-05 | 34-03 | Task 1 | Full | 4 new endpoint_limits entries added; per-user limit for GDPR export in 34-05 |
| SECR-06 | 34-02 | Task 1 | Full | os.environ.get PORT violation in server.py removed; auth_google.py + vector_store.py verified clean |
| SECR-07 | 34-02 | Task 1 | Full | Global exception handler already correct; Sentry _scrub_pii callback added |
| SECR-08 | 34-04 | Task 1+2 | Full | pip-audit + npm audit run; CVEs fixed or documented in SECURITY-EXCEPTIONS.md |
| SECR-09 | 34-05 | Task 1 | Full (backend) | 4 missing collections added; per-user Redis rate limit added |
| SECR-09 | 34-06 | Task 1 | Full (frontend) | Settings Data tab with Export button wired to GET /api/auth/export |
| SECR-10 | 34-05 | Task 1 | Full (backend) | Delete-account verified correct; path discrepancy comment added |
| SECR-10 | 34-06 | Task 1 | Full (frontend) | Settings Data tab with Delete section wired to POST /api/auth/delete-account |
| SECR-11 | 34-07 | Task 1+2 | Full | posthog.init() gated in index.html + CookieConsent.jsx accept handler fixed |
| SECR-12 | 34-08 | Task 1 | Full | PrivacyPolicy.jsx cookies section updated; App.js routing verified public |
| SECR-13 | 34-08 | Task 1 | Full | TermsOfService.jsx verified real content; App.js routing verified public |

**Coverage: 13/13 SECR requirements covered. Zero gaps.**

---

## File Ownership by Plan

Conflicts only exist within the same wave. Cross-wave conflicts are allowed (sequential plans overwrite prior plan changes by design).

### Wave 1 file ownership (must have zero overlap):

| Plan | Files Modified |
|------|---------------|
| 34-01 | backend/services/sanitize.py (NEW), backend/routes/auth.py, backend/routes/onboarding.py, backend/routes/persona.py, backend/routes/content.py, backend/routes/templates.py |
| 34-02 | backend/server.py |
| 34-03 | backend/middleware/security.py |
| 34-04 | backend/requirements.txt, frontend/package.json, .planning/phases/34-security-gdpr/SECURITY-EXCEPTIONS.md (NEW) |

**Wave 1 conflicts: ZERO** — all files are distinct across the four Wave 1 plans.

### Wave 2 file ownership:

| Plan | Files Modified |
|------|---------------|
| 34-05 | backend/routes/auth.py |
| 34-06 | frontend/src/pages/Dashboard/Settings.jsx |
| 34-07 | frontend/public/index.html, frontend/src/components/CookieConsent.jsx |
| 34-08 | frontend/src/pages/PrivacyPolicy.jsx, frontend/src/App.js, .planning/ROADMAP.md |

**Wave 2 conflicts: ZERO** — all files are distinct across the four Wave 2 plans.

**Note:** 34-01 (Wave 1) and 34-05 (Wave 2) both modify `backend/routes/auth.py`. This is intentional and safe — 34-01 adds the sanitize_text import and call, 34-05 adds the GDPR export gaps. They run sequentially (Wave 1 before Wave 2), so no conflict.

---

## Autonomous Flag Review

All 9 plans are `autonomous: true`. No billing code is modified in any plan — `backend/routes/billing.py` and `backend/services/stripe_service.py` are untouched. The CLAUDE.md billing review requirement is NOT triggered.

If during execution the executor discovers that any GDPR export or delete endpoint touches billing collections in a way that requires changes to billing files, the executor should pause and request human review per CLAUDE.md rule 7.

---

## Open Assumptions

1. **Redis is available in the test environment** — Plan 34-05 adds a per-user Redis rate limit with a try/except fallback. Tests that exercise the rate limit path will need Redis available (or the test should mock the Redis call). If `conftest.py` doesn't have a Redis fixture, plan 34-09 should mock `get_redis()` in the rate limit test.

2. **`pip-audit` or `safety` installable in CI** — Plan 34-04 installs `pip-audit` as a dev tool. If the CI environment restricts pip installs, use `safety check` instead (already familiar in Python security tooling).

3. **CookieConsent.jsx button text** — Plan 34-07 Task 2 looks for "Accept all" text. If the actual button text differs (e.g., "Accept All" or "Accept"), the RTL selector will fall back to `queryByTestId('consent-accept-btn')`. Executor must read CookieConsent.jsx before writing the test.

4. **SECR-01 completeness** — Plan 34-01 Task 2 performs an audit for missing Pydantic body models on POST endpoints and flags them with TODO comments. If the audit finds significant gaps (>5 endpoints without Pydantic models), a follow-up task may be needed. The task intentionally doesn't refactor missing Pydantic models in this plan (scope control) — it only flags them.

5. **`window.posthog.__loaded`** — This is the PostHog internal property used to check if `init()` was already called. If PostHog's API changes this property name in a future version, the CookieConsent.jsx check may need updating. The current PostHog version (as of April 2026) uses `__loaded`. Executor should verify this against the actual posthog library version in `frontend/public/index.html`.

---

## Plans That Are autonomous: false

**None.** All 9 plans are fully autonomous. The reasoning:

- No billing files are touched (CLAUDE.md rule 7 not triggered)
- No external service dashboard configuration is required
- CVE audit (Plan 34-04) makes targeted version bumps — not blind `--force` upgrades
- Consent gate changes are verifiable via grep and build test
- The GDPR UI (Plan 34-06) can be verified via `npm run build` and the existing test patterns

A human-verify checkpoint is NOT added because the Phase 34 verification will be done by the standard gsd-verify-phase command after all 9 plans execute. If the user wants a mid-phase visual checkpoint after Plan 34-07 (PostHog consent gate), they can run the app in a browser and verify the consent banner behavior in incognito mode.

---

## Research Source Alignment

Every plan in Phase 34 implements exactly what the research recommended:

| Research Finding | Implemented In | Match |
|-----------------|---------------|-------|
| Use html.escape() not bleach for JSON API | 34-01 (sanitize.py uses stdlib html.escape) | EXACT |
| PostHog fix must be in index.html not React | 34-07 (Task 1 modifies index.html) | EXACT |
| os.environ.get PORT in __main__ block — remove | 34-02 (removes __main__ block) | EXACT |
| GDPR export missing 4 collections | 34-05 (adds scheduled_posts, media_assets, workspace_memberships, authored_templates) | EXACT |
| Rate limit GDPR endpoints to 3/min | 34-03 (endpoint_limits dict) + 34-05 (per-user Redis) | EXACT |
| Update roadmap endpoint path | 34-08 (ROADMAP.md Task 2) | EXACT |
| Sentry PII scrubbing | 34-02 (_scrub_pii before_send callback) | EXACT |
| XSS test assertion must change direction | 34-09 (Task 1 — asserts &lt;script&gt; not literal) | EXACT |
| Privacy policy cookies section references banner | 34-08 (Task 1 — updates cookies section) | EXACT |
