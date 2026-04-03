"""
Tests for n8n webhook bridge (Phase 09, Plan 01).

Covers:
  TestN8nCallback      — /api/n8n/callback HMAC-verified endpoint
  TestN8nTrigger       — /api/n8n/trigger/{workflow_name} auth-protected endpoint
  TestHmacVerification — _verify_n8n_signature unit tests (timing-safe)
"""

import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from server import app
from auth_utils import get_current_user
from routes.n8n_bridge import _verify_n8n_signature


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_TEST_SECRET = "test_webhook_secret_12345"
_TEST_PAYLOAD = json.dumps(
    {"workflow_type": "test", "result": {"ok": True}}
).encode()


def _sign(payload: bytes, secret: str = _TEST_SECRET) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# TestHmacVerification — direct unit tests for _verify_n8n_signature
# ---------------------------------------------------------------------------


class TestHmacVerification:
    """Unit tests for _verify_n8n_signature helper."""

    def test_valid_signature_returns_true(self):
        """Correct HMAC-SHA256 signature returns True."""
        sig = _sign(_TEST_PAYLOAD)
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            assert _verify_n8n_signature(_TEST_PAYLOAD, sig) is True

    def test_wrong_signature_returns_false(self):
        """Incorrect signature returns False."""
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET
            assert _verify_n8n_signature(_TEST_PAYLOAD, "wrong_signature") is False

    def test_empty_secret_returns_false(self):
        """Empty webhook_secret always returns False (not configured)."""
        sig = _sign(_TEST_PAYLOAD)
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = ""
            assert _verify_n8n_signature(_TEST_PAYLOAD, sig) is False

    def test_uses_compare_digest_not_equality(self):
        """_verify_n8n_signature uses hmac.compare_digest for timing-safe comparison."""
        import inspect
        import routes.n8n_bridge as bridge_module

        source = inspect.getsource(bridge_module._verify_n8n_signature)
        assert "hmac.compare_digest" in source, (
            "_verify_n8n_signature must use hmac.compare_digest for timing-safe comparison"
        )


# ---------------------------------------------------------------------------
# TestN8nCallback — POST /api/n8n/callback endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestN8nCallback:
    """Tests for POST /api/n8n/callback."""

    async def test_valid_signature_returns_200(self):
        """POST with correctly signed body returns 200 and {'status': 'accepted'}."""
        sig = _sign(_TEST_PAYLOAD)

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/callback",
                    content=_TEST_PAYLOAD,
                    headers={
                        "Content-Type": "application/json",
                        "X-ThookAI-Signature": sig,
                    },
                )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "accepted"

    async def test_invalid_signature_returns_401(self):
        """POST with wrong signature returns 401."""
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/callback",
                    content=_TEST_PAYLOAD,
                    headers={
                        "Content-Type": "application/json",
                        "X-ThookAI-Signature": "bad_signature_value",
                    },
                )

        assert resp.status_code == 401, resp.text

    async def test_missing_signature_header_returns_401(self):
        """POST without X-ThookAI-Signature header returns 401."""
        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = _TEST_SECRET

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/callback",
                    content=_TEST_PAYLOAD,
                    headers={"Content-Type": "application/json"},
                )

        assert resp.status_code == 401, resp.text

    async def test_empty_webhook_secret_rejects_all(self):
        """When N8N_WEBHOOK_SECRET is empty, all callbacks return 401."""
        sig = _sign(_TEST_PAYLOAD)

        with patch("routes.n8n_bridge.settings") as mock_settings:
            mock_settings.n8n.webhook_secret = ""

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/n8n/callback",
                    content=_TEST_PAYLOAD,
                    headers={
                        "Content-Type": "application/json",
                        "X-ThookAI-Signature": sig,
                    },
                )

        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# TestN8nTrigger — POST /api/n8n/trigger/{workflow_name} endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestN8nTrigger:
    """Tests for POST /api/n8n/trigger/{workflow_name}."""

    async def test_known_workflow_triggers_successfully(self):
        """POST /api/n8n/trigger/cleanup-stale-jobs with auth returns 200 + triggered."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user-id"}

        try:
            with patch("routes.n8n_bridge.settings") as mock_settings:
                mock_settings.n8n.webhook_secret = _TEST_SECRET
                mock_settings.n8n.n8n_url = "http://mock-n8n:5678"
                mock_settings.n8n.workflow_cleanup_stale_jobs = "test-workflow-id-123"
                mock_settings.n8n.workflow_scheduled_posts = None
                mock_settings.n8n.workflow_reset_daily_limits = None
                mock_settings.n8n.workflow_refresh_monthly_credits = None
                mock_settings.n8n.workflow_cleanup_old_jobs = None
                mock_settings.n8n.workflow_cleanup_expired_shares = None
                mock_settings.n8n.workflow_aggregate_daily_analytics = None

                with patch("routes.n8n_bridge.httpx.AsyncClient", return_value=mock_context):
                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        resp = await client.post(
                            "/api/n8n/trigger/cleanup-stale-jobs",
                            json={},
                        )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "triggered"
        assert data["workflow"] == "cleanup-stale-jobs"

    async def test_unknown_workflow_returns_404(self):
        """POST /api/n8n/trigger/nonexistent-workflow returns 404."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user-id"}

        try:
            with patch("routes.n8n_bridge.settings") as mock_settings:
                mock_settings.n8n.webhook_secret = _TEST_SECRET
                mock_settings.n8n.n8n_url = "http://mock-n8n:5678"
                mock_settings.n8n.workflow_scheduled_posts = None
                mock_settings.n8n.workflow_reset_daily_limits = None
                mock_settings.n8n.workflow_refresh_monthly_credits = None
                mock_settings.n8n.workflow_cleanup_old_jobs = None
                mock_settings.n8n.workflow_cleanup_expired_shares = None
                mock_settings.n8n.workflow_aggregate_daily_analytics = None
                mock_settings.n8n.workflow_cleanup_stale_jobs = None

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/trigger/nonexistent-workflow",
                        json={},
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 404, resp.text

    async def test_unconfigured_workflow_id_returns_404(self):
        """POST /api/n8n/trigger/cleanup-stale-jobs when workflow ID is None returns 404."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user-id"}

        try:
            with patch("routes.n8n_bridge.settings") as mock_settings:
                mock_settings.n8n.webhook_secret = _TEST_SECRET
                mock_settings.n8n.n8n_url = "http://mock-n8n:5678"
                mock_settings.n8n.workflow_cleanup_stale_jobs = None  # Not configured
                mock_settings.n8n.workflow_scheduled_posts = None
                mock_settings.n8n.workflow_reset_daily_limits = None
                mock_settings.n8n.workflow_refresh_monthly_credits = None
                mock_settings.n8n.workflow_cleanup_old_jobs = None
                mock_settings.n8n.workflow_cleanup_expired_shares = None
                mock_settings.n8n.workflow_aggregate_daily_analytics = None

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/n8n/trigger/cleanup-stale-jobs",
                        json={},
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 404, resp.text

    async def test_trigger_requires_authentication(self):
        """POST /api/n8n/trigger/* without auth returns 401 or 403."""
        # No dependency override — use real auth which requires a valid token
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/n8n/trigger/cleanup-stale-jobs",
                json={},
            )

        assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# TestExecutePollAnalytics — /api/n8n/execute/poll-analytics-{24h,7d} tests
# Covers ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04
# ---------------------------------------------------------------------------


def _make_async_cursor(items):
    """Return a mock Motor cursor that supports .to_list()."""
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=items)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    return mock_cursor


def _make_published_job(job_id: str, user_id: str, platform: str = "linkedin") -> dict:
    """Build a minimal published content_job dict with analytics fields unpolled."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    return {
        "job_id": job_id,
        "user_id": user_id,
        "platform": platform,
        "status": "published",
        "publish_results": {
            platform: {"post_id": f"post-{job_id}"},
        },
        "analytics_24h_polled": False,
        "analytics_24h_due_at": now - timedelta(minutes=5),
        "analytics_7d_polled": False,
        "analytics_7d_due_at": now - timedelta(minutes=5),
    }


@pytest.mark.asyncio
class TestExecutePollAnalytics:
    """Tests for POST /api/n8n/execute/poll-analytics-{24h,7d}."""

    # -------------------------------------------------------------------
    # Shared helper: override _verify_n8n_request dependency so HMAC is bypassed
    # -------------------------------------------------------------------

    def _override_verify(self):
        """Return context manager that bypasses the HMAC dependency."""
        from routes.n8n_bridge import _verify_n8n_request

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        from routes.n8n_bridge import _verify_n8n_request
        app.dependency_overrides.pop(_verify_n8n_request, None)

    # -------------------------------------------------------------------
    # ANLYT-01: 24h endpoint happy path
    # -------------------------------------------------------------------

    async def test_execute_poll_analytics_24h(self):
        """ANLYT-01: 2 due jobs across 2 users → update_post_performance called twice, polled=2."""
        from routes.n8n_bridge import _verify_n8n_request

        jobs = [
            _make_published_job("job-1", "user-1", "linkedin"),
            _make_published_job("job-2", "user-2", "x"),
        ]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(jobs))
        mock_db.content_jobs.update_one = AsyncMock()

        mock_update_perf = AsyncMock(return_value=True)
        mock_calc_times = AsyncMock(return_value={})

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    with patch(
                        "services.social_analytics.update_post_performance",
                        mock_update_perf,
                    ):
                        with patch(
                            "services.persona_refinement.calculate_optimal_posting_times",
                            mock_calc_times,
                        ):
                            resp = await client.post(
                                "/api/n8n/execute/poll-analytics-24h",
                                headers={"X-ThookAI-Signature": "bypassed"},
                                json={},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        result = data["result"]
        assert result["polled"] == 2
        assert result["users_updated"] == 2
        assert result["deferred"] == 0

    # -------------------------------------------------------------------
    # ANLYT-01: 7d endpoint uses the 7d field names
    # -------------------------------------------------------------------

    async def test_execute_poll_analytics_7d(self):
        """ANLYT-01: 7d endpoint queries analytics_7d_polled and marks analytics_7d_polled=True."""
        from routes.n8n_bridge import _verify_n8n_request

        jobs = [
            _make_published_job("job-7d-1", "user-1", "linkedin"),
        ]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(jobs))
        mock_db.content_jobs.update_one = AsyncMock()

        mock_update_perf = AsyncMock(return_value=True)
        mock_calc_times = AsyncMock(return_value={})

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    with patch(
                        "services.social_analytics.update_post_performance",
                        mock_update_perf,
                    ):
                        with patch(
                            "services.persona_refinement.calculate_optimal_posting_times",
                            mock_calc_times,
                        ):
                            resp = await client.post(
                                "/api/n8n/execute/poll-analytics-7d",
                                headers={"X-ThookAI-Signature": "bypassed"},
                                json={},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        result = data["result"]
        assert result["polled"] == 1
        assert result["users_updated"] == 1

        # Verify update_one was called with analytics_7d_polled=True
        update_call = mock_db.content_jobs.update_one.call_args
        set_fields = update_call.args[1]["$set"]
        assert set_fields.get("analytics_7d_polled") is True
        assert "analytics_7d_polled_at" in set_fields

    # -------------------------------------------------------------------
    # ANLYT-01: per-user rate limit
    # -------------------------------------------------------------------

    async def test_poll_analytics_per_user_rate_limit(self):
        """ANLYT-01: 7 jobs for same user → only 5 processed, 2 deferred."""
        from routes.n8n_bridge import _verify_n8n_request

        jobs = [_make_published_job(f"job-{i}", "user-1", "linkedin") for i in range(7)]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(jobs))
        mock_db.content_jobs.update_one = AsyncMock()

        mock_update_perf = AsyncMock(return_value=True)
        mock_calc_times = AsyncMock(return_value={})

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    with patch(
                        "services.social_analytics.update_post_performance",
                        mock_update_perf,
                    ):
                        with patch(
                            "services.persona_refinement.calculate_optimal_posting_times",
                            mock_calc_times,
                        ):
                            resp = await client.post(
                                "/api/n8n/execute/poll-analytics-24h",
                                headers={"X-ThookAI-Signature": "bypassed"},
                                json={},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        result = data["result"]
        assert mock_update_perf.call_count == 5, f"Expected 5 calls, got {mock_update_perf.call_count}"
        assert result["deferred"] == 2

    # -------------------------------------------------------------------
    # ANLYT-01: failed update_post_performance still marks job as polled
    # -------------------------------------------------------------------

    async def test_poll_analytics_marks_polled_on_failure(self):
        """ANLYT-01: update_post_performance returns False → analytics_24h_polled=True + analytics_24h_error=True."""
        from routes.n8n_bridge import _verify_n8n_request

        jobs = [_make_published_job("job-fail", "user-1", "linkedin")]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(jobs))
        mock_db.content_jobs.update_one = AsyncMock()

        mock_update_perf = AsyncMock(return_value=False)
        mock_calc_times = AsyncMock(return_value={})

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    with patch(
                        "services.social_analytics.update_post_performance",
                        mock_update_perf,
                    ):
                        with patch(
                            "services.persona_refinement.calculate_optimal_posting_times",
                            mock_calc_times,
                        ):
                            resp = await client.post(
                                "/api/n8n/execute/poll-analytics-24h",
                                headers={"X-ThookAI-Signature": "bypassed"},
                                json={},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        result = data["result"]
        assert result["errors"] == 1
        assert result["polled"] == 0

        # Job must still be marked as polled even though fetch failed
        update_call = mock_db.content_jobs.update_one.call_args
        set_fields = update_call.args[1]["$set"]
        assert set_fields.get("analytics_24h_polled") is True
        assert set_fields.get("analytics_24h_error") is True

    # -------------------------------------------------------------------
    # ANLYT-02: process-scheduled-posts writes publish_results + due-at fields
    # -------------------------------------------------------------------

    async def test_process_scheduled_posts_writes_publish_results(self):
        """ANLYT-02: Successful publish writes publish_results[platform] to content_jobs."""
        from routes.n8n_bridge import _verify_n8n_request
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        post = {
            "schedule_id": "sched-1",
            "job_id": "test-job-1",
            "user_id": "user-1",
            "platform": "linkedin",
            "content": "Test content",
            "status": "scheduled",
            "scheduled_at": now - timedelta(minutes=1),
        }
        token = {"user_id": "user-1", "platform": "linkedin", "access_token": "tok-123"}
        publish_result = {"success": True, "post_id": "li-123"}

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
                        with patch(
                            "services.notification_service.create_notification",
                            AsyncMock(),
                        ):
                            resp = await client.post(
                                "/api/n8n/execute/process-scheduled-posts",
                                headers={"X-ThookAI-Signature": "bypassed"},
                                json={},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["result"]["published"] == 1

        # Find the content_jobs.update_one call
        content_job_calls = mock_db.content_jobs.update_one.call_args_list
        assert len(content_job_calls) >= 1
        set_fields = content_job_calls[0].args[1]["$set"]
        assert "publish_results.linkedin" in set_fields
        assert set_fields["publish_results.linkedin"].get("post_id") == "li-123"

    # -------------------------------------------------------------------
    # ANLYT-02: analytics due-at timestamps set on publish
    # -------------------------------------------------------------------

    async def test_analytics_due_at_set_on_publish(self):
        """ANLYT-02: After publish, analytics_24h_due_at > now+20h, analytics_7d_due_at > now+6d."""
        from routes.n8n_bridge import _verify_n8n_request
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        post = {
            "schedule_id": "sched-2",
            "job_id": "test-job-2",
            "user_id": "user-1",
            "platform": "x",
            "content": "Tweet content",
            "status": "scheduled",
            "scheduled_at": now - timedelta(minutes=1),
        }
        token = {"user_id": "user-1", "platform": "x", "access_token": "tok-x"}
        publish_result = {"success": True, "tweet_id": "tw-456"}

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
                        with patch(
                            "services.notification_service.create_notification",
                            AsyncMock(),
                        ):
                            resp = await client.post(
                                "/api/n8n/execute/process-scheduled-posts",
                                headers={"X-ThookAI-Signature": "bypassed"},
                                json={},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text

        content_job_calls = mock_db.content_jobs.update_one.call_args_list
        assert len(content_job_calls) >= 1
        set_fields = content_job_calls[0].args[1]["$set"]

        due_24h = set_fields.get("analytics_24h_due_at")
        due_7d = set_fields.get("analytics_7d_due_at")
        assert due_24h is not None
        assert due_7d is not None

        # Both should be datetimes in the future
        assert due_24h > now
        assert due_7d > now
        # 7d window should be further out than 24h window
        assert due_7d > due_24h

        # polled flags must be initialized to False
        assert set_fields.get("analytics_24h_polled") is False
        assert set_fields.get("analytics_7d_polled") is False

    # -------------------------------------------------------------------
    # ANLYT-03: calculate_optimal_posting_times called once per user
    # -------------------------------------------------------------------

    async def test_poll_analytics_calls_optimal_times(self):
        """ANLYT-03: 3 jobs across 2 users → calculate_optimal_posting_times called once per user."""
        from routes.n8n_bridge import _verify_n8n_request

        jobs = [
            _make_published_job("job-a1", "user-1", "linkedin"),
            _make_published_job("job-a2", "user-1", "x"),
            _make_published_job("job-b1", "user-2", "linkedin"),
        ]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(jobs))
        mock_db.content_jobs.update_one = AsyncMock()

        mock_update_perf = AsyncMock(return_value=True)
        mock_calc_times = AsyncMock(return_value={})

        app.dependency_overrides[_verify_n8n_request] = lambda: {}
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with patch("database.db", mock_db):
                    with patch(
                        "services.social_analytics.update_post_performance",
                        mock_update_perf,
                    ):
                        with patch(
                            "services.persona_refinement.calculate_optimal_posting_times",
                            mock_calc_times,
                        ):
                            resp = await client.post(
                                "/api/n8n/execute/poll-analytics-24h",
                                headers={"X-ThookAI-Signature": "bypassed"},
                                json={},
                            )
        finally:
            app.dependency_overrides.pop(_verify_n8n_request, None)

        assert resp.status_code == 200, resp.text
        # Must be called exactly once per affected user (2 users total)
        assert mock_calc_times.call_count == 2, (
            f"Expected 2 calls (one per user), got {mock_calc_times.call_count}"
        )
        called_user_ids = {call.args[0] for call in mock_calc_times.call_args_list}
        assert called_user_ids == {"user-1", "user-2"}

    # -------------------------------------------------------------------
    # ANLYT-04: Strategist _gather_user_context reads performance_data
    # -------------------------------------------------------------------

    async def test_strategist_reads_performance_data(self):
        """ANLYT-04: _gather_user_context returns performance_signals from jobs with performance_data."""
        from agents.strategist import _gather_user_context

        jobs = [
            {
                "job_id": "j1",
                "user_id": "test-user",
                "platform": "linkedin",
                "status": "published",
                "performance_data": {"latest": {"impressions": 1000, "engagement_rate": 0.04}},
                "final_content": "Post 1",
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "job_id": "j2",
                "user_id": "test-user",
                "platform": "x",
                "status": "published",
                "performance_data": {"latest": {"impressions": 500, "engagement_rate": 0.02}},
                "final_content": "Post 2",
                "created_at": "2026-01-02T00:00:00Z",
            },
            {
                "job_id": "j3",
                "user_id": "test-user",
                "platform": "linkedin",
                "status": "approved",
                # No performance_data — not yet published
                "final_content": "Post 3",
                "created_at": "2026-01-03T00:00:00Z",
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=jobs)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=mock_cursor)
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={
                "user_id": "test-user",
                "card": {"archetype": "Expert"},
                "voice_fingerprint": {},
                "content_identity": {},
            }
        )
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )

        # Patch db at the module-level binding in agents.strategist
        import sys

        # Strategist imports lightrag_service lazily — stub the module so
        # the lazy import doesn't fail if LightRAG is not installed
        class _FakeLightRAGModule:
            async def query_knowledge_graph(self, *a, **kw):
                return ""

        fake_lightrag = MagicMock()
        fake_lightrag.query_knowledge_graph = AsyncMock(return_value="")

        with patch.dict(sys.modules, {"services.lightrag_service": fake_lightrag}):
            with patch("agents.strategist.db", mock_db):
                result = await _gather_user_context("test-user")

        performance_signals = result.get("performance_signals", [])
        # Only the 2 jobs with performance_data should appear in signals
        assert len(performance_signals) == 2, (
            f"Expected 2 performance signals (jobs with data), got {len(performance_signals)}"
        )
