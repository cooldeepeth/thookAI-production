"""
Unit tests for email service and password reset flow.

Tests cover:
- Email service: configured/unconfigured state, resend API calls, XSS prevention
- Password reset flow: token generation, expiry, reuse prevention, no email enumeration
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote as url_quote

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ===========================================================================
# TestEmailService — pure unit tests (no DB, no HTTP)
# ===========================================================================


class TestEmailService:
    """Tests for backend/services/email_service.py"""

    # ------------------------------------------------------------------
    # _send_email — unconfigured path
    # ------------------------------------------------------------------

    def test_send_email_unconfigured_returns_false(self, caplog):
        """_send_email must return False (not raise) when Resend is not configured."""
        with patch("services.email_service.settings") as mock_settings:
            mock_settings.email.is_configured.return_value = False
            with caplog.at_level(logging.WARNING, logger="services.email_service"):
                from services.email_service import _send_email

                result = _send_email("user@example.com", "Test Subject", "<p>body</p>")
        assert result is False
        # Must log a warning — not silently swallow
        assert any("configured" in r.message.lower() or "missing" in r.message.lower() for r in caplog.records), (
            "Expected a warning log when email is not configured"
        )

    # ------------------------------------------------------------------
    # _send_email — configured path
    # ------------------------------------------------------------------

    def test_send_email_configured_calls_resend(self):
        """_send_email must call resend.Emails.send with correct payload."""
        with patch("services.email_service.settings") as mock_settings, \
             patch("services.email_service.resend") as mock_resend:
            mock_settings.email.is_configured.return_value = True
            mock_settings.email.resend_api_key = "re_test_key_123"
            mock_settings.email.from_email = "noreply@thookai.com"
            mock_resend.Emails.send.return_value = {"id": "msg_123"}

            from services.email_service import _send_email

            result = _send_email("user@example.com", "Hello", "<p>Hello</p>")

        assert result is True
        mock_resend.Emails.send.assert_called_once()
        call_kwargs = mock_resend.Emails.send.call_args[0][0]
        assert call_kwargs["from"] == "noreply@thookai.com"
        assert call_kwargs["to"] == ["user@example.com"]
        assert call_kwargs["subject"] == "Hello"
        assert call_kwargs["html"] == "<p>Hello</p>"

    def test_send_email_resend_exception_returns_false(self):
        """_send_email must return False (not raise) when resend.Emails.send throws."""
        with patch("services.email_service.settings") as mock_settings, \
             patch("services.email_service.resend") as mock_resend:
            mock_settings.email.is_configured.return_value = True
            mock_settings.email.resend_api_key = "re_test_key_123"
            mock_settings.email.from_email = "noreply@thookai.com"
            mock_resend.Emails.send.side_effect = Exception("Resend network error")

            from services.email_service import _send_email

            result = _send_email("user@example.com", "Hello", "<p>Hello</p>")

        assert result is False  # Must not raise

    # ------------------------------------------------------------------
    # send_password_reset_email — reset link construction
    # ------------------------------------------------------------------

    def test_send_password_reset_email_builds_correct_link(self):
        """send_password_reset_email must build reset link with correct frontend URL and URL-encoded token."""
        raw_token = "abc+def/ghi=jkl"  # Contains special URL chars
        expected_encoded = url_quote(raw_token, safe="")

        with patch("services.email_service.settings") as mock_settings, \
             patch("services.email_service.resend") as mock_resend:
            mock_settings.email.is_configured.return_value = True
            mock_settings.email.resend_api_key = "re_test_key"
            mock_settings.email.from_email = "noreply@thookai.com"
            mock_settings.email.frontend_url = "https://app.thookai.com"
            mock_resend.Emails.send.return_value = {"id": "msg_1"}

            from services.email_service import send_password_reset_email

            send_password_reset_email("user@example.com", raw_token)

        html_body = mock_resend.Emails.send.call_args[0][0]["html"]
        expected_link = f"https://app.thookai.com/reset-password?token={expected_encoded}"
        assert expected_link in html_body, (
            f"Expected reset link {expected_link!r} not found in HTML body"
        )

    def test_send_password_reset_email_strips_trailing_slash(self):
        """Frontend URL with trailing slash must not produce double slash in link."""
        with patch("services.email_service.settings") as mock_settings, \
             patch("services.email_service.resend") as mock_resend:
            mock_settings.email.is_configured.return_value = True
            mock_settings.email.resend_api_key = "re_key"
            mock_settings.email.from_email = "noreply@thookai.com"
            mock_settings.email.frontend_url = "https://app.thookai.com/"  # trailing slash
            mock_resend.Emails.send.return_value = {"id": "msg_2"}

            from services.email_service import send_password_reset_email

            send_password_reset_email("user@example.com", "token123")

        html_body = mock_resend.Emails.send.call_args[0][0]["html"]
        assert "//reset-password" not in html_body, "Double slash found in reset link"

    # ------------------------------------------------------------------
    # send_workspace_invite_email — XSS prevention
    # ------------------------------------------------------------------

    def test_send_workspace_invite_email_escapes_workspace_name(self):
        """send_workspace_invite_email must HTML-escape workspace_name (XSS prevention)."""
        xss_name = "<script>alert(1)</script>"
        with patch("services.email_service.settings") as mock_settings, \
             patch("services.email_service.resend") as mock_resend:
            mock_settings.email.is_configured.return_value = True
            mock_settings.email.resend_api_key = "re_key"
            mock_settings.email.from_email = "noreply@thookai.com"
            mock_settings.email.frontend_url = "https://app.thookai.com"
            mock_resend.Emails.send.return_value = {"id": "msg_3"}

            from services.email_service import send_workspace_invite_email

            send_workspace_invite_email("user@example.com", xss_name, "tok123", "Alice")

        html_body = mock_resend.Emails.send.call_args[0][0]["html"]
        assert "<script>" not in html_body, "Raw <script> tag found — XSS not prevented"
        assert "&lt;script&gt;" in html_body, "Escaped script tag not found in HTML body"

    def test_send_workspace_invite_email_escapes_inviter_name(self):
        """send_workspace_invite_email must HTML-escape inviter_name (XSS prevention)."""
        xss_inviter = '<img src=x onerror=alert(1)>'
        with patch("services.email_service.settings") as mock_settings, \
             patch("services.email_service.resend") as mock_resend:
            mock_settings.email.is_configured.return_value = True
            mock_settings.email.resend_api_key = "re_key"
            mock_settings.email.from_email = "noreply@thookai.com"
            mock_settings.email.frontend_url = "https://app.thookai.com"
            mock_resend.Emails.send.return_value = {"id": "msg_4"}

            from services.email_service import send_workspace_invite_email

            send_workspace_invite_email("user@example.com", "MyWorkspace", "tok456", xss_inviter)

        html_body = mock_resend.Emails.send.call_args[0][0]["html"]
        assert "<img" not in html_body, "Raw <img> tag found — XSS not prevented in inviter_name"


# ===========================================================================
# TestPasswordResetFlow — integration tests using FastAPI TestClient + mock DB
# ===========================================================================


class TestPasswordResetFlow:
    """Tests for POST /auth/forgot-password and POST /auth/reset-password."""

    # ------------------------------------------------------------------
    # Fixtures / helpers
    # ------------------------------------------------------------------

    @pytest.fixture
    def email_user(self):
        """A minimal email-auth user document."""
        return {
            "user_id": "test-user-001",
            "email": "alice@example.com",
            "hashed_password": "$2b$12$fakehash",
            "auth_method": "email",
        }

    @pytest.fixture
    def google_user(self):
        """A Google-auth user — should not receive reset email."""
        return {
            "user_id": "test-user-002",
            "email": "bob@example.com",
            "auth_method": "google",
        }

    # ------------------------------------------------------------------
    # forgot-password
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_forgot_password_creates_token_in_db(self, email_user):
        """POST /auth/forgot-password with existing email-auth user must create token in password_resets."""
        inserted_docs = []

        mock_users = AsyncMock()
        mock_users.find_one.return_value = email_user

        mock_password_resets = AsyncMock()

        async def capture_insert(doc):
            inserted_docs.append(doc)
            return MagicMock(inserted_id="fake_id")

        mock_password_resets.insert_one.side_effect = capture_insert

        with patch("routes.password_reset.db") as mock_db, \
             patch("routes.password_reset.send_password_reset_email") as mock_send:
            mock_db.users = mock_users
            mock_db.password_resets = mock_password_resets

            # Import app here to avoid DB connection at module level
            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/forgot-password",
                    json={"email": "alice@example.com"},
                )

        assert response.status_code == 200
        assert "reset link" in response.json()["message"].lower() or "sent" in response.json()["message"].lower()
        assert len(inserted_docs) == 1, "Expected exactly one password_reset document to be inserted"
        doc = inserted_docs[0]
        assert "token_hash" in doc
        assert doc["user_id"] == "test-user-001"
        assert doc["used"] is False
        # Token hash must be SHA-256 (64 hex chars)
        assert len(doc["token_hash"]) == 64

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email_returns_200(self):
        """POST /auth/forgot-password with nonexistent email must return same 200 (no email enumeration)."""
        mock_users = AsyncMock()
        mock_users.find_one.return_value = None  # User not found

        with patch("routes.password_reset.db") as mock_db, \
             patch("routes.password_reset.send_password_reset_email") as mock_send:
            mock_db.users = mock_users

            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/forgot-password",
                    json={"email": "nonexistent@example.com"},
                )

        assert response.status_code == 200
        # Message must be same as for valid users — no enumeration
        assert "reset link" in response.json()["message"].lower() or "sent" in response.json()["message"].lower()
        mock_send.assert_not_called()  # No email must be sent

    @pytest.mark.asyncio
    async def test_forgot_password_google_user_returns_200_no_email(self, google_user):
        """POST /auth/forgot-password with Google-auth user must return 200 without sending email."""
        mock_users = AsyncMock()
        mock_users.find_one.return_value = google_user  # Found but auth_method=google

        mock_password_resets = AsyncMock()

        with patch("routes.password_reset.db") as mock_db, \
             patch("routes.password_reset.send_password_reset_email") as mock_send:
            mock_db.users = mock_users
            mock_db.password_resets = mock_password_resets

            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/forgot-password",
                    json={"email": "bob@example.com"},
                )

        assert response.status_code == 200
        mock_send.assert_not_called()  # No email for OAuth users
        mock_password_resets.insert_one.assert_not_called()  # No token created

    # ------------------------------------------------------------------
    # reset-password
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_reset_password_valid_token_updates_password(self):
        """POST /auth/reset-password with valid token must update the user's password hash."""
        raw_token = "valid_token_abc123"
        th = _token_hash(raw_token)

        reset_doc = {
            "token_hash": th,
            "user_id": "test-user-001",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False,
        }

        updated_ops = []

        mock_password_resets = AsyncMock()
        mock_password_resets.find_one.return_value = reset_doc

        async def capture_update_one(filter_, update):
            updated_ops.append((filter_, update))

        mock_password_resets.update_one.side_effect = capture_update_one

        mock_users = AsyncMock()
        mock_users.update_one.side_effect = capture_update_one

        with patch("routes.password_reset.db") as mock_db:
            mock_db.password_resets = mock_password_resets
            mock_db.users = mock_users

            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/reset-password",
                    json={"token": raw_token, "new_password": "NewPass123!"},
                )

        assert response.status_code == 200
        assert "success" in response.json()["message"].lower() or "reset" in response.json()["message"].lower()
        # Users collection must have been updated
        user_update = next((op for op in updated_ops if "hashed_password" in str(op)), None)
        assert user_update is not None, "Expected users collection to be updated with new password hash"
        # Token must be marked used
        token_update = next((op for op in updated_ops if "token_hash" in str(op[0]) or "used" in str(op[1])), None)
        assert token_update is not None, "Expected token to be marked as used"

    @pytest.mark.asyncio
    async def test_reset_password_used_token_returns_400(self):
        """POST /auth/reset-password with already-used token must return 400."""
        raw_token = "used_token_xyz"
        th = _token_hash(raw_token)

        reset_doc = {
            "token_hash": th,
            "user_id": "test-user-001",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": True,  # Already used
        }

        mock_password_resets = AsyncMock()
        mock_password_resets.find_one.return_value = reset_doc

        with patch("routes.password_reset.db") as mock_db:
            mock_db.password_resets = mock_password_resets

            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/reset-password",
                    json={"token": raw_token, "new_password": "NewPass123!"},
                )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_expired_token_returns_400(self):
        """POST /auth/reset-password with expired token must return 400."""
        raw_token = "expired_token_123"
        th = _token_hash(raw_token)

        reset_doc = {
            "token_hash": th,
            "user_id": "test-user-001",
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=2),  # Expired 2 hours ago
            "used": False,
        }

        mock_password_resets = AsyncMock()
        mock_password_resets.find_one.return_value = reset_doc

        with patch("routes.password_reset.db") as mock_db:
            mock_db.password_resets = mock_password_resets

            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/reset-password",
                    json={"token": raw_token, "new_password": "NewPass123!"},
                )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_too_short_returns_400(self):
        """POST /auth/reset-password with password < 8 chars must return 400."""
        with patch("routes.password_reset.db") as mock_db:
            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/reset-password",
                    json={"token": "anytoken", "new_password": "short"},
                )

        assert response.status_code == 400
        assert "8" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_password_nonexistent_token_returns_400(self):
        """POST /auth/reset-password with unknown token must return 400."""
        mock_password_resets = AsyncMock()
        mock_password_resets.find_one.return_value = None  # Token not found

        with patch("routes.password_reset.db") as mock_db:
            mock_db.password_resets = mock_password_resets

            from server import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/reset-password",
                    json={"token": "nonexistent_token", "new_password": "NewPass123!"},
                )

        assert response.status_code == 400
