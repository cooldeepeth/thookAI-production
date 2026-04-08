---
phase: 02-infrastructure-celery
plan: 02
subsystem: backend-config
tags: [startup-validation, health-check, env-vars, monitoring]
dependency_graph:
  requires: []
  provides: [validate_required_env_vars, hardened-health-endpoint]
  affects: [backend/config.py, backend/server.py, backend/.env.example]
tech_stack:
  added: []
  patterns: [fail-fast startup validation, structured health check response]
key_files:
  created: []
  modified:
    - backend/config.py
    - backend/server.py
    - backend/.env.example
decisions:
  - "MongoDB failure in /health returns 503 (not 200 with degraded status) — critical service down must be immediately detectable by load balancers"
  - "Only MongoDB is 'critical_down' — Redis/R2/LLM are checked and reported but don't trigger 503 since app can partially function without them"
  - "Removed duplicate /api/health endpoint — root /health is canonical health check for Render/load balancers"
  - "validate_required_env_vars uses plain list[str] return type (not List[str]) for Python 3.10+ compatibility without import"
metrics:
  duration: "12 minutes"
  completed_date: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
requirements_satisfied: [INFRA-04, INFRA-05]
---

# Phase 02 Plan 02: Startup Env Var Validation and Health Endpoint Hardening Summary

Startup now validates required environment variables with per-var `CRITICAL` log messages and fails fast in production. The `/health` endpoint returns structured per-service status with HTTP 503 when MongoDB is unreachable. `.env.example` documents all 81 environment variables used across config.py.

## What Was Built

### Task 1: validate_required_env_vars() and .env.example completion

Added `validate_required_env_vars()` function to `backend/config.py`:
- Always checks: `MONGO_URL`, `DB_NAME`, `JWT_SECRET_KEY`, `FERNET_KEY` (including placeholder value detection)
- In production additionally checks: `REDIS_URL`, all 5 R2 vars, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `ENCRYPTION_KEY`, and at least one LLM key
- Returns list of missing variable names

Called from `backend/server.py` lifespan immediately after `settings.log_startup_info()`:
- Logs each missing var as `CRITICAL: MISSING REQUIRED ENV VAR: {var}`
- In production: raises `RuntimeError` halting startup
- In development: logs `WARNING` and continues with reduced functionality

Completed `backend/.env.example` from 69 to 81 documented vars, adding:
- `ENCRYPTION_KEY` (platform OAuth token encryption)
- `PINECONE_ENVIRONMENT` (vector store region)
- `RUNWAY_API_KEY`, `PIKA_API_KEY`, `HEYGEN_API_KEY`, `DID_API_KEY` (video generation)
- `PLAYHT_API_KEY`, `PLAYHT_USER_ID`, `GOOGLE_TTS_API_KEY` (voice/TTS)
- `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` (LinkedIn OAuth)
- `META_APP_ID`, `META_APP_SECRET` (Meta/Instagram OAuth)
- `TWITTER_API_KEY`, `TWITTER_API_SECRET` (Twitter/X OAuth)

### Task 2: Hardened /health endpoint

Replaced the flat `/health` response structure with a nested `services` dict:

```json
{
  "status": "ok",
  "timestamp": "2026-03-31T...",
  "services": {
    "mongodb": {"status": "connected"},
    "redis": {"status": "not_configured"},
    "r2_storage": {"status": "not_configured"},
    "llm": {"status": "configured"}
  }
}
```

- MongoDB failure sets `critical_down = True` → HTTP 503 (was returning 200 with "degraded")
- Redis, R2, LLM failures are reported but do not trigger 503
- Removed the duplicate `GET /api/health` endpoint entirely — root `/health` is the canonical check

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | d485109 | feat(02-02): add startup env var validation and complete .env.example |
| 2 | 2939cc7 | feat(02-02): harden /health endpoint with structured service checks and 503 on MongoDB down |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no stub data or placeholder values introduced.

## Self-Check: PASSED

- `backend/config.py` contains `def validate_required_env_vars`: FOUND
- `backend/server.py` contains `validate_required_env_vars` call: FOUND (2 references)
- `backend/server.py` contains `MISSING REQUIRED ENV VAR:`: FOUND
- `backend/.env.example` contains `ENCRYPTION_KEY`: FOUND
- `backend/.env.example` contains `LINKEDIN_CLIENT_ID`: FOUND
- `backend/.env.example` contains `META_APP_ID`: FOUND
- `backend/.env.example` contains `TWITTER_API_KEY`: FOUND
- `backend/.env.example` contains `PINECONE_ENVIRONMENT`: FOUND
- `backend/.env.example` contains `PLAYHT_API_KEY`: FOUND
- `backend/.env.example` contains `HEYGEN_API_KEY`: FOUND
- `.env.example` has 81 `=` assignments (requirement: 35+): PASSED
- `critical_down` appears 4 times in server.py: PASSED
- Duplicate `/api/health` removed: PASSED
- Commits d485109 and 2939cc7 exist: PASSED
