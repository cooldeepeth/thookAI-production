# Agent: Performance Intelligence — Optimal Posting Times + Persona Evolution
Sprint: 5 | Branch: feat/performance-intelligence | PR target: dev
Depends on: Sprint 5 Agent 8 merged (real analytics must be ingested first)

## Context
db.persona_engines has two fields that are always empty:
1. performance_intelligence: {} — meant to hold aggregated performance patterns
2. optimal_posting_times: {} — meant to hold best times to post per platform

These are declared in the schema and shown in the analytics route but never
calculated from real data. This agent builds the calculation layer that runs
after real post metrics are ingested (built in Agent 8).

## Files You Will Touch
- backend/services/persona_refinement.py   (MODIFY — add performance calculations)
- backend/tasks/content_tasks.py           (MODIFY — trigger performance update after metrics poll)
- backend/agents/analyst.py               (MODIFY — return real performance_intelligence)
- backend/routes/analytics.py             (MODIFY — add optimal times endpoint)

## Files You Must Read First (do not modify)
- backend/services/persona_refinement.py  (read fully — existing refinement functions)
- backend/services/social_analytics.py   (MUST exist from Agent 8 — read update_post_performance)
- backend/agents/analyst.py              (find where performance_intelligence is referenced)
- backend/routes/analytics.py            (find existing analytics endpoints)

## Step 1: Add performance calculation functions to persona_refinement.py

```python
async def calculate_optimal_posting_times(user_id: str) -> dict:
    """
    Analyses all published posts for this user that have real performance data.
    Groups by platform → day_of_week → hour_of_day.
    Calculates average engagement_rate for each slot.
    Returns top 3 slots per platform:
    {
      "linkedin": [
        {"day": "Tuesday", "hour": 9, "avg_engagement": 0.045, "sample_size": 12},
        {"day": "Thursday", "hour": 11, "avg_engagement": 0.038, "sample_size": 8},
        {"day": "Wednesday", "hour": 8, "avg_engagement": 0.031, "sample_size": 6}
      ],
      "twitter": [...],
      "instagram": [...]
    }
    Minimum sample_size of 3 per slot to be included (avoid noise from 1-2 posts).
    If insufficient data: return {"linkedin": [], "twitter": [], "instagram": [],
                                  "message": "Need at least 10 published posts to calculate optimal times"}
    Writes result to db.persona_engines[user_id].optimal_posting_times
    """

async def calculate_performance_intelligence(user_id: str) -> dict:
    """
    Aggregates real post performance data into persona-level intelligence.
    Calculates:
    - top_performing_hook_types: which hook patterns get most engagement
    - top_performing_content_pillars: which topics resonate most
    - avg_engagement_by_platform: {linkedin: 0.04, twitter: 0.02, instagram: 0.06}
    - best_performing_formats: {linkedin: "list_post", twitter: "thread", instagram: "carousel"}
    - performance_trend: "improving" | "declining" | "stable" (last 30d vs previous 30d)
    - total_posts_with_data: int
    
    Only counts posts where performance_data exists and has no error field.
    Writes result to db.persona_engines[user_id].performance_intelligence
    Returns the calculated dict.
    """
```

## Step 2: Trigger calculations after metrics polling (content_tasks.py)
In the `poll_post_metrics_7d` task (created in Agent 8), after writing metrics:
```python
# After 7-day metrics are stored, recalculate performance intelligence
from services.persona_refinement import (
    calculate_optimal_posting_times,
    calculate_performance_intelligence
)
asyncio.run(calculate_performance_intelligence(user_id))
asyncio.run(calculate_optimal_posting_times(user_id))
logger.info(f"Performance intelligence updated for user {user_id}")
```
Use 7-day (not 24h) metrics for this because 24h data is too early for meaningful patterns.

## Step 3: Return real data from analyst.py
Find where analyst.py reads `performance_intelligence` and `optimal_posting_times`
from the persona engine. Remove any hardcoded empty dict fallbacks. Instead:
```python
perf_intel = persona_engine.get("performance_intelligence", {})
optimal_times = persona_engine.get("optimal_posting_times", {})

if not perf_intel:
    perf_intel = {"message": "Performance data is being collected. Check back after your first 5 published posts."}

if not optimal_times:
    optimal_times = {"message": "Optimal times are calculated after 10+ published posts with performance data."}
```

## Step 4: Add dedicated optimal times endpoint
In analytics.py:
```python
# GET /api/analytics/optimal-times
# Returns the user's optimal_posting_times from persona_engines
# If empty, returns guidance message about how many posts are needed
# Includes: last_calculated_at timestamp so frontend can show data freshness
```

## Definition of Done
- calculate_optimal_posting_times runs after 7-day metrics polling
- calculate_performance_intelligence aggregates real data into persona
- analyst.py returns real data with helpful messages when insufficient data exists
- GET /api/analytics/optimal-times endpoint works
- PR created to dev: "feat: performance intelligence — optimal posting times + engagement patterns"