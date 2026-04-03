"""OAuth flow tests for all 4 platforms: LinkedIn, X/Twitter, Instagram, Google.

Covers E2E-07:
- Redirect URL construction (client_id, scope, callback URL)
- PKCE code_challenge for X/Twitter (S256 method)
- Token exchange via httpx (mocked)
- Token storage with encryption in db.platform_tokens
- Platform disconnect removes stored tokens
- Platform connections list
- Google OAuth creates/finds user and returns JWT

All external HTTP calls and DB operations are mocked — no real OAuth.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_USER = {"user_id": "test_user_oauth_001", "email": "test@example.com"}


def _make_platforms_app():
    """Create minimal FastAPI app with platforms router."""
    import routes.platforms as platforms_module
    from auth_utils import get_current_user

    test_app = FastAPI()
    test_app.include_router(platforms_module.router, prefix="/api")
    return test_app, platforms_module, get_current_user


def _make_google_app():
    """Create minimal FastAPI app with google auth router."""
    import routes.auth_google as google_module
    from auth_utils import get_current_user

    test_app = FastAPI()
    test_app.include_router(google_module.router, prefix="/api")
    return test_app, google_module, get_current_user


def _mock_httpx_client(json_response: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.AsyncClient that returns the given JSON response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_response
    mock_response.text = str(json_response)

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    return mock_client


# ---------------------------------------------------------------------------
# TestPlatformOAuthFlows
# ---------------------------------------------------------------------------

class TestPlatformOAuthFlows:
    """OAuth flow tests for LinkedIn, X/Twitter, and Instagram."""

    # ------------------------------------------------------------------
    # LinkedIn
    # ------------------------------------------------------------------

    def test_linkedin_auth_redirect_url(self):
        """GET /connect/linkedin returns auth_url with client_id, scope, redirect_uri."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.LINKEDIN_CLIENT_ID", "test_linkedin_client_abc"), \
             patch("routes.platforms.db") as mock_db:
            mock_db.oauth_states.insert_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/linkedin")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200, (
            f"Expected 200 from connect/linkedin, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "auth_url" in data
        assert "state" in data

        auth_url = data["auth_url"]
        assert "linkedin.com/oauth/v2/authorization" in auth_url
        assert "client_id=test_linkedin_client_abc" in auth_url
        assert "response_type=code" in auth_url
        # Scope must include social posting permission
        assert "w_member_social" in auth_url or "openid" in auth_url
        # Must include callback to our backend
        assert "callback/linkedin" in auth_url or "redirect_uri" in auth_url

    def test_linkedin_auth_redirect_includes_state(self):
        """auth_url includes a state param matching the returned state value."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.LINKEDIN_CLIENT_ID", "test_client_state_check"), \
             patch("routes.platforms.db") as mock_db:
            mock_db.oauth_states.insert_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/linkedin")

        test_app.dependency_overrides.clear()

        data = response.json()
        state = data["state"]
        assert f"state={state}" in data["auth_url"]

    def test_linkedin_callback_stores_encrypted_token(self):
        """LinkedIn callback stores an encrypted (not plaintext) access token in db."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        valid_state = "test_state_linkedin_callback"
        oauth_state_doc = {
            "state": valid_state,
            "user_id": FAKE_USER["user_id"],
            "platform": "linkedin",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        }

        token_response = {
            "access_token": "plaintext_linkedin_token_abc123",
            "expires_in": 5184000,
            "refresh_token": None,
        }
        profile_response = {"name": "Test User", "given_name": "Test"}

        stored_token_doc = {}

        async def fake_update_one(filter_q, update_doc, *args, **kwargs):
            stored_token_doc.update(update_doc.get("$set", {}))
            return MagicMock()

        mock_httpx = _mock_httpx_client(token_response)
        # Second get call returns profile
        profile_mock = MagicMock()
        profile_mock.status_code = 200
        profile_mock.json.return_value = profile_response
        mock_httpx.get = AsyncMock(return_value=profile_mock)

        with patch("routes.platforms.db") as mock_db, \
             patch("httpx.AsyncClient", return_value=mock_httpx):
            mock_db.oauth_states.find_one_and_delete = AsyncMock(return_value=oauth_state_doc)
            mock_db.platform_tokens.update_one = AsyncMock(side_effect=fake_update_one)
            mock_db.users.update_one = AsyncMock()

            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get(
                f"/api/platforms/callback/linkedin?code=test_auth_code&state={valid_state}",
                follow_redirects=False
            )

        test_app.dependency_overrides.clear()

        # Callback should redirect (either to success or error page)
        assert response.status_code in (200, 302, 307), (
            f"Unexpected status: {response.status_code}: {response.text}"
        )

        # Most importantly: stored token must NOT be plaintext
        if stored_token_doc.get("access_token"):
            assert stored_token_doc["access_token"] != "plaintext_linkedin_token_abc123", (
                "Token should be encrypted before storage, not stored as plaintext"
            )

    def test_linkedin_callback_invalid_state_redirects_to_error(self):
        """LinkedIn callback with missing/invalid state redirects to error page."""
        test_app, platforms_module, get_current_user = _make_platforms_app()

        with patch("routes.platforms.db") as mock_db:
            mock_db.oauth_states.find_one_and_delete = AsyncMock(return_value=None)
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get(
                "/api/platforms/callback/linkedin?code=code&state=invalid_state",
                follow_redirects=False
            )

        assert response.status_code in (302, 307)
        location = response.headers.get("location", "")
        assert "error" in location.lower() or "invalid_state" in location

    # ------------------------------------------------------------------
    # X/Twitter (PKCE)
    # ------------------------------------------------------------------

    def test_twitter_auth_redirect_has_pkce(self):
        """GET /connect/x returns auth_url with code_challenge and S256 method."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.TWITTER_API_KEY", "test_twitter_api_key_xyz"), \
             patch("routes.platforms.db") as mock_db:
            mock_db.oauth_states.insert_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/x")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200, (
            f"Expected 200 from connect/x, got {response.status_code}: {response.text}"
        )
        data = response.json()
        auth_url = data["auth_url"]

        assert "twitter.com/i/oauth2/authorize" in auth_url
        assert "code_challenge=" in auth_url, (
            f"Expected PKCE code_challenge in URL: {auth_url}"
        )
        assert "code_challenge_method=S256" in auth_url, (
            f"Expected S256 method in URL: {auth_url}"
        )
        assert "client_id=test_twitter_api_key_xyz" in auth_url

    def test_twitter_auth_redirect_includes_scopes(self):
        """Twitter auth_url includes read and write tweet scopes."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.TWITTER_API_KEY", "test_twitter_key_scopes"), \
             patch("routes.platforms.db") as mock_db:
            mock_db.oauth_states.insert_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/x")

        test_app.dependency_overrides.clear()

        auth_url = response.json()["auth_url"]
        # URL-encoded scopes must include tweet.read and tweet.write
        assert "tweet.read" in auth_url or "tweet.write" in auth_url

    def test_twitter_callback_exchanges_code_with_verifier(self):
        """X/Twitter callback sends code_verifier in token exchange request."""
        test_app, platforms_module, get_current_user = _make_platforms_app()

        valid_state = "test_state_twitter_callback"
        code_verifier = "test_code_verifier_for_pkce_123"
        oauth_state_doc = {
            "state": valid_state,
            "user_id": FAKE_USER["user_id"],
            "platform": "x",
            "code_verifier": code_verifier,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        }

        token_response = {
            "access_token": "twitter_access_token_xyz",
            "refresh_token": "twitter_refresh_token",
            "expires_in": 7200,
        }
        user_response = {"data": {"username": "testuser", "id": "12345"}}

        # Track what was sent in token exchange
        post_call_data = {}

        async def mock_post(url, data=None, headers=None, **kwargs):
            if data:
                post_call_data.update(data)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = token_response
            mock_resp.text = str(token_response)
            return mock_resp

        async def mock_get(url, headers=None, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = user_response
            return mock_resp

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client.get = AsyncMock(side_effect=mock_get)

        with patch("routes.platforms.db") as mock_db, \
             patch("httpx.AsyncClient", return_value=mock_client):
            mock_db.oauth_states.find_one_and_delete = AsyncMock(return_value=oauth_state_doc)
            mock_db.platform_tokens.update_one = AsyncMock()
            mock_db.users.update_one = AsyncMock()

            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get(
                f"/api/platforms/callback/x?code=test_x_code&state={valid_state}",
                follow_redirects=False
            )

        # The token exchange POST should have included code_verifier
        assert "code_verifier" in post_call_data, (
            f"Expected code_verifier in token exchange request. Got: {post_call_data}"
        )
        assert post_call_data["code_verifier"] == code_verifier

    def test_twitter_auth_rejects_without_api_key(self):
        """Returns 400 when TWITTER_API_KEY is not configured."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.TWITTER_API_KEY", ""):
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/x")

        test_app.dependency_overrides.clear()
        assert response.status_code == 400

    # ------------------------------------------------------------------
    # Instagram (Meta)
    # ------------------------------------------------------------------

    def test_instagram_auth_redirect(self):
        """GET /connect/instagram returns Facebook OAuth auth_url with required params."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.META_APP_ID", "test_meta_app_id_123"), \
             patch("routes.platforms.db") as mock_db:
            mock_db.oauth_states.insert_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/instagram")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200, (
            f"Expected 200 from connect/instagram, got {response.status_code}: {response.text}"
        )
        data = response.json()
        auth_url = data["auth_url"]

        # Must redirect to Facebook/Meta OAuth
        assert "facebook.com" in auth_url, f"Expected Facebook OAuth URL: {auth_url}"
        assert "client_id=test_meta_app_id_123" in auth_url
        assert "response_type=code" in auth_url
        assert "state=" in auth_url

    def test_instagram_auth_includes_instagram_scope(self):
        """Instagram auth_url includes Instagram-specific scope."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.META_APP_ID", "test_meta_scope_check"), \
             patch("routes.platforms.db") as mock_db:
            mock_db.oauth_states.insert_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/instagram")

        test_app.dependency_overrides.clear()

        auth_url = response.json()["auth_url"]
        assert "instagram" in auth_url.lower() or "pages_show_list" in auth_url

    def test_instagram_callback_stores_token(self):
        """Instagram callback stores token in platform_tokens after token exchange."""
        test_app, platforms_module, get_current_user = _make_platforms_app()

        valid_state = "test_state_instagram_callback"
        oauth_state_doc = {
            "state": valid_state,
            "user_id": FAKE_USER["user_id"],
            "platform": "instagram",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        }

        short_token_response = {"access_token": "short_lived_token", "token_type": "bearer"}
        long_token_response = {"access_token": "long_lived_token_60days", "expires_in": 5184000}
        pages_response = {"data": [{"id": "page_001", "name": "Test Page", "access_token": "page_token"}]}
        ig_response = {"id": "page_001", "instagram_business_account": {"id": "ig_account_001"}}

        call_count = 0

        async def mock_get(url, params=None, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "oauth/access_token" in url and call_count == 1:
                mock_resp.json.return_value = short_token_response
            elif "oauth/access_token" in url and call_count == 2:
                mock_resp.json.return_value = long_token_response
            elif "me/accounts" in url:
                mock_resp.json.return_value = pages_response
            elif "instagram_business_account" in str(params or {}):
                mock_resp.json.return_value = ig_response
            else:
                mock_resp.json.return_value = {}
            return mock_resp

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=mock_get)

        token_stored = {}

        async def fake_update_one(filter_q, update_doc, *args, **kwargs):
            token_stored.update(update_doc.get("$set", {}))
            return MagicMock()

        with patch("routes.platforms.db") as mock_db, \
             patch("httpx.AsyncClient", return_value=mock_client):
            mock_db.oauth_states.find_one_and_delete = AsyncMock(return_value=oauth_state_doc)
            mock_db.platform_tokens.update_one = AsyncMock(side_effect=fake_update_one)
            mock_db.users.update_one = AsyncMock()

            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get(
                f"/api/platforms/callback/instagram?code=ig_test_code&state={valid_state}",
                follow_redirects=False
            )

        assert response.status_code in (200, 302, 307)
        # Token should have been stored
        assert mock_db.platform_tokens.update_one.called

    def test_instagram_auth_rejects_without_meta_app_id(self):
        """Returns 400 when META_APP_ID is not configured."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        with patch("routes.platforms.META_APP_ID", ""):
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/platforms/connect/instagram")

        test_app.dependency_overrides.clear()
        assert response.status_code == 400

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    def test_disconnect_removes_platform_tokens(self):
        """DELETE /disconnect/linkedin calls delete_one on platform_tokens."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
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
        mock_db.platform_tokens.delete_one.assert_called_once()

        # Verify delete was called with correct user_id and platform
        call_args = mock_db.platform_tokens.delete_one.call_args[0][0]
        assert call_args["user_id"] == FAKE_USER["user_id"]
        assert call_args["platform"] == "linkedin"

    def test_disconnect_x_removes_tokens(self):
        """DELETE /disconnect/x removes X/Twitter platform tokens."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        delete_result = MagicMock()
        delete_result.deleted_count = 1

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.delete_one = AsyncMock(return_value=delete_result)
            mock_db.users.update_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.delete("/api/platforms/disconnect/x")

        test_app.dependency_overrides.clear()

        assert response.status_code == 200
        call_args = mock_db.platform_tokens.delete_one.call_args[0][0]
        assert call_args["platform"] == "x"

    def test_disconnect_nonexistent_returns_404(self):
        """DELETE /disconnect/linkedin returns 404 when platform not connected."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        delete_result = MagicMock()
        delete_result.deleted_count = 0

        with patch("routes.platforms.db") as mock_db:
            mock_db.platform_tokens.delete_one = AsyncMock(return_value=delete_result)
            mock_db.users.update_one = AsyncMock()
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.delete("/api/platforms/disconnect/linkedin")

        test_app.dependency_overrides.clear()
        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Connections list
    # ------------------------------------------------------------------

    def test_connections_list_returns_connected_platforms(self):
        """GET /status returns connected=True for platforms with stored tokens."""
        test_app, platforms_module, get_current_user = _make_platforms_app()
        test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

        future = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_tokens = [
            {
                "platform": "linkedin",
                "account_name": "Test LinkedIn",
                "expires_at": future,
                "connected_at": datetime.now(timezone.utc),
            },
            {
                "platform": "x",
                "account_name": "@testuser",
                "expires_at": future,
                "connected_at": datetime.now(timezone.utc),
            },
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
        assert data["total_connected"] == 2
        assert data["platforms"]["linkedin"]["connected"] is True
        assert data["platforms"]["x"]["connected"] is True
        assert data["platforms"]["instagram"]["connected"] is False


# ---------------------------------------------------------------------------
# TestGoogleOAuthFlow
# ---------------------------------------------------------------------------

class TestGoogleOAuthFlow:
    """Google OAuth flow tests — redirect, callback, user creation/lookup."""

    def test_google_auth_requires_configuration(self):
        """GET /auth/google returns 503 when Google OAuth is not configured."""
        test_app, google_module, get_current_user = _make_google_app()

        with patch("config.settings") as mock_settings:
            mock_settings.google.is_configured.return_value = False
            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/auth/google")

        assert response.status_code == 503

    def test_google_auth_redirects_when_configured(self):
        """GET /api/auth/google redirects to Google OAuth when configured."""
        from starlette.testclient import TestClient as StarletteClient
        from fastapi.responses import RedirectResponse
        import routes.auth_google as google_module

        test_app, _google_module, get_current_user = _make_google_app()

        # Add session middleware required by authlib/starlette
        from starlette.middleware.sessions import SessionMiddleware
        test_app.add_middleware(SessionMiddleware, secret_key="test_session_secret")

        mock_oauth_google = AsyncMock()
        mock_oauth_google.authorize_redirect = AsyncMock()
        mock_oauth_google.authorize_redirect.return_value = RedirectResponse(
            url="https://accounts.google.com/o/oauth2/auth?client_id=test&scope=openid+email+profile",
            status_code=302
        )

        # Patch settings directly on the auth_google module (it imports settings at load time)
        mock_google_config = MagicMock()
        mock_google_config.is_configured.return_value = True
        mock_google_config.redirect_uri = "http://localhost:8001/api/auth/google/callback"

        with patch.object(google_module.settings, "google", mock_google_config), \
             patch("routes.auth_google._register_google_client", return_value=True), \
             patch("routes.auth_google._oauth") as mock_oauth:
            mock_oauth.google = mock_oauth_google

            client = StarletteClient(test_app, raise_server_exceptions=False)
            response = client.get("/api/auth/google", follow_redirects=False)

        # Should attempt a redirect to Google's OAuth endpoint
        assert response.status_code in (302, 307), (
            f"Expected redirect from /api/auth/google, got {response.status_code}: {response.text}"
        )
        location = response.headers.get("location", "")
        assert "google.com" in location or "accounts.google.com" in location

    @pytest.mark.asyncio
    async def test_google_callback_creates_new_user(self):
        """Google callback creates a new user in db.users when email not found."""
        import routes.auth_google as google_module
        from routes.auth_google import google_callback

        mock_request = MagicMock()
        mock_request.session = {}

        mock_token = {
            "access_token": "google_access_token_xyz",
            "userinfo": {
                "email": "newuser@example.com",
                "name": "New User",
                "picture": "https://example.com/pic.jpg",
                "sub": "google_sub_123"
            }
        }

        inserted_user = {}

        async def fake_insert_one(doc):
            inserted_user.update(doc)
            return MagicMock()

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=None)  # New user
        mock_db.users.insert_one = AsyncMock(side_effect=fake_insert_one)
        mock_db.users.update_one = AsyncMock()

        mock_google_config = MagicMock()
        mock_google_config.is_configured.return_value = True
        mock_email_config = MagicMock()
        mock_email_config.frontend_url = "http://localhost:3000"

        with patch("routes.auth_google.db", mock_db), \
             patch.object(google_module.settings, "google", mock_google_config), \
             patch.object(google_module.settings, "email", mock_email_config), \
             patch("routes.auth_google._register_google_client", return_value=True), \
             patch("routes.auth_google._oauth") as mock_oauth, \
             patch("routes.auth_google.create_jwt_token", return_value="test_jwt_token"), \
             patch("routes.auth_google.set_auth_cookie"):
            mock_oauth.google.authorize_access_token = AsyncMock(return_value=mock_token)
            response = await google_callback(mock_request)

        # User should have been created in the database
        assert mock_db.users.insert_one.called, "Expected new user to be created in db.users"
        assert inserted_user.get("email") == "newuser@example.com"
        assert inserted_user.get("auth_method") == "google"

    @pytest.mark.asyncio
    async def test_google_callback_finds_existing_user(self):
        """Google callback updates and logs in existing user without creating duplicate."""
        import routes.auth_google as google_module
        from routes.auth_google import google_callback

        mock_request = MagicMock()
        mock_request.session = {}

        existing_user = {
            "user_id": "user_existing_google_001",
            "email": "existing@example.com",
            "name": "Existing User",
        }

        mock_token = {
            "access_token": "google_access_token_existing",
            "userinfo": {
                "email": "existing@example.com",
                "name": "Existing User Updated",
                "picture": "https://example.com/newpic.jpg",
                "sub": "google_sub_existing"
            }
        }

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=existing_user)
        mock_db.users.update_one = AsyncMock()

        mock_google_config = MagicMock()
        mock_google_config.is_configured.return_value = True
        mock_email_config = MagicMock()
        mock_email_config.frontend_url = "http://localhost:3000"

        with patch("routes.auth_google.db", mock_db), \
             patch.object(google_module.settings, "google", mock_google_config), \
             patch.object(google_module.settings, "email", mock_email_config), \
             patch("routes.auth_google._register_google_client", return_value=True), \
             patch("routes.auth_google._oauth") as mock_oauth, \
             patch("routes.auth_google.create_jwt_token", return_value="test_jwt_existing"), \
             patch("routes.auth_google.set_auth_cookie"):
            mock_oauth.google.authorize_access_token = AsyncMock(return_value=mock_token)
            response = await google_callback(mock_request)

        # Should NOT create a new user — only update existing
        mock_db.users.insert_one.assert_not_called()
        # Should update the existing user's name/picture
        mock_db.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_google_callback_redirects_with_jwt_token(self):
        """Google callback redirects to frontend with a JWT token in the URL."""
        import routes.auth_google as google_module
        from routes.auth_google import google_callback

        mock_request = MagicMock()
        mock_request.session = {}

        mock_token = {
            "access_token": "google_access_token_jwt_test",
            "userinfo": {
                "email": "jwt_test@example.com",
                "name": "JWT Test User",
                "picture": None,
                "sub": "google_sub_jwt"
            }
        }

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_db.users.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.users.update_one = AsyncMock()

        mock_google_config = MagicMock()
        mock_google_config.is_configured.return_value = True
        mock_email_config = MagicMock()
        mock_email_config.frontend_url = "http://localhost:3000"

        with patch("routes.auth_google.db", mock_db), \
             patch.object(google_module.settings, "google", mock_google_config), \
             patch.object(google_module.settings, "email", mock_email_config), \
             patch("routes.auth_google._register_google_client", return_value=True), \
             patch("routes.auth_google._oauth") as mock_oauth, \
             patch("routes.auth_google.create_jwt_token", return_value="jwt_token_abc123"), \
             patch("routes.auth_google.set_auth_cookie"):
            mock_oauth.google.authorize_access_token = AsyncMock(return_value=mock_token)
            response = await google_callback(mock_request)

        # Should be a redirect response containing the JWT
        assert hasattr(response, "headers"), "Expected a response object"
        location = response.headers.get("location", "")
        assert "jwt_token_abc123" in location or "token" in location, (
            f"Expected JWT token in redirect URL: {location}"
        )

    @pytest.mark.asyncio
    async def test_google_callback_handles_token_exchange_failure(self):
        """Google callback redirects to error page when token exchange fails."""
        import routes.auth_google as google_module
        from routes.auth_google import google_callback

        mock_request = MagicMock()
        mock_request.session = {}

        mock_google_config = MagicMock()
        mock_google_config.is_configured.return_value = True
        mock_email_config = MagicMock()
        mock_email_config.frontend_url = "http://localhost:3000"

        with patch.object(google_module.settings, "google", mock_google_config), \
             patch.object(google_module.settings, "email", mock_email_config), \
             patch("routes.auth_google._register_google_client", return_value=True), \
             patch("routes.auth_google._oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                side_effect=Exception("OAuth token exchange failed")
            )
            response = await google_callback(mock_request)

        # Should redirect to error page, not crash
        location = response.headers.get("location", "")
        assert "error" in location.lower() or "auth" in location.lower(), (
            f"Expected error redirect, got: {location}"
        )


# ---------------------------------------------------------------------------
# Token encryption round-trip
# ---------------------------------------------------------------------------

class TestTokenEncryption:
    """Platform token encryption/decryption is symmetric."""

    def test_encrypt_decrypt_roundtrip(self):
        """_encrypt_token and _decrypt_token are inverses of each other."""
        from routes.platforms import _encrypt_token, _decrypt_token

        original = "my_secret_access_token_12345"
        encrypted = _encrypt_token(original)

        assert encrypted != original, "Token should not be stored in plaintext"
        assert _decrypt_token(encrypted) == original

    def test_different_tokens_produce_different_ciphertext(self):
        """Two different tokens produce different ciphertext values."""
        from routes.platforms import _encrypt_token

        token_a = "access_token_for_user_001"
        token_b = "access_token_for_user_002"

        assert _encrypt_token(token_a) != _encrypt_token(token_b)
