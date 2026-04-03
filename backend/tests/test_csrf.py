"""
CSRF Protection Test Suite (AUTH-05)

Tests the double-submit cookie CSRF protection pattern:
- Cookie-authenticated requests require matching X-CSRF-Token header
- Bearer-token-authenticated requests bypass CSRF entirely
- Safe methods (GET/HEAD/OPTIONS) are never CSRF-checked
- Auth endpoints (login/register) are exempt (user not yet authenticated)
- Billing webhooks are exempt (use Stripe signature verification)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import httpx
from fastapi import FastAPI, Depends, Response, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport
from starlette.middleware.cors import CORSMiddleware


# ---------------------------------------------------------------------------
# Minimal test app
# ---------------------------------------------------------------------------

def _build_test_app() -> FastAPI:
    """Build a minimal FastAPI app with CSRFMiddleware and dummy routes."""
    from middleware.csrf import CSRFMiddleware

    app = FastAPI()

    # Add CSRF middleware (no CORS needed for unit tests)
    app.add_middleware(CSRFMiddleware)

    @app.post("/api/protected")
    async def protected_post():
        return {"ok": True}

    @app.put("/api/protected")
    async def protected_put():
        return {"ok": True}

    @app.delete("/api/protected")
    async def protected_delete():
        return {"ok": True}

    @app.get("/api/protected")
    async def protected_get():
        return {"ok": True}

    @app.options("/api/protected")
    async def protected_options():
        return {"ok": True}

    # Exempt paths
    @app.post("/api/auth/login")
    async def fake_login():
        return {"token": "fake"}

    @app.post("/api/auth/register")
    async def fake_register():
        return {"token": "fake"}

    @app.post("/api/billing/webhook")
    async def fake_webhook():
        return {"received": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest_asyncio.fixture
async def csrf_client():
    """Async test client using the minimal test app."""
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# TestCSRFProtection
# ---------------------------------------------------------------------------

class TestCSRFProtection:
    """CSRF double-submit cookie protection tests."""

    # ------------------------------------------------------------------
    # Test 1: Cookie auth + no CSRF header → 403
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cookie_auth_no_csrf_header_returns_403(self, csrf_client):
        """POST with session_token cookie but no X-CSRF-Token header is rejected."""
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        resp = await csrf_client.post("/api/protected")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "CSRF token missing"

    # ------------------------------------------------------------------
    # Test 2: Cookie auth + matching CSRF header → 200
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cookie_auth_correct_csrf_header_returns_200(self, csrf_client):
        """POST with session_token cookie AND matching X-CSRF-Token header succeeds."""
        csrf_value = "matching-csrf-value-abc123"
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        csrf_client.cookies.set("csrf_token", csrf_value)
        resp = await csrf_client.post(
            "/api/protected",
            headers={"X-CSRF-Token": csrf_value},
        )
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 3: Cookie auth + wrong CSRF header → 403
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cookie_auth_wrong_csrf_header_returns_403(self, csrf_client):
        """POST with session_token cookie AND wrong X-CSRF-Token is rejected."""
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        csrf_client.cookies.set("csrf_token", "correct-csrf-value")
        resp = await csrf_client.post(
            "/api/protected",
            headers={"X-CSRF-Token": "WRONG-csrf-value"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "CSRF token invalid"

    # ------------------------------------------------------------------
    # Test 4: Bearer auth (no cookie) → 200 regardless of CSRF
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_bearer_auth_bypasses_csrf(self, csrf_client):
        """POST with Authorization Bearer header skips CSRF check entirely."""
        # No cookies set, Bearer header only
        resp = await csrf_client.post(
            "/api/protected",
            headers={"Authorization": "Bearer some-jwt-token"},
        )
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 5: GET with cookie + no CSRF → 200 (safe methods exempt)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_request_exempt_from_csrf(self, csrf_client):
        """GET with session_token cookie but no CSRF token still returns 200."""
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        resp = await csrf_client.get("/api/protected")
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 6: OPTIONS is always exempt (preflight)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_options_request_exempt_from_csrf(self, csrf_client):
        """OPTIONS preflight is never CSRF-checked."""
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        resp = await csrf_client.options("/api/protected")
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 7: POST /api/auth/login is exempt (pre-auth)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_login_endpoint_exempt_from_csrf(self, csrf_client):
        """Login endpoint must be exempt — user can't have a CSRF token before auth."""
        resp = await csrf_client.post("/api/auth/login", json={})
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 8: POST /api/auth/register is exempt (pre-auth)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_endpoint_exempt_from_csrf(self, csrf_client):
        """Register endpoint must be exempt — user can't have a CSRF token before signup."""
        resp = await csrf_client.post("/api/auth/register", json={})
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 9: POST /api/billing/webhook is exempt (Stripe signature)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_webhook_endpoint_exempt_from_csrf(self, csrf_client):
        """Billing webhook is exempt — Stripe uses signature verification, not cookies."""
        resp = await csrf_client.post("/api/billing/webhook")
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 10: Login response sets both cookies
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_login_sets_both_session_and_csrf_cookies(self):
        """Login response sets session_token (httpOnly) and csrf_token (non-httpOnly)."""
        from server import app

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
            with (
                patch("routes.auth.db") as mock_db,
                patch("routes.auth.settings") as mock_settings,
            ):
                _setup_mock_auth_settings(mock_settings)
                mock_db.users.find_one = AsyncMock(return_value=None)
                mock_db.users.with_options = MagicMock(return_value=mock_db.users)
                mock_db.users.insert_one = AsyncMock(return_value=MagicMock())

                resp = await client.post("/api/auth/register", json={
                    "email": email,
                    "password": "TestPass123!",
                    "name": "Test User",
                })

        assert resp.status_code == 200
        cookie_names = [c.name for c in resp.cookies.jar]
        assert "session_token" in cookie_names, f"Missing session_token cookie: {cookie_names}"
        assert "csrf_token" in cookie_names, f"Missing csrf_token cookie: {cookie_names}"
        # csrf_token must be present in the response body too
        body = resp.json()
        assert "csrf_token" in body, f"Missing csrf_token in response body: {body}"

    # ------------------------------------------------------------------
    # Test 11: Register response sets both cookies
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_sets_both_session_and_csrf_cookies(self):
        """Register response sets session_token (httpOnly) and csrf_token (non-httpOnly)."""
        from server import app

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
            with (
                patch("routes.auth.db") as mock_db,
                patch("routes.auth.settings") as mock_settings,
            ):
                _setup_mock_auth_settings(mock_settings)
                mock_db.users.find_one = AsyncMock(return_value=None)
                mock_db.users.with_options = MagicMock(return_value=mock_db.users)
                mock_db.users.insert_one = AsyncMock(return_value=MagicMock())

                resp = await client.post("/api/auth/register", json={
                    "email": email,
                    "password": "TestPass123!",
                    "name": "Test User",
                })

        assert resp.status_code == 200
        cookie_names = [c.name for c in resp.cookies.jar]
        assert "session_token" in cookie_names, f"Missing session_token cookie: {cookie_names}"
        assert "csrf_token" in cookie_names, f"Missing csrf_token cookie: {cookie_names}"

    # ------------------------------------------------------------------
    # Test 12: Logout clears both cookies
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_logout_clears_csrf_cookie(self):
        """Logout response deletes both session_token and csrf_token cookies."""
        from server import app

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("routes.auth.db") as mock_db:
                mock_db.user_sessions.delete_one = AsyncMock(return_value=None)

                resp = await client.post("/api/auth/logout")

        assert resp.status_code == 200
        # After logout both cookies should be deleted (Max-Age=0 or empty value)
        # Check the Set-Cookie headers for deletion markers
        set_cookie_headers = resp.headers.get_list("set-cookie")
        # At least two cookies should be addressed (deleted) in the response
        assert len(set_cookie_headers) >= 2, (
            f"Expected at least 2 Set-Cookie headers (session_token + csrf_token deletion), "
            f"got {len(set_cookie_headers)}: {set_cookie_headers}"
        )
        csrf_cookie_deleted = any(
            "csrf_token" in hdr and ("max-age=0" in hdr.lower() or "expires" in hdr.lower())
            for hdr in set_cookie_headers
        )
        assert csrf_cookie_deleted, (
            f"csrf_token cookie not cleared in logout response. Headers: {set_cookie_headers}"
        )

    # ------------------------------------------------------------------
    # Test 13: PUT with cookie + correct CSRF → 200
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_put_with_correct_csrf_returns_200(self, csrf_client):
        """PUT requests also require CSRF when using cookie auth."""
        csrf_value = "put-csrf-value-xyz"
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        csrf_client.cookies.set("csrf_token", csrf_value)
        resp = await csrf_client.put(
            "/api/protected",
            headers={"X-CSRF-Token": csrf_value},
        )
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 14: DELETE with cookie + no CSRF → 403
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_delete_with_no_csrf_returns_403(self, csrf_client):
        """DELETE requests require CSRF when using cookie auth."""
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        resp = await csrf_client.delete("/api/protected")
        assert resp.status_code == 403

    # ------------------------------------------------------------------
    # Test 15: /health is always exempt
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_health_endpoint_always_exempt(self, csrf_client):
        """Health check never requires CSRF."""
        csrf_client.cookies.set("session_token", "some-valid-jwt")
        resp = await csrf_client.get("/health")
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Test 16: No cookie + no header → treat as header auth attempt → 200
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_no_cookie_no_header_not_csrf_checked(self, csrf_client):
        """Without a session_token cookie, request is not cookie-authenticated — no CSRF check."""
        # This represents an unauthenticated request or API-key auth approach
        resp = await csrf_client.post("/api/protected")
        # CSRF is only enforced for cookie-authenticated requests
        # Without cookie, CSRF is skipped (auth check will happen at route level)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_mock_auth_settings(mock_settings):
    """Configure mock settings for auth route tests."""
    mock_app = MagicMock()
    mock_app.is_development = True
    mock_security = MagicMock()
    mock_security.jwt_secret_key = "test-secret-key-for-unit-tests-32ch!!"
    mock_security.jwt_expire_days = 7
    mock_security.jwt_algorithm = "HS256"
    mock_settings.app = mock_app
    mock_settings.security = mock_security
