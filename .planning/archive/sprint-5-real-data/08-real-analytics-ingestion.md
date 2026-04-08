# Agent: Real Social Analytics Ingestion
Sprint: 5 | Branch: feat/real-analytics-ingestion | PR target: dev
Depends on: Sprint 1 fully merged (correct model name + Celery must be running)

## Context
All analytics data shown to users is fabricated from internal DB job counts.
No actual post performance data (likes, impressions, comments, shares, reach) is
ever fetched from LinkedIn, X, or Instagram. The performance_intelligence field
in persona_engines is always {} and optimal_posting_times is always {}.

## Files You Will Touch
- backend/services/social_analytics.py      (CREATE — does not exist)
- backend/tasks/content_tasks.py            (MODIFY — add analytics polling tasks)
- backend/agents/analyst.py                 (MODIFY — use real data when available)
- backend/celeryconfig.py                   (MODIFY — add analytics polling schedules)

## Files You Must Read First (do not modify)
- backend/agents/publisher.py              (understand published_url and post_id storage)
- backend/routes/platforms.py             (understand OAuth token storage format)
- backend/agents/analyst.py               (read fully — understand current fake metrics)
- backend/tasks/content_tasks.py          (read aggregate_daily_analytics task)

## ⚠️ Rate Limit Note
LinkedIn: 500 calls/day per app on basic tier
X API v2: 500,000 tweets/month read on Basic ($100/mo)
Instagram Graph: 200 calls/hour per user token
Claude must implement exponential backoff and respect retry_after headers.
Do NOT poll more frequently than the beat schedule allows.

## Step 1: Create backend/services/social_analytics.py
Implement platform API calls for post metrics. The service needs these functions:

### LinkedIn metrics (using LinkedIn UGC API v2)
```python
async def fetch_linkedin_post_metrics(post_urn: str, access_token: str) -> dict:
    """
    Calls: GET https://api.linkedin.com/v2/socialActions/{encoded_post_urn}
    And:   GET https://api.linkedin.com/v2/organizationalEntityShareStatistics
    Returns: {impressions, clicks, likes, comments, shares, engagement_rate}
    """
```

### X/Twitter metrics (using X API v2)
```python
async def fetch_x_post_metrics(tweet_id: str, access_token: str) -> dict:
    """
    Calls: GET https://api.twitter.com/2/tweets/{tweet_id}?tweet.fields=public_metrics
    Returns: {impressions, likes, retweets, replies, bookmarks, engagement_rate}
    """
```

### Instagram metrics (using Instagram Graph API)
```python
async def fetch_instagram_post_metrics(media_id: str, access_token: str) -> dict:
    """
    Calls: GET https://graph.instagram.com/{media_id}/insights
           ?metric=impressions,reach,likes,comments,shares,saved
    Returns: {impressions, reach, likes, comments, shares, saved, engagement_rate}
    """
```

All functions must:
- Use httpx.AsyncClient for async HTTP calls
- Handle token expiry (401 response) by returning {"error": "token_expired"}
- Handle rate limits (429 response) by returning {"error": "rate_limited", "retry_after": N}
- Return {"error": "api_unavailable"} for any other failure — never raise exceptions

### Aggregation function
```python
async def update_post_performance(job_id: str, user_id: str, platform: str) -> bool:
    """
    Fetches metrics for a published post and writes them to:
    - db.content_jobs[job_id].performance_data
    - db.persona_engines[user_id].performance_intelligence (aggregated)
    Calculates optimal_posting_times from historical patterns.
    """
```

## Step 2: Add analytics polling tasks to content_tasks.py
Add two new Celery tasks:
1. `poll_post_metrics_24h` — runs 24h after a post is published
   Triggered by: adding a `countdown=86400` when scheduling the task after publish
2. `poll_post_metrics_7d` — runs 7 days after publish for longer-term metrics

In the `process_scheduled_posts` task, after a post is confirmed published,
schedule these two follow-up tasks:
```python
poll_post_metrics_24h.apply_async(
    args=[job_id, user_id, platform],
    countdown=86400  # 24 hours
)
poll_post_metrics_7d.apply_async(
    args=[job_id, user_id, platform],
    countdown=604800  # 7 days
)
```

## Step 3: Update analyst.py to use real data when available
In the analytics generation functions, add a fallback pattern:
```python
# Use real performance data if available, calculated data if not
real_metrics = job.get("performance_data", {})
if real_metrics and not real_metrics.get("error"):
    engagement = real_metrics.get("engagement_rate", 0)
    impressions = real_metrics.get("impressions", 0)
else:
    # Fallback to calculated estimate with clear label
    engagement = calculated_estimate
    impressions = 0
    is_estimated = True
```
Add an `is_estimated: bool` flag to all analytics responses so the frontend can
show "estimated" vs "actual" labels to users.

## Definition of Done
- backend/services/social_analytics.py exists with all 3 platform functions
- content_tasks.py schedules 24h and 7d polling after every published post
- analyst.py uses real data when available, estimated data as fallback
- Analytics responses include is_estimated flag
- PR created to dev with title: "feat: real social analytics ingestion from LinkedIn/X/Instagram"