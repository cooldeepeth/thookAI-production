---
phase: 04-content-pipeline
plan: "02"
subsystem: backend-pipeline
tags: [testing, pipeline, celery, timeout, stale-jobs]
dependency_graph:
  requires: ["04-01"]
  provides: ["PIPE-01-verified", "PIPE-06-verified"]
  affects: ["backend/tests/"]
tech_stack:
  added: []
  patterns: ["pytest.mark.asyncio", "unittest.mock.AsyncMock", "patch-with-side_effect"]
key_files:
  created:
    - backend/tests/test_pipeline_e2e.py
  modified: []
decisions:
  - "Stale job cleanup only targets status='running' (not 'processing') — all jobs start as 'running' in content routes"
  - "research_needed=True used in agent ordering test to ensure Scout is called (design: Scout is skipped when research_needed=False)"
  - "Task 2 was no-op — stale job cleanup filter is correct as-is, no code changes needed"
metrics:
  duration_minutes: 3
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_modified: 1
requirements_satisfied: [PIPE-01, PIPE-06]
---

# Phase 04 Plan 02: Pipeline E2E Tests and Stale Job Cleanup Verification Summary

**One-liner:** 14 pytest tests proving pipeline 180s timeout, agent ordering, job status transitions (completed/error), and stale job cleanup via Celery beat schedule.

## What Was Built

Created `backend/tests/test_pipeline_e2e.py` with 14 tests covering:

**PIPE-01 — Pipeline execution and timeout:**
- `PIPELINE_TIMEOUT_SECONDS` constant equals 180.0
- `run_agent_pipeline` wraps inner call with `asyncio.wait_for(timeout=PIPELINE_TIMEOUT_SECONDS)`
- `asyncio.TimeoutError` causes job status to be set to `error` with message containing "timed out"
- All 5 agents (commander, scout, thinker, writer, qc) are called in correct order when `research_needed=True`
- Successful run sets job status to `completed` with `final_content` set
- Agent exception sets job status to `error` with the exception message

**PIPE-06 — Stale job cleanup:**
- `cleanup_stale_running_jobs` marks running jobs older than 10 minutes as `error`
- Filter correctly uses `$lt` threshold on `updated_at` to exclude recent jobs
- Jobs updated less than 10 minutes ago are structurally excluded (threshold check)
- Completed jobs are never matched (filter requires `status='running'`)
- `celeryconfig.beat_schedule` contains `"cleanup-stale-jobs"` with correct task name
- All 7 required periodic tasks are present in the beat schedule
- Error message includes "stale running job" text
- Return value contains `stale_jobs_cleaned` integer key

## Test Results

- **New tests:** 14 tests in `test_pipeline_e2e.py` — all pass
- **Full suite:** 172 passed, 36 skipped (server-dependent integration tests), 0 failed
- **Total collected:** 208 tests (up from 194 baseline, exceeds 175+ requirement)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test used research_needed=False causing Scout agent to be skipped**
- **Found during:** Task 1 — first test run
- **Issue:** The test mock for commander returned `research_needed: False`, which correctly skips `run_scout()` in the pipeline by design (scout is only called when research is needed). Test assertion `assert "scout" in call_order` failed.
- **Fix:** Changed mock commander to return `research_needed: True` so scout is invoked in the agent-ordering test
- **Files modified:** `backend/tests/test_pipeline_e2e.py`
- **Commit:** 6725517

### Task 2 Verification (No-op)

The stale job cleanup filter was verified to be correct:
- Uses `status: "running"` filter — matches actual job creation status in content routes
- Plan concern about `"processing"` status was investigated: all content routes create jobs with `status: "running"`, not `"processing"`. No code change needed.
- Threshold uses `timedelta(minutes=10)` with `datetime.now(timezone.utc)` — correct.
- Error message includes "stale running job detected by cleanup task" — passes test.

## Known Stubs

None — all tests test real code paths and verify actual behavior.

## Self-Check

Files created:
- `backend/tests/test_pipeline_e2e.py` — EXISTS

Commits:
- `6725517` — test(04-02): add pipeline e2e and stale job cleanup tests

## Self-Check: PASSED
