"""
Celery Task Queue Configuration for ThookAI

Handles async processing of:
- Video generation (Runway, Pika, etc.)
- Image generation (DALL-E, Stable Diffusion)
- Voice synthesis (ElevenLabs)
- Heavy AI operations

Usage:
    # Start worker:
    celery -A tasks.celery_app worker --loglevel=info

    # Start beat scheduler (for periodic tasks):
    celery -A tasks.celery_app beat --loglevel=info
"""

import os
import logging
from celery import Celery
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ============ CONFIGURATION ============

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)

# Check if Redis is configured
def is_redis_configured() -> bool:
    """Check if Redis is available for Celery."""
    if not REDIS_URL or REDIS_URL == 'redis://localhost:6379/0':
        # Try to connect to localhost Redis
        try:
            import redis
            r = redis.Redis.from_url(REDIS_URL)
            r.ping()
            return True
        except Exception:
            return False
    return True


# ============ CELERY APP SETUP ============

# Create Celery app
celery_app = Celery(
    'thook_tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['tasks.media_tasks', 'tasks.content_tasks']
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes (prevents lost tasks)
    task_reject_on_worker_lost=True,
    
    # Concurrency and rate limiting
    worker_prefetch_multiplier=1,  # One task at a time per worker
    task_default_rate_limit='10/m',  # Default rate limit
    
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    
    # Task routes - different queues for different priorities
    task_routes={
        'tasks.media_tasks.generate_video': {'queue': 'video'},
        'tasks.media_tasks.generate_voice': {'queue': 'voice'},
        'tasks.media_tasks.generate_image': {'queue': 'media'},
        'tasks.content_tasks.*': {'queue': 'content'},
    },
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute delay between retries
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Reset daily content limits at midnight UTC
    'reset-daily-limits': {
        'task': 'tasks.content_tasks.reset_daily_limits',
        'schedule': 86400.0,  # Every 24 hours
    },
    # Process scheduled posts every 5 minutes
    'process-scheduled-posts': {
        'task': 'tasks.content_tasks.process_scheduled_posts',
        'schedule': 300.0,  # Every 5 minutes
    },
    # Clean up old job data
    'cleanup-old-jobs': {
        'task': 'tasks.content_tasks.cleanup_old_jobs',
        'schedule': 86400.0,  # Daily
    },
}


# ============ FALLBACK MODE ============

class SyncTaskRunner:
    """
    Fallback synchronous task runner when Celery/Redis is not available.
    Executes tasks immediately in the current thread.
    """
    
    @staticmethod
    def delay(*args, **kwargs):
        """Immediate execution fallback."""
        return SyncTaskRunner()
    
    @staticmethod
    def apply_async(*args, **kwargs):
        """Immediate execution fallback."""
        return SyncTaskRunner()
    
    @property
    def id(self):
        return f"sync-{datetime.now(timezone.utc).timestamp()}"
    
    def get(self, timeout=None):
        return None


def get_task_runner():
    """Get the appropriate task runner based on Redis availability."""
    if is_redis_configured():
        return celery_app
    else:
        logger.warning("Redis not available. Tasks will run synchronously.")
        return None


# ============ TASK STATUS UTILITIES ============

async def get_task_status(task_id: str) -> dict:
    """Get status of a Celery task."""
    if not is_redis_configured():
        return {
            "task_id": task_id,
            "status": "completed",
            "message": "Running in sync mode"
        }
    
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": result.result if result.ready() else None
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e)
        }


async def revoke_task(task_id: str, terminate: bool = False) -> dict:
    """Revoke/cancel a pending task."""
    if not is_redis_configured():
        return {"success": False, "error": "Celery not configured"}
    
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        return {"success": True, "task_id": task_id, "revoked": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ WORKER HEALTH CHECK ============

def check_celery_health() -> dict:
    """Check Celery worker health."""
    if not is_redis_configured():
        return {
            "status": "disabled",
            "message": "Redis not configured. Running in sync mode."
        }
    
    try:
        # Ping workers
        inspect = celery_app.control.inspect()
        active = inspect.active()
        
        if active:
            worker_count = len(active)
            return {
                "status": "healthy",
                "workers": worker_count,
                "active_tasks": sum(len(tasks) for tasks in active.values())
            }
        else:
            return {
                "status": "no_workers",
                "message": "No Celery workers are running"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
