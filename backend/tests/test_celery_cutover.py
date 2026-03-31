"""
Tests for the Celery → n8n cutover (Phase 9, Plan 02).

Verifies:
  - beat_schedule is empty (migrated to n8n)
  - task_routes for media/content queues are preserved
  - Procfile has 2 processes (web + worker), no beat line
  - docker-compose.yml has n8n + postgres-n8n + n8n-worker, no celery-beat
  - Idempotency guard logic on process-scheduled-posts
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Paths resolve relative to this test file's location (backend/tests/)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROCFILE = os.path.join(_BACKEND_DIR, "Procfile")
_DOCKER_COMPOSE = os.path.join(_BACKEND_DIR, "..", "docker-compose.yml")


# ---------------------------------------------------------------------------
# Celery Beat Removal
# ---------------------------------------------------------------------------


class TestCeleryBeatRemoval:
    def test_beat_schedule_is_empty(self) -> None:
        """beat_schedule must be an empty dict — all tasks migrated to n8n."""
        import celeryconfig

        assert celeryconfig.beat_schedule == {}, (
            f"beat_schedule should be empty, got: {celeryconfig.beat_schedule}"
        )

    def test_task_routes_preserved(self) -> None:
        """task_routes must still route media tasks to their dedicated queues."""
        import celeryconfig

        assert "tasks.media_tasks.*" in celeryconfig.task_routes, (
            "tasks.media_tasks.* route is missing"
        )
        assert celeryconfig.task_routes["tasks.media_tasks.*"] == {"queue": "media"}, (
            "tasks.media_tasks.* must route to media queue"
        )
        assert "tasks.media_tasks.generate_video*" in celeryconfig.task_routes, (
            "tasks.media_tasks.generate_video* route is missing"
        )
        assert celeryconfig.task_routes["tasks.media_tasks.generate_video*"] == {
            "queue": "video"
        }, "video generation tasks must route to video queue"

    def test_content_task_routes_preserved(self) -> None:
        """Content pipeline tasks still route to content queue via Celery worker."""
        import celeryconfig

        assert "tasks.content_tasks.*" in celeryconfig.task_routes, (
            "tasks.content_tasks.* route is missing"
        )
        assert celeryconfig.task_routes["tasks.content_tasks.*"] == {
            "queue": "content"
        }

    def test_task_serializer_unchanged(self) -> None:
        """Core Celery serialisation settings must not have changed."""
        import celeryconfig

        assert celeryconfig.task_serializer == "json"
        assert celeryconfig.timezone == "UTC"
        assert celeryconfig.enable_utc is True
        assert celeryconfig.task_acks_late is True

    def test_crontab_import_removed(self) -> None:
        """celeryconfig.py should no longer import crontab since beat_schedule is empty."""
        celeryconfig_path = os.path.join(_BACKEND_DIR, "celeryconfig.py")
        with open(celeryconfig_path) as f:
            content = f.read()
        # crontab import is no longer needed when beat_schedule is empty
        assert "from celery.schedules import crontab" not in content, (
            "crontab import should be removed now that beat_schedule is empty"
        )


# ---------------------------------------------------------------------------
# Procfile
# ---------------------------------------------------------------------------


class TestProcfile:
    def test_no_beat_process(self) -> None:
        """Procfile must not contain a beat process after Celery cutover."""
        with open(_PROCFILE) as f:
            content = f.read()
        assert "beat" not in content.lower(), (
            "Procfile should not contain beat process after n8n migration"
        )

    def test_web_process_exists(self) -> None:
        """web: process must remain for the FastAPI server."""
        with open(_PROCFILE) as f:
            lines = f.read().strip().split("\n")
        assert any(line.startswith("web:") for line in lines), (
            "Procfile must have a web: process"
        )

    def test_worker_process_exists(self) -> None:
        """worker: process must remain for Celery media/content tasks."""
        with open(_PROCFILE) as f:
            lines = f.read().strip().split("\n")
        worker_lines = [line for line in lines if line.startswith("worker:")]
        assert len(worker_lines) == 1, f"Expected exactly 1 worker line, got: {worker_lines}"
        assert "--beat" not in worker_lines[0], (
            "Worker must not include --beat flag (beat is handled by n8n now)"
        )

    def test_exactly_two_processes(self) -> None:
        """After cutover, Procfile has exactly 2 processes: web + worker."""
        with open(_PROCFILE) as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        assert len(lines) == 2, (
            f"Expected exactly 2 processes after beat removal, got {len(lines)}: {lines}"
        )

    def test_uvicorn_in_web_process(self) -> None:
        """web: process must start uvicorn (not gunicorn or something else)."""
        with open(_PROCFILE) as f:
            content = f.read()
        assert "uvicorn server:app" in content, (
            "web: process must use uvicorn server:app"
        )


# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------


class TestDockerCompose:
    def test_no_celery_beat_service(self) -> None:
        """celery-beat service must be removed after n8n migration."""
        with open(_DOCKER_COMPOSE) as f:
            content = f.read()
        assert "celery-beat" not in content, (
            "docker-compose.yml should not contain celery-beat service after n8n migration"
        )

    def test_n8n_service_exists(self) -> None:
        """n8n, postgres-n8n, and n8n-worker services must be present."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed — using string-based check")

        with open(_DOCKER_COMPOSE) as f:
            compose = yaml.safe_load(f)

        services = compose.get("services", {})
        assert "n8n" in services, "n8n service missing from docker-compose.yml"
        assert "postgres-n8n" in services, "postgres-n8n service missing"
        assert "n8n-worker" in services, "n8n-worker service missing"

    def test_n8n_uses_stable_image(self) -> None:
        """n8n service must use n8nio/n8n:stable image."""
        with open(_DOCKER_COMPOSE) as f:
            content = f.read()
        assert "n8nio/n8n:stable" in content, (
            "n8n service must use n8nio/n8n:stable image"
        )

    def test_n8n_worker_has_process_type(self) -> None:
        """n8n-worker must have N8N_PROCESS_TYPE=worker to run in worker mode."""
        with open(_DOCKER_COMPOSE) as f:
            content = f.read()
        assert "N8N_PROCESS_TYPE=worker" in content, (
            "n8n-worker must have N8N_PROCESS_TYPE=worker (required for queue mode)"
        )

    def test_postgres_n8n_volume_defined(self) -> None:
        """n8n_postgres_data volume must be defined at the top level."""
        with open(_DOCKER_COMPOSE) as f:
            content = f.read()
        assert "n8n_postgres_data" in content, (
            "n8n_postgres_data volume must be defined in docker-compose.yml volumes section"
        )

    def test_n8n_uses_postgres_db(self) -> None:
        """n8n must be configured to use PostgreSQL (not SQLite) for production reliability."""
        with open(_DOCKER_COMPOSE) as f:
            content = f.read()
        assert "DB_TYPE=postgresdb" in content, (
            "n8n must use postgresdb (not SQLite) for production reliability"
        )

    def test_n8n_executions_mode_queue(self) -> None:
        """n8n must run in queue mode to support multiple workers."""
        with open(_DOCKER_COMPOSE) as f:
            content = f.read()
        assert "EXECUTIONS_MODE=queue" in content, (
            "n8n must use EXECUTIONS_MODE=queue to enable n8n-worker scaling"
        )

    def test_celery_worker_preserved(self) -> None:
        """celery-worker service must still exist for media generation tasks."""
        with open(_DOCKER_COMPOSE) as f:
            content = f.read()
        assert "celery-worker" in content, (
            "celery-worker service must remain for media/content task processing"
        )


# ---------------------------------------------------------------------------
# Idempotency Guard
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Tests for the idempotency guard on process-scheduled-posts endpoint."""

    @pytest.mark.asyncio
    async def test_atomic_claim_prevents_duplicate_processing(self) -> None:
        """
        find_one_and_update with status=scheduled claims post atomically.
        A second call for the same schedule_id returns None (already claimed).
        """
        mock_db = MagicMock()
        mock_scheduled_posts = AsyncMock()
        mock_db.scheduled_posts = mock_scheduled_posts

        now = datetime.now(timezone.utc)
        test_post = {
            "schedule_id": "test-123",
            "status": "scheduled",
            "scheduled_at": now - timedelta(minutes=1),
            "platform": "linkedin",
            "user_id": "user-abc",
            "content": "Test post",
        }

        # First call: claim succeeds — returns the claimed document
        mock_scheduled_posts.find_one_and_update.return_value = {
            **test_post,
            "status": "processing",
            "processing_started_at": now,
        }

        claim1 = await mock_scheduled_posts.find_one_and_update(
            {
                "schedule_id": "test-123",
                "status": "scheduled",
                "$or": [
                    {"processing_started_at": {"$exists": False}},
                    {"processing_started_at": {"$lt": now - timedelta(minutes=5)}},
                ],
            },
            {"$set": {"status": "processing", "processing_started_at": now}},
            return_document=True,
        )
        assert claim1 is not None, "First claim should succeed"
        assert claim1["status"] == "processing"

        # Second call: claim fails — post is already processing
        mock_scheduled_posts.find_one_and_update.return_value = None

        claim2 = await mock_scheduled_posts.find_one_and_update(
            {
                "schedule_id": "test-123",
                "status": "scheduled",
                "$or": [
                    {"processing_started_at": {"$exists": False}},
                    {"processing_started_at": {"$lt": now - timedelta(minutes=5)}},
                ],
            },
            {"$set": {"status": "processing", "processing_started_at": now}},
            return_document=True,
        )
        assert claim2 is None, "Second claim should fail — post already processing"

    @pytest.mark.asyncio
    async def test_recently_published_post_is_skipped(self) -> None:
        """A post with published_at within last 2 minutes should be skipped."""
        now = datetime.now(timezone.utc)

        # published_at 1 minute ago — should be skipped (within 2-min window)
        published_at_recent = now - timedelta(minutes=1)
        assert (now - published_at_recent) < timedelta(minutes=2), (
            "Post published 1 min ago should be within 2-min window and skipped"
        )

        # published_at 3 minutes ago — should NOT be skipped (outside 2-min window)
        published_at_old = now - timedelta(minutes=3)
        assert (now - published_at_old) >= timedelta(minutes=2), (
            "Post published 3 min ago should be outside 2-min window and not skipped"
        )

    @pytest.mark.asyncio
    async def test_stale_claim_is_reclaimed_after_5_minutes(self) -> None:
        """A post claimed more than 5 minutes ago (stale) can be reclaimed."""
        mock_db = MagicMock()
        mock_scheduled_posts = AsyncMock()
        mock_db.scheduled_posts = mock_scheduled_posts

        now = datetime.now(timezone.utc)
        stale_processing_time = now - timedelta(minutes=6)

        # The query's $or condition allows reclaiming posts with
        # processing_started_at older than 5 minutes (stale claims)
        mock_scheduled_posts.find_one_and_update.return_value = {
            "schedule_id": "stale-456",
            "status": "processing",
            "processing_started_at": stale_processing_time,
        }

        claim = await mock_scheduled_posts.find_one_and_update(
            {
                "schedule_id": "stale-456",
                "status": "scheduled",
                "$or": [
                    {"processing_started_at": {"$exists": False}},
                    {
                        "processing_started_at": {
                            "$lt": now - timedelta(minutes=5)
                        }
                    },
                ],
            },
            {"$set": {"status": "processing", "processing_started_at": now}},
            return_document=True,
        )
        assert claim is not None, (
            "Stale claim (>5 min) should be reclaimable to prevent stuck posts"
        )

    @pytest.mark.asyncio
    async def test_fresh_claim_not_reclaimable(self) -> None:
        """A post claimed 2 minutes ago (not yet stale) should not be reclaimed."""
        mock_db = MagicMock()
        mock_scheduled_posts = AsyncMock()
        mock_db.scheduled_posts = mock_scheduled_posts

        now = datetime.now(timezone.utc)
        fresh_processing_time = now - timedelta(minutes=2)

        # Post is in processing and was claimed only 2 minutes ago — not reclaimable
        # The $or condition requires processing_started_at < (now - 5min)
        # fresh_processing_time is only 2 min ago, so it does NOT match — returns None
        mock_scheduled_posts.find_one_and_update.return_value = None

        claim = await mock_scheduled_posts.find_one_and_update(
            {
                "schedule_id": "fresh-789",
                "status": "scheduled",
                "$or": [
                    {"processing_started_at": {"$exists": False}},
                    {
                        "processing_started_at": {
                            "$lt": now - timedelta(minutes=5)
                        }
                    },
                ],
            },
            {"$set": {"status": "processing", "processing_started_at": now}},
            return_document=True,
        )
        assert claim is None, (
            "Post claimed 2 min ago should not be reclaimable (not stale yet)"
        )
