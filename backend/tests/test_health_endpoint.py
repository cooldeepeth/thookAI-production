"""
Test plan items 7-8 proxy: verify /health endpoint returns correct structure.

These tests exercise the /health endpoint which acts as a backend integration
check. Frontend mobile-nav and 401-handling behaviours are verified via code
review (see PR description) since they require a browser environment.
"""
import sys
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure backend/ is on the import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestHealthEndpoint:
    """Verify GET /health returns the expected JSON structure."""

    @pytest.fixture(autouse=True)
    def _setup_client(self):
        """Create a TestClient for each test, mocking external dependencies."""
        # Patch database and redis before importing app so the lifespan
        # event doesn't try to reach real Mongo / Redis.
        with (
            patch("database.db") as mock_db,
            patch("database.client") as _mock_client,
            patch("db_indexes.create_indexes", new_callable=AsyncMock, return_value={"created": 0, "skipped": 0, "errors": []}),
            patch("middleware.redis_client.get_redis", new_callable=AsyncMock, return_value=None),
        ):
            mock_db.command = AsyncMock(return_value={"ok": 1})
            from server import app
            from fastapi.testclient import TestClient

            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    # ------------------------------------------------------------------
    # Test: structure of /health response
    # ------------------------------------------------------------------
    def test_health_returns_required_keys(self):
        """GET /health must include status, mongodb, redis, r2_storage, llm_provider, timestamp."""
        response = self.client.get("/health")

        assert response.status_code in (200, 503), f"Unexpected status {response.status_code}"
        data = response.json()

        required_keys = {"status", "mongodb", "redis", "r2_storage", "llm_provider", "timestamp"}
        missing = required_keys - set(data.keys())
        assert not missing, f"Missing keys in /health response: {missing}"

    def test_health_status_value(self):
        """status field should be either 'ok' or 'degraded'."""
        response = self.client.get("/health")
        data = response.json()
        assert data["status"] in ("ok", "degraded"), f"Unexpected status value: {data['status']}"

    def test_health_timestamp_is_iso(self):
        """timestamp should be a valid ISO-8601 string."""
        from datetime import datetime

        response = self.client.get("/health")
        data = response.json()
        # Will raise ValueError if the format is wrong
        datetime.fromisoformat(data["timestamp"])

    # ------------------------------------------------------------------
    # Test: /api/health (the second health endpoint)
    # ------------------------------------------------------------------
    def test_api_health_returns_required_keys(self):
        """GET /api/health should return status, environment, and checks dict."""
        response = self.client.get("/api/health")

        assert response.status_code == 200, f"Unexpected status {response.status_code}"
        data = response.json()

        assert "status" in data, "Missing 'status' key in /api/health"
        assert "environment" in data, "Missing 'environment' key in /api/health"
        assert "checks" in data, "Missing 'checks' key in /api/health"
        assert isinstance(data["checks"], dict), "'checks' should be a dict"

    def test_api_health_checks_contain_subsystems(self):
        """The checks dict should report on database, llm, media, auth, vector store, billing."""
        response = self.client.get("/api/health")
        data = response.json()
        checks = data["checks"]

        expected_check_keys = {
            "database",
            "llm_configured",
            "media_storage",
            "google_auth",
            "vector_store",
            "billing",
        }
        missing = expected_check_keys - set(checks.keys())
        assert not missing, f"Missing subsystem checks: {missing}"
