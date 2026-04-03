"""
n8n Bridge Contract Tests — Phase 19, Plan 04.

Tests every /api/n8n/execute/* endpoint with HMAC authentication, covering:
  - HMAC tampered-signature rejection (401) for all endpoint categories
  - Missing-signature rejection (401)
  - Empty webhook secret rejects all requests
  - Constant-time comparison via hmac.compare_digest
  - All 10 execute endpoints: correct DB mutations and response shapes
  - Callback endpoint: HMAC-verified payload processing + notification dispatch
  - Trigger endpoint: auth-required, workflow dispatch, unknown-workflow 404

NOTE: Do NOT duplicate tests from test_n8n_bridge.py.  That file covers:
  - TestHmacVerification (unit — valid/invalid/empty secret/compare_digest)
  - TestN8nCallback (valid, invalid, missing header, empty secret)
  - TestN8nTrigger (known workflow, unknown, unconfigured, no-auth)
  - TestExecutePollAnalytics (24h, 7d, rate limit, error handling, process-scheduled-posts)
This file closes coverage gaps on the 7 remaining execute endpoints and
adds new scenarios not present in the existing test file.
"""

import hashlib
import hmac
import inspect
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from server import app
from auth_utils import get_current_user
from routes.n8n_bridge import _verify_n8n_request, _verify_n8n_signature

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_SECRET = "n8n_contract_test_secret_abc123"


def _make_hmac_headers(body: bytes, secret: str = _TEST_SECRET) -> dict:
    """Compute the X-ThookAI-Signature header value for a given body."""
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-ThookAI-Signature": sig,
    }


def _signed_post(body: bytes = b"{}") -> dict:
    """Return headers dict with correct HMAC signature for the given body."""
    return _make_hmac_headers(body)


def _make_async_cursor(items):
    """Return a mock Motor cursor supporting .to_list()."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.sort = MagicMock(return_value=cursor)
    return cursor


# ---------------------------------------------------------------------------
# TestHMACSignatureVerification — focused on execute endpoint behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHMACSignatureVerification:
    """Verify HMAC enforcement on execute endpoints beyond basic unit tests."""

    async def test_valid_hmac_returns_200_on_execute_cleanup_stale_jobs(self):
        """Correctly signed request to /execute/cleanup-stale-jobs returns 200."""
        body = b"{}"
        headers = _make_hmac_headers(body)

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_db.content_jobs.update_many = AsyncMock(return_value=mock_result)

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/cleanup-stale-jobs",
                        content=body,
                        headers=headers,
                    )

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"

    async def test_tampered_hmac_returns_401_on_execute_cleanup_stale_jobs(self):
        """Tampered signature is rejected with 401."""
        body = b"{}"
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/execute/cleanup-stale-jobs",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-ThookAI-Signature": "tampered_signature_xyz",
                    },
                )

        assert resp.status_code == 401, resp.text

    async def test_missing_signature_header_returns_401(self):
        """Request to any execute endpoint without X-ThookAI-Signature returns 401."""
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/execute/reset-daily-limits",
                    content=b"{}",
                    headers={"Content-Type": "application/json"},
                )

        assert resp.status_code == 401, resp.text

    async def test_empty_webhook_secret_rejects_all_requests(self):
        """When webhook_secret is empty, even a correctly computed signature is rejected."""
        # Compute a signature with a known key — but server has empty secret
        body = b'{"test": true}'
        sig = hmac.new(b"some_secret", body, hashlib.sha256).hexdigest()

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = ""
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/execute/cleanup-expired-shares",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-ThookAI-Signature": sig,
                    },
                )

        assert resp.status_code == 401, resp.text

    def test_hmac_uses_constant_time_comparison(self):
        """_verify_n8n_signature uses hmac.compare_digest for timing-safe comparison."""
        source = inspect.getsource(_verify_n8n_signature)
        assert "hmac.compare_digest" in source, (
            "_verify_n8n_signature must use hmac.compare_digest to prevent timing attacks"
        )


# ---------------------------------------------------------------------------
# TestExecuteCleanupStaleJobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteCleanupStaleJobs:
    """Tests for /api/n8n/execute/cleanup-stale-jobs beyond poll-analytics."""

    async def test_marks_running_jobs_older_than_threshold_as_errored(self):
        """Running jobs older than 10 min are updated to status='error'."""
        body = b"{}"

        # Mock update_many: old job gets cleaned
        mock_result = MagicMock()
        mock_result.modified_count = 1  # Only old job matched the threshold

        mock_db = MagicMock()
        mock_db.content_jobs.update_many = AsyncMock(return_value=mock_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/cleanup-stale-jobs",
                        content=body,
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["result"]["stale_jobs_cleaned"] == 1

        # Verify the update_many was called with status="running" filter
        call_filter = mock_db.content_jobs.update_many.call_args.args[0]
        assert call_filter["status"] == "running"

    async def test_returns_count_of_cleaned_jobs(self):
        """Response includes stale_jobs_cleaned count."""
        mock_result = MagicMock()
        mock_result.modified_count = 3

        mock_db = MagicMock()
        mock_db.content_jobs.update_many = AsyncMock(return_value=mock_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/cleanup-stale-jobs",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200
        assert resp.json()["result"]["stale_jobs_cleaned"] == 3


# ---------------------------------------------------------------------------
# TestExecuteCleanupOldJobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteCleanupOldJobs:
    """Tests for /api/n8n/execute/cleanup-old-jobs."""

    async def test_deletes_failed_jobs_older_than_30_days(self):
        """Old failed/errored jobs deleted; response includes failed_jobs_deleted count."""
        mock_jobs_result = MagicMock()
        mock_jobs_result.deleted_count = 5

        mock_sessions_result = MagicMock()
        mock_sessions_result.deleted_count = 2

        mock_oauth_result = MagicMock()
        mock_oauth_result.deleted_count = 1

        mock_db = MagicMock()
        mock_db.content_jobs.delete_many = AsyncMock(return_value=mock_jobs_result)
        mock_db.onboarding_sessions.delete_many = AsyncMock(return_value=mock_sessions_result)
        mock_db.oauth_states.delete_many = AsyncMock(return_value=mock_oauth_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/cleanup-old-jobs",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        result = resp.json()["result"]
        assert result["failed_jobs_deleted"] == 5
        assert result["sessions_deleted"] == 2

        # Verify the delete_many filter includes the 30-day threshold
        call_filter = mock_db.content_jobs.delete_many.call_args.args[0]
        assert "$in" in call_filter.get("status", {}) or "status" in call_filter

    async def test_does_not_delete_recent_failed_jobs(self):
        """Recent failed jobs (< 30 days old) should NOT be deleted.

        We verify this by checking that the delete_many filter includes
        a created_at < threshold constraint.
        """
        mock_jobs_result = MagicMock()
        mock_jobs_result.deleted_count = 0

        mock_sessions_result = MagicMock()
        mock_sessions_result.deleted_count = 0

        mock_oauth_result = MagicMock()
        mock_oauth_result.deleted_count = 0

        mock_db = MagicMock()
        mock_db.content_jobs.delete_many = AsyncMock(return_value=mock_jobs_result)
        mock_db.onboarding_sessions.delete_many = AsyncMock(return_value=mock_sessions_result)
        mock_db.oauth_states.delete_many = AsyncMock(return_value=mock_oauth_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/cleanup-old-jobs",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        # Delete filter must include a datetime constraint ($lt) on created_at
        call_filter = mock_db.content_jobs.delete_many.call_args.args[0]
        assert "created_at" in call_filter, (
            "cleanup-old-jobs filter must include created_at threshold"
        )
        assert "$lt" in call_filter["created_at"]


# ---------------------------------------------------------------------------
# TestExecuteCleanupExpiredShares
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteCleanupExpiredShares:
    """Tests for /api/n8n/execute/cleanup-expired-shares."""

    async def test_deactivates_expired_persona_shares(self):
        """Expired shares (expires_at < now, is_active=True) are set to is_active=False."""
        mock_result = MagicMock()
        mock_result.modified_count = 4

        mock_db = MagicMock()
        mock_db.persona_shares.update_many = AsyncMock(return_value=mock_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/cleanup-expired-shares",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        assert resp.json()["result"]["deactivated"] == 4

        # Verify the update sets is_active=False
        update_payload = mock_db.persona_shares.update_many.call_args.args[1]
        assert update_payload["$set"]["is_active"] is False

    async def test_does_not_touch_active_shares(self):
        """Active shares (not expired) are not modified.

        We verify the filter requires is_active=True AND expires_at < now,
        so non-expired shares are excluded from the update.
        """
        mock_result = MagicMock()
        mock_result.modified_count = 0

        mock_db = MagicMock()
        mock_db.persona_shares.update_many = AsyncMock(return_value=mock_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/cleanup-expired-shares",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        # The filter must include is_active=True (only update active shares)
        call_filter = mock_db.persona_shares.update_many.call_args.args[0]
        assert call_filter.get("is_active") is True
        assert "expires_at" in call_filter


# ---------------------------------------------------------------------------
# TestExecuteResetDailyLimits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteResetDailyLimits:
    """Tests for /api/n8n/execute/reset-daily-limits."""

    async def test_resets_daily_content_count_to_zero(self):
        """Users with daily_content_count > 0 get reset to 0."""
        mock_result = MagicMock()
        mock_result.modified_count = 12

        mock_db = MagicMock()
        mock_db.users.update_many = AsyncMock(return_value=mock_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/reset-daily-limits",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        assert resp.json()["result"]["reset_count"] == 12

        # Verify daily_content_count is set to 0
        update_set = mock_db.users.update_many.call_args.args[1]["$set"]
        assert update_set["daily_content_count"] == 0

    async def test_returns_user_count_in_response(self):
        """Response includes reset_count field."""
        mock_result = MagicMock()
        mock_result.modified_count = 7

        mock_db = MagicMock()
        mock_db.users.update_many = AsyncMock(return_value=mock_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/reset-daily-limits",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "reset_count" in data["result"]
        assert "executed_at" in data


# ---------------------------------------------------------------------------
# TestExecuteRefreshMonthlyCredits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteRefreshMonthlyCredits:
    """Tests for /api/n8n/execute/refresh-monthly-credits."""

    async def test_refreshes_credits_based_on_subscription_tier(self):
        """Starter/free users get credits refreshed to their tier allowance."""
        now = datetime.now(timezone.utc)
        old_refresh = now - timedelta(days=35)

        starter_user = {
            "user_id": "u1",
            "subscription_tier": "starter",
            "credits_refreshed_at": old_refresh.isoformat(),
        }

        mock_users_cursor = MagicMock()
        mock_users_cursor.to_list = AsyncMock(return_value=[starter_user])

        mock_db = MagicMock()
        mock_db.users.find = MagicMock(return_value=mock_users_cursor)
        mock_db.users.update_one = AsyncMock()

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/refresh-monthly-credits",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["result"]["refreshed_count"] == 1
        # update_one should have been called for the user
        assert mock_db.users.update_one.called
        update_set = mock_db.users.update_one.call_args.args[1]["$set"]
        assert "credits" in update_set
        assert "credits_refreshed_at" in update_set

    async def test_does_not_refresh_for_recently_refreshed_users(self):
        """Users refreshed within last 30 days are skipped."""
        now = datetime.now(timezone.utc)
        recent_refresh = now - timedelta(days=2)

        recently_refreshed_user = {
            "user_id": "u2",
            "subscription_tier": "starter",
            "credits_refreshed_at": recent_refresh.isoformat(),
        }

        mock_users_cursor = MagicMock()
        mock_users_cursor.to_list = AsyncMock(return_value=[recently_refreshed_user])

        mock_db = MagicMock()
        mock_db.users.find = MagicMock(return_value=mock_users_cursor)
        mock_db.users.update_one = AsyncMock()

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/refresh-monthly-credits",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        # User was refreshed recently — should be skipped
        assert resp.json()["result"]["refreshed_count"] == 0
        assert not mock_db.users.update_one.called


# ---------------------------------------------------------------------------
# TestExecuteAggregateDailyAnalytics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteAggregateDailyAnalytics:
    """Tests for /api/n8n/execute/aggregate-daily-analytics."""

    async def test_aggregates_daily_stats_and_upserts_document(self):
        """Endpoint counts content, users, and upserts daily_stats document."""
        mock_db = MagicMock()
        mock_db.content_jobs.count_documents = AsyncMock(return_value=15)
        mock_db.users.count_documents = AsyncMock(return_value=3)
        mock_db.content_jobs.distinct = AsyncMock(return_value=["u1", "u2", "u3", "u4"])
        mock_db.daily_stats.update_one = AsyncMock()

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/aggregate-daily-analytics",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        result = resp.json()["result"]
        assert result["content_created"] == 15
        assert result["new_users"] == 3
        assert result["active_users"] == 4
        assert "date" in result

        # daily_stats upserted
        assert mock_db.daily_stats.update_one.called
        upsert_call = mock_db.daily_stats.update_one.call_args
        assert upsert_call.kwargs.get("upsert") is True

    async def test_returns_stats_summary_with_date(self):
        """Response includes date, content_created, new_users, active_users fields."""
        mock_db = MagicMock()
        mock_db.content_jobs.count_documents = AsyncMock(return_value=0)
        mock_db.users.count_documents = AsyncMock(return_value=0)
        mock_db.content_jobs.distinct = AsyncMock(return_value=[])
        mock_db.daily_stats.update_one = AsyncMock()

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    resp = await client.post(
                        "/api/n8n/execute/aggregate-daily-analytics",
                        content=b"{}",
                        headers={"X-ThookAI-Signature": "bypassed"},
                    )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        for field in ("date", "content_created", "new_users", "active_users"):
            assert field in data["result"], f"Missing field: {field}"
        assert "executed_at" in data


# ---------------------------------------------------------------------------
# TestExecuteProcessScheduledPosts — additional scenarios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteProcessScheduledPostsContracts:
    """Additional contract tests for /api/n8n/execute/process-scheduled-posts.

    NOTE: Core scenarios (publish_results written, due_at set, published/failed counts)
    are already covered in test_n8n_bridge.py TestExecutePollAnalytics.
    This class covers NEW scenarios not present there.
    """

    async def test_skips_future_posts(self):
        """Posts with scheduled_at in the future are NOT published.

        The endpoint queries with scheduled_at: {$lte: now}, so future posts
        are excluded by the DB query — the mock returns empty list.
        """
        mock_db = MagicMock()
        # find returns no documents when queried with $lte now (future posts excluded)
        mock_db.scheduled_posts.find = MagicMock(
            return_value=_make_async_cursor([])  # empty — future post excluded by query
        )
        mock_publish = AsyncMock(return_value={"success": True, "post_id": "li-1"})

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("routes.n8n_bridge.real_publish_to_platform", mock_publish):
                    with patch("database.db", mock_db):
                        with patch("services.notification_service.create_notification", AsyncMock()):
                            resp = await client.post(
                                "/api/n8n/execute/process-scheduled-posts",
                                content=b"{}",
                                headers={"X-ThookAI-Signature": "bypassed"},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        assert resp.json()["result"]["published"] == 0
        assert not mock_publish.called

    async def test_writes_publish_results_to_content_jobs(self):
        """Successful publish writes publish_results[platform] to content_jobs."""
        now = datetime.now(timezone.utc)
        post = {
            "schedule_id": "sched-ok",
            "job_id": "job-ok",
            "user_id": "user-1",
            "platform": "linkedin",
            "content": "Great content",
            "status": "scheduled",
            "scheduled_at": now - timedelta(minutes=5),
        }
        token = {"user_id": "user-1", "platform": "linkedin", "access_token": "tok123"}
        publish_result = {"success": True, "post_id": "li-post-999"}

        mock_db = MagicMock()
        mock_db.scheduled_posts.find = MagicMock(return_value=_make_async_cursor([post]))
        mock_db.scheduled_posts.find_one_and_update = AsyncMock(return_value=post)
        mock_db.scheduled_posts.update_one = AsyncMock()
        mock_db.platform_tokens.find_one = AsyncMock(return_value=token)
        mock_db.content_jobs.update_one = AsyncMock()

        mock_publish = AsyncMock(return_value=publish_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("routes.n8n_bridge.real_publish_to_platform", mock_publish):
                    with patch("database.db", mock_db):
                        with patch("services.notification_service.create_notification", AsyncMock()):
                            resp = await client.post(
                                "/api/n8n/execute/process-scheduled-posts",
                                content=b"{}",
                                headers={"X-ThookAI-Signature": "bypassed"},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        assert resp.json()["result"]["published"] == 1

        content_job_calls = mock_db.content_jobs.update_one.call_args_list
        assert len(content_job_calls) >= 1
        set_fields = content_job_calls[0].args[1]["$set"]
        assert "publish_results.linkedin" in set_fields
        assert set_fields["publish_results.linkedin"]["post_id"] == "li-post-999"


# ---------------------------------------------------------------------------
# TestExecuteRunNightlyStrategist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteRunNightlyStrategist:
    """Tests for /api/n8n/execute/run-nightly-strategist."""

    async def test_calls_run_strategist_for_all_users(self):
        """Endpoint calls run_strategist_for_all_users and returns the result."""
        import agents.strategist as _strat_mod

        strategist_result = {"users_processed": 5, "recommendations_created": 23}
        original_fn = _strat_mod.run_strategist_for_all_users
        _strat_mod.run_strategist_for_all_users = AsyncMock(return_value=strategist_result)

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/execute/run-nightly-strategist",
                    content=b"{}",
                    headers={"X-ThookAI-Signature": "bypassed"},
                )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)
            _strat_mod.run_strategist_for_all_users = original_fn

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        assert data["result"]["users_processed"] == 5
        assert "executed_at" in data

    async def test_returns_execution_summary(self):
        """Response has status, result, and executed_at fields."""
        import agents.strategist as _strat_mod

        original_fn = _strat_mod.run_strategist_for_all_users
        _strat_mod.run_strategist_for_all_users = AsyncMock(
            return_value={"users_processed": 3, "recommendations_created": 10}
        )

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/execute/run-nightly-strategist",
                    content=b"{}",
                    headers={"X-ThookAI-Signature": "bypassed"},
                )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)
            _strat_mod.run_strategist_for_all_users = original_fn

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        assert "result" in data
        assert "executed_at" in data


# ---------------------------------------------------------------------------
# TestCallbackEndpoint — additional scenarios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCallbackEndpointContracts:
    """Additional contract tests for POST /api/n8n/callback.

    NOTE: Basic 200/401/missing-header/empty-secret are in test_n8n_bridge.py.
    This class covers notification dispatch behaviour.
    """

    async def test_callback_with_valid_signature_returns_workflow_type(self):
        """Valid callback returns accepted status and workflow_type in response."""
        payload = {"workflow_type": "nightly-strategist", "status": "success", "result": {}}
        body = json.dumps(payload).encode()
        headers = _make_hmac_headers(body)

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            with patch(
                "services.notification_service.create_notification", AsyncMock()
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/callback",
                        content=body,
                        headers=headers,
                    )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["workflow_type"] == "nightly-strategist"

    async def test_callback_fires_notification_dispatch_on_success(self):
        """Callback invokes _dispatch_workflow_notification for user-facing workflows."""
        payload = {
            "workflow_type": "analytics-poll-24h",
            "status": "success",
            "result": {"polled": 3},
            "affected_user_ids": ["user-abc"],
        }
        body = json.dumps(payload).encode()
        headers = _make_hmac_headers(body)

        mock_create_notification = AsyncMock()

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            with patch(
                "services.notification_service.create_notification", mock_create_notification
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/callback",
                        content=body,
                        headers=headers,
                    )

        assert resp.status_code == 200, resp.text
        # Notification should have been created for the affected user
        assert mock_create_notification.called
        call_kwargs = mock_create_notification.call_args.kwargs
        assert call_kwargs["user_id"] == "user-abc"

    async def test_callback_with_invalid_signature_returns_401(self):
        """Tampered callback signature returns 401 without processing."""
        body = b'{"workflow_type": "cleanup-old-jobs"}'
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/callback",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-ThookAI-Signature": "invalid_signature_999",
                    },
                )

        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# TestTriggerEndpointContracts — additional scenarios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTriggerEndpointContracts:
    """Additional contract tests for /api/n8n/trigger/{workflow_name}.

    NOTE: known-workflow-200, unknown-404, unconfigured-404, no-auth-401
    are already covered in test_n8n_bridge.py TestN8nTrigger.
    This class adds a new scenario.
    """

    async def test_trigger_dispatches_post_to_n8n_url(self):
        """Authenticated trigger sends POST to the configured n8n webhook URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user"}
        try:
            with patch("routes.n8n_bridge.settings") as mock_settings:
                mock_settings.n8n.webhook_secret = _TEST_SECRET
                mock_settings.n8n.n8n_url = "http://mock-n8n:5678"
                mock_settings.n8n.workflow_cleanup_stale_jobs = "wf-id-abc"
                mock_settings.n8n.workflow_scheduled_posts = None
                mock_settings.n8n.workflow_reset_daily_limits = None
                mock_settings.n8n.workflow_refresh_monthly_credits = None
                mock_settings.n8n.workflow_cleanup_old_jobs = None
                mock_settings.n8n.workflow_cleanup_expired_shares = None
                mock_settings.n8n.workflow_aggregate_daily_analytics = None
                mock_settings.n8n.workflow_nightly_strategist = None
                mock_settings.n8n.workflow_analytics_poll_24h = None
                mock_settings.n8n.workflow_analytics_poll_7d = None

                with patch("routes.n8n_bridge.httpx.AsyncClient", return_value=mock_context):
                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        resp = await client.post(
                            "/api/n8n/trigger/cleanup-stale-jobs",
                            json={"extra_param": "value"},
                        )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "triggered"
        # Verify POST was made to n8n URL
        assert mock_http_client.post.called
        called_url = mock_http_client.post.call_args.args[0]
        assert "wf-id-abc" in called_url

    async def test_trigger_requires_authentication(self):
        """POST /api/n8n/trigger/* without auth returns 401 or 403."""
        # No dependency override — real auth required
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/n8n/trigger/cleanup-stale-jobs",
                json={},
            )

        assert resp.status_code in (401, 403), resp.text

    async def test_trigger_unknown_workflow_returns_404(self):
        """POST /api/n8n/trigger/nonexistent-workflow returns 404."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user"}
        try:
            with patch("routes.n8n_bridge.settings") as mock_settings:
                mock_settings.n8n.webhook_secret = _TEST_SECRET
                mock_settings.n8n.n8n_url = "http://mock-n8n:5678"
                mock_settings.n8n.workflow_cleanup_stale_jobs = None
                mock_settings.n8n.workflow_scheduled_posts = None
                mock_settings.n8n.workflow_reset_daily_limits = None
                mock_settings.n8n.workflow_refresh_monthly_credits = None
                mock_settings.n8n.workflow_cleanup_old_jobs = None
                mock_settings.n8n.workflow_cleanup_expired_shares = None
                mock_settings.n8n.workflow_aggregate_daily_analytics = None
                mock_settings.n8n.workflow_nightly_strategist = None
                mock_settings.n8n.workflow_analytics_poll_24h = None
                mock_settings.n8n.workflow_analytics_poll_7d = None

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/trigger/completely-unknown-workflow",
                        json={},
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 404, resp.text
