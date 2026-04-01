"""
Tests for n8n workflow status notifications (Phase 09, Plan 03).

Covers:
  TestWorkflowStatusNotifications — callback endpoint creates workflow_status notifications
  TestDispatchWorkflowNotification — _dispatch_workflow_notification unit tests
  TestWorkflowNotificationMap — structural tests for WORKFLOW_NOTIFICATION_MAP
"""

import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport

from server import app
from routes.n8n_bridge import WORKFLOW_NOTIFICATION_MAP, _dispatch_workflow_notification


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_TEST_SECRET = "test_webhook_secret_notifications"


def _sign(payload: bytes, secret: str = _TEST_SECRET) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def _make_callback_payload(
    workflow_type: str,
    status: str = "completed",
    result: dict = None,
    affected_user_ids: list = None,
) -> bytes:
    """Build a callback payload bytes for testing."""
    payload = {
        "workflow_type": workflow_type,
        "status": status,
        "result": result or {},
        "executed_at": "2026-04-01T12:00:00Z",
        "affected_user_ids": affected_user_ids or [],
    }
    return json.dumps(payload).encode()


# ---------------------------------------------------------------------------
# TestWorkflowStatusNotifications — callback endpoint integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWorkflowStatusNotifications:
    """Tests for workflow_status notification dispatch via /api/n8n/callback."""

    async def test_callback_creates_notification_for_publish(self):
        """POST /api/n8n/callback calls _dispatch_workflow_notification for process-scheduled-posts."""
        payload_bytes = _make_callback_payload(
            workflow_type="process-scheduled-posts",
            status="completed",
            result={"published": 3, "failed": 0},
            affected_user_ids=["user_abc123"],
        )
        sig = _sign(payload_bytes)

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            with patch(
                "routes.n8n_bridge._dispatch_workflow_notification",
                new=AsyncMock(),
            ) as mock_dispatch:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/callback",
                        content=payload_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "X-ThookAI-Signature": sig,
                        },
                    )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "accepted"
        assert data.get("workflow_type") == "process-scheduled-posts"
        mock_dispatch.assert_called_once()

    async def test_callback_dispatches_for_cleanup_tasks_too(self):
        """POST /api/n8n/callback always calls _dispatch_workflow_notification (it internally skips cleanup)."""
        payload_bytes = _make_callback_payload(
            workflow_type="cleanup-stale-jobs",
            status="completed",
            result={"stale_jobs_cleaned": 2},
            affected_user_ids=[],
        )
        sig = _sign(payload_bytes)

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            with patch(
                "routes.n8n_bridge._dispatch_workflow_notification",
                new=AsyncMock(),
            ) as mock_dispatch:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/callback",
                        content=payload_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "X-ThookAI-Signature": sig,
                        },
                    )

        assert resp.status_code == 200, resp.text
        # Dispatch is always called; it internally skips cleanup tasks
        mock_dispatch.assert_called_once()

    async def test_callback_returns_workflow_type_in_response(self):
        """POST /api/n8n/callback response includes workflow_type field."""
        payload_bytes = _make_callback_payload(
            workflow_type="reset-daily-limits",
            status="completed",
        )
        sig = _sign(payload_bytes)

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            with patch(
                "routes.n8n_bridge._dispatch_workflow_notification",
                new=AsyncMock(),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/callback",
                        content=payload_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "X-ThookAI-Signature": sig,
                        },
                    )

        assert resp.status_code == 200, resp.text
        assert resp.json()["workflow_type"] == "reset-daily-limits"


# ---------------------------------------------------------------------------
# TestDispatchWorkflowNotification — unit tests for _dispatch_workflow_notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDispatchWorkflowNotification:
    """Unit tests for the _dispatch_workflow_notification helper function."""

    async def test_creates_notification_for_supported_workflow(self):
        """Creates workflow_status notification for process-scheduled-posts."""
        mock_create_notification = AsyncMock(return_value={})

        payload = {
            "workflow_type": "process-scheduled-posts",
            "status": "completed",
            "result": {"published": 2, "failed": 0},
            "executed_at": "2026-04-01T12:00:00Z",
            "affected_user_ids": ["user_123"],
        }

        # Patch at the module level where it will be imported
        with patch("services.notification_service.create_notification", mock_create_notification):
            await _dispatch_workflow_notification(payload)

        mock_create_notification.assert_called_once()
        call_kwargs = mock_create_notification.call_args[1]
        assert call_kwargs["type"] == "workflow_status"
        assert call_kwargs["user_id"] == "user_123"
        assert call_kwargs["title"] == "Scheduled posts processed"
        assert "metadata" in call_kwargs
        assert call_kwargs["metadata"]["workflow_type"] == "process-scheduled-posts"

    async def test_skips_cleanup_workflows(self):
        """Cleanup task workflows are silently skipped (not in WORKFLOW_NOTIFICATION_MAP)."""
        mock_create_notification = AsyncMock()

        payload = {
            "workflow_type": "cleanup-stale-jobs",
            "status": "completed",
            "result": {"stale_jobs_cleaned": 5},
            "affected_user_ids": ["user_123"],
        }

        with patch("services.notification_service.create_notification", mock_create_notification):
            await _dispatch_workflow_notification(payload)

        # cleanup-stale-jobs is not in WORKFLOW_NOTIFICATION_MAP — no notification created
        mock_create_notification.assert_not_called()

    async def test_includes_failure_prefix_when_status_failed(self):
        """When status is 'failed', notification title is prefixed with [Failed]."""
        mock_create_notification = AsyncMock(return_value={})

        payload = {
            "workflow_type": "reset-daily-limits",
            "status": "failed",
            "result": {},
            "executed_at": "2026-04-01T12:00:00Z",
            "affected_user_ids": ["user_456"],
        }

        with patch("services.notification_service.create_notification", mock_create_notification):
            await _dispatch_workflow_notification(payload)

        mock_create_notification.assert_called_once()
        call_kwargs = mock_create_notification.call_args[1]
        assert call_kwargs["title"].startswith("[Failed]")
        assert "Daily limits reset" in call_kwargs["title"]

    async def test_skips_when_no_affected_user_ids(self):
        """When affected_user_ids is empty, no notification is created."""
        mock_create_notification = AsyncMock()

        payload = {
            "workflow_type": "refresh-monthly-credits",
            "status": "completed",
            "result": {},
            "affected_user_ids": [],
        }

        with patch("services.notification_service.create_notification", mock_create_notification):
            await _dispatch_workflow_notification(payload)

        mock_create_notification.assert_not_called()

    async def test_notification_metadata_includes_workflow_type_and_status(self):
        """Notification metadata contains workflow_type, status, result, and executed_at."""
        mock_create_notification = AsyncMock(return_value={})
        executed_at = "2026-04-01T01:00:00Z"

        payload = {
            "workflow_type": "aggregate-daily-analytics",
            "status": "completed",
            "result": {"records_aggregated": 100},
            "executed_at": executed_at,
            "affected_user_ids": ["user_789"],
        }

        with patch("services.notification_service.create_notification", mock_create_notification):
            await _dispatch_workflow_notification(payload)

        mock_create_notification.assert_called_once()
        call_kwargs = mock_create_notification.call_args[1]
        metadata = call_kwargs["metadata"]
        assert metadata["workflow_type"] == "aggregate-daily-analytics"
        assert metadata["status"] == "completed"
        assert metadata["result"] == {"records_aggregated": 100}
        assert metadata["executed_at"] == executed_at

    async def test_notification_dispatch_handles_exception_gracefully(self):
        """If create_notification raises, _dispatch_workflow_notification swallows it."""
        mock_create_notification = AsyncMock(side_effect=Exception("DB connection failed"))

        payload = {
            "workflow_type": "process-scheduled-posts",
            "status": "completed",
            "result": {"published": 1, "failed": 0},
            "affected_user_ids": ["user_abc"],
        }

        with patch("services.notification_service.create_notification", mock_create_notification):
            # Should not raise — exception is caught and logged as warning
            await _dispatch_workflow_notification(payload)

        # Called once; exception was swallowed (logged as warning)
        mock_create_notification.assert_called_once()

    async def test_creates_notifications_for_multiple_users(self):
        """When affected_user_ids has multiple users, each gets a notification."""
        mock_create_notification = AsyncMock(return_value={})

        payload = {
            "workflow_type": "reset-daily-limits",
            "status": "completed",
            "result": {},
            "affected_user_ids": ["user_1", "user_2", "user_3"],
        }

        with patch("services.notification_service.create_notification", mock_create_notification):
            await _dispatch_workflow_notification(payload)

        assert mock_create_notification.call_count == 3
        called_user_ids = [
            call[1]["user_id"] for call in mock_create_notification.call_args_list
        ]
        assert "user_1" in called_user_ids
        assert "user_2" in called_user_ids
        assert "user_3" in called_user_ids


# ---------------------------------------------------------------------------
# TestWorkflowNotificationMap — verify map structure
# ---------------------------------------------------------------------------


class TestWorkflowNotificationMap:
    """Structural tests for WORKFLOW_NOTIFICATION_MAP."""

    def test_map_contains_publish_workflow(self):
        """WORKFLOW_NOTIFICATION_MAP has entry for process-scheduled-posts."""
        assert "process-scheduled-posts" in WORKFLOW_NOTIFICATION_MAP

    def test_map_contains_reset_daily_limits(self):
        """WORKFLOW_NOTIFICATION_MAP has entry for reset-daily-limits."""
        assert "reset-daily-limits" in WORKFLOW_NOTIFICATION_MAP

    def test_map_contains_refresh_monthly_credits(self):
        """WORKFLOW_NOTIFICATION_MAP has entry for refresh-monthly-credits."""
        assert "refresh-monthly-credits" in WORKFLOW_NOTIFICATION_MAP

    def test_map_contains_aggregate_daily_analytics(self):
        """WORKFLOW_NOTIFICATION_MAP has entry for aggregate-daily-analytics."""
        assert "aggregate-daily-analytics" in WORKFLOW_NOTIFICATION_MAP

    def test_cleanup_tasks_not_in_map(self):
        """Cleanup tasks are NOT in WORKFLOW_NOTIFICATION_MAP (no user notification needed)."""
        assert "cleanup-stale-jobs" not in WORKFLOW_NOTIFICATION_MAP
        assert "cleanup-old-jobs" not in WORKFLOW_NOTIFICATION_MAP
        assert "cleanup-expired-shares" not in WORKFLOW_NOTIFICATION_MAP

    def test_each_entry_has_title_and_body_template(self):
        """Every entry in WORKFLOW_NOTIFICATION_MAP has title and body_template fields."""
        for workflow_type, config in WORKFLOW_NOTIFICATION_MAP.items():
            assert "title" in config, f"Missing 'title' in {workflow_type}"
            assert "body_template" in config, f"Missing 'body_template' in {workflow_type}"
            assert config["title"], f"Empty 'title' in {workflow_type}"
            assert config["body_template"], f"Empty 'body_template' in {workflow_type}"

    def test_map_has_expected_entries(self):
        """WORKFLOW_NOTIFICATION_MAP has all user-facing workflows."""
        assert len(WORKFLOW_NOTIFICATION_MAP) >= 5
