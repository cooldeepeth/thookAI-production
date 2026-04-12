---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Distribution-Ready Platform Rebuild
status: executing
stopped_at: Completed 30-social-publishing-end-to-end/30-04-PLAN.md
last_updated: "2026-04-12T09:35:17.661Z"
last_activity: 2026-04-12
progress:
  total_phases: 27
  completed_phases: 4
  total_plans: 24
  completed_plans: 23
  percent: 96
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Every feature that exists in the codebase must actually work end-to-end — a user can sign up, onboard, generate content, schedule, publish, pay, and manage their account without hitting broken flows.
**Current focus:** Phase 30 — Social Publishing End-to-End

## Current Position

Phase: 30 (Social Publishing End-to-End) — EXECUTING
Plan: 4 of 4 — checkpoint human-verify reached (Tasks 1+2 complete, Task 3 code implemented)
Status: Ready to execute
Last activity: 2026-04-12

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 5
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
| ----- | ----- | ----- | -------- |
| 29    | 5     | -     | -        |

**Recent Trend:**

- Last 5 plans: none yet
- Trend: -

_Updated after each plan completion_
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
| Phase 23 P01 | 3 | 2 tasks | 6 files |
| Phase 23 P03 | 17 | 2 tasks | 7 files |
| Phase 23 P02 | 92 | 2 tasks | 5 files |
| Phase 30 P02 | 3 | 2 tasks | 2 files |
| Phase 30 P03 | 5 | 2 tasks | 3 files |
| Phase 30 P04 | 20 | 2 tasks | 3 files |

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
- [Phase 23-01]: No eject: jest.configure block added via craco.config.js jest key; MSW v2 with wildcard URL patterns; centralized lifecycle in setupTests.js
- [Phase 23-03]: EventSource mock must be in beforeEach/afterEach (not module scope) because babel hoists imports before global assignments execute
- [Phase 23-03]: react-router-dom v7.13.2 main field (dist/main.js) missing — Jest 27 needs explicit moduleNameMapper to dist/index.js; same for react-router/dom subpath
- [Phase 23]: AbortError timeout test: stub global.fetch (not MSW never-resolving handler) because MSW v2 Node mode does not propagate AbortError from intercepted handlers
- [Phase 23]: EventSource mock: re-assign in beforeEach (not module level) to survive resetMocks: true auto-reset between tests
- [Phase 30]: Proactive 24h refresh window prevents silent publish failures from stale tokens
- [Phase 30]: Instagram fb_exchange_token renewal: access_token passed as refresh input since Instagram has no separate refresh_token
- [Phase 30-03]: token_expiring_soon defaults False in disconnected platform dict — field always present to avoid frontend null checks
- [Phase 30-03]: Expiring-soon badge only shows when token_expiring_soon=true AND needs_reconnect=false — expired tokens use orange "Token Expired" badge
- [Phase 30-03]: Fernet round-trip test: monkeypatch.setattr on routes.platforms.ENCRYPTION_KEY (module-level var) ensures cipher uses test key without key-length fallback path
- [Phase 30]: LinkedIn registerUpload fallback: non-200 response falls back to text-only ensuring publishing never fails due to media upload errors
- [Phase 30]: X media upload uses v1.1 multipart upload; media_id_string attached to first tweet only
- [Phase 30]: Instagram publish_to_platform dispatcher confirmed to extract image_url from media_assets correctly — no code change needed

### Pending Todos

None yet.

### Blockers/Concerns

- CONCERNS.md documents race condition in credit deduction (credits.py) — fix required in Phase 5
- Celery files exist (celery_app.py, celeryconfig.py) but Procfile missing worker/beat entries — confirm in Phase 2
- Publishing placeholder in content_tasks.py fallback path — must be replaced in Phase 5
- 20+ worktree-agent-\* branches must be deleted before any new branches are created — Phase 1 prerequisite
- Stripe Price IDs are blank in .env.example — owner must create Stripe products; flag in Phase 5

## Session Continuity

Last session: 2026-04-12T09:35:17.657Z
Stopped at: Completed 30-social-publishing-end-to-end/30-04-PLAN.md
Resume file: None
