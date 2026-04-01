---
phase: 13-analytics-feedback-loop
plan: "02"
subsystem: n8n-bridge/analytics-polling
tags: [analytics, n8n, social-platforms, performance-intelligence, testing]
dependency_graph:
  requires: [13-01]
  provides: [ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04]
  affects: [backend/routes/n8n_bridge.py, backend/tests/test_n8n_bridge.py]
tech_stack:
  added: []
  patterns:
    - "Per-user rate limiting (max 5 jobs per polling run) via defaultdict counter"
    - "Lazy import pattern for social_analytics and persona_refinement inside execute endpoints"
    - "app.dependency_overrides[_verify_n8n_request] pattern for HMAC bypass in tests"
    - "Mark-polled-regardless-of-success pattern to prevent infinite retry loops"
key_files:
  created: []
  modified:
    - backend/routes/n8n_bridge.py
    - backend/tests/test_n8n_bridge.py
decisions:
  - "Per-user rate limit (MAX_JOBS_PER_USER=5) applied before platform API calls to respect LinkedIn/X/Instagram rate limits"
  - "Jobs marked analytics_24h_polled=True (plus analytics_24h_error=True on failure) regardless of API result — no infinite retry"
  - "calculate_optimal_posting_times called once per affected user set after all jobs processed — not per job"
  - "app.dependency_overrides[_verify_n8n_request] used in tests to bypass HMAC without patching settings MagicMock"
  - "Lazy imports kept inside endpoint function bodies consistent with all other execute endpoints in n8n_bridge.py"
metrics:
  duration_seconds: 285
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_modified: 2
---

# Phase 13 Plan 02: Analytics Polling Execute Endpoints Summary

**One-liner:** Two HMAC-verified n8n execute endpoints (poll-analytics-24h and poll-analytics-7d) that query due published jobs, fetch real social metrics via update_post_performance(), enforce per-user rate limits, and recalculate optimal posting times — validated by 8 comprehensive tests covering all 4 ANLYT requirements.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add poll-analytics-24h and poll-analytics-7d execute endpoints | 69f7c9d | backend/routes/n8n_bridge.py |
| 2 | Add comprehensive tests for all ANLYT requirements | 3f3ae1a | backend/tests/test_n8n_bridge.py |

## What Was Built

### Task 1: Two Analytics Polling Execute Endpoints

Added `execute_poll_analytics_24h` and `execute_poll_analytics_7d` to `backend/routes/n8n_bridge.py` following the established HMAC-verified execute endpoint pattern.

Both endpoints:
1. Query `content_jobs` for published jobs with `analytics_{Nh}_polled=False` and `analytics_{Nh}_due_at <= now` and `publish_results` field present
2. Enforce per-user rate limit of max 5 jobs per polling run (deferred jobs picked up in next 15-minute cron cycle)
3. Call `update_post_performance(job_id, user_id, platform)` for each platform key in `publish_results`
4. Mark `analytics_{Nh}_polled=True` + `analytics_{Nh}_polled_at=now` regardless of API success (prevents infinite retry)
5. Set `analytics_{Nh}_error=True` if any platform fetch failed
6. After all jobs, call `calculate_optimal_posting_times(user_id)` once per affected user (not per job)
7. Return `{"status": "completed", "result": {"polled": N, "errors": N, "deferred": N, "users_updated": N}}`

Module docstring updated to list both new endpoints.

### Task 2: Comprehensive Test Coverage (8 New Tests)

Added `TestExecutePollAnalytics` class to `backend/tests/test_n8n_bridge.py` with 8 tests:

| Test | Requirement | What it verifies |
|------|-------------|-----------------|
| test_execute_poll_analytics_24h | ANLYT-01 | 2 jobs 2 users → polled=2, users_updated=2 |
| test_execute_poll_analytics_7d | ANLYT-01 | analytics_7d_polled=True in update_one args |
| test_poll_analytics_per_user_rate_limit | ANLYT-01 | 7 jobs same user → 5 processed, 2 deferred |
| test_poll_analytics_marks_polled_on_failure | ANLYT-01 | False return → polled=True, error=True |
| test_process_scheduled_posts_writes_publish_results | ANLYT-02 | publish_results.linkedin.post_id written |
| test_analytics_due_at_set_on_publish | ANLYT-02 | 24h/7d due-at set, polled flags=False |
| test_poll_analytics_calls_optimal_times | ANLYT-03 | 3 jobs 2 users → called exactly twice |
| test_strategist_reads_performance_data | ANLYT-04 | _gather_user_context extracts 2 signals from 3 jobs |

Total test count: 20 (was 12). All 20 pass.

## ANLYT Requirements Coverage

- **ANLYT-01** (Poll analytics endpoints): Covered by Tasks 1 and tests 1-4. Both endpoints query DB, call platform APIs, enforce rate limits, mark polled.
- **ANLYT-02** (publish_results write-back): Confirmed by tests 5-6 exercising existing execute_process_scheduled_posts code from Phase 13-01.
- **ANLYT-03** (Optimal times recalculation): Confirmed by test 7 — calculate_optimal_posting_times called once per affected user.
- **ANLYT-04** (Strategist reads performance_data): Confirmed by test 8 — _gather_user_context returns performance_signals from jobs that have performance_data, without any code changes.

## Deviations from Plan

None — plan executed exactly as written. The `_verify_n8n_request` dependency override approach (`app.dependency_overrides`) was used instead of `patch("routes.n8n_bridge._verify_n8n_request")` because the latter interferes with FastAPI's dependency injection system (settings becomes MagicMock and HMAC function throws TypeError). This is consistent with how existing tests bypass `get_current_user` in the same file.

## Known Stubs

None. The polling endpoints call real service functions (`update_post_performance`, `calculate_optimal_posting_times`) which are fully implemented and tested in Phase 13-01 and the social analytics service. No placeholder logic.

## Deferred Issues (Out of Scope)

- `tests/test_pipeline_e2e.py::TestBeatScheduleHasCleanupStaleJobs::test_beat_schedule_has_cleanup_stale_jobs` — pre-existing failure from Phase 09 migration (tests for old Celery beat schedule that was intentionally removed). Logged to deferred-items.

## Self-Check: PASSED

- `backend/routes/n8n_bridge.py` — exists, contains both endpoints
- `backend/tests/test_n8n_bridge.py` — exists, 8 new tests all pass
- Commit 69f7c9d — exists (feat: poll endpoints)
- Commit 3f3ae1a — exists (test: comprehensive analytics tests)
