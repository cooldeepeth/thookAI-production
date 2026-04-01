---
phase: 12-strategist-agent
plan: 01
subsystem: database, infra
tags: [mongodb, config, n8n, strategist, indexes]

# Dependency graph
requires:
  - phase: 09-n8n-orchestration
    provides: N8nConfig pattern for workflow IDs
  - phase: 11-multi-model-media-orchestration
    provides: RemotionConfig pattern (nearest preceding config dataclass)
provides:
  - StrategistConfig dataclass with cadence controls (max_cards_per_day=3, suppression_days=14, consecutive_dismissal_threshold=5)
  - N8nConfig.workflow_nightly_strategist field reading N8N_WORKFLOW_NIGHTLY_STRATEGIST env var
  - MongoDB indexes for strategy_recommendations (6 indexes) and strategist_state (3 indexes)
  - N8N_WORKFLOW_NIGHTLY_STRATEGIST documented in .env.example
affects: [12-02, 12-03, 12-04, strategist-agent, strategy-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "StrategistConfig constants pattern: cadence parameters as Python constants (not env vars) in a dedicated dataclass"
    - "idx_user_topic_status compound index: mandatory for 14-day topic suppression single-query check (STRAT-05)"

key-files:
  created: []
  modified:
    - backend/config.py
    - backend/db_indexes.py
    - backend/.env.example

key-decisions:
  - "StrategistConfig fields are application constants (not env-driven) — cadence parameters are launch-tuned values, not operator config"
  - "Compound index (user_id, topic, status) on strategy_recommendations is MANDATORY — enables STRAT-05 14-day suppression as a single indexed query"
  - "strategist_state has unique user_id index — one state document per user, upserted by nightly runner"

patterns-established:
  - "Config constants pattern: use plain dataclass defaults (no field(default_factory=...)) for application-level tuning parameters that are not operator-configurable"

requirements-completed: [STRAT-01, STRAT-02, STRAT-04, STRAT-05]

# Metrics
duration: 1min
completed: 2026-04-01
---

# Phase 12 Plan 01: Strategist Agent Foundation Summary

**StrategistConfig dataclass with cadence controls (max 3 cards/day, 14-day suppression) plus MongoDB indexes for strategy_recommendations and strategist_state collections**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-01T06:27:00Z
- **Completed:** 2026-04-01T06:28:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added StrategistConfig dataclass to config.py with all STRAT-04/05/06 cadence fields (max_cards_per_day, suppression_days, consecutive_dismissal_threshold, min_approved_content, synthesis_timeout, nightly_cron_hour_utc)
- Added workflow_nightly_strategist to N8nConfig, added strategist to Settings — all importable and verified
- Defined 6 indexes for strategy_recommendations (including the MANDATORY compound user_id+topic+status for STRAT-05) and 3 indexes for strategist_state with unique user_id
- Documented N8N_WORKFLOW_NIGHTLY_STRATEGIST in backend/.env.example alongside existing n8n workflow vars

## Task Commits

Each task was committed atomically:

1. **Task 1: Add StrategistConfig dataclass and N8nConfig workflow field** - `e543e2c` (feat)
2. **Task 2: Add MongoDB indexes for strategy_recommendations and strategist_state + update .env.example** - `a13e903` (feat)

## Files Created/Modified

- `backend/config.py` - Added StrategistConfig dataclass (6 fields), workflow_nightly_strategist to N8nConfig, strategist field to Settings
- `backend/db_indexes.py` - Added strategy_recommendations (6 IndexModels) and strategist_state (3 IndexModels) entries to INDEXES dict
- `backend/.env.example` - Added N8N_WORKFLOW_NIGHTLY_STRATEGIST with comment under n8n workflow section

## Decisions Made

- StrategistConfig fields are plain Python defaults, not env-driven — cadence parameters (max_cards_per_day, suppression_days, etc.) are application-level constants tuned for launch, not operator configuration. Changing them requires a code change + deploy, which is intentional (prevents accidental misconfiguration in production).
- Compound index (user_id, topic, status) on strategy_recommendations is MANDATORY per STRAT-05 — the 14-day suppression check queries this exact triple, and without the compound index it degrades to a full collection scan per user per run.
- strategist_state uses unique user_id (not user_id + date) — one state doc per user, updated in-place by nightly runner. History is not stored here (if needed, log to a separate audit collection in a later plan).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for this plan. N8N_WORKFLOW_NIGHTLY_STRATEGIST will be set when the n8n workflow is created in Plan 04.

## Next Phase Readiness

- Plan 02 (strategist agent + routes) can import `from config import settings; settings.strategist.max_cards_per_day` immediately
- MongoDB indexes will be created automatically on next server startup via `create_indexes()` in lifespan
- strategy_recommendations and strategist_state collections are ready for document writes

---
*Phase: 12-strategist-agent*
*Completed: 2026-04-01*
