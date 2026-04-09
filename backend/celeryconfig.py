"""Celery configuration for ThookAI.

Defines serialisation, task routing.

NOTE: Beat schedule has been removed — all 7 periodic tasks are now
driven by n8n cron triggers calling POST /api/n8n/execute/{task_name}.
See: backend/routes/n8n_bridge.py
"""

# Serialisation
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True

# Execution
task_acks_late = True
task_reject_on_worker_lost = True
worker_prefetch_multiplier = 1

# Results
result_expires = 86400  # 24 hours

# Task routing
task_routes = {
    # Video generation tasks route to dedicated video queue for isolation
    "tasks.media_tasks.generate_video*": {"queue": "video"},
    "tasks.media_tasks.generate_video_for_job*": {"queue": "video"},
    # All other media tasks (images, audio) route to media queue
    "tasks.media_tasks.*": {"queue": "media"},
    # Content pipeline and scheduled task management
    "tasks.content_tasks.*": {"queue": "content"},
}

# Beat schedule — restored from n8n migration.
# All periodic tasks run via Celery Beat calling the same logic
# that was previously in n8n bridge endpoints.
from celery.schedules import crontab

beat_schedule = {
    # Every 5 minutes: publish scheduled posts
    "process-scheduled-posts": {
        "task": "tasks.scheduled_tasks.process_scheduled_posts",
        "schedule": crontab(minute="*/5"),
    },
    # Every 10 minutes: mark stale running jobs as errored
    "cleanup-stale-jobs": {
        "task": "tasks.scheduled_tasks.cleanup_stale_jobs",
        "schedule": crontab(minute="*/10"),
    },
    # Midnight UTC: reset daily content creation counters
    "reset-daily-limits": {
        "task": "tasks.scheduled_tasks.reset_daily_limits",
        "schedule": crontab(hour=0, minute=0),
    },
    # 1st of month midnight: refresh monthly credits
    "refresh-monthly-credits": {
        "task": "tasks.scheduled_tasks.refresh_monthly_credits",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
    },
    # 1am UTC daily: run nightly strategist
    "run-nightly-strategist": {
        "task": "tasks.scheduled_tasks.run_nightly_strategist",
        "schedule": crontab(hour=1, minute=0),
    },
    # 2am UTC daily: aggregate daily analytics
    "aggregate-daily-analytics": {
        "task": "tasks.scheduled_tasks.aggregate_daily_analytics",
        "schedule": crontab(hour=2, minute=0),
    },
    # 3am UTC daily: delete old failed jobs
    "cleanup-old-jobs": {
        "task": "tasks.scheduled_tasks.cleanup_old_jobs",
        "schedule": crontab(hour=3, minute=0),
    },
    # 4am UTC daily: deactivate expired persona shares
    "cleanup-expired-shares": {
        "task": "tasks.scheduled_tasks.cleanup_expired_shares",
        "schedule": crontab(hour=4, minute=0),
    },
    # Every 8 hours: poll 24h post analytics
    "poll-analytics-24h": {
        "task": "tasks.scheduled_tasks.poll_analytics_24h",
        "schedule": crontab(hour="*/8", minute=0),
    },
    # Monday 6am: poll 7-day post analytics
    "poll-analytics-7d": {
        "task": "tasks.scheduled_tasks.poll_analytics_7d",
        "schedule": crontab(day_of_week=1, hour=6, minute=0),
    },
}
