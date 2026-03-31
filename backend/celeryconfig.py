"""Celery configuration for ThookAI.

Defines serialisation, task routing, and the beat schedule
for all 6 periodic tasks.
"""

from celery.schedules import crontab

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

# Beat schedule — all 6 periodic tasks
beat_schedule = {
    "process-scheduled-posts": {
        "task": "tasks.content_tasks.process_scheduled_posts",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "reset-daily-limits": {
        "task": "tasks.content_tasks.reset_daily_limits",
        "schedule": crontab(hour=0, minute=0),  # Daily at 00:00 UTC
    },
    "refresh-monthly-credits": {
        "task": "tasks.content_tasks.refresh_monthly_credits",
        "schedule": crontab(day_of_month=1, hour=0, minute=5),  # 1st of month at 00:05 UTC
    },
    "cleanup-old-jobs": {
        "task": "tasks.content_tasks.cleanup_old_jobs",
        "schedule": crontab(hour=2, minute=0),  # Daily at 02:00 UTC
    },
    "cleanup-expired-shares": {
        "task": "tasks.content_tasks.cleanup_expired_shares",
        "schedule": crontab(hour=2, minute=30),  # Daily at 02:30 UTC
    },
    "aggregate-daily-analytics": {
        "task": "tasks.content_tasks.aggregate_daily_analytics",
        "schedule": crontab(hour=1, minute=0),  # Daily at 01:00 UTC
    },
    "cleanup-stale-jobs": {
        "task": "tasks.content_tasks.cleanup_stale_running_jobs",
        "schedule": crontab(minute="*/10"),  # Every 10 minutes
    },
}
