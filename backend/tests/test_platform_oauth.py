"""Tests for platform OAuth connect/disconnect/status flows.

Verifies that:
- GET /platforms/status returns all three platforms with connected/configured fields.
- Connect endpoints return correct auth URLs for LinkedIn, X, and Instagram.
- Disconnect removes stored tokens and returns 404 for already-disconnected platforms.
- get_platform_token decrypts stored tokens and handles expiry + refresh correctly.
- get_platform_token proactively refreshes tokens expiring within 24 hours.
- _refresh_token has a working Instagram renewal branch (fb_exchange_token).

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

def _make_response(status_code: int, json_data: dict) -> MagicMock:
    """Create a mock HTTP response with the given status code and JSON body."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    return mock_resp


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


# ---------------------------------------------------------------------------
# 7. Proactive 24h token refresh
# ---------------------------------------------------------------------------

class TestProactiveTokenRefresh:
    """get_platform_token() must refresh tokens expiring within 24 hours."""

    @pytest.mark.asyncio
    async def test_refreshes_token_expiring_within_24h(self):
        """Token expiring in 12h triggers proactive refresh."""
        soon = datetime.now(timezone.utc) + timedelta(hours=12)
        token_doc = {
            "user_id": "u1",
            "platform": "linkedin",
            "access_token": "enc_old",
            "refresh_token": "enc_refresh",
            "expires_at": soon,
        }

        refresh_called = {"called": False}

        async def fake_refresh(user_id, platform, refresh_token):
            refresh_called["called"] = True
            return "new_access_token_123"

        with (
            patch("routes.platforms.db") as mock_db,
            patch("routes.platforms._decrypt_token", side_effect=lambda x: f"dec_{x}"),
            patch("routes.platforms._refresh_token", new=fake_refresh),
        ):
            mock_db.platform_tokens.find_one = AsyncMock(return_value=token_doc)
            from routes.platforms import get_platform_token
            result = await get_platform_token("u1", "linkedin")

        assert refresh_called["called"], "Expected _refresh_token to be called for token expiring in 12h"
        assert result == "new_access_token_123"

    @pytest.mark.asyncio
    async def test_does_not_refresh_token_expiring_in_30h(self):
        """Token expiring in 30h is outside the 24h window — should NOT trigger refresh."""
        future = datetime.now(timezone.utc) + timedelta(hours=30)
        token_doc = {
            "user_id": "u1",
            "platform": "x",
            "access_token": "enc_valid",
            "refresh_token": "enc_refresh",
            "expires_at": future,
        }

        refresh_called = {"called": False}

        async def fake_refresh(user_id, platform, refresh_token):
            refresh_called["called"] = True
            return "new_token"

        with (
            patch("routes.platforms.db") as mock_db,
            patch("routes.platforms._decrypt_token", return_value="dec_valid"),
            patch("routes.platforms._refresh_token", new=fake_refresh),
        ):
            mock_db.platform_tokens.find_one = AsyncMock(return_value=token_doc)
            from routes.platforms import get_platform_token
            result = await get_platform_token("u1", "x")

        assert not refresh_called["called"], "refresh_token should NOT be called for token expiring in 30h"
        assert result == "dec_valid"

    @pytest.mark.asyncio
    async def test_falls_back_to_current_token_if_proactive_refresh_fails(self):
        """If proactive refresh fails but token still valid, return current decrypted token."""
        soon = datetime.now(timezone.utc) + timedelta(hours=10)
        token_doc = {
            "user_id": "u2",
            "platform": "linkedin",
            "access_token": "enc_current",
            "refresh_token": "enc_ref",
            "expires_at": soon,
        }

        async def failing_refresh(user_id, platform, refresh_token):
            return None  # Refresh fails

        with (
            patch("routes.platforms.db") as mock_db,
            patch("routes.platforms._decrypt_token", return_value="decrypted_current"),
            patch("routes.platforms._refresh_token", new=failing_refresh),
        ):
            mock_db.platform_tokens.find_one = AsyncMock(return_value=token_doc)
            from routes.platforms import get_platform_token
            result = await get_platform_token("u2", "linkedin")

        assert result == "decrypted_current", (
            f"Expected fallback to current valid token, got: {result}"
        )

    @pytest.mark.asyncio
    async def test_returns_none_if_refresh_fails_and_token_expired(self):
        """If token actually expired and refresh fails, must return None."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token_doc = {
            "user_id": "u3",
            "platform": "x",
            "access_token": "enc_expired",
            "refresh_token": "enc_ref",
            "expires_at": past,
        }

        async def failing_refresh(user_id, platform, refresh_token):
            return None

        with (
            patch("routes.platforms.db") as mock_db,
            patch("routes.platforms._decrypt_token", return_value="dec_expired"),
            patch("routes.platforms._refresh_token", new=failing_refresh),
        ):
            mock_db.platform_tokens.find_one = AsyncMock(return_value=token_doc)
            from routes.platforms import get_platform_token
            result = await get_platform_token("u3", "x")

        assert result is None, f"Expected None for expired token with failed refresh, got: {result}"


# ---------------------------------------------------------------------------
# 8. Instagram token refresh branch
# ---------------------------------------------------------------------------

class TestInstagramTokenRefresh:
    """_refresh_token() must have a working Instagram renewal branch."""

    @pytest.mark.asyncio
    async def test_instagram_calls_fb_exchange_token(self):
        """Instagram refresh calls GET graph.facebook.com with fb_exchange_token."""
        captured_requests = []

        new_access_token = "NEW_IG_ACCESS_TOKEN_456"
        exchange_response = _make_response(
            200,
            {"access_token": new_access_token, "expires_in": 5184000}
        )

        async def mock_get(url, **kwargs):
            captured_requests.append(("GET", url, kwargs))
            return exchange_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get
        mock_client.post = AsyncMock()  # should not be called

        with (
            patch("routes.platforms.httpx.AsyncClient", return_value=mock_client),
            patch("routes.platforms.db") as mock_db,
            patch("routes.platforms._encrypt_token", return_value="enc_new"),
        ):
            mock_db.platform_tokens.update_one = AsyncMock()
            from routes.platforms import _refresh_token
            result = await _refresh_token("user_ig", "instagram", "current_access_token")

        assert result == new_access_token
        assert len(captured_requests) == 1
        method, url, kwargs = captured_requests[0]
        assert "graph.facebook.com" in url
        params = kwargs.get("params", {})
        assert params.get("grant_type") == "fb_exchange_token"
        assert params.get("fb_exchange_token") == "current_access_token"

    @pytest.mark.asyncio
    async def test_instagram_stores_new_token_in_db(self):
        """Successful Instagram refresh must update platform_tokens with new access_token."""
        new_token = "REFRESHED_IG_TOKEN"
        exchange_response = _make_response(
            200,
            {"access_token": new_token, "expires_in": 5184000}
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=exchange_response)

        with (
            patch("routes.platforms.httpx.AsyncClient", return_value=mock_client),
            patch("routes.platforms.db") as mock_db,
            patch("routes.platforms._encrypt_token", return_value="enc_new"),
        ):
            mock_db.platform_tokens.update_one = AsyncMock()
            from routes.platforms import _refresh_token
            await _refresh_token("user_ig", "instagram", "old_access_token")

        assert mock_db.platform_tokens.update_one.called
        call_args = mock_db.platform_tokens.update_one.call_args
        filter_doc = call_args[0][0]
        assert filter_doc.get("platform") == "instagram"
        update_doc = call_args[0][1]["$set"]
        assert "access_token" in update_doc

    @pytest.mark.asyncio
    async def test_instagram_returns_none_on_400(self):
        """Bad fb_exchange_token (400 response) must return None."""
        bad_response = _make_response(400, {"error": "invalid_token"})

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=bad_response)

        with (
            patch("routes.platforms.httpx.AsyncClient", return_value=mock_client),
            patch("routes.platforms.db") as mock_db,
        ):
            mock_db.platform_tokens.update_one = AsyncMock()
            from routes.platforms import _refresh_token
            result = await _refresh_token("user_ig", "instagram", "invalid_old_token")

        assert result is None
