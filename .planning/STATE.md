---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Production Hardening — 50x Testing Sprint
status: executing
stopped_at: Completed 19-core-features/19-05-PLAN.md
last_updated: "2026-04-03T07:43:49.960Z"
last_activity: 2026-04-03
progress:
  total_phases: 12
  completed_phases: 3
  total_plans: 14
  completed_plans: 14
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Every feature that exists in the codebase must actually work end-to-end — a user can sign up, onboard, generate content, schedule, publish, pay, and manage their account without hitting broken flows.
**Current focus:** Phase 19 — core-features

## Current Position

Phase: 19 (core-features) — EXECUTING
Plan: 5 of 5
Status: Ready to execute
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

### Pending Todos

None yet.

### Blockers/Concerns

- CONCERNS.md documents race condition in credit deduction (credits.py) — fix required in Phase 5
- Celery files exist (celery_app.py, celeryconfig.py) but Procfile missing worker/beat entries — confirm in Phase 2
- Publishing placeholder in content_tasks.py fallback path — must be replaced in Phase 5
- 20+ worktree-agent-* branches must be deleted before any new branches are created — Phase 1 prerequisite
- Stripe Price IDs are blank in .env.example — owner must create Stripe products; flag in Phase 5

## Session Continuity

Last session: 2026-04-03T07:43:49.956Z
Stopped at: Completed 19-core-features/19-05-PLAN.md
Resume file: None
