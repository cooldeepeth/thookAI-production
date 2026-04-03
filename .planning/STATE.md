---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Production Hardening — 50x Testing Sprint
status: verifying
stopped_at: Completed 17-test-foundation-billing-payments/17-04-PLAN.md
last_updated: "2026-04-03T03:44:41.229Z"
last_activity: 2026-04-03
progress:
  total_phases: 12
  completed_phases: 0
  total_plans: 5
  completed_plans: 4
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Every feature that exists in the codebase must actually work end-to-end — a user can sign up, onboard, generate content, schedule, publish, pay, and manage their account without hitting broken flows.
**Current focus:** Phase 07 — Platform Features, Admin & Frontend Quality

## Current Position

Phase: 07 (Platform Features, Admin & Frontend Quality) — EXECUTING
Plan: 4 of 4
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
| Phase 03 P03 | 8 | 2 tasks | 2 files |
| Phase 04 P01 | 5 | 2 tasks | 1 files |
| Phase 04-content-pipeline P02 | 3 | 2 tasks | 1 files |
| Phase 05-publishing-scheduling-billing P02 | 4 | 2 tasks | 3 files |
| Phase 05-publishing-scheduling-billing P01 | 6 | 2 tasks | 4 files |
| Phase 05-publishing-scheduling-billing P03 | 2 | 2 tasks | 2 files |
| Phase 06-media-generation-analytics P01 | 3 | 2 tasks | 1 files |
| Phase 06-media-generation-analytics P02 | 5 | 2 tasks | 1 files |
| Phase 06-media-generation-analytics P03 | 6 | 2 tasks | 1 files |
| Phase 17-test-foundation-billing-payments P03 | 2 | 1 tasks | 1 files |
| Phase 17-test-foundation-billing-payments P02 | 9 | 2 tasks | 10 files |
| Phase 17 P04 | 7 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stabilization milestone: Fix existing features before building new ones — no new features until everything works
- Git strategy: All work branches from dev; PRs target dev; never commit to main directly
- PR #30 included: Custom plan builder (pricing pivot) is final direction, merge into dev in Phase 1
- Billing changes: Flag for human review — no auto-merge on billing code
- Verification standard: Manual E2E + automated tests required — 59 existing tests missed real bugs
- [Phase 03]: AUTH-05 verified: claude-sonnet-4-20250514 is correct model name in both analyze-posts and generate-persona endpoints
- [Phase 03]: AUTH-06 verified: Persona Engine has voice_fingerprint, content_identity, uom, learning_signals; smart fallback produces archetype-specific non-generic personas
- [Phase 03]: Source transparency: generate-persona returns source field (llm|smart_fallback) so frontend can show notice when fallback used
- [Phase 04]: Mock langgraph.graph at sys.modules level to allow testing orchestrator pure functions in envs without langgraph installed
- [Phase 04-content-pipeline]: Stale job cleanup only targets status='running' — all jobs start with this status in content routes
- [Phase 05]: Use find_one_and_update with credits >= amount filter for atomic deduction — eliminates race condition without transactions
- [Phase 05]: Platform restriction in route handler (not credits service) — keeps billing concerns separate from access control
- [Phase 05-01]: Test httpx.AsyncClient (not publisher function) to verify real HTTP dispatch code path
- [Phase 05-01]: Extracted _run_scheduled_posts_inner to module level for unit-testable scheduled post processing
- [Phase 05-publishing-scheduling-billing]: validate_stripe_config runs on module import so startup warnings appear in logs immediately
- [Phase 05-publishing-scheduling-billing]: Task 2 regression check required zero test file changes — all 222 tests passed cleanly
- [Phase 06-01]: Pre-existing test_uploads_media_storage.py failures (7 tests) are out of scope — confirmed pre-existing before this plan's changes
- [Phase 06-01]: TDD approach: wrote all 28 tests before any agent code changes — all passed immediately because agents already implemented correctly
- [Phase 06-02]: Use app.dependency_overrides[get_current_user] (not patch) for auth bypass in FastAPI route tests
- [Phase 06-02]: Mount upload router at root (no prefix) in TestClient apps to avoid double-prefix path issues
- [Phase 06-media-generation-analytics]: Patch services.social_analytics.db (not database.db) because social_analytics.py binds db at import time via 'from database import db'
- [Phase 17-03]: Billing CI job uses continue-on-error=true until Phase 17 billing tests satisfy the 95% coverage gate
- [Phase 17-03]: CI matrix uses 4 domain-specific jobs (billing 95%, security 85%, pipeline 85%, general no gate) for fast feedback and domain-isolated failure
- [Phase 17-02]: TDD RED commit before GREEN fix: each P0 bug got a failing test committed before the production fix
- [Phase 17-02]: stripe_events collection with unique event_id index provides O(1) webhook dedup; 7d TTL prevents unbounded growth
- [Phase 17-02]: _TEST_JWT_SECRET constant in test helpers after removing fallback secret; tests patch auth_utils.settings.security to match
- [Phase 17-04]: Patching both 'services.stripe_service.db' and 'database.db' required because stripe_service binds db at import time and credits.py uses lazy import inside functions
- [Phase 17-04]: Separated sync pure-function tests from async DB tests into distinct classes to avoid PytestWarning about async marks on sync methods

### Pending Todos

None yet.

### Blockers/Concerns

- CONCERNS.md documents race condition in credit deduction (credits.py) — fix required in Phase 5
- Celery files exist (celery_app.py, celeryconfig.py) but Procfile missing worker/beat entries — confirm in Phase 2
- Publishing placeholder in content_tasks.py fallback path — must be replaced in Phase 5
- 20+ worktree-agent-* branches must be deleted before any new branches are created — Phase 1 prerequisite
- Stripe Price IDs are blank in .env.example — owner must create Stripe products; flag in Phase 5

## Session Continuity

Last session: 2026-04-03T03:44:41.225Z
Stopped at: Completed 17-test-foundation-billing-payments/17-04-PLAN.md
Resume file: None
