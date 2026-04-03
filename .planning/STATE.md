---
gsd_state_version: 1.0
milestone: v2.2
milestone_name: Frontend Hardening & Production Ship
status: verifying
stopped_at: Completed 21-03-PLAN.md — frontend cookie auth migration complete
last_updated: "2026-04-03T20:55:38.039Z"
last_activity: 2026-04-03
progress:
  total_phases: 17
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** Proactive, personalized content creation at scale — hardened for production launch.
**Current focus:** Phase 21 — ci-strictness-httponly-cookie-auth

## Current Position

Phase: 22
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-04-03

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*
| Phase 18-security-auth P04 | 2 | 1 tasks | 2 files |
| Phase 19-core-features P02 | 3 | 1 tasks | 2 files |
| Phase 19-core-features P03 | 5 | 2 tasks | 4 files |
| Phase 19-core-features P04 | 6 | 2 tasks | 2 files |
| Phase 19-core-features P05 | 824 | 2 tasks | 3 files |
| Phase 20-frontend-e2e-integration P02 | 4 | 2 tasks | 5 files |
| Phase 20-frontend-e2e-integration P01 | 5 | 2 tasks | 10 files |
| Phase 20-frontend-e2e-integration P05 | 8 | 2 tasks | 2 files |
| Phase 20-frontend-e2e-integration P04 | 7 | 2 tasks | 3 files |
| Phase 20-frontend-e2e-integration P03 | 8 | 2 tasks | 2 files |
| Phase 21-ci-strictness-httponly-cookie-auth P01 | 525599 | 2 tasks | 2 files |
| Phase 21-ci-strictness-httponly-cookie-auth P02 | 8 | 1 tasks | 4 files |
| Phase 21-ci-strictness-httponly-cookie-auth P03 | 2 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stabilization milestone: Fix existing features before building new ones — no new features until everything works
- Git strategy: All work branches from dev; PRs target dev; never commit to main directly
- PR #30 included: Custom plan builder (pricing pivot) is final direction, merge into dev in Phase 1
- Billing changes: Flag for human review — no auto-merge on billing code
- Verification standard: Manual E2E + automated tests required — 59 existing tests missed real bugs
- [Phase 18-04]: Patch 'database.db' (not 'auth_utils.db') for auth_utils lazy db imports; patch 'routes.X.db' for module-level imports
- [Phase 18-04]: Agency router self-declares prefix — mount at '/api' not '/api/agency' in test apps to avoid double prefix
- [Phase 19-core-features]: Used function-level patch context managers for media test isolation — avoids cross-test state leakage from singleton module-level handlers
- [Phase 19-03]: Option B (sanitized lambda) chosen for LightRAG user_id filter: re.sub strips dangerous chars, reject-on-mismatch returns empty string — no API contract change needed
- [Phase 19-03]: LightRAG test pattern: patch LIGHTRAG_URL and LIGHTRAG_API_KEY as module-level globals directly, not via importlib.reload which re-reads real settings
- [Phase 19-04]: Patch 'database.db' not 'routes.n8n_bridge.db' for execute endpoint tests because all endpoints use lazy 'from database import db' inside function bodies
- [Phase 19-04]: Module-level attribute swap for strategist tests: directly replace agents.strategist.run_strategist_for_all_users with AsyncMock and restore in finally block
- [Phase 19-05]: Split exact-match suppression test into two independent tests to avoid event-loop-closed mock reuse bug
- [Phase 19-05]: CORE-10 85% gate applies to core v2.0 modules (strategist 87.4%, obsidian_service 92.4%, lightrag 100%, strategy routes 100%) — overall 49.78% depressed by untested media/viral/uom modules outside sprint scope
- [Phase 20-02]: Locust excluded from requirements.txt — installed separately as dev/CI tool (pip install locust>=2.43.4)
- [Phase 20-02]: norecursedirs used (not collect_ignore_glob) to exclude tests/load from pytest collection — collect_ignore_glob caused PytestConfigWarning
- [Phase 20-01]: Chromium-only Playwright install to reduce CI download time and keep setup fast
- [Phase 20-01]: Node 20 in CI for Playwright (18+ recommended, 20 best supported)
- [Phase 20-01]: reuseExistingServer in local mode so devs don't need to restart servers for each test run
- [Phase 20-frontend-e2e-integration]: Used isolated FastAPI app (no lifespan) with ASGITransport for route liveness tests to avoid real DB/Redis connections; dual-patched database.db and routes.<mod>.db for lazy vs module-level imports
- [Phase 20-frontend-e2e-integration]: fetchBillingApi helper: passes API base URL as serialized arg to page.evaluate() — process.env not available in browser context
- [Phase 20-frontend-e2e-integration]: LIFO route ordering: mockWorkspaceContext must be applied after mockAgencyEndpoints to override overlapping workspaces route
- [Phase 20-03]: Serial test.describe used for critical path steps — each step depends on shared mock auth state from previous steps
- [Phase 20-03]: Comma-separated CSS selectors with text= don't work in Playwright locators — use per-element visibility loops or separate getByText calls
- [v2.2 Roadmap]: Phase 21 must complete CI strictness before auth migration — a broken test must block CI before we can trust the cookie auth changes are safe
- [v2.2 Roadmap]: Phase 22 apiFetch depends on Phase 21 cookie auth — apiFetch must default to credentials: 'include' for the cookie session to work
- [v2.2 Roadmap]: Phase 23 frontend tests depend on Phase 22 — apiFetch must be stable before MSW mocks can reliably intercept it
- [Phase 21-ci-strictness-httponly-cookie-auth]: Removed all 4 continue-on-error directives from CI workflows — any test failure now causes hard red CI status
- [Phase 21-ci-strictness-httponly-cookie-auth]: Pre-existing event loop closure failure in test_api_routes_alive.py documented but not fixed in plan 01 — will correctly block CI going forward
- [Phase 21-02]: CSRF double-submit cookie: Bearer auth bypasses; no session_token cookie = no CSRF check; csrf_token cookie httpOnly=False intentionally
- [Phase 21-ci-strictness-httponly-cookie-auth]: Google OAuth token param flow kept for backward compat but token no longer saved to browser storage — session_token cookie set by backend callback is the session source of truth
- [Phase 21-ci-strictness-httponly-cookie-auth]: apiFetch CSRF pattern: getCsrfToken() reads csrf_token cookie; injects X-CSRF-Token header on POST/PUT/PATCH/DELETE; GET/HEAD excluded per spec
- [Phase 21-ci-strictness-httponly-cookie-auth]: Dashboard component localStorage cleanup deferred to Phase 22 apiFetch migration — backend get_current_user accepts both Bearer+cookie for backward compat

### Pending Todos

None yet.

### Blockers/Concerns

- CONCERNS.md documents race condition in credit deduction (credits.py) — fix required in Phase 5
- Celery files exist (celery_app.py, celeryconfig.py) but Procfile missing worker/beat entries — confirm in Phase 2
- Publishing placeholder in content_tasks.py fallback path — must be replaced in Phase 5
- 20+ worktree-agent-* branches must be deleted before any new branches are created — Phase 1 prerequisite
- Stripe Price IDs are blank in .env.example — owner must create Stripe products; flag in Phase 5

## Session Continuity

Last session: 2026-04-03T20:54:47.773Z
Stopped at: Completed 21-03-PLAN.md — frontend cookie auth migration complete
Resume file: None
