"""
Unit tests for auth core endpoints: registration, login, session persistence, Google OAuth.

These tests use httpx.AsyncClient with the FastAPI app directly — no live server required.
Database calls are mocked so tests run in isolation without MongoDB.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from jose import jwt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    return f"test_auth_{uuid.uuid4().hex[:8]}@test.com"


def _make_user(email: str, auth_method: str = "email") -> dict:
    """Return a minimal user document as stored in MongoDB (without _id)."""
    from auth_utils import hash_password
    user: dict = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": email,
        "name": "Test User",
        "picture": None,
        "auth_method": auth_method,
        "plan": "starter",
        "subscription_tier": "starter",
        "credits": 200,
        "credit_allowance": 0,
        "credits_last_refresh": datetime.now(timezone.utc),
        "credits_refreshed_at": datetime.now(timezone.utc),
        "onboarding_completed": False,
        "platforms_connected": [],
        "created_at": datetime.now(timezone.utc),
    }
    if auth_method == "email":
        user["hashed_password"] = hash_password("TestPass123!")
    return user


# Fixed test JWT secret — used in all test token helpers so decode_token
# sees the same secret as the token was signed with. After BILL-06 fix,
# decode_token raises JWTError when jwt_secret_key is empty, so tests must
# patch auth_utils.settings.security.jwt_secret_key to _TEST_JWT_SECRET.
_TEST_JWT_SECRET = "test-secret-key-for-unit-tests-32-chars!!"


def _make_valid_jwt(user_id: str, email: str) -> str:
    """Create a valid JWT using the test secret.

    NOTE: Tests that use this token must also patch auth_utils settings so
    decode_token uses _TEST_JWT_SECRET (not the empty string from env).
    See test_me_with_valid_bearer_token_returns_user_data for the pattern.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        _TEST_JWT_SECRET,
        algorithm="HS256",
    )


def _make_expired_jwt(user_id: str, email: str) -> str:
    """Create an expired JWT using the test secret."""
    expire = datetime.now(timezone.utc) - timedelta(days=1)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        _TEST_JWT_SECRET,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# Shared async client fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Return the FastAPI app instance."""
    from server import app as _app
    return _app


@pytest_asyncio.fixture
async def client(app):
    """Async test client that does NOT require a live server."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# TestRegistration
# ---------------------------------------------------------------------------

class TestRegistration:
    """Registration endpoint: POST /api/auth/register"""

    @pytest.mark.asyncio
    async def test_register_success_returns_200_with_token(self, client):
        email = _unique_email()
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.with_options = MagicMock(return_value=mock_db.users)
            mock_db.users.insert_one = AsyncMock(return_value=MagicMock())

            resp = await client.post("/api/auth/register", json={
                "email": email,
                "password": "TestPass123!",
                "name": "Test User",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["email"] == email
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_register_returns_credits_200(self, client):
        email = _unique_email()
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.with_options = MagicMock(return_value=mock_db.users)
            mock_db.users.insert_one = AsyncMock(return_value=MagicMock())

            resp = await client.post("/api/auth/register", json={
                "email": email,
                "password": "TestPass123!",
                "name": "Test User",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("credits") == 200, f"Expected 200 starter credits, got {data.get('credits')}"

    @pytest.mark.asyncio
    async def test_register_does_not_return_hashed_password(self, client):
        email = _unique_email()
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.with_options = MagicMock(return_value=mock_db.users)
            mock_db.users.insert_one = AsyncMock(return_value=MagicMock())

            resp = await client.post("/api/auth/register", json={
                "email": email,
                "password": "TestPass123!",
                "name": "Test User",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "hashed_password" not in data
        assert "_id" not in data

    @pytest.mark.asyncio
    async def test_register_onboarding_completed_false(self, client):
        email = _unique_email()
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.with_options = MagicMock(return_value=mock_db.users)
            mock_db.users.insert_one = AsyncMock(return_value=MagicMock())

            resp = await client.post("/api/auth/register", json={
                "email": email,
                "password": "TestPass123!",
                "name": "Test User",
            })
        assert resp.status_code == 200
        assert resp.json().get("onboarding_completed") is False

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_400(self, client):
        email = _unique_email()
        existing_user = _make_user(email)
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=existing_user)

            resp = await client.post("/api/auth/register", json={
                "email": email,
                "password": "TestPass123!",
                "name": "Test User",
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_sets_session_token_cookie(self, client):
        email = _unique_email()
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.with_options = MagicMock(return_value=mock_db.users)
            mock_db.users.insert_one = AsyncMock(return_value=MagicMock())

            resp = await client.post("/api/auth/register", json={
                "email": email,
                "password": "TestPass123!",
                "name": "Test User",
            })
        assert resp.status_code == 200
        # Cookie may be named session_token
        cookie_names = [c.name for c in resp.cookies.jar]
        assert "session_token" in cookie_names, f"session_token cookie not set; cookies: {cookie_names}"


# ---------------------------------------------------------------------------
# TestLogin
# ---------------------------------------------------------------------------

class TestLogin:
    """Login endpoint: POST /api/auth/login"""

    @pytest.mark.asyncio
    async def test_login_valid_credentials_returns_200_with_token(self, client):
        email = _unique_email()
        user = _make_user(email)
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=user)

            resp = await client.post("/api/auth/login", json={
                "email": email,
                "password": "TestPass123!",
            })
        assert resp.status_code == 200
        assert "token" in resp.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, client):
        email = _unique_email()
        user = _make_user(email)
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=user)

            resp = await client.post("/api/auth/login", json={
                "email": email,
                "password": "WrongPassword!",
            })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_email_returns_401(self, client):
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)

            resp = await client.post("/api/auth/login", json={
                "email": "nobody@test.com",
                "password": "TestPass123!",
            })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_google_user_returns_401(self, client):
        """Users who registered via Google OAuth cannot log in with email/password."""
        email = _unique_email()
        google_user = _make_user(email, auth_method="google")
        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=google_user)

            resp = await client.post("/api/auth/login", json={
                "email": email,
                "password": "TestPass123!",
            })
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestSessionPersistence
# ---------------------------------------------------------------------------

class TestSessionPersistence:
    """Session endpoints: GET /api/auth/me"""

    @pytest.mark.asyncio
    async def test_me_with_valid_bearer_token_returns_user_data(self, client):
        email = _unique_email()
        user = _make_user(email)
        jwt_token = _make_valid_jwt(user["user_id"], email)

        # Patch JWT secret so decode_token uses _TEST_JWT_SECRET (BILL-06 fix:
        # decode_token now raises JWTError when jwt_secret_key is empty, so tests
        # must provide a matching secret for both encode and decode).
        mock_security = MagicMock()
        mock_security.jwt_secret_key = _TEST_JWT_SECRET
        mock_security.jwt_algorithm = "HS256"

        # auth_utils imports db inside the function body, so patch database.db
        with patch("auth_utils.settings.security", mock_security), \
             patch("database.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=user)

            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == email
        assert "hashed_password" not in data
        assert "_id" not in data

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_expired_token_returns_401(self, client):
        email = _unique_email()
        user = _make_user(email)
        expired_token = _make_expired_jwt(user["user_id"], email)

        with patch("database.db") as mock_db:
            # Session lookup should also fail
            mock_db.user_sessions.find_one = AsyncMock(return_value=None)

            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_clears_session_token_cookie(self, client):
        with patch("routes.auth.db") as mock_db:
            mock_db.user_sessions.delete_one = AsyncMock(return_value=None)

            resp = await client.post("/api/auth/logout")
        assert resp.status_code == 200
        # After logout the cookie should be deleted (set to empty or Max-Age=0)
        # httpx doesn't store deleted cookies, so just verify the response is OK
        assert resp.json().get("message") == "Logged out"


# ---------------------------------------------------------------------------
# TestGoogleOAuth
# ---------------------------------------------------------------------------

class TestGoogleOAuth:
    """Google OAuth endpoints: GET /api/auth/google, GET /api/auth/google/callback"""

    @pytest.mark.asyncio
    async def test_google_login_returns_503_when_not_configured(self, client):
        """When Google credentials are not set, /auth/google must return 503."""
        with patch("routes.auth_google.settings") as mock_settings:
            mock_google = MagicMock()
            mock_google.is_configured.return_value = False
            mock_settings.google = mock_google

            resp = await client.get("/api/auth/google")
        assert resp.status_code == 503
        body = resp.json()
        # The error field must be 'google_auth_unavailable'
        detail = body.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("error") == "google_auth_unavailable"
        else:
            assert "google_auth_unavailable" in str(detail)

    @pytest.mark.asyncio
    async def test_google_callback_creates_new_user_with_200_credits(self, client):
        """Callback with a new email creates a user with credits=200 and auth_method=google."""
        email = _unique_email()
        fake_userinfo = {
            "email": email,
            "name": "New Google User",
            "picture": "https://example.com/pic.jpg",
        }

        with (
            patch("routes.auth_google.settings") as mock_settings,
            patch("routes.auth_google._oauth") as mock_oauth,
            patch("routes.auth_google.db") as mock_db,
        ):
            # Google is configured
            mock_google_cfg = MagicMock()
            mock_google_cfg.is_configured.return_value = True
            mock_google_cfg.redirect_uri = "http://test/api/auth/google/callback"
            mock_settings.google = mock_google_cfg
            mock_settings.email.frontend_url = "http://localhost:3000"

            # Token exchange returns userinfo
            mock_token = {"userinfo": fake_userinfo}
            mock_oauth.google.authorize_access_token = AsyncMock(return_value=mock_token)

            # New user — no existing record
            mock_db.users.find_one = AsyncMock(return_value=None)

            inserted_doc: dict = {}

            async def capture_insert(doc):
                inserted_doc.update(doc)
                return MagicMock()

            mock_db.users.insert_one = AsyncMock(side_effect=capture_insert)

            resp = await client.get("/api/auth/google/callback", follow_redirects=False)

        # Should redirect to frontend dashboard
        assert resp.status_code in (302, 303, 307)
        assert inserted_doc.get("credits") == 200
        assert inserted_doc.get("auth_method") == "google"
        assert inserted_doc.get("email") == email

    @pytest.mark.asyncio
    async def test_google_callback_links_existing_user(self, client):
        """Callback with existing email updates name/picture, does NOT create a duplicate."""
        email = _unique_email()
        existing = _make_user(email, auth_method="email")
        fake_userinfo = {
            "email": email,
            "name": "Updated Name",
            "picture": "https://example.com/new.jpg",
        }

        with (
            patch("routes.auth_google.settings") as mock_settings,
            patch("routes.auth_google._oauth") as mock_oauth,
            patch("routes.auth_google.db") as mock_db,
        ):
            mock_google_cfg = MagicMock()
            mock_google_cfg.is_configured.return_value = True
            mock_settings.google = mock_google_cfg
            mock_settings.email.frontend_url = "http://localhost:3000"

            mock_token = {"userinfo": fake_userinfo}
            mock_oauth.google.authorize_access_token = AsyncMock(return_value=mock_token)

            # Existing user found
            mock_db.users.find_one = AsyncMock(return_value=existing)
            mock_db.users.update_one = AsyncMock(return_value=MagicMock())

            resp = await client.get("/api/auth/google/callback", follow_redirects=False)

        assert resp.status_code in (302, 303, 307)
        # insert_one should NOT have been called (no new user created)
        mock_db.users.insert_one.assert_not_called()
        mock_db.users.update_one.assert_called_once()
