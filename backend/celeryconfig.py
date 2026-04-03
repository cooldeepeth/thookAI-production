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

# Beat schedule — MIGRATED TO n8n (Phase 9)
# All 7 periodic tasks now run via n8n cron triggers calling
# POST /api/n8n/execute/{task_name} endpoints.
# See: backend/routes/n8n_bridge.py
beat_schedule = {}
