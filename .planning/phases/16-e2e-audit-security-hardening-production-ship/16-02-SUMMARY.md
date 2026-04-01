---
phase: 16-e2e-audit-security-hardening-production-ship
plan: "02"
subsystem: infrastructure-security
tags:
  - docker
  - n8n
  - security-hardening
  - network-isolation
  - production
dependency_graph:
  requires:
    - docker-compose.yml (n8n base config)
    - backend/routes/n8n_bridge.py (n8n communication pattern)
  provides:
    - docker-compose.prod.yml (production n8n network isolation)
    - backend/tests/test_n8n_security.py (security configuration verification)
  affects:
    - n8n public accessibility (E2E-02)
    - execution history storage (E2E-09)
tech_stack:
  added:
    - PyYAML>=6.0.0 (test utility for docker-compose YAML parsing)
  patterns:
    - Docker Compose override pattern (docker-compose.prod.yml merges with base)
    - Internal Docker bridge network (internal: true blocks external routing)
    - n8n basic auth for defence-in-depth within internal network
key_files:
  created:
    - docker-compose.prod.yml
    - backend/tests/test_n8n_security.py
  modified:
    - docker-compose.yml (DEV ONLY comment on n8n ports line)
    - backend/requirements.txt (added PyYAML>=6.0.0)
decisions:
  - Production docker-compose.prod.yml uses ports:[] to remove host-published ports (merges cleanly over base list)
  - thookai-internal network uses internal:true to block all external routing at Docker daemon level
  - Only backend and frontend attached to thookai-public — all other services are internal-only
  - mongo, redis, postgres-n8n ports also removed in prod (defence-in-depth beyond n8n)
  - PyYAML added to requirements.txt as explicit test utility dependency (was transitive only)
metrics:
  duration: "3m"
  completed: "2026-04-01T12:33:33Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 16 Plan 02: n8n Security Hardening Summary

**One-liner:** Production Docker Compose isolates n8n to an internal-only Docker bridge network with basic auth, removing port 5678 from host exposure, plus 7 pytest tests verifying E2E-02 and E2E-09 security requirements.

## What Was Built

### Task 1: Production Docker Compose with n8n network isolation (`6dd2968`)

Created `docker-compose.prod.yml` as a production override file used via:
```
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Key changes in the production override:
- **n8n port exposure removed**: `ports: []` replaces `ports: ["5678:5678"]` — n8n is unreachable from outside Docker
- **n8n basic auth enabled**: `N8N_BASIC_AUTH_ACTIVE=true` with credentials from env vars (never hardcoded)
- **Network isolation**: `thookai-internal` bridge network with `internal: true` blocks all external routing at Docker daemon level
- **Backend/frontend only** on `thookai-public` network (host-reachable)
- **All internal services** (n8n, n8n-worker, lightrag, remotion, mongo, redis, postgres-n8n, celery-worker) isolated to `thookai-internal`
- **lightrag and remotion** also de-exposed in production (`ports: []`)
- `docker-compose.yml` n8n ports line annotated with `# DEV ONLY — overridden in docker-compose.prod.yml`

### Task 2: n8n security verification tests (`081e0d6`)

Created `backend/tests/test_n8n_security.py` with 7 tests in `TestN8nSecurityConfig`:

| Test | What it verifies | Requirement |
|------|------------------|-------------|
| `test_n8n_block_env_access_in_node` | `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` in base n8n | Security |
| `test_n8n_execution_pruning_max_age` | `EXECUTIONS_DATA_MAX_AGE=336` in base n8n | E2E-09 |
| `test_n8n_execution_pruning_max_count` | `EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000` in base n8n | E2E-09 |
| `test_n8n_worker_block_env_access` | `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` in n8n-worker | Security |
| `test_prod_n8n_no_public_ports` | prod n8n has `ports: []` + `expose: ["5678"]` | E2E-02 |
| `test_prod_n8n_basic_auth_active` | prod n8n has `N8N_BASIC_AUTH_ACTIVE=true` | E2E-02 |
| `test_prod_internal_network_defined` | `thookai-internal.internal: true` in networks | E2E-02 |

Tests use PyYAML to parse docker-compose files (not string grep) for structural correctness verification.

## Success Criteria Met

- [x] E2E-02: n8n instance not publicly accessible in production — ports removed (`ports: []`), basic auth enabled (`N8N_BASIC_AUTH_ACTIVE=true`), internal network isolation (`internal: true`)
- [x] E2E-09: Execution history pruning configured at 336h max age (`EXECUTIONS_DATA_MAX_AGE=336`) and 10000 max count (`EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000`)
- [x] `docker-compose.prod.yml` exists with 67 lines (above 40-line minimum)
- [x] `backend/tests/test_n8n_security.py` exists with 150 lines (above 60-line minimum)
- [x] All 7 security tests pass: `7 passed in 0.06s`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Dependency] Added PyYAML to requirements.txt**
- **Found during:** Task 2 (test import failed with `ModuleNotFoundError: No module named 'yaml'`)
- **Issue:** Tests require `import yaml` but `PyYAML` was not explicitly listed in `backend/requirements.txt` (only present as a transitive dependency)
- **Fix:** Added `PyYAML>=6.0.0` under a `# Test utilities` section in `requirements.txt`
- **Files modified:** `backend/requirements.txt`
- **Commit:** `081e0d6`

**2. [Rule 2 - Defence in depth] Removed prod ports for mongo, redis, postgres-n8n**
- **Found during:** Task 1 (architectural review of docker-compose.yml)
- **Issue:** The plan specified removing ports for n8n, lightrag, and remotion. However, mongo (27017), redis (6379), and postgres-n8n also expose host ports in the base file — leaving them open in production would undermine the network isolation goal.
- **Fix:** Added `ports: []` overrides for mongo, redis, and postgres-n8n in `docker-compose.prod.yml`
- **Files modified:** `docker-compose.prod.yml`
- **Commit:** `6dd2968`

## Known Stubs

None. Both artifacts (docker-compose.prod.yml and test_n8n_security.py) are complete and functional.

## Self-Check: PASSED

Files exist:
- `/Users/kuldeepsinhparmar/thookAI-production/docker-compose.prod.yml` — FOUND
- `/Users/kuldeepsinhparmar/thookAI-production/backend/tests/test_n8n_security.py` — FOUND

Commits exist:
- `6dd2968` feat(16-02): production Docker Compose — FOUND
- `081e0d6` test(16-02): n8n security verification tests — FOUND

Test results: 7 passed in 0.06s
