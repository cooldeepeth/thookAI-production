---
phase: 15-obsidian-vault-integration
plan: 01
subsystem: api
tags: [obsidian, httpx, config, fernet, path-sandboxing, vault, python]

# Dependency graph
requires:
  - phase: 09-n8n-infrastructure-real-publishing
    provides: "n8n bridge established as sidecar service integration pattern"
  - phase: 10-lightrag-knowledge-graph
    provides: "lightrag_service.py lazy import + non-fatal HTTP client pattern"
  - phase: 12-strategist-agent
    provides: "strategist.py _gather_user_context pattern for signal injection"

provides:
  - "ObsidianConfig dataclass in config.py with is_configured() gate"
  - "backend/services/obsidian_service.py: search_vault, get_recent_notes, is_configured"
  - "_validate_vault_path() with path traversal prevention (OBS-05)"
  - "_resolve_config() per-user override with global env fallback"
  - "_decrypt_obsidian_api_key() Fernet decryption mirroring platforms.py pattern"
  - "OBSIDIAN_BASE_URL + OBSIDIAN_API_KEY documented in .env.example"
  - "30 unit tests covering all behaviors"

affects:
  - "15-02: Scout agent integration uses search_vault()"
  - "15-03: Strategist uses get_recent_notes() + frontend opt-in Settings"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pathlib.PurePosixPath for URL path traversal prevention (no filesystem access required)"
    - "Per-user DB config with Fernet-encrypted API key, falls back to global env vars"
    - "Non-fatal async HTTP client with 10s timeout, returns empty result on any failure"
    - "is_configured() sync gate uses settings check, _resolve_config() async for accurate per-user check"

key-files:
  created:
    - "backend/services/obsidian_service.py"
    - "backend/tests/test_obsidian_service.py"
  modified:
    - "backend/config.py"
    - "backend/.env.example"

key-decisions:
  - "PurePosixPath(vault_path).parts check for '..' component — catches traversal without filesystem access, works for remote vault paths"
  - "Per-user obsidian_config in db.users.obsidian_config (Fernet-encrypted API key) takes precedence over global env fallback — same isolation model as platform OAuth tokens"
  - "is_configured() is synchronous (reads settings only) — callers needing per-user check must use async _resolve_config()"
  - "verify=False in httpx.AsyncClient — Obsidian REST API uses self-signed certificate on local port 27124; tunnel endpoints may have valid certs but sync via verify=False is correct default"
  - "vault_path sandbox enforced at service layer, not Obsidian API layer — Obsidian REST API has no subdirectory restriction"

patterns-established:
  - "obsidian_service.py follows lightrag_service.py non-fatal HTTP client pattern exactly"
  - "path traversal: _validate_vault_path(path) raises ValueError before any HTTP call — secure by default"
  - "_resolve_config() tuple return (base_url, api_key, vault_path) — callers check base_url truthy before proceeding"

requirements-completed:
  - OBS-03
  - OBS-04
  - OBS-05

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 15 Plan 01: Obsidian Vault Integration — Foundation Summary

**ObsidianConfig dataclass + obsidian_service.py HTTP client with PurePosixPath path traversal prevention, per-user Fernet-encrypted config, and 30 passing tests.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-01T11:48:13Z
- **Completed:** 2026-04-01T11:53:07Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments

- Created `backend/services/obsidian_service.py` with full Obsidian Local REST API client — search_vault (OBS-01 prerequisite), get_recent_notes (OBS-02 prerequisite), is_configured, _validate_vault_path, _resolve_config, _decrypt_obsidian_api_key
- Added `ObsidianConfig` dataclass to `backend/config.py` following LightRAGConfig/N8nConfig pattern (OBS-03)
- Implemented strict path sandboxing via `PurePosixPath.parts` — blocks `../`, absolute paths, and Windows drive letters without filesystem access (OBS-05)
- All 30 unit tests pass — coverage includes path traversal edge cases, graceful degradation when not configured (OBS-04), Fernet decryption, per-user override logic

## Task Commits

Each task was committed atomically:

1. **TDD RED: test_obsidian_service.py (failing tests)** - `9f3e93d` (test)
2. **TDD GREEN: ObsidianConfig + obsidian_service.py + env vars** - `f390d50` (feat)

_Note: TDD task had 2 commits (test RED → implementation GREEN). Tests adjusted for is_configured() sync vs async signature during GREEN phase._

## Files Created/Modified

- `backend/config.py` - Added ObsidianConfig dataclass + Settings.obsidian field
- `backend/services/obsidian_service.py` - New Obsidian Local REST API HTTP client with path sandboxing
- `backend/.env.example` - Added OBSIDIAN_BASE_URL + OBSIDIAN_API_KEY documentation
- `backend/tests/test_obsidian_service.py` - 30 unit tests (TDD)

## Decisions Made

- **PurePosixPath for path validation**: `PurePosixPath(vault_path).parts` traversal check doesn't require filesystem access — correct approach for remote vault paths over HTTP
- **Per-user config with Fernet**: db.users.obsidian_config stores `api_key_encrypted` (Fernet) — mirrors existing platform OAuth token encryption pattern in routes/platforms.py
- **verify=False for httpx**: Obsidian REST API uses a self-signed SSL certificate by default; verify=False is the correct default for local dev and valid for production tunnel testing
- **Sync is_configured() vs async _resolve_config()**: sync check uses settings.obsidian.is_configured() for import-time guards; callers needing per-user accuracy call async _resolve_config()

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test: is_configured() mock approach adjusted for sync vs async**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Tests mocked `_resolve_config` (async) for `is_configured()` (sync), causing false assertion failure
- **Fix:** Updated 2 tests in TestIsConfigured to patch `settings.obsidian.is_configured` directly matching the sync implementation
- **Files modified:** `backend/tests/test_obsidian_service.py`
- **Committed in:** `f390d50` (part of GREEN phase commit)

**2. [Rule 1 - Bug] Error message casing mismatch in _validate_vault_path**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Error message started with capital "Path traversal blocked" but test matched lowercase "path traversal"
- **Fix:** Changed all ValueError messages in _validate_vault_path to start lowercase
- **Files modified:** `backend/services/obsidian_service.py`
- **Committed in:** `f390d50` (part of GREEN phase commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes were minor test/message corrections. No scope change.

## Issues Encountered

Pre-existing test failure in `test_pipeline_e2e.py::TestBeatScheduleHasCleanupStaleJobs::test_beat_schedule_has_cleanup_stale_jobs` — beat_schedule is empty dict. This is out-of-scope and pre-dates Phase 15. No action taken.

## User Setup Required

None - no external service configuration required for this plan. OBSIDIAN_BASE_URL and OBSIDIAN_API_KEY are optional env vars that enable the feature when set.

## Next Phase Readiness

Ready for Plan 02 (Scout agent integration):
- `search_vault(topic, user_id)` is available and tested
- `is_configured()` feature gate is available
- Lazy import pattern matches existing scout.py import style

Plan 03 (Frontend Settings page + routes) depends on `is_configured()` and the per-user DB config schema documented in obsidian_service.py.

## Self-Check: PASSED

- FOUND: backend/services/obsidian_service.py
- FOUND: backend/tests/test_obsidian_service.py
- FOUND: .planning/phases/15-obsidian-vault-integration/15-01-SUMMARY.md
- FOUND commit: 9f3e93d (test RED phase)
- FOUND commit: f390d50 (feat GREEN phase)

---
*Phase: 15-obsidian-vault-integration*
*Completed: 2026-04-01*
