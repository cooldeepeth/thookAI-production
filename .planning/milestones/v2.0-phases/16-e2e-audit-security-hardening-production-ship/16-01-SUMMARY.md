---
phase: 16-e2e-audit-security-hardening-production-ship
plan: "01"
subsystem: testing
tags: [e2e, smoke-tests, dead-links, ci, testing]
dependency_graph:
  requires:
    - Phase 15 (Obsidian integration)
    - Phase 14 (Strategy Dashboard + Notifications)
    - Phase 13 (Analytics feedback loop)
    - Phase 12 (Strategist Agent)
    - Phase 09 (n8n bridge)
  provides:
    - E2E-01: Full critical path verified in automated tests
    - E2E-10: Dead link detection — no orphan API refs, no localhost leaks, no /tmp media URLs
  affects:
    - CI pipeline (both test files can run in GitHub Actions without external services)
tech_stack:
  added: []
  patterns:
    - "dependency_overrides[get_current_user] for auth bypass in tests"
    - "patch('database.db') for lazy-import database mocking in n8n/notifications routes"
    - "TestClient(app, raise_server_exceptions=False) for isolated route testing"
    - "inspect.getsource() for static verification of SSE and source patterns"
    - "pathlib.Path for file scanning in dead link tests (no subprocess)"
key_files:
  created:
    - backend/tests/test_e2e_critical_path.py
    - backend/tests/test_dead_links.py
  modified: []
decisions:
  - "SSE stream test uses inspect.getsource() not client.stream() — infinite polling loop prevents synchronous test client from returning"
  - "Schedule endpoint is in routes/dashboard.py (POST /api/dashboard/schedule/content) not routes/content.py"
  - "n8n_bridge and notifications use lazy 'from database import db' inside handlers — must patch 'database.db' not 'routes.n8n_bridge.db'"
  - "Merged dev branch into worktree before implementation — worktree was behind dev by all Phase 9-15 commits"
metrics:
  duration_seconds: 600
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_created: 2
  tests_added: 17
---

# Phase 16 Plan 01: E2E Critical Path + Dead Link Detection Summary

E2E smoke test suite (10 tests) verifies the full user journey from signup through strategy approve and second-cycle content generation; dead link detector (7 tests) confirms no orphan API references, no localhost leaks, and all routes registered.

## What Was Built

### Task 1: E2E Critical Path Smoke Tests (`backend/tests/test_e2e_critical_path.py`)

**617 lines, 10 tests** in `TestE2ECriticalPath` class covering:

1. `test_signup_creates_user` — POST /api/auth/register returns user_id + token, inserts user doc with credits=200
2. `test_onboarding_generates_persona` — POST /api/onboarding/generate-persona with 7 answers returns persona_card
3. `test_content_generation_starts` — POST /api/content/create returns job_id + status="running"
4. `test_schedule_then_publish` — POST /api/dashboard/schedule/content returns schedule confirmation
5. `test_analytics_poll_writes_performance` — POST /api/n8n/execute/poll-analytics-24h triggers update_post_performance
6. `test_strategy_approve_returns_generate_payload` — POST /api/strategy/{id}/approve returns generate_payload
7. `test_notification_stream_returns_sse_content_type` — Verifies notification_stream uses StreamingResponse with text/event-stream
8. `test_second_cycle_generation_after_approve` — Second content generation from strategy generate_payload succeeds
9. `test_get_job_status_after_generation` — GET /api/content/job/{id} returns job with correct fields
10. `test_full_critical_path_sequential` — Full journey: generate → schedule → approve → regenerate in one test

### Task 2: Dead Link Detection (`backend/tests/test_dead_links.py`)

**348 lines, 7 tests** across 4 test classes:

- `TestFrontendApiReferences.test_frontend_api_references_resolve` — Scans all frontend JS/JSX for /api/* strings, verifies each maps to a registered FastAPI route
- `TestNoHardcodedLocalhost.test_no_hardcoded_localhost_in_frontend` — No hardcoded localhost URLs outside REACT_APP_ fallback patterns
- `TestMediaUrlPatterns.test_media_url_uses_r2_public_url` — media_storage.py uses r2_public_url setting
- `TestMediaUrlPatterns.test_uploads_route_blocks_tmp_in_production` — uploads.py raises 503 (not /tmp fallback) in production
- `TestMediaUrlPatterns.test_media_storage_r2_public_url_in_get_public_url` — get_public_url() references r2_public_url
- `TestRouteRegistration.test_all_route_files_registered` — All .py files in routes/ are imported in server.py
- `TestRouteRegistration.test_all_route_files_include_router_called` — Every imported router alias has include_router() called

## Key Technical Decisions

**SSE stream test approach:** The `_sse_event_generator` is an infinite async loop with 10s sleep. Using `TestClient.stream()` would block indefinitely. Solution: use `inspect.getsource()` to verify the route returns `StreamingResponse` with `media_type="text/event-stream"` — static analysis instead of runtime.

**Database mocking for n8n_bridge and notifications:** Both modules use lazy `from database import db` inside handler bodies (not module-level imports). This means `patch("routes.n8n_bridge.db")` raises `AttributeError` (the attribute doesn't exist on the module). Solution: `patch("database.db", mock_db)` which patches the canonical import location.

**Schedule endpoint location:** The plan referenced `/api/content/{job_id}/schedule` but the actual endpoint is `POST /api/dashboard/schedule/content` in `routes/dashboard.py`. Tests updated to use the correct endpoint.

**Dev branch merge:** The worktree was created before Phase 9-15 work merged to dev. Merged dev into the worktree branch before implementing tests to ensure all new routes (n8n_bridge, strategy, obsidian) were available.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Onboarding uses update_one not insert_one**
- Found during: Task 1, test_onboarding_generates_persona
- Issue: Plan specified mocking `db.persona_engines.insert_one`, but `routes/onboarding.py` uses `db.persona_engines.update_one(upsert=True)` — causing AsyncMock error
- Fix: Changed mock to `db.persona_engines.update_one = AsyncMock()`
- Commit: 68b858c

**2. [Rule 1 - Bug] Schedule endpoint in wrong module**
- Found during: Task 1, test_schedule_then_publish
- Issue: Plan specified `/api/content/{job_id}/schedule`, but the endpoint is at `POST /api/dashboard/schedule/content` in routes/dashboard.py
- Fix: Updated tests to use the correct route and module
- Commit: 68b858c

**3. [Rule 1 - Bug] Lazy import database mocking for n8n_bridge/notifications**
- Found during: Task 1, test_analytics_poll_writes_performance and test_notification_stream
- Issue: `patch("routes.n8n_bridge.db")` fails with AttributeError — both modules use lazy imports inside function bodies
- Fix: Changed to `patch("database.db", mock_db)` to patch the canonical import location
- Commit: 68b858c

## Verification Results

All 17 tests pass in CI environment with no external service dependencies:

```
tests/test_e2e_critical_path.py::TestE2ECriticalPath  10 passed
tests/test_dead_links.py::TestFrontendApiReferences   1 passed
tests/test_dead_links.py::TestNoHardcodedLocalhost    1 passed
tests/test_dead_links.py::TestMediaUrlPatterns        3 passed
tests/test_dead_links.py::TestRouteRegistration       2 passed
Total: 17 passed in 0.91s
```

## Known Stubs

None — both test files fully implement their intended functionality.

## Self-Check: PASSED

- [x] `backend/tests/test_e2e_critical_path.py` exists (617 lines, min 200 required)
- [x] `backend/tests/test_dead_links.py` exists (348 lines, min 80 required)
- [x] Task 1 commit exists: 68b858c
- [x] Task 2 commit exists: f867a07
- [x] Both test files pass: 17/17 tests
