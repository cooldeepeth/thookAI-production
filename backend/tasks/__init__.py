"""
Celery Task Queue for ThookAI

Usage:
    # Start worker:
    celery -A celery_app worker --loglevel=info

    # Start beat scheduler:
    celery -A celery_app beat --loglevel=info
"""

import logging
from datetime import datetime, timezone

from celery_app import celery_app  # canonical app from backend/celery_app.py

logger = logging.getLogger(__name__)


# ============ REDIS AVAILABILITY CHECK ============

def is_redis_configured() -> bool:
    """Check if Redis is reachable."""
    try:
        import redis
        url = celery_app.conf.broker_url or "redis://localhost:6379/0"
        r = redis.Redis.from_url(url)
        r.ping()
        return True
    except Exception:
        return False


# ============ FALLBACK MODE ============

class SyncTaskRunner:
    """Fallback runner when Celery/Redis is not available."""

    @staticmethod
    def delay(*args, **kwargs):
        return SyncTaskRunner()

    @staticmethod
    def apply_async(*args, **kwargs):
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
        return {"task_id": task_id, "status": "completed", "message": "Running in sync mode"}

    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": result.result if result.ready() else None,
        }
    except Exception as e:
        return {"task_id": task_id, "status": "error", "error": str(e)}


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
        return {"status": "disabled", "message": "Redis not configured. Running in sync mode."}

    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()

        if active:
            return {
                "status": "healthy",
                "workers": len(active),
                "active_tasks": sum(len(tasks) for tasks in active.values()),
            }
        else:
            return {"status": "no_workers", "message": "No Celery workers are running"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
