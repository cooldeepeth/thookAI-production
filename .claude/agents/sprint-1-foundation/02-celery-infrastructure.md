# Agent: Celery Infrastructure + Real Publisher Wiring
Sprint: 1 | Branch: infra/celery-setup | PR target: dev
Depends on: Agent 01 merged (model fix should be on dev already, but not a hard dependency)

## Context
The entire async task system is dead. There is no celery_app.py, no beat schedule,
and the _publish_to_platform() function in content_tasks.py is a placeholder that
logs "SIMULATED" and never actually publishes. This means:
- Scheduled posts NEVER publish to any platform
- Daily credit limits NEVER reset (users stay locked out forever)
- Monthly credits NEVER refresh
- No cleanup of old jobs or expired shares

## Files You Will Touch (create or modify)
- backend/celery_app.py          (CREATE — does not exist)
- backend/celeryconfig.py        (CREATE — does not exist)
- backend/tasks/content_tasks.py (MODIFY — fix _publish_to_platform)
- backend/tasks/__init__.py      (MODIFY — import celery_app)
- backend/Procfile               (MODIFY — add worker and beat processes)

## Files You Must Read First (do not modify)
- backend/config.py              (settings.app.redis_url pattern)
- backend/database.py            (db access pattern for async tasks)
- backend/agents/publisher.py    (the REAL publisher — understand its interface)
- backend/tasks/content_tasks.py (read fully before modifying)
- backend/auth_utils.py          (understand how platform tokens are retrieved)

## ⚠️ Celery + Async Note
Celery workers run in a sync context. Do NOT use asyncio.run() if a loop
may already be running. Preferred pattern inside Celery tasks for DB access:
  import pymongo (sync) for task-internal DB reads
  OR use: loop = asyncio.new_event_loop(); loop.run_until_complete(coro); loop.close()
Claude must check if motor or pymongo is used and pick the correct pattern.

## Step 1: Create backend/celery_app.py
```python
from celery import Celery
from config import settings

def make_celery():
    broker = settings.app.redis_url or "redis://localhost:6379/0"
    backend = settings.app.redis_url or "redis://localhost:6379/0"
    
    app = Celery(
        "thookai",
        broker=broker,
        backend=backend,
        include=[
            "tasks.content_tasks",
            "tasks.media_tasks",
        ]
    )
    app.config_from_object("celeryconfig")
    return app

celery_app = make_celery()
```

## Step 2: Create backend/celeryconfig.py
Define beat_schedule with these exact 6 tasks:
- process_scheduled_posts: runs every 5 minutes (crontab minute="*/5")
- reset_daily_limits: runs daily at 00:00 UTC
- refresh_monthly_credits: runs on the 1st of each month at 00:05 UTC
- cleanup_old_jobs: runs daily at 02:00 UTC
- cleanup_expired_shares: runs daily at 02:30 UTC
- aggregate_daily_analytics: runs daily at 01:00 UTC

## Step 3: Fix _publish_to_platform() in content_tasks.py
Current code logs "[SIMULATED]" and returns True. Replace the entire function body:

The function receives: platform (str), content (str), user_id (str), media_urls (list)
It must:
1. Import publisher from agents.publisher (use lazy import to avoid circular imports)
2. Fetch the user's platform token from db.platform_tokens using motor sync via
   asyncio.run() since this is a Celery task (sync context):
   token_doc = asyncio.run(db.platform_tokens.find_one({"user_id": user_id, "platform": platform}))
3. If no token found, raise ValueError(f"No OAuth token found for {user_id} on {platform}")
4. Call the appropriate publisher method based on platform:
   - "linkedin" → publisher.publish_to_linkedin(content, token_doc["access_token"], media_urls)
   - "twitter" → publisher.publish_to_x(content, token_doc["access_token"], media_urls)
   - "instagram" → publisher.publish_to_instagram(content, token_doc["access_token"], media_urls)
5. Return the result dict from the publisher
6. Wrap everything in try/except, log errors with full traceback, re-raise

## Step 4: Update backend/tasks/__init__.py
Add: `from celery_app import celery_app`

## Step 5: Update backend/Procfile
Current: `web: uvicorn server:app --host 0.0.0.0 --port $PORT`
New (add two lines):

web: uvicorn server:app --host 0.0.0.0 --port $PORT
worker: celery -A celery_app worker --loglevel=info --concurrency=2
beat: celery -A celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler

## Definition of Done
- `python -c "from celery_app import celery_app; print(celery_app)"` runs without error
- `grep -n "SIMULATED" backend/tasks/content_tasks.py` returns zero results
- Procfile has 3 process types: web, worker, beat
- PR created to dev with title: "infra: configure Celery beat + wire real publisher"