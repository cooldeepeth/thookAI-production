---
phase: 15-obsidian-vault-integration
plan: 03
subsystem: api
tags: [obsidian, fernet, vault, config, crud, path-sandboxing, routes, python, fastapi]

# Dependency graph
requires:
  - phase: 15-01
    provides: "obsidian_service.py with _validate_vault_path + search_vault exports"
  - phase: 15-02
    provides: "Scout agent integration uses search_vault()"

provides:
  - "POST /api/obsidian/config — save Fernet-encrypted vault config in db.users"
  - "GET /api/obsidian/config — retrieve config with masked API key"
  - "DELETE /api/obsidian/config — remove vault config"
  - "POST /api/obsidian/test — test vault connection via search_vault"
  - "vault_path_display field showing exact path ThookAI will read"
  - "OBS-05 path traversal rejection (400) at route save time"
  - "OBS-06 per-user opt-in config with Fernet-encrypted API key"
  - "18 route-level tests (48 total Phase 15 tests pass)"

affects:
  - "frontend: Settings page Obsidian section wires to these endpoints"
  - "server.py: obsidian_router registered in api_router"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fernet key normalisation pattern (SHA-256 hash then base64 for non-44-byte keys)"
    - "field_validator for base_url non-empty enforcement"
    - "_mask_api_key shows only last 4 chars of decrypted key"

# Key files
key-files:
  created:
    - backend/routes/obsidian.py
    - backend/tests/test_obsidian_routes.py
  modified:
    - backend/server.py

# Decisions
decisions:
  - "Fernet key normalisation mirrors routes/platforms.py _get_cipher() exactly — SHA-256 hash then base64-encode for non-44-byte keys, ensuring any FERNET_KEY value works"
  - "vault_path_display shows 'entire vault' when vault_path is empty — explicit user communication per OBS-06 opt-in UX"
  - "_validate_vault_path imported directly from obsidian_service — single source of truth for path traversal logic (OBS-05)"
  - "POST /api/obsidian/test returns connected=false with error message (not 500) so frontend can surface vault unreachable state gracefully"

# Metrics
metrics:
  duration_seconds: 151
  completed_date: "2026-04-01"
  tasks_completed: 1
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 15 Plan 03: Obsidian Config CRUD Routes Summary

**One-liner:** Obsidian config CRUD endpoints (POST/GET/DELETE) + connection test, Fernet-encrypted API key in db.users, path traversal blocked at 400, vault_path_display shows exact subdirectory before activation.

## What Was Built

Four FastAPI endpoints in `backend/routes/obsidian.py` implementing OBS-06 opt-in Obsidian vault integration with OBS-05 path sandboxing:

- **POST /api/obsidian/config** — validates vault_path (400 on traversal/absolute path), Fernet-encrypts API key, stores `obsidian_config` sub-doc in `db.users`, returns `vault_path_display` showing "ThookAI will read files from: {path}"
- **GET /api/obsidian/config** — reads config, masks API key to "****last4", returns `{"configured": false}` when none set
- **DELETE /api/obsidian/config** — `$unset` obsidian_config from db.users
- **POST /api/obsidian/test** — calls `search_vault(topic="test connection", user_id=...)`, returns `{"connected": true/false, "notes_found": N}` or error message

Router registered in `server.py` after `strategy_router`.

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Obsidian config CRUD routes + connection test + server registration | Complete | a8d877a |
| 2 | Checkpoint: human verify endpoints | Checkpoint | — |

## Test Results

```
tests/test_obsidian_service.py  30 passed
tests/test_obsidian_routes.py   18 passed
Total Phase 15 tests:           48 passed
```

All 18 route tests cover: valid save, encryption verification, path traversal (../../etc), absolute path (/etc/passwd), empty base_url (422), empty vault_path display, GET masked key, GET no config, DELETE $unset, DELETE user filter, test connected, test exception, test user_id passed, auth 401 x4.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all four endpoints are fully wired to database and obsidian_service.

## Self-Check: PASSED

Files created:
- FOUND: /Users/kuldeepsinhparmar/thookAI-production/backend/routes/obsidian.py
- FOUND: /Users/kuldeepsinhparmar/thookAI-production/backend/tests/test_obsidian_routes.py

Commits:
- FOUND: a8d877a feat(15-03): Obsidian config CRUD routes + connection test
