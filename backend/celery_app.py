"""ThookAI Celery application.

Single source of truth for the Celery app instance.
All workers, beat, and task modules import from here.
"""

from celery import Celery
from config import settings


def make_celery() -> Celery:
    broker = settings.app.redis_url or "redis://localhost:6379/0"
    backend = settings.app.redis_url or "redis://localhost:6379/0"

    app = Celery(
        "thookai",
        broker=broker,
        backend=backend,
        include=[
            "tasks.content_tasks",
            "tasks.media_tasks",
        ],
    )
    app.config_from_object("celeryconfig")
    return app


celery_app = make_celery()
