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
