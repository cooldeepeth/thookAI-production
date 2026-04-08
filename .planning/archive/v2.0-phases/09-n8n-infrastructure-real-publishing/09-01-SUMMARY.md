---
phase: 09-n8n-infrastructure-real-publishing
plan: 01
subsystem: infra
tags: [n8n, hmac, webhook, fastapi, httpx, celery-replacement]

# Dependency graph
requires: []
provides:
  - N8nConfig dataclass in config.py with 7 workflow ID fields and is_configured() method
  - POST /api/n8n/callback endpoint with HMAC-SHA256 verification (X-ThookAI-Signature header)
  - POST /api/n8n/trigger/{workflow_name} endpoint with JWT auth protection
  - Timing-safe signature verification via hmac.compare_digest
  - All N8N_* env vars documented in .env.example
  - 12 unit tests covering callback, trigger, and HMAC verification
affects: [09-02, 09-03, all phases using n8n workflow orchestration]

# Tech tracking
tech-stack:
  added: [httpx (already in requirements), hmac+hashlib (stdlib)]
  patterns:
    - N8nConfig dataclass following existing settings pattern in config.py
    - HMAC-SHA256 signature verification with hmac.compare_digest for timing safety
    - Router prefix pattern (/n8n) consistent with existing routes

key-files:
  created:
    - backend/routes/n8n_bridge.py
    - backend/tests/test_n8n_bridge.py
  modified:
    - backend/config.py (N8nConfig dataclass + Settings.n8n field)
    - backend/server.py (import + api_router.include_router registration)
    - backend/.env.example (N8N_* env var documentation)

key-decisions:
  - "HMAC-SHA256 over full request body bytes for n8n callback authentication — consistent with existing webhook_service.py pattern"
  - "hmac.compare_digest used for constant-time comparison to prevent timing attacks"
  - "Trigger endpoint returns 404 for unconfigured (None) workflow IDs — explicit failure over silent no-op"
  - "N8nConfig.is_configured() requires both n8n_url AND webhook_secret — URL alone is insufficient"

patterns-established:
  - "n8n callback authentication: raw body bytes → HMAC-SHA256 → X-ThookAI-Signature header comparison"
  - "Workflow name-to-ID mapping via _get_workflow_map() dict — all 7 task workflows addressable by kebab-case name"
  - "settings.n8n.* pattern for all n8n config access — never os.environ.get() in route files"

requirements-completed: [N8N-01, N8N-02]

# Metrics
duration: 4min
completed: 2026-03-31
---

# Phase 09 Plan 01: n8n Webhook Bridge Foundation Summary

**HMAC-SHA256-authenticated n8n callback endpoint and auth-protected workflow trigger endpoint wired into FastAPI, with N8nConfig dataclass and 12 passing unit tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-31T21:15:03Z
- **Completed:** 2026-03-31T21:18:24Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- N8nConfig dataclass with n8n_url, webhook_secret, api_key, backend_callback_url, 7 workflow_* ID fields, and is_configured() method added to config.py
- POST /api/n8n/callback with HMAC-SHA256 signature verification (X-ThookAI-Signature header, timing-safe via hmac.compare_digest) registered in server.py
- POST /api/n8n/trigger/{workflow_name} auth-protected endpoint mapping 7 workflow names to n8n webhook IDs
- 12 unit tests covering all acceptance criteria: valid/invalid/missing signature, empty secret, known/unknown/unconfigured workflow, auth requirement

## Task Commits

Each task was committed atomically:

1. **Task 1: Create N8nConfig dataclass and n8n_bridge route with HMAC verification** - `9d4987f` (feat)
2. **Task 2: Unit tests for n8n bridge route** - `f85e845` (test)

## Files Created/Modified
- `backend/routes/n8n_bridge.py` - n8n webhook bridge with HMAC callback and auth-protected trigger endpoints
- `backend/tests/test_n8n_bridge.py` - 12 unit tests (TestHmacVerification, TestN8nCallback, TestN8nTrigger)
- `backend/config.py` - N8nConfig dataclass (16 fields + is_configured()) and Settings.n8n field
- `backend/server.py` - Import and registration of n8n_bridge_router via api_router
- `backend/.env.example` - N8N_URL, N8N_WEBHOOK_SECRET, N8N_API_KEY, N8N_BACKEND_CALLBACK_URL, 7 N8N_WORKFLOW_* vars

## Decisions Made
- Used `hmac.compare_digest` (not `==`) for timing-safe signature comparison — prevents timing oracle attacks on HMAC verification
- Trigger endpoint returns 404 for both unknown workflow names AND workflow names with None IDs — explicit over silent
- `is_configured()` requires BOTH url AND secret — URL alone means n8n is reachable but not authenticated
- Workflow map built per-request via `_get_workflow_map()` so settings patches work in tests without module-level caching

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The `lru_cache` on `get_settings()` required using `patch("routes.n8n_bridge.settings")` rather than patching `config.settings` directly in tests — this is the standard pattern used elsewhere in the test suite.

## User Setup Required

None - no external service configuration required for this plan. N8n workflow IDs are configured via env vars when n8n is deployed (Phase 09-02 and beyond).

## Known Stubs

None - no UI-facing stubs. N8N_WORKFLOW_* env vars are intentionally empty in .env.example as they are populated after creating workflows in the n8n UI (a human-action step outside this plan's scope).

## Next Phase Readiness
- n8n bridge HTTP contract is complete and tested — Plan 09-02 (Docker Compose with n8n service) can depend on these endpoints
- /api/n8n/callback is ready to receive signed callbacks from n8n workflows
- /api/n8n/trigger/* is ready for manual/programmatic workflow triggering
- All 7 scheduled task workflows are addressable by name once workflow IDs are populated

---
*Phase: 09-n8n-infrastructure-real-publishing*
*Completed: 2026-03-31*
