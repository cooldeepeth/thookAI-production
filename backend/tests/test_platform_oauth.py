"""Tests for platform OAuth connect/disconnect/status flows.

Verifies that:
- GET /platforms/status returns all three platforms with connected/configured fields.
- Connect endpoints return correct auth URLs for LinkedIn, X, and Instagram.
- Disconnect removes stored tokens and returns 404 for already-disconnected platforms.
- get_platform_token decrypts stored tokens and handles expiry + refresh correctly.

All tests run without real OAuth credentials or external HTTP calls.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_app():
    """Create a minimal FastAPI app with the platforms router and auth override.

    platforms.py router already has prefix="/platforms".  Mount it at /api so
    the full path is /api/platforms/... matching the production app layout.
    """
    import routes.platforms as platforms_module
    from auth_utils import get_current_user

    test_app = FastAPI()
    test_app.include_router(platforms_module.router, prefix="/api")
    return test_app, platforms_module, get_current_user


FAKE_USER = {"user_id": "test_user_001", "email": "test@example.com"}


# ---------------------------------------------------------------------------
# 1. Platform status endpoint
# ---------------------------------------------------------------------------

class TestPlatformStatus:
    """GET /api/platforms/status returns all three platforms with correct fields."""

    def test_platforms_status_returns_all_three(self):
        """Response has platforms dict with linkedin, x, instagram keys."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])  # No connected platforms

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.find.return_value = mock_cursor
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/status")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data, f"Expected 'platforms' key in response: {data}"
        platforms = data["platforms"]
        assert "linkedin" in platforms, f"Expected 'linkedin' in platforms: {platforms}"
        assert "x" in platforms, f"Expected 'x' in platforms: {platforms}"
        assert "instagram" in platforms, f"Expected 'instagram' in platforms: {platforms}"

        # Each platform entry must have 'connected' and 'configured' fields
        for name, info in platforms.items():
            assert "connected" in info, f"Missing 'connected' in {name}: {info}"
            assert "configured" in info, f"Missing 'configured' in {name}: {info}"

    def test_platforms_status_shows_connected_token(self):
        """A stored platform token is reflected as connected=True in status."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        future = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_tokens = [
            {
                "platform": "linkedin",
                "account_name": "Test User",
                "expires_at": future,
                "connected_at": datetime.now(timezone.utc),
            }
        ]
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_tokens)

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.find.return_value = mock_cursor
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/status")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["platforms"]["linkedin"]["connected"] is True
        assert data["total_connected"] == 1


# ---------------------------------------------------------------------------
# 2. Connect LinkedIn
# ---------------------------------------------------------------------------

class TestConnectLinkedIn:
    """GET /api/platforms/connect/linkedin returns a LinkedIn OAuth auth_url."""

    def test_connect_linkedin_returns_auth_url(self):
        """Returns auth_url starting with linkedin.com/oauth/v2/authorization and a state."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.LINKEDIN_CLIENT_ID", "test_linkedin_client_id"):
            with patch("routes.platforms.db") as mock_db:
                mock_db.oauth_states.insert_one = AsyncMock()
                client = TestClient(test_app, raise_server_exceptions=False)
                response = client.get("/api/platforms/connect/linkedin")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200, f"Unexpected status: {response.status_code} — {response.text}"
        data = response.json()
        assert "auth_url" in data, f"Missing auth_url in response: {data}"
        assert "state" in data, f"Missing state in response: {data}"
        assert "linkedin.com/oauth/v2/authorization" in data["auth_url"], (
            f"Expected LinkedIn OAuth URL, got: {data['auth_url']}"
        )

    def test_connect_linkedin_rejects_without_client_id(self):
        """Returns 400 when LINKEDIN_CLIENT_ID is empty/unconfigured."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.LINKEDIN_CLIENT_ID", ""):
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/linkedin")

        test_app.dependency_overrides.clear()
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# 3. Connect X/Twitter
# ---------------------------------------------------------------------------

class TestConnectX:
    """GET /api/platforms/connect/x returns a Twitter OAuth auth_url with PKCE params."""

    def test_connect_x_returns_auth_url(self):
        """Returns auth_url starting with twitter.com/i/oauth2/authorize with PKCE challenge."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.TWITTER_API_KEY", "test_twitter_api_key"):
            with patch("routes.platforms.db") as mock_db:
                mock_db.oauth_states.insert_one = AsyncMock()
                client = TestClient(test_app, raise_server_exceptions=False)
                response = client.get("/api/platforms/connect/x")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200, f"Unexpected status: {response.status_code} — {response.text}"
        data = response.json()
        assert "auth_url" in data, f"Missing auth_url: {data}"
        assert "state" in data, f"Missing state: {data}"
        assert "twitter.com/i/oauth2/authorize" in data["auth_url"], (
            f"Expected X OAuth URL, got: {data['auth_url']}"
        )
        # PKCE challenge params should be present
        assert "code_challenge" in data["auth_url"], (
            f"Expected PKCE code_challenge in URL: {data['auth_url']}"
        )
        assert "code_challenge_method=S256" in data["auth_url"], (
            f"Expected S256 method in URL: {data['auth_url']}"
        )

    def test_connect_x_rejects_without_api_key(self):
        """Returns 400 when TWITTER_API_KEY is empty/unconfigured."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.TWITTER_API_KEY", ""):
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/x")

        test_app.dependency_overrides.clear()
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# 4. Connect Instagram
# ---------------------------------------------------------------------------

class TestConnectInstagram:
    """GET /api/platforms/connect/instagram returns a Facebook OAuth auth_url."""

    def test_connect_instagram_returns_auth_url(self):
        """Returns auth_url starting with facebook.com/dialog/oauth with state."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.META_APP_ID", "test_meta_app_id"):
            with patch("routes.platforms.db") as mock_db:
                mock_db.oauth_states.insert_one = AsyncMock()
                client = TestClient(test_app, raise_server_exceptions=False)
                response = client.get("/api/platforms/connect/instagram")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200, f"Unexpected status: {response.status_code} — {response.text}"
        data = response.json()
        assert "auth_url" in data, f"Missing auth_url: {data}"
        assert "state" in data, f"Missing state: {data}"
        assert "facebook.com" in data["auth_url"], (
            f"Expected Facebook OAuth URL, got: {data['auth_url']}"
        )

    def test_connect_instagram_rejects_without_meta_app_id(self):
        """Returns 400 when META_APP_ID is empty/unconfigured."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.META_APP_ID", ""):
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/instagram")

        test_app.dependency_overrides.clear()
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# 5. Disconnect platform
# ---------------------------------------------------------------------------

class TestDisconnectPlatform:
    """DELETE /api/platforms/disconnect/{platform} removes stored token."""

    def test_disconnect_platform_removes_token(self):
        """Successful disconnect returns 200 after deleting the token doc."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        delete_result = MagicMock()
        delete_result.deleted_count = 1

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.delete_one = AsyncMock(return_value=delete_result)
            mock_db.users.update_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.delete("/api/platforms/disconnect/linkedin")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data.get("platform") == "linkedin"
        # Confirm token was actually deleted
        mock_db.platform_tokens.delete_one.assert_called_once()

    def test_disconnect_nonexistent_returns_404(self):
        """DELETE /disconnect/linkedin returns 404 when no token exists."""
        test_app, platforms_module, get_current_user = _make_test_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        delete_result = MagicMock()
        delete_result.deleted_count = 0  # Nothing deleted — wasn't connected

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.delete_one = AsyncMock(return_value=delete_result)
            mock_db.users.update_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.delete("/api/platforms/disconnect/linkedin")

        test_app.dependency_overrides.clear()
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 6. get_platform_token — encryption/decryption
# ---------------------------------------------------------------------------

class TestGetPlatformToken:
    """get_platform_token returns decrypted token or None for expired/missing."""

    @pytest.mark.asyncio
    async def test_get_platform_token_decrypts(self):
        """A valid non-expired stored token is decrypted and returned."""
        from routes.platforms import get_platform_token, _encrypt_token

        real_token = "real_access_token_abc123"
        encrypted = _encrypt_token(real_token)
        future = datetime.now(timezone.utc) + timedelta(hours=24)

        token_doc = {
            "user_id": "user_001",
            "platform": "linkedin",
            "access_token": encrypted,
            "expires_at": future,
        }

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.find_one = AsyncMock(return_value=token_doc)
            result = await get_platform_token("user_001", "linkedin")

        assert result == real_token, f"Expected '{real_token}', got: {result}"

    @pytest.mark.asyncio
    async def test_get_platform_token_expired_returns_none(self):
        """An expired token with no refresh_token returns None."""
        from routes.platforms import get_platform_token, _encrypt_token

        encrypted = _encrypt_token("expired_token")
        past = datetime.now(timezone.utc) - timedelta(hours=2)

        token_doc = {
            "user_id": "user_002",
            "platform": "x",
            "access_token": encrypted,
            "expires_at": past,
            # No refresh_token
        }

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.find_one = AsyncMock(return_value=token_doc)
            result = await get_platform_token("user_002", "x")

        assert result is None, f"Expected None for expired token, got: {result}"

    @pytest.mark.asyncio
    async def test_get_platform_token_missing_returns_none(self):
        """Returns None when no token doc exists in the database."""
        from routes.platforms import get_platform_token

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.find_one = AsyncMock(return_value=None)
            result = await get_platform_token("user_999", "linkedin")

        assert result is None, f"Expected None for missing token, got: {result}"

    @pytest.mark.asyncio
    async def test_get_platform_token_expired_attempts_refresh(self):
        """An expired token with a refresh_token triggers a refresh HTTP call."""
        from routes.platforms import get_platform_token, _encrypt_token

        encrypted_access = _encrypt_token("old_access_token")
        encrypted_refresh = _encrypt_token("my_refresh_token")
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        token_doc = {
            "user_id": "user_003",
            "platform": "linkedin",
            "access_token": encrypted_access,
            "refresh_token": encrypted_refresh,
            "expires_at": past,
        }

        # Mock the refresh HTTP call — returns a new token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token_xyz",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.find_one = AsyncMock(return_value=token_doc)
            mock_db.platform_tokens.update_one = AsyncMock()
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await get_platform_token("user_003", "linkedin")

        # A refresh was attempted — httpx.post should have been called
        assert mock_client.post.called, "Expected refresh HTTP call when token is expired + has refresh_token"
        # The new token should be returned
        assert result == "new_access_token_xyz", f"Expected new token after refresh, got: {result}"
