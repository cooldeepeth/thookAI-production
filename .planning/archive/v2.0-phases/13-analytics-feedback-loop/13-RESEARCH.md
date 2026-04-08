# Phase 13: Analytics Feedback Loop — Research

**Researched:** 2026-04-01
**Domain:** Social platform metrics APIs, n8n workflow orchestration, MongoDB aggregation, Strategist data contract
**Confidence:** HIGH (all findings verified against live codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md / STATE.md)

### Locked Decisions
- v2.0 architectural principle: New components (n8n, LightRAG, Remotion) run as sidecar services, integrated over HTTP — no new Python imports into FastAPI monolith
- n8n hybrid: Move cron + external-API tasks to n8n; keep Celery for Motor-coupled media generation tasks
- Phase 12 depends on both Phase 10 (LightRAG populated) and Phase 13 (analytics flowing) — plan Phase 13 before Phase 12 execution starts
- [Phase 09]: process-scheduled-posts uses `agents.publisher.publish_to_platform` directly — no `content_tasks._publish_to_platform` indirection
- Config pattern: All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly
- Database pattern: Always `from database import db` with Motor async. Never synchronous PyMongo
- LLM model: `claude-sonnet-4-20250514` (Anthropic primary)

### Claude's Discretion
- n8n Wait node vs scheduled cron for 24h/7d polling timing strategy
- Whether `analytics_24h_due_at` and `analytics_7d_due_at` fields belong on `content_jobs` or `scheduled_posts`
- Whether performance_intelligence update is synchronous in the execute endpoint or queued
- How the Strategist prompt changes to reference real performance data once available

### Deferred Ideas (OUT OF SCOPE)
- Real-time analytics dashboard with live socket updates
- Platform-native analytics API integrations beyond LinkedIn/X/Instagram
- Historical bulk analytics import from before ThookAI was used
- Advanced statistical modeling of posting time optimization
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANLYT-01 | Real social metrics polling (24h + 7d after publish) via n8n workflows for LinkedIn, X, and Instagram | `social_analytics.py` already implements all three platform fetchers. Gap: no n8n execute endpoints to trigger polling, no `analytics_24h_due_at` / `analytics_7d_due_at` fields on content_jobs to drive scheduling |
| ANLYT-02 | Performance data written to `content_jobs.performance_data` with engagement, reach, impressions per platform | `update_post_performance()` in `social_analytics.py` already writes `performance_data.latest` + history. Gap: it is never called — no n8n workflow triggers it |
| ANLYT-03 | Aggregated performance intelligence updates `persona_engines.performance_intelligence` with real `optimal_posting_times` | `_aggregate_performance_intelligence()` and `calculate_optimal_posting_times()` both exist. `update_performance_intelligence` Celery task exists but is never scheduled. Gap: no n8n execute endpoint wires this up post-poll |
| ANLYT-04 | Analytics data feeds into Strategist Agent for smarter recommendations (each publish cycle improves output) | Strategist `_gather_user_context()` already reads `performance_data` from recent jobs. Gap: data is empty because ANLYT-01/02/03 don't run. No code change needed to strategist once data flows — it already reads it |
</phase_requirements>

---

## Summary

Phase 13 is primarily a **wiring and orchestration phase**, not a build phase. The core analytics infrastructure is already implemented and tested:

- `backend/services/social_analytics.py` — All three platform fetchers (LinkedIn, X, Instagram) are complete, correct, and tested in `backend/tests/test_analytics_social.py`
- `backend/services/persona_refinement.py::calculate_optimal_posting_times()` — Calculates top posting slots per platform from real data, persists to persona_engines
- `backend/services/persona_refinement.py::calculate_performance_intelligence()` — Aggregates cross-post signal (exists but rarely called)
- `backend/agents/strategist.py::_gather_user_context()` — Already reads `performance_data` from recent jobs and passes it as `performance_signals` into the LLM prompt

What is completely missing: the n8n workflow trigger-and-execute chain that calls these functions after a post is published. Specifically:
1. When a post is published via `n8n_bridge.py::execute_process_scheduled_posts`, the publisher does NOT set `analytics_24h_due_at` / `analytics_7d_due_at` on the job
2. No n8n execute endpoints exist for `POST /api/n8n/execute/poll-analytics-24h` or `POST /api/n8n/execute/poll-analytics-7d`
3. No n8n workflow config fields exist in `N8nConfig` for the analytics poll workflows
4. The Strategist `_build_synthesis_prompt` has a `"No performance data available yet"` fallback branch that will be eliminated once data flows

**Primary recommendation:** Add `analytics_24h_due_at` + `analytics_7d_due_at` timestamp fields to `content_jobs` at publish time, then add two n8n execute endpoints that query jobs by due date and call `update_post_performance()`. Wire the n8n workflows to call these endpoints at the correct intervals.

---

## Standard Stack

### Core (all already in requirements.txt — no new packages)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `httpx` | 0.28.1 | Calls LinkedIn/X/Instagram APIs from `social_analytics.py` | Existing |
| `motor` | 3.3.1 | MongoDB async driver for all DB writes | Existing |
| `fastapi` | 0.110.1 | Execute endpoint registration in `n8n_bridge.py` | Existing |
| `cryptography` | 42.0.8 | Fernet decrypt for platform OAuth tokens | Existing |

### No New Packages Required

All analytics functionality already exists in the codebase. Zero new Python packages needed.

**Version verification:** Not applicable — no new packages.

---

## Architecture Patterns

### Pattern 1: n8n-Driven Scheduled Poll (ANLYT-01 mechanism)

The established Phase 9 pattern for n8n → FastAPI task execution applies directly here:

```
[n8n Workflow: analytics-poll-24h]
  Schedule: CRON every 15 minutes (checks due_at timestamps)
         OR Wait node 24h after trigger (from publish callback)
  → POST /api/n8n/execute/poll-analytics-24h
       X-ThookAI-Signature: <HMAC-SHA256>
  → FastAPI queries: content_jobs WHERE analytics_24h_due_at <= now AND analytics_24h_polled = false
  → For each: calls update_post_performance(job_id, user_id, platform)
  → After all polled: calls calculate_optimal_posting_times(user_id) per affected user
  → Returns: { polled_count, updated_users }
```

**n8n Wait Node approach (recommended):** Use n8n Wait node rather than a cron that scans all jobs. The publish workflow triggers the analytics workflow directly, passing `job_id` + `user_id` + `platform`. The analytics workflow waits 24h (Wait node), then calls FastAPI. This avoids the scan-all-jobs pattern and guarantees per-job timing. However it requires the n8n workflow to be stateful.

**Cron scan approach (simpler, more robust):** FastAPI stores `analytics_24h_due_at = published_at + 24h` on the content_job at publish time. n8n cron runs every 15 minutes, calls `POST /api/n8n/execute/poll-analytics-24h`, FastAPI finds all jobs with `analytics_24h_due_at <= now AND analytics_24h_polled = false`. This is the same pattern as `process-scheduled-posts` and is easier to debug.

**Decision recommendation:** Use the cron scan approach — it matches the existing `process-scheduled-posts` pattern, is idempotent by default, and is easier to operate. The n8n Wait node approach requires a separate workflow instance per published post which at scale creates thousands of waiting executions.

### Pattern 2: Analytics Due-Date Fields on content_jobs

Add two fields at publish time (in `execute_process_scheduled_posts` and when `content.py` marks a job as published):

```python
# Source: n8n_bridge.py::execute_process_scheduled_posts — after successful publish
await db.content_jobs.update_one(
    {"job_id": job_id},
    {"$set": {
        "status": "published",
        "published_at": now,
        "analytics_24h_due_at": now + timedelta(hours=24),
        "analytics_7d_due_at": now + timedelta(days=7),
        "analytics_24h_polled": False,
        "analytics_7d_polled": False,
    }}
)
```

### Pattern 3: Execute Endpoint for Analytics Polling

Two new endpoints in `n8n_bridge.py`, following the exact same HMAC-verified pattern as the existing execute endpoints:

```python
@router.post("/execute/poll-analytics-24h")
async def execute_poll_analytics_24h(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Poll 24h analytics for all published posts where analytics_24h_due_at <= now.
    Called by n8n every 15 minutes.
    """
    from services.social_analytics import update_post_performance
    from services.persona_refinement import calculate_optimal_posting_times

    now = datetime.now(timezone.utc)
    cursor = db.content_jobs.find({
        "analytics_24h_polled": False,
        "analytics_24h_due_at": {"$lte": now},
        "status": "published",
        "publish_results": {"$exists": True},
    })
    jobs = await cursor.to_list(length=200)

    polled = 0
    errors = 0
    affected_user_ids = set()

    for job in jobs:
        job_id = job["job_id"]
        user_id = job["user_id"]
        # Determine platform from publish_results dict keys
        publish_results = job.get("publish_results", {})
        for platform in publish_results.keys():
            success = await update_post_performance(job_id, user_id, platform)
            if success:
                polled += 1
                affected_user_ids.add(user_id)
            else:
                errors += 1

        # Mark as polled regardless of API success to avoid infinite retry loops
        await db.content_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"analytics_24h_polled": True, "analytics_24h_polled_at": now}}
        )

    # Recalculate optimal posting times for all affected users
    for user_id in affected_user_ids:
        await calculate_optimal_posting_times(user_id)  # ANLYT-03

    return {
        "status": "completed",
        "result": {"polled": polled, "errors": errors, "users_updated": len(affected_user_ids)},
        "executed_at": now.isoformat(),
    }
```

The `poll-analytics-7d` endpoint is identical except it filters on `analytics_7d_due_at` / `analytics_7d_polled`.

### Pattern 4: n8n Config Fields

Add to `N8nConfig` dataclass in `backend/config.py`:

```python
workflow_analytics_poll_24h: Optional[str] = field(
    default_factory=lambda: os.environ.get('N8N_WORKFLOW_ANALYTICS_POLL_24H')
)
workflow_analytics_poll_7d: Optional[str] = field(
    default_factory=lambda: os.environ.get('N8N_WORKFLOW_ANALYTICS_POLL_7D')
)
```

And add to `_get_workflow_map()` in `n8n_bridge.py`:
```python
"analytics-poll-24h": settings.n8n.workflow_analytics_poll_24h,
"analytics-poll-7d": settings.n8n.workflow_analytics_poll_7d,
```

### Pattern 5: Strategist Integration (ANLYT-04)

**No code changes required.** Strategist `_gather_user_context()` already reads `performance_data` from recent jobs:

```python
# Source: backend/agents/strategist.py:225-232 — already implemented
recent_jobs_cursor = db.content_jobs.find(
    {"user_id": user_id, "status": {"$in": ["approved", "published"]}},
    {"_id": 0, "platform": 1, ..., "performance_data": 1, ...},
).sort("created_at", -1)
...
performance_signals = [
    j.get("performance_data")
    for j in recent_jobs
    if j.get("performance_data")
]
```

And `_build_synthesis_prompt()` already injects this as `PERFORMANCE SIGNALS:` in the LLM prompt. Once ANLYT-01/02/03 are working, the Strategist automatically starts using real data — the `"No performance data available yet"` fallback branch disappears from practice.

The **only optional improvement** for ANLYT-04: Add a `WORKFLOW_NOTIFICATION_MAP` entry for `analytics-poll-24h` and `analytics-poll-7d` so users see a notification when their post analytics are updated. This mirrors the existing `process-scheduled-posts` notification pattern.

### Pattern 6: publish_results field alignment

`social_analytics.py::update_post_performance()` reads from `job.get("publish_results", {})` — a dict keyed by platform. The publisher (`agents/publisher.py`) does NOT currently set `publish_results` on `content_jobs`; it returns the publish result dict from the function but the n8n bridge (`execute_process_scheduled_posts`) stores it in `scheduled_posts.status` only, not back to `content_jobs`.

**Gap:** When publishing via `execute_process_scheduled_posts`, the job_id of the corresponding `content_job` is not updated with `publish_results`. The n8n bridge needs to look up the `content_job` linked to the `scheduled_post` and write the publisher's return value as `content_jobs.publish_results[platform]`.

Check `scheduled_posts` schema: the post has `schedule_id`, `user_id`, `platform`, `content`, but not a direct `job_id` foreign key reference. This needs investigation:

```python
# Check if job_id is stored on scheduled_posts
# If not, content_tasks.py schedule creation must be checked
```

**Action required in planning:** Verify whether `scheduled_posts` documents have a `job_id` field. If not, the execute endpoint needs a different lookup strategy (match by `user_id` + `platform` + `content` exact match, or add `job_id` to `scheduled_posts` at creation time).

### Recommended Project Structure Changes

No new files beyond additions to existing files:

```
backend/
├── routes/
│   └── n8n_bridge.py          # +2 execute endpoints: poll-analytics-24h, poll-analytics-7d
├── config.py                  # +2 N8nConfig fields: workflow_analytics_poll_24h/7d
├── db_indexes.py              # +1 compound index: (analytics_24h_polled, analytics_24h_due_at)
└── tests/
    └── test_analytics_social.py  # +tests for new execute endpoints
```

### Anti-Patterns to Avoid

- **Calling `update_post_performance` from within `execute_process_scheduled_posts` synchronously** — the publisher must return first; analytics polling must be a separate delayed call. If done synchronously it blocks publishing execution for 20+ seconds per post.
- **Using n8n Wait node for per-post analytics scheduling** — creates unbounded numbers of waiting workflow executions. Use cron + due_at timestamp scan instead.
- **Marking `analytics_24h_polled = True` only on success** — if the platform API is down, the job stays in the polling queue forever. Mark as polled regardless; log errors separately. If token is expired, mark with `analytics_error: "token_expired"` for later re-attempt.
- **Calling `calculate_optimal_posting_times` inside the inner per-job loop** — it performs a full MongoDB query per user. Call it once per affected user after all jobs are processed (set-based deduplication).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Platform API calls | Custom HTTP client | Existing `social_analytics.py` fetchers | Already handles 401/429/timeout gracefully |
| Optimal time calculation | Custom statistics | `calculate_optimal_posting_times()` in `persona_refinement.py` | Already tested and persists to DB |
| n8n auth verification | Custom HMAC | `_verify_n8n_request` dependency in `n8n_bridge.py` | Consistent with all other execute endpoints |
| Performance aggregation | Custom aggregation | `_aggregate_performance_intelligence()` in `social_analytics.py` | Already running-average implementation |
| Performance intelligence update | Re-implement | `update_performance_intelligence` Celery task pattern | Already exists in `content_tasks.py` — adapt for execute endpoint |

---

## Runtime State Inventory

Not applicable — this is a greenfield wiring phase, not a rename/refactor phase.

---

## Common Pitfalls

### Pitfall 1: `publish_results` not written to `content_jobs`
**What goes wrong:** `social_analytics.py::update_post_performance()` reads `job.get("publish_results", {}).get(platform, {})` to find the post_id/tweet_id needed to call the platform API. But `execute_process_scheduled_posts` currently writes publish results only to `scheduled_posts` status, not back to `content_jobs.publish_results`. The analytics fetch returns `False` (no publish_results found) for every job.
**Why it happens:** The n8n bridge for publishing was written to mimic the Celery task which also didn't propagate results back to content_jobs.
**How to avoid:** After a successful publish in `execute_process_scheduled_posts`, also update the linked content_job with `publish_results[platform] = result` where `result` contains `post_id` (LinkedIn), `tweet_ids` (X), or `post_id` (Instagram). Requires either adding `job_id` to `scheduled_posts` at creation, or looking up the job by `user_id + platform + content`.
**Warning signs:** `update_post_performance` returns False for all jobs; `performance_data` in MongoDB stays empty.

### Pitfall 2: n8n workflow config fields not in `_get_workflow_map()`
**What goes wrong:** Adding `workflow_analytics_poll_24h` to `N8nConfig` but forgetting to add it to `_get_workflow_map()` means `POST /api/n8n/trigger/analytics-poll-24h` returns 404.
**How to avoid:** Always update both `N8nConfig` dataclass AND `_get_workflow_map()` together. They are parallel dictionaries.

### Pitfall 3: Platform API rate limits during bulk catch-up
**What goes wrong:** On first deployment, every published post with a due_at in the past gets polled in one n8n execution. For users with 50+ published posts, this means 50+ API calls to LinkedIn in a few seconds — LinkedIn rate limits at ~10 requests/minute per OAuth token.
**How to avoid:** In the execute endpoint, process at most N jobs per user per execution (e.g., `limit=5` per user). Jobs that weren't processed will be picked up in the next cron run. Log a warning when the per-user limit is hit.

### Pitfall 4: Token expiry silently blocks all analytics
**What goes wrong:** `update_post_performance` returns `False` when the access token is expired (`get_platform_token` returns None or the API returns 401). The job stays in the queue indefinitely if `analytics_24h_polled` is only set on success.
**How to avoid:** Always set `analytics_24h_polled = True` after an attempt. Store the error reason: `analytics_24h_error = "token_expired"`. Do not retry indefinitely.

### Pitfall 5: `calculate_optimal_posting_times` called too eagerly
**What goes wrong:** Calling `calculate_optimal_posting_times(user_id)` after every single job update causes excessive DB queries. It requires 10+ posts with data to return anything useful; calling it after 1 post wastes CPU.
**How to avoid:** Call it once per affected user at the end of the execute endpoint, after all jobs for all users have been processed. Also check the user's total `published` job count first — skip if below 10.

### Pitfall 6: Instagram Insights requires Business/Creator account
**What goes wrong:** Personal Instagram accounts do NOT have access to the Insights API. `fetch_instagram_post_metrics` returns HTTP 400 with "permissions error" for personal accounts. The error is stored but looks like an API failure.
**Why it happens:** Meta restricts the `instagram_basic` + media insights scope to Business/Creator accounts.
**How to avoid:** In the execute endpoint, detect this specific error pattern and set `analytics_instagram_error = "requires_business_account"`. Surface this to the user in the analytics route as a distinct message, not a generic error.

### Pitfall 7: LinkedIn impression data only available for Organization pages
**What goes wrong:** `fetch_linkedin_post_metrics` falls back to estimated impressions for personal creator accounts (the `organizationalEntityShareStatistics` endpoint requires `r_organization_social` scope, which only Company Pages have). The fallback heuristic (25x engagements) is documented in the code but may create misleading "real data" signals in the Strategist.
**How to avoid:** The existing code already applies the heuristic. Document in the execute endpoint response that `impressions: estimated` is a flag. The Strategist's performance_signals already include the raw `engagement_rate` which is real data — the impressions estimate doesn't affect recommendation quality significantly.

---

## Code Examples

### Example 1: Adding analytics due-at fields at publish time

```python
# In n8n_bridge.py::execute_process_scheduled_posts
# After: await db.scheduled_posts.update_one({"schedule_id": schedule_id}, {"$set": {"status": "published", ...}})
# Add: update the linked content_job

# Lookup content_job by job_id (requires job_id on scheduled_post — see Pitfall 1)
if post.get("job_id"):
    await db.content_jobs.update_one(
        {"job_id": post["job_id"]},
        {
            "$set": {
                f"publish_results.{platform}": result,  # result = publish_to_platform() return value
                "published_at": now,
                "analytics_24h_due_at": now + timedelta(hours=24),
                "analytics_7d_due_at": now + timedelta(days=7),
                "analytics_24h_polled": False,
                "analytics_7d_polled": False,
                "analytics_7d_polled_at": None,
            }
        },
    )
```

### Example 2: MongoDB index for efficient analytics polling queries

```python
# In backend/db_indexes.py — add alongside existing indexes
# Sparse compound index: only indexes documents with the field present
await db.content_jobs.create_index(
    [("analytics_24h_polled", 1), ("analytics_24h_due_at", 1)],
    sparse=True,
    name="analytics_24h_poll_queue",
)
await db.content_jobs.create_index(
    [("analytics_7d_polled", 1), ("analytics_7d_due_at", 1)],
    sparse=True,
    name="analytics_7d_poll_queue",
)
```

### Example 3: WORKFLOW_NOTIFICATION_MAP addition for analytics

```python
# In n8n_bridge.py::WORKFLOW_NOTIFICATION_MAP
"analytics-poll-24h": {
    "title": "Post analytics updated (24h)",
    "body_template": "Performance data collected for {polled} published post(s)",
},
"analytics-poll-7d": {
    "title": "Post analytics updated (7-day)",
    "body_template": "7-day performance data collected for {polled} published post(s)",
},
```

### Example 4: Per-user rate limiting in execute endpoint

```python
# In execute_poll_analytics_24h: limit jobs processed per user
from collections import defaultdict
user_job_counts: dict = defaultdict(int)
MAX_JOBS_PER_USER_PER_RUN = 5

for job in jobs:
    user_id = job["user_id"]
    if user_job_counts[user_id] >= MAX_JOBS_PER_USER_PER_RUN:
        logger.info("Per-user limit reached for %s — deferring remaining jobs", user_id)
        continue
    # ... process job ...
    user_job_counts[user_id] += 1
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery beat task for analytics polling | n8n cron workflow calling FastAPI execute endpoint | Phase 9 n8n migration | All polling now observable in n8n execution history |
| Simulated engagement metrics | Real platform API data via `social_analytics.py` | Phase 8 gap closure | Analytics and Strategist use actual engagement signals |
| `performance_intelligence = {}` always | Running average per platform from real API data | Phase 13 (this phase) | Strategist performance_signals are non-empty; optimal_posting_times get calculated |

**Not deprecated:** `_simulate_engagement()` in `analyst.py` — kept as fallback when real data is unavailable. This is correct behavior; simulated data is clearly flagged to users via `is_estimated: True`.

---

## Open Questions

1. **Does `scheduled_posts` have a `job_id` foreign key?**
   - What we know: `execute_process_scheduled_posts` reads from `scheduled_posts` with `schedule_id`, `user_id`, `platform`, `content`, `media_assets`. The `social_analytics.py::update_post_performance` reads from `content_jobs`.
   - What's unclear: Is there a `job_id` field on `scheduled_posts` documents? If not, writing `publish_results` back to the correct `content_job` requires a different lookup strategy.
   - Recommendation: Inspect `scheduled_posts` schema at plan time. Add `job_id` to `scheduled_posts` at creation time if missing — this is the cleanest solution. If adding `job_id` requires a schema migration, use `user_id + platform + content[:200]` matching as a fallback (fragile, prefer the schema change).

2. **n8n workflow design: cron scan vs Wait node for 24h/7d timing?**
   - What we know: Both approaches work. Cron scan is the existing pattern from `process-scheduled-posts`. Wait node triggers per-job and requires n8n execution persistence.
   - Recommendation: Use cron scan (every 15 minutes) with `analytics_24h_due_at` timestamp field. This is idempotent, debuggable, and consistent with existing patterns. Document this as the chosen approach in PLAN.md.

3. **ANLYT-04: does the Strategist need explicit code changes?**
   - What we know: Strategist already reads `performance_data` from `content_jobs` and injects as `PERFORMANCE SIGNALS`. Once data flows, it will be used automatically.
   - What's unclear: The Strategist prompt does not currently tell the LLM *how* to interpret engagement rate vs impressions vs likes for "why now" rationale quality. Adding a brief data interpretation hint might improve recommendation quality.
   - Recommendation: Treat ANLYT-04 as satisfied by ANLYT-01/02/03 completion. Optionally add a one-sentence hint in `STRATEGIST_SYSTEM_PROMPT` about interpreting performance signals, but this is not required for ANLYT-04 compliance.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `social_analytics.py` platform fetchers | ANLYT-01 | ✓ | Existing in codebase | — |
| `calculate_optimal_posting_times()` | ANLYT-03 | ✓ | Existing in `persona_refinement.py` | — |
| n8n (Phase 9 deployed) | ANLYT-01 workflows | ✓ | Phase 9 complete | — |
| LinkedIn OAuth tokens in `platform_tokens` | ANLYT-01 | Conditional — user must have connected LinkedIn | Metrics return False for unconnected users | graceful failure in `update_post_performance` |
| Instagram Business/Creator account | ANLYT-01 IG metrics | Conditional — personal accounts fail | IG metrics not available for personal accounts | log `requires_business_account` error |

**Missing dependencies with no fallback:** None — all execute endpoint infrastructure is in place from Phase 9.

**Missing dependencies with fallback:** Platform tokens must be present for a user's analytics to poll. Users without connected platforms return graceful errors, not exceptions.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/test_analytics_social.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLYT-01 | `execute_poll_analytics_24h` queries due jobs and calls `update_post_performance` | unit | `pytest tests/test_n8n_bridge.py::test_execute_poll_analytics_24h -x` | ❌ Wave 0 |
| ANLYT-01 | `execute_poll_analytics_7d` queries due jobs and calls `update_post_performance` | unit | `pytest tests/test_n8n_bridge.py::test_execute_poll_analytics_7d -x` | ❌ Wave 0 |
| ANLYT-01 | Platform fetchers already tested | unit | `pytest tests/test_analytics_social.py -x` | ✅ |
| ANLYT-02 | `publish_results[platform]` written to `content_jobs` after successful publish | unit | `pytest tests/test_n8n_bridge.py::test_execute_process_scheduled_posts_writes_publish_results -x` | ❌ Wave 0 |
| ANLYT-02 | `analytics_24h_due_at` set at publish time | unit | `pytest tests/test_n8n_bridge.py::test_analytics_due_at_set_on_publish -x` | ❌ Wave 0 |
| ANLYT-02 | `performance_data` written to `content_jobs` by `update_post_performance` | unit | `pytest tests/test_analytics_social.py::TestUpdatePostPerformance -x` | ✅ |
| ANLYT-03 | `calculate_optimal_posting_times` called after polling | unit | `pytest tests/test_n8n_bridge.py::test_poll_analytics_calls_optimal_times -x` | ❌ Wave 0 |
| ANLYT-03 | `optimal_posting_times` persisted to `persona_engines` | unit | `pytest tests/test_analytics_social.py -x` | ✅ |
| ANLYT-04 | Strategist `_gather_user_context` includes non-empty `performance_signals` when data present | unit | `pytest tests/test_strategist.py::test_gather_user_context_includes_performance -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_n8n_bridge.py tests/test_analytics_social.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps (tests to add before implementation)

- [ ] `tests/test_n8n_bridge.py::test_execute_poll_analytics_24h` — covers ANLYT-01: mocks DB cursor with due jobs, verifies `update_post_performance` called per job
- [ ] `tests/test_n8n_bridge.py::test_execute_poll_analytics_7d` — covers ANLYT-01: same pattern for 7d endpoint
- [ ] `tests/test_n8n_bridge.py::test_execute_process_scheduled_posts_writes_publish_results` — covers ANLYT-02: verifies `content_jobs.publish_results[platform]` written after publish
- [ ] `tests/test_n8n_bridge.py::test_analytics_due_at_set_on_publish` — covers ANLYT-02: verifies `analytics_24h_due_at` and `analytics_7d_due_at` fields set at publish time
- [ ] `tests/test_n8n_bridge.py::test_poll_analytics_calls_optimal_times` — covers ANLYT-03: verifies `calculate_optimal_posting_times` called for affected users
- [ ] `tests/test_strategist.py::test_gather_user_context_includes_performance` — covers ANLYT-04: verifies performance_signals non-empty when jobs have `performance_data`

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 13 |
|-----------|-------------------|
| Never use `os.environ.get()` directly in routes/agents/services | N8nConfig fields use `os.environ.get()` via dataclass field_factory — this is the approved pattern |
| Always `from database import db` with Motor async | All new execute endpoints follow this pattern |
| After any change to `backend/agents/`, verify full pipeline | ANLYT-04 involves only reading from `strategist.py`, not modifying it — but verify pipeline after any agent file edit |
| All settings come from `backend/config.py` dataclasses | New `N8N_WORKFLOW_ANALYTICS_POLL_24H` and `N8N_WORKFLOW_ANALYTICS_POLL_7D` env vars must go into `N8nConfig` |
| Never commit directly to `main` | Branch: `feat/analytics-feedback-loop` from `dev` |
| Never introduce a new Python package without adding to `requirements.txt` | No new packages — not applicable |

---

## Sources

### Primary (HIGH confidence — verified against live codebase)

- `backend/services/social_analytics.py` — All three platform fetchers + `update_post_performance` + `_aggregate_performance_intelligence` fully implemented
- `backend/services/persona_refinement.py:465` — `calculate_optimal_posting_times` fully implemented
- `backend/routes/n8n_bridge.py` — All 8 execute endpoints, `_verify_n8n_request` dependency, `_get_workflow_map()`, `WORKFLOW_NOTIFICATION_MAP` patterns
- `backend/agents/strategist.py:219-242` — `_gather_user_context()` already reads `performance_data` from jobs
- `backend/config.py:217-235` — `N8nConfig` dataclass fields — confirmed no analytics poll workflow fields exist yet
- `backend/tests/test_analytics_social.py` — Existing test coverage for platform fetchers and `update_post_performance`
- `backend/tasks/content_tasks.py:530-556` — `update_performance_intelligence` Celery task as reference for the execute endpoint logic

### Secondary (MEDIUM confidence — architecture docs)

- `.planning/research/ARCHITECTURE.md:375-387` — Analytics feedback loop architecture documented (n8n Wait node + callback pattern)
- `.planning/research/SUMMARY.md` — Phase 4 research flags for LinkedIn/Instagram API scopes confirmed

### Tertiary (LOW confidence — not re-verified)

- Phase 9 research: LinkedIn UGC API `r_organization_social` scope limitations for personal accounts — reflected in `fetch_linkedin_post_metrics` fallback heuristic

---

## Metadata

**Confidence breakdown:**
- What already exists (social_analytics.py, persona_refinement.py, strategist.py): HIGH — verified by reading source files
- What needs to be added (execute endpoints, N8nConfig fields, analytics due-at fields): HIGH — follows established n8n_bridge.py patterns exactly
- publish_results gap (Pitfall 1): HIGH — confirmed by reading both execute_process_scheduled_posts and update_post_performance
- Instagram Business account limitation: HIGH — documented in social_analytics.py code comment
- ANLYT-04 Strategist auto-wiring: HIGH — confirmed by reading _gather_user_context and _build_synthesis_prompt

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable APIs, no fast-moving dependencies)
