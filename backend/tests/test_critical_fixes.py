"""Tests for critical fixes applied during the full-stack audit.

Each test targets a specific confirmed bug that was fixed.
Tests are designed to run without external service dependencies
(Stripe, Resend, Pinecone, social platform APIs).
"""

import html as html_lib
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# 1. Analytics field names: publish_results (plural), per-platform
# ============================================================

class TestAnalyticsFieldNames:
    """Fix 2.1.1 — social_analytics reads publish_results correctly."""

    @pytest.mark.asyncio
    async def test_update_post_performance_reads_publish_results_plural(self):
        """publish_results is a dict keyed by platform, not a flat publish_result."""
        from unittest.mock import AsyncMock, patch

        mock_job = {
            "job_id": "job_123",
            "user_id": "user_1",
            "publish_results": {
                "linkedin": {"post_id": "urn:li:share:999", "success": True},
            },
        }

        with patch("services.social_analytics.db") as mock_db:
            mock_db.content_jobs.find_one = AsyncMock(return_value=mock_job)
            mock_db.content_jobs.update_one = AsyncMock()
            mock_db.persona_engines.find_one = AsyncMock(return_value=None)

            with patch("services.social_analytics.fetch_linkedin_post_metrics", new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = {
                    "impressions": 500, "likes": 10, "comments": 3,
                    "shares": 2, "engagement_rate": 0.03,
                    "platform": "linkedin",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }

                with patch("routes.platforms.get_platform_token", new_callable=AsyncMock, return_value="fake_token"):
                    from services.social_analytics import update_post_performance
                    result = await update_post_performance("job_123", "user_1", "linkedin")

                mock_fetch.assert_called_once_with("urn:li:share:999", "fake_token")

    @pytest.mark.asyncio
    async def test_update_post_performance_returns_false_for_missing_platform(self):
        """If publish_results exists but the requested platform isn't in it, return False."""
        mock_job = {
            "job_id": "job_124",
            "user_id": "user_1",
            "publish_results": {
                "linkedin": {"post_id": "urn:li:share:999"},
            },
        }

        with patch("services.social_analytics.db") as mock_db:
            mock_db.content_jobs.find_one = AsyncMock(return_value=mock_job)

            from services.social_analytics import update_post_performance
            result = await update_post_performance("job_124", "user_1", "x")
            assert result is False


# ============================================================
# 2. Email security: HTML escaping
# ============================================================

class TestEmailSecurity:
    """Fix 2.3.1 — email_service escapes user-controlled HTML."""

    def test_workspace_invite_escapes_html_in_workspace_name(self):
        """XSS payload in workspace_name must be escaped in the email body."""
        with patch("services.email_service._send_email", return_value=True) as mock_send:
            from services.email_service import send_workspace_invite_email

            result = send_workspace_invite_email(
                to_email="test@example.com",
                workspace_name="<script>alert(1)</script>",
                invite_token="abc123",
                inviter_name="<img onerror=alert(1) src=x>",
            )

            # Get the html argument passed to _send_email
            call_args = mock_send.call_args
            html_body = call_args[0][2] if call_args[0] else call_args[1].get("html", "")

            assert "<script>" not in html_body
            assert "&lt;script&gt;" in html_body
            assert "<img onerror" not in html_body
            assert "&lt;img onerror" in html_body

    def test_content_published_escapes_preview(self):
        """User-authored content preview must be HTML-escaped."""
        with patch("services.email_service._send_email", return_value=True) as mock_send:
            from services.email_service import send_content_published_email

            result = send_content_published_email(
                to_email="test@example.com",
                platform="linkedin",
                content_preview='<div onmouseover="steal()">Hello</div>',
            )

            call_args = mock_send.call_args
            html_body = call_args[0][2] if call_args[0] else call_args[1].get("html", "")

            assert "<div onmouseover" not in html_body
            assert "&lt;div onmouseover" in html_body


# ============================================================
# 3. Google OAuth: redirect_uri strips trailing slash
# ============================================================

class TestGoogleOAuthConfig:
    """Fix 2.4.1 — GoogleConfig strips whitespace and trailing slashes."""

    def test_redirect_uri_strips_trailing_slash(self):
        from config import GoogleConfig

        config = GoogleConfig.__new__(GoogleConfig)
        config.client_id = "test_id"
        config.client_secret = "test_secret"
        config.backend_url = "https://api.example.com/"

        assert config.redirect_uri == "https://api.example.com/api/auth/google/callback"

    def test_redirect_uri_no_trailing_slash(self):
        from config import GoogleConfig

        config = GoogleConfig.__new__(GoogleConfig)
        config.client_id = "test_id"
        config.client_secret = "test_secret"
        config.backend_url = "https://api.example.com"

        assert config.redirect_uri == "https://api.example.com/api/auth/google/callback"

    def test_is_configured_strips_whitespace(self):
        from config import GoogleConfig

        config = GoogleConfig.__new__(GoogleConfig)
        config.client_id = "  "
        config.client_secret = "real_secret"
        config.backend_url = ""

        assert config.is_configured() is False

    def test_is_configured_with_real_values(self):
        from config import GoogleConfig

        config = GoogleConfig.__new__(GoogleConfig)
        config.client_id = "real_id"
        config.client_secret = "real_secret"
        config.backend_url = ""

        assert config.is_configured() is True


# ============================================================
# 4. Stripe webhook rejects in staging without secret
# ============================================================

class TestStripeWebhookGuard:
    """Fix 2.7.1 — webhook rejects in non-dev/test environments without secret."""

    def test_webhook_rejects_in_staging_without_secret(self):
        """Staging environment without webhook secret should return 500."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch, MagicMock
        import importlib

        # Import billing module first (so database.py initialises with real settings)
        import routes.billing as billing_module

        test_app = FastAPI()
        test_app.include_router(billing_module.router, prefix="/api")
        client = TestClient(test_app, raise_server_exceptions=False)

        # Build a minimal settings mock that mimics the real config shape
        mock_stripe = MagicMock()
        mock_stripe.webhook_secret = ""
        mock_app = MagicMock()
        mock_app.environment = "staging"
        mock_app.is_production = False
        mock_settings = MagicMock()
        mock_settings.stripe = mock_stripe
        mock_settings.app = mock_app

        # Patch config.settings only during the request so the lazy
        # `from config import settings` inside the route handler sees the mock
        with patch("config.settings", mock_settings):
            response = client.post(
                "/api/billing/webhook/stripe",
                content="{}",
                headers={"Stripe-Signature": "t=1,v1=abc"},
            )

        # A staging env with no webhook secret must be rejected
        assert mock_settings.app.environment not in {"development", "test"}
        assert response.status_code == 500
        assert response.json().get("detail") == "Webhook secret not configured"


# ============================================================
# 5. Fatigue shield uses correct key names
# ============================================================

class TestFatigueShieldKeys:
    """Fix 2.5 — pipeline checks shield_status, not fatigue_detected."""

    def test_fatigue_shield_returns_shield_status_key(self):
        """get_pattern_fatigue_shield returns shield_status, not fatigue_detected."""
        # Verify the expected keys exist in the return contract
        # by checking the source directly
        import inspect
        from services.persona_refinement import get_pattern_fatigue_shield

        source = inspect.getsource(get_pattern_fatigue_shield)
        assert '"shield_status"' in source
        assert '"risk_factors"' in source
        assert '"recommendations"' in source

    def test_pipeline_checks_correct_keys(self):
        """pipeline.py should check shield_status, not fatigue_detected."""
        import inspect
        from agents.pipeline import run_agent_pipeline_legacy

        source = inspect.getsource(run_agent_pipeline_legacy)
        # After fix: should reference shield_status
        assert "shield_status" in source
        # Should NOT reference the old wrong key
        assert "fatigue_detected" not in source


# ============================================================
# 6. Datetime normalization in persona_refinement
# ============================================================

class TestDatetimeNormalization:
    """Fix 2.1.4 — _normalize_datetime handles strings and naive datetimes."""

    def test_normalize_iso_string(self):
        from services.persona_refinement import _normalize_datetime

        result = _normalize_datetime("2025-03-15T10:30:00Z")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_normalize_naive_datetime(self):
        from services.persona_refinement import _normalize_datetime

        naive = datetime(2025, 3, 15, 10, 30, 0)
        result = _normalize_datetime(naive)
        assert result.tzinfo is not None

    def test_normalize_aware_datetime(self):
        from services.persona_refinement import _normalize_datetime

        aware = datetime(2025, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _normalize_datetime(aware)
        assert result == aware

    def test_normalize_none(self):
        from services.persona_refinement import _normalize_datetime

        assert _normalize_datetime(None) is None

    def test_normalize_non_datetime(self):
        from services.persona_refinement import _normalize_datetime

        assert _normalize_datetime(12345) is None

    def test_normalize_invalid_iso_string(self):
        """Invalid ISO string should return None without raising."""
        from services.persona_refinement import _normalize_datetime

        assert _normalize_datetime("not-a-date") is None
        assert _normalize_datetime("2025-99-99T00:00:00Z") is None


# ============================================================
# 7. Engagement normalizer in analyst.py
# ============================================================

class TestEngagementNormalizer:
    """Fix 2.1.6 — _normalize_engagements aggregates platform-specific fields."""

    def test_normalize_linkedin_metrics(self):
        from agents.analyst import _normalize_engagements

        metrics = {"likes": 10, "comments": 5, "shares": 3}
        result = _normalize_engagements(metrics)
        assert result["engagements"] == 18

    def test_normalize_x_metrics(self):
        from agents.analyst import _normalize_engagements

        metrics = {"likes": 10, "retweets": 5, "replies": 3, "bookmarks": 2}
        result = _normalize_engagements(metrics)
        assert result["engagements"] == 20

    def test_normalize_preserves_existing_engagements(self):
        from agents.analyst import _normalize_engagements

        metrics = {"engagements": 42, "likes": 10}
        result = _normalize_engagements(metrics)
        assert result["engagements"] == 42  # Should not be overwritten


# ============================================================
# 8. Stripe config rejects placeholder keys
# ============================================================

class TestStripeConfigValidation:
    """Fix 2.4.1 — StripeConfig rejects placeholder keys."""

    def test_placeholder_key_rejected(self):
        from config import StripeConfig

        config = StripeConfig.__new__(StripeConfig)
        config.secret_key = "placeholder_key_123"
        config.webhook_secret = "whsec_test"
        config.price_pro_monthly = "price_1"
        config.price_pro_annual = "price_2"
        config.price_studio_monthly = "price_3"
        config.price_studio_annual = "price_4"
        config.price_agency_monthly = "price_5"
        config.price_agency_annual = "price_6"

        assert config.is_fully_configured() is False

    def test_real_key_accepted(self):
        from config import StripeConfig

        config = StripeConfig.__new__(StripeConfig)
        config.secret_key = "sk_test_51ngLef4k3"
        config.webhook_secret = "whsec_test"
        config.price_pro_monthly = "price_1"
        config.price_pro_annual = "price_2"
        config.price_studio_monthly = "price_3"
        config.price_studio_annual = "price_4"
        config.price_agency_monthly = "price_5"
        config.price_agency_annual = "price_6"

        assert config.is_fully_configured() is True


# ============================================================
# 9. Writer uses correct model name
# ============================================================

class TestWriterModelName:
    """Fix 2.6.1 — writer.py uses claude-sonnet-4-20250514 (not claude-4-sonnet)."""

    def test_correct_model_name_in_source(self):
        import inspect
        from agents.writer import run_writer

        source = inspect.getsource(run_writer)
        assert "claude-sonnet-4-20250514" in source
        assert "claude-4-sonnet-20250514" not in source


# ============================================================
# 10. Celery Procfile has queue flags
# ============================================================

class TestCeleryProcfile:
    """Fix 2.2.1 — Procfile worker consumes all named queues."""

    def test_procfile_has_queue_flags(self):
        import pathlib

        procfile = pathlib.Path(__file__).parent.parent / "Procfile"
        content = procfile.read_text()

        assert "-Q default,media,content,video" in content
        assert "celery_app:celery_app" in content


# ============================================================
# 11. Billing /payments endpoint returns correct shape
# ============================================================

class TestBillingPaymentsEndpoint:
    """Copilot review comment 1 — test coverage for GET /billing/payments."""

    @pytest.mark.asyncio
    async def test_get_payments_returns_success_and_list(self):
        """GET /billing/payments should return {success: True, payments: [...]}."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch, AsyncMock, MagicMock
        from auth_utils import get_current_user
        import routes.billing as billing_module

        fake_user = {"user_id": "user_test_123", "email": "test@example.com"}
        sample_payments = [
            {"payment_id": "pay_abc123", "user_id": "user_test_123",
             "amount_cents": 1900, "currency": "usd", "tier": "pro", "status": "succeeded"},
            {"payment_id": "pay_def456", "user_id": "user_test_123",
             "amount_cents": 4900, "currency": "usd", "tier": "studio", "status": "succeeded"},
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=sample_payments)

        test_app = FastAPI()
        test_app.include_router(billing_module.router, prefix="/api")
        test_app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("routes.billing.db") as mock_db:
            mock_db.payments.find.return_value = mock_cursor
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/billing/payments")

        test_app.dependency_overrides.clear()
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["payments"], list)
        assert len(data["payments"]) == 2
        assert data["payments"][0]["payment_id"] == "pay_abc123"

    @pytest.mark.asyncio
    async def test_get_payments_returns_empty_list_when_no_payments(self):
        """GET /billing/payments should return empty list for users with no payments."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch, AsyncMock, MagicMock
        from auth_utils import get_current_user
        import routes.billing as billing_module

        fake_user = {"user_id": "user_no_payments", "email": "empty@example.com"}

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])

        test_app = FastAPI()
        test_app.include_router(billing_module.router, prefix="/api")
        test_app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("routes.billing.db") as mock_db:
            mock_db.payments.find.return_value = mock_cursor
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/billing/payments")

        test_app.dependency_overrides.clear()
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["payments"], list)
        assert len(data["payments"]) == 0
