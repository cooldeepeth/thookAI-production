---
phase: 13-analytics-feedback-loop
plan: 01
subsystem: api
tags: [n8n, analytics, mongodb, content_jobs, scheduled_posts]

# Dependency graph
requires:
  - phase: 09-n8n-infrastructure
    provides: "execute_process_scheduled_posts in n8n_bridge.py, N8nConfig dataclass"
  - phase: 12-strategist-agent
    provides: "WORKFLOW_NOTIFICATION_MAP pattern, n8n bridge workflow map pattern"
provides:
  - "publish_results[platform] written to content_jobs after every successful n8n publish"
  - "analytics_24h_due_at and analytics_7d_due_at set on content_jobs at publish time"
  - "analytics_24h_polled=False and analytics_7d_polled=False initialized on content_jobs"
  - "N8nConfig workflow_analytics_poll_24h and workflow_analytics_poll_7d fields"
  - "Sparse compound DB indexes for analytics poll queue scanning"
affects: [13-analytics-feedback-loop, plan-02, social-analytics, performance-intelligence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "publish write-back: write publisher return value into content_jobs.publish_results[platform] immediately after successful scheduled post publish"
    - "analytics due-at pattern: set analytics_24h_due_at = published_at + 24h and analytics_7d_due_at = published_at + 7d at publish time, not at polling time"
    - "sparse poll queue indexes: analytics_24h_poll_queue and analytics_7d_poll_queue are sparse because only published posts have these fields"

key-files:
  created: []
  modified:
    - backend/config.py
    - backend/db_indexes.py
    - backend/.env.example
    - backend/routes/n8n_bridge.py

key-decisions:
  - "publish_results data is the raw result dict returned by real_publish_to_platform — contains post_id/tweet_id needed by social_analytics.update_post_performance()"
  - "job_id write-back is silently skipped if job_id is missing on a legacy scheduled_post — no crash on legacy data"
  - "analytics_24h_polled and analytics_7d_polled initialized to False at publish time (not None) so sparse indexes can include them in poll queue queries"
  - "analytics-poll-24h and analytics-poll-7d added to both _get_workflow_map and WORKFLOW_NOTIFICATION_MAP following the pattern established in Phase 12"

patterns-established:
  - "Analytics due-at scheduling: set *_due_at timestamps at publish time so Plan 02 poll loop only needs to query by due_at <= now without computing offsets"
  - "Sparse DB index for poll queue: polled_flag + due_at compound sparse index enables O(log n) poll queue scanning over potentially millions of content_jobs"

requirements-completed: [ANLYT-02]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 13 Plan 01: Analytics Feedback Loop Infrastructure Summary

**Publish write-back wires content_jobs.publish_results[platform] + analytics due-at timestamps to every n8n-published scheduled post, enabling Plan 02 to poll real social metrics**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-01T07:22:00Z
- **Completed:** 2026-04-01T07:24:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- N8nConfig extended with `workflow_analytics_poll_24h` and `workflow_analytics_poll_7d` fields (env-driven, Optional[str])
- Two sparse compound indexes added to `content_jobs` for analytics poll queue scanning: `analytics_24h_poll_queue` and `analytics_7d_poll_queue`
- `execute_process_scheduled_posts` now writes `publish_results[platform]`, `published_at`, `analytics_24h_due_at`, `analytics_7d_due_at`, `analytics_24h_polled=False`, and `analytics_7d_polled=False` to the linked `content_job` after every successful publish
- `_get_workflow_map` and `WORKFLOW_NOTIFICATION_MAP` updated with analytics poll workflow entries

## Task Commits

1. **Task 1: Add N8nConfig fields + DB indexes + .env.example** - `c8cc019` (feat)
2. **Task 2: Write publish_results + analytics due-at fields back to content_jobs on publish** - `33b85ef` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `backend/config.py` - Added `workflow_analytics_poll_24h` and `workflow_analytics_poll_7d` to `N8nConfig`
- `backend/db_indexes.py` - Added `analytics_24h_poll_queue` and `analytics_7d_poll_queue` sparse compound indexes on `content_jobs`
- `backend/.env.example` - Documented `N8N_WORKFLOW_ANALYTICS_POLL_24H` and `N8N_WORKFLOW_ANALYTICS_POLL_7D` env vars
- `backend/routes/n8n_bridge.py` - publish_results write-back + analytics due-at in success branch; workflow map + notification map entries for analytics poll workflows

## Decisions Made

- `publish_results` stores the raw `result` dict from `real_publish_to_platform` (or `{"success": True}` if result is not a dict) — this preserves the `post_id`/`tweet_id` that `social_analytics.update_post_performance()` reads via `job.get("publish_results", {}).get(platform, {})`
- `job_id` write-back is guarded by `if job_id:` — silently skips legacy scheduled posts missing `job_id`, no crash
- `analytics_24h_polled` and `analytics_7d_polled` are set to `False` (not omitted/None) so the sparse compound indexes pick them up for Plan 02's poll queue queries
- Analytics due-at timestamps are computed relative to `now` (publish time) not relative to `scheduled_at`, ensuring accurate 24h/7d windows from actual publish moment

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (`13-02`) can now build the analytics polling n8n execute endpoint: it queries `content_jobs` by `analytics_24h_polled=False` and `analytics_24h_due_at <= now`, calls `social_analytics.update_post_performance()`, and marks polled=True
- The `social_analytics.update_post_performance()` function already reads `job.get("publish_results", {}).get(platform, {})` to find the post identifier — the write-back in this plan supplies that data
- DB indexes are ready — no further index work needed for analytics polling

---
*Phase: 13-analytics-feedback-loop*
*Completed: 2026-04-01*
