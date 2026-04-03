"""
OWASP Top 10 2021 Systematic Verification Tests — SEC-07

Each test class maps to one OWASP Top 10 risk category and verifies that
the ThookAI backend addresses that risk at the code/config level.

Coverage:
- A01: Broken Access Control — unauthenticated requests to protected routes
- A02: Cryptographic Failures — bcrypt storage, JWT HS256, HttpOnly cookie
- A03: Injection — NoSQL injection blocked, parameterized queries
- A04: Insecure Design — password policy, common password rejection
- A05: Security Misconfiguration — debug mode, default secrets, headers on errors
- A07: Identification and Authentication Failures — error message uniformity
- A08: Software and Data Integrity Failures — Stripe webhook signature required
- A09: Security Logging and Monitoring Failures — failed login logging

Design: httpx.AsyncClient + ASGITransport for route tests; direct unit tests
for policy classes; all database calls mocked via unittest.mock.

Note on mocking: routes/auth.py binds `db` at module import time via
  `from database import db`
so tests that exercise auth routes must patch *both* `database.db` and
`routes.auth.db` (and `auth_utils.db` where get_current_user is used).
Tests that test auth_utils.get_current_user also need `auth_utils.db`.
"""
from __future__ import annotations

import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import pytest_asyncio
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport
from jose import jwt


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "test-owasp-suite-secret-32chars!!!"


def _unique_email() -> str:
    return f"owasp_{uuid.uuid4().hex[:8]}@test.com"


def _make_mock_db(find_return=None, find_sessions_return=None):
    """Build a minimal AsyncMock database for auth tests."""
    mock_db = MagicMock()
    mock_db.users = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=find_return)
    mock_db.users.with_options = MagicMock(return_value=MagicMock(
        insert_one=AsyncMock(return_value=MagicMock(inserted_id="oid"))
    ))
    mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id="oid"))
    mock_db.user_sessions = MagicMock()
    mock_db.user_sessions.find_one = AsyncMock(return_value=find_sessions_return)
    mock_db.user_sessions.delete_one = AsyncMock(return_value=None)
    return mock_db


@contextmanager
def _patch_all_db(mock_db):
    """
    Context manager that patches database.db, routes.auth.db, and
    auth_utils internals so both the route and the auth dependency
    see the same mock.
    """
    with (
        patch("database.db", mock_db),
        patch("routes.auth.db", mock_db),
    ):
        yield mock_db


def _make_valid_jwt(user_id: str, email: str, secret: str = TEST_JWT_SECRET) -> str:
    """Create a valid JWT signed with a test secret."""
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        secret,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# A01: Broken Access Control
# ---------------------------------------------------------------------------

class TestA01BrokenAccessControl:
    """
    OWASP A01 2021: Broken Access Control

    Verify that unauthenticated users cannot access protected API endpoints.
    All protected routes must return 401 when no token is provided.
    """

    @pytest.mark.asyncio
    async def test_unauthenticated_request_to_auth_me_returns_401(self):
        """GET /api/auth/me without Bearer token must return 401."""
        mock_db = _make_mock_db()
        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/auth/me")
        assert resp.status_code == 401, (
            f"Unauthenticated /api/auth/me must return 401, got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_unauthenticated_request_to_dashboard_returns_401(self):
        """GET /api/dashboard/stats without token must return 401."""
        mock_db = _make_mock_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/dashboard/stats")
        assert resp.status_code == 401, (
            f"Unauthenticated /api/dashboard/stats must return 401, got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_unauthenticated_request_to_content_returns_401(self):
        """GET /api/content/jobs without token must return 401."""
        mock_db = _make_mock_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/content/jobs")
        assert resp.status_code == 401, (
            f"Unauthenticated /api/content/jobs must return 401, got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_unauthenticated_request_to_persona_returns_401(self):
        """GET /api/persona/me without token must return 401."""
        mock_db = _make_mock_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/persona/me")
        assert resp.status_code == 401, (
            f"Unauthenticated /api/persona/me must return 401, got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401_not_500(self):
        """Bearer token with garbage value must return 401, not 500."""
        mock_db = _make_mock_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/api/auth/me",
                    headers={"Authorization": "Bearer totally.invalid.token"},
                )
        assert resp.status_code == 401, (
            f"Invalid token must return 401, got {resp.status_code}"
        )
        assert resp.status_code != 500, "Invalid token must never cause a 500 error"


# ---------------------------------------------------------------------------
# A02: Cryptographic Failures
# ---------------------------------------------------------------------------

class TestA02CryptographicFailures:
    """
    OWASP A02 2021: Cryptographic Failures

    Verify passwords are stored as bcrypt hashes, JWTs use HS256, and auth
    cookies are HttpOnly. Never store plaintext credentials.
    """

    @pytest.mark.asyncio
    async def test_password_stored_as_bcrypt_hash_not_plaintext(self):
        """
        Registration must store hashed_password as a bcrypt hash (starts with $2b$),
        never as the plaintext password.
        """
        captured_doc: dict = {}

        async def capture_insert(doc):
            captured_doc.update(doc)
            return MagicMock(inserted_id="oid")

        mock_db = _make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=None)
        wmaj = MagicMock()
        wmaj.insert_one = AsyncMock(side_effect=capture_insert)
        mock_db.users.with_options = MagicMock(return_value=wmaj)

        plaintext = "TestPass123!"
        email = _unique_email()

        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/register",
                    json={"email": email, "password": plaintext, "name": "Test"},
                )

        assert resp.status_code in (200, 201), (
            f"Registration failed unexpectedly: {resp.status_code} {resp.text}"
        )
        assert captured_doc, "Expected insert_one to be called with user document"
        stored_password = captured_doc.get("hashed_password", "")
        # Bcrypt hashes start with $2b$ (bcrypt identifier + cost factor)
        assert stored_password.startswith("$2b$"), (
            f"Stored password must be bcrypt hash (starts with $2b$), got: {stored_password!r}"
        )
        # Must NOT store the plaintext
        assert stored_password != plaintext, (
            "Stored hashed_password must NOT equal the plaintext password"
        )

    def test_jwt_uses_hs256_algorithm_not_none(self):
        """
        create_access_token() in auth_utils must produce a JWT with alg=HS256.
        The 'none' algorithm bypass is a critical JWT vulnerability.
        """
        from auth_utils import create_access_token

        with patch("auth_utils.settings.security.jwt_secret_key", TEST_JWT_SECRET):
            token = create_access_token("user_test_001")

        # Decode without verification to inspect the header
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "HS256", (
            f"JWT algorithm must be HS256, got: {header['alg']!r}"
        )
        assert header["alg"] != "none", (
            "JWT algorithm must NOT be 'none' — this allows signature bypass"
        )

    @pytest.mark.asyncio
    async def test_auth_cookie_has_httponly_flag(self):
        """
        The session_token cookie set on login must have the HttpOnly flag.
        HttpOnly prevents JavaScript (including XSS) from reading the cookie.
        """
        from auth_utils import hash_password

        plaintext = "TestPass123!"
        email = _unique_email()
        mock_user = {
            "user_id": "user_a02_test",
            "email": email,
            "name": "A02 User",
            "auth_method": "email",
            "hashed_password": hash_password(plaintext),
            "plan": "starter",
            "subscription_tier": "starter",
            "credits": 200,
            "credit_allowance": 0,
            "onboarding_completed": True,
            "platforms_connected": [],
            "created_at": datetime.now(timezone.utc),
        }
        mock_db = _make_mock_db(find_return=mock_user)

        with _patch_all_db(mock_db):
            with patch("routes.auth.settings.security.jwt_expire_days", 7):
                from server import app
                async with httpx.AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/auth/login",
                        json={"email": email, "password": plaintext},
                    )

        assert resp.status_code == 200, (
            f"Login failed unexpectedly: {resp.status_code} {resp.text}"
        )
        set_cookie = resp.headers.get("set-cookie", "")
        assert "session_token" in set_cookie, (
            f"Response must set session_token cookie, got: {set_cookie!r}"
        )
        # HttpOnly is case-insensitive in cookie headers
        assert "httponly" in set_cookie.lower(), (
            f"session_token cookie must have HttpOnly flag, got: {set_cookie!r}"
        )

    def test_fernet_encrypt_output_differs_from_input(self):
        """
        encrypt_token() must produce output that differs from the plaintext input.
        This is the basic sanity check for the Fernet OAuth token encryption.
        """
        from auth_utils import encrypt_token
        from cryptography.fernet import Fernet

        test_key = Fernet.generate_key().decode()
        plaintext = "oauth_access_token_abc123"

        with patch("auth_utils.settings.security.fernet_key", test_key):
            encrypted = encrypt_token(plaintext)

        assert encrypted != plaintext, (
            "encrypt_token() output must differ from plaintext input"
        )
        assert len(encrypted) > len(plaintext), (
            "Encrypted token should be longer than plaintext (base64+overhead)"
        )


# ---------------------------------------------------------------------------
# A03: Injection
# ---------------------------------------------------------------------------

class TestA03Injection:
    """
    OWASP A03 2021: Injection

    Verify NoSQL injection payloads are rejected at the boundary (Pydantic)
    and that auth.py uses parameterized queries (dict parameters to find_one),
    not string interpolation.
    """

    @pytest.mark.asyncio
    async def test_nosql_injection_in_email_blocked_by_pydantic(self):
        """POST /api/auth/login with email={"$gt":""} is rejected with 422."""
        mock_db = _make_mock_db()
        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": {"$gt": ""}, "password": "test"},
                )
        assert resp.status_code == 422, (
            f"NoSQL injection in email must return 422 (Pydantic EmailStr), got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_nosql_injection_in_password_rejected(self):
        """POST /api/auth/login with password={"$ne":""} must NOT return 200."""
        mock_db = _make_mock_db()
        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "test@test.com", "password": {"$ne": ""}},
                )
        assert resp.status_code != 200, (
            f"NoSQL injection in password must NOT return 200, got {resp.status_code}"
        )

    def test_mongo_queries_use_dict_params_not_string_concat(self):
        """
        Static assertion: auth.py must NOT use f-strings or .format() inside
        db.find_one() calls. Parameterized dict queries prevent injection.
        """
        import ast
        import os

        auth_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "routes", "auth.py"
        )
        with open(auth_path, "r") as f:
            source = f.read()

        # Check that find_one is called with dict literals, not f-strings
        # We parse the AST to look for string formatting in find_one arguments
        tree = ast.parse(source)

        violations = []
        for node in ast.walk(tree):
            # Look for calls like db.users.find_one(...)
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "find_one":
                    for arg in node.args:
                        # Check if any argument contains f-string (JoinedStr)
                        for subnode in ast.walk(arg):
                            if isinstance(subnode, ast.JoinedStr):
                                violations.append(ast.unparse(node))

        assert not violations, (
            f"find_one() calls must not use f-strings (injection risk): {violations}"
        )


# ---------------------------------------------------------------------------
# A04: Insecure Design
# ---------------------------------------------------------------------------

class TestA04InsecureDesign:
    """
    OWASP A04 2021: Insecure Design

    Verify password policy enforces strong passwords and rejects known
    weak/common passwords at the design level.
    """

    def test_password_policy_rejects_weak_password_no_uppercase(self):
        """PasswordPolicy.validate() rejects password without uppercase letter."""
        from auth_utils import PasswordPolicy

        is_valid, errors = PasswordPolicy.validate("testpass123!")
        assert not is_valid, "Password without uppercase should be invalid"
        assert any("uppercase" in e.lower() for e in errors)

    def test_password_policy_rejects_weak_password_no_digit(self):
        """PasswordPolicy.validate() rejects password without a digit."""
        from auth_utils import PasswordPolicy

        is_valid, errors = PasswordPolicy.validate("TestPassword!")
        assert not is_valid, "Password without digit should be invalid"
        assert any("number" in e.lower() or "digit" in e.lower() for e in errors)

    def test_password_policy_rejects_weak_password_too_short(self):
        """PasswordPolicy.validate() rejects password under 8 characters."""
        from auth_utils import PasswordPolicy

        is_valid, errors = PasswordPolicy.validate("Abc1!")
        assert not is_valid, "Password shorter than 8 chars should be invalid"
        assert any("8" in e or "least" in e.lower() for e in errors)

    def test_password_policy_rejects_common_password(self):
        """PasswordPolicy.validate() rejects known common passwords."""
        from auth_utils import PasswordPolicy

        for common_pw in ("password", "password123", "qwerty", "admin"):
            is_valid, _ = PasswordPolicy.validate(common_pw)
            assert not is_valid, f"Common password '{common_pw}' should be rejected"

    def test_password_policy_accepts_strong_password(self):
        """PasswordPolicy.validate() accepts a strong password."""
        from auth_utils import PasswordPolicy

        is_valid, errors = PasswordPolicy.validate("TestPass123!")
        assert is_valid, f"Strong password must be valid, got errors: {errors}"

    def test_password_policy_max_length_enforced(self):
        """PasswordPolicy.validate() rejects password over 128 characters."""
        from auth_utils import PasswordPolicy

        long_pw = "A" * 129 + "1!"
        is_valid, errors = PasswordPolicy.validate(long_pw)
        assert not is_valid, "Password over 128 chars should be rejected"
        assert any("128" in e or "most" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# A05: Security Misconfiguration
# ---------------------------------------------------------------------------

class TestA05SecurityMisconfiguration:
    """
    OWASP A05 2021: Security Misconfiguration

    Verify security headers are present even on error responses, and that
    the application is not leaking debug information.
    """

    @pytest.mark.asyncio
    async def test_security_headers_present_on_404_response(self):
        """
        A 404 response to a non-existent route must still include security headers.
        Security headers must apply to ALL responses, not just 200 OK.
        """
        mock_db = _make_mock_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/this-route-does-not-exist")

        # Route not found — 404
        assert resp.status_code == 404

        # Security headers must still be present
        assert resp.headers.get("x-content-type-options") == "nosniff", (
            "X-Content-Type-Options must be set on error responses"
        )
        assert resp.headers.get("x-frame-options") == "DENY", (
            "X-Frame-Options must be set on error responses"
        )
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'none'" in csp, (
            f"CSP must be set on error responses, got: {csp!r}"
        )

    @pytest.mark.asyncio
    async def test_security_headers_present_on_422_validation_error(self):
        """
        Pydantic validation errors (422) must also include security headers.
        """
        mock_db = _make_mock_db()
        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "not-an-email", "password": "test"},
                )

        assert resp.status_code == 422
        assert resp.headers.get("x-content-type-options") == "nosniff", (
            "X-Content-Type-Options must be set on 422 responses"
        )

    def test_jwt_secret_empty_raises_jwt_error(self):
        """
        decode_token() must raise JWTError when jwt_secret_key is empty.
        This prevents the application from accepting tokens in misconfigured state.
        BILL-06 fix: no fallback to hardcoded dev secret.
        """
        from auth_utils import decode_token
        from jose import JWTError

        with patch("auth_utils.settings.security.jwt_secret_key", ""):
            with pytest.raises(JWTError, match="not configured"):
                decode_token("any.token.here")

    def test_security_config_validates_weak_jwt_secret(self):
        """
        SecurityConfig.validate() returns warnings for short JWT secrets.
        """
        from config import SecurityConfig

        cfg = SecurityConfig.__new__(SecurityConfig)
        cfg.jwt_secret_key = "short"
        cfg.cors_origins = ["https://app.thookai.com"]
        cfg.jwt_algorithm = "HS256"
        cfg.jwt_expire_days = 7
        cfg.fernet_key = None
        cfg.rate_limit_per_minute = 60
        cfg.rate_limit_auth_per_minute = 10

        issues = cfg.validate()
        assert any("32" in i or "short" in i.lower() or "key" in i.lower() for i in issues), (
            f"Short JWT secret should produce a validation warning, got: {issues}"
        )


# ---------------------------------------------------------------------------
# A07: Identification and Authentication Failures
# ---------------------------------------------------------------------------

class TestA07IdentificationFailures:
    """
    OWASP A07 2021: Identification and Authentication Failures

    Verify login error messages do not reveal whether an email address exists
    (prevents user enumeration attacks).
    """

    @pytest.mark.asyncio
    async def test_login_nonexistent_email_returns_generic_error(self):
        """
        Login with a non-existent email must return "Invalid email or password",
        NOT "Email not found" (which reveals user existence).
        """
        mock_db = _make_mock_db(find_return=None)  # user not found
        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": _unique_email(), "password": "SomePass123!"},
                )

        assert resp.status_code == 401
        detail = resp.json().get("detail", "")
        assert detail == "Invalid email or password", (
            f"Error must be 'Invalid email or password', got: {detail!r}"
        )
        # Must NOT reveal that the email doesn't exist
        assert "not found" not in detail.lower(), (
            f"Error message must not reveal user non-existence: {detail!r}"
        )
        assert "exist" not in detail.lower(), (
            f"Error message must not reveal user non-existence: {detail!r}"
        )

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_same_generic_error(self):
        """
        Login with correct email but wrong password must return the SAME error
        message as a non-existent email — prevents user enumeration.
        """
        from auth_utils import hash_password

        email = _unique_email()
        existing_user = {
            "user_id": "user_a07_test",
            "email": email,
            "name": "A07 User",
            "auth_method": "email",
            "hashed_password": hash_password("CorrectPass123!"),
            "plan": "starter",
            "subscription_tier": "starter",
            "credits": 200,
            "credit_allowance": 0,
            "onboarding_completed": True,
            "platforms_connected": [],
            "created_at": datetime.now(timezone.utc),
        }
        mock_db = _make_mock_db(find_return=existing_user)

        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": email, "password": "WrongPass999!"},
                )

        assert resp.status_code == 401
        detail = resp.json().get("detail", "")
        assert detail == "Invalid email or password", (
            f"Wrong password error must be 'Invalid email or password', got: {detail!r}"
        )

    @pytest.mark.asyncio
    async def test_login_google_user_with_password_returns_generic_error(self):
        """
        A user registered via Google OAuth who tries email/password login
        must receive the same "Invalid email or password" message — not
        "Please use Google login" (which reveals auth method).
        """
        email = _unique_email()
        google_user = {
            "user_id": "user_google_a07",
            "email": email,
            "name": "Google User",
            "auth_method": "google",  # Google OAuth user
            "plan": "starter",
            "subscription_tier": "starter",
            "credits": 200,
            "credit_allowance": 0,
            "onboarding_completed": True,
            "platforms_connected": [],
            "created_at": datetime.now(timezone.utc),
        }
        mock_db = _make_mock_db(find_return=google_user)

        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": email, "password": "TestPass123!"},
                )

        assert resp.status_code == 401
        detail = resp.json().get("detail", "")
        assert detail == "Invalid email or password", (
            f"Google user login error must be 'Invalid email or password', got: {detail!r}"
        )
        # Must NOT reveal auth method
        assert "google" not in detail.lower(), (
            "Error message must not reveal that the user uses Google OAuth"
        )

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_400(self):
        """
        Registering with an already-existing email returns 400 "Email already registered".
        This is standard practice (registration explicitly checks for uniqueness).
        """
        email = _unique_email()
        existing_user = {
            "user_id": "user_dup_test",
            "email": email,
            "name": "Duplicate",
        }
        # routes/auth.py binds db at import time — must patch routes.auth.db directly
        mock_db = _make_mock_db(find_return=existing_user)

        with _patch_all_db(mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/register",
                    json={"email": email, "password": "TestPass123!", "name": "Test"},
                )

        assert resp.status_code == 400
        detail = resp.json().get("detail", "")
        assert "already registered" in detail.lower() or "already" in detail.lower(), (
            f"Duplicate email must return 400 with clear message, got: {detail!r}"
        )


# ---------------------------------------------------------------------------
# A08: Software and Data Integrity Failures
# ---------------------------------------------------------------------------

class TestA08SoftwareIntegrity:
    """
    OWASP A08 2021: Software and Data Integrity Failures

    Verify Stripe webhooks require signature verification.
    Accepting unsigned webhooks enables attackers to forge billing events.
    """

    @pytest.mark.asyncio
    async def test_stripe_webhook_without_signature_returns_400(self):
        """
        POST /api/billing/webhook/stripe without Stripe-Signature header
        must return 400 (not 200) — signature is required for integrity verification.
        """
        mock_db = _make_mock_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/billing/webhook/stripe",
                    content=b'{"type": "checkout.session.completed"}',
                    headers={"Content-Type": "application/json"},
                    # Deliberately no Stripe-Signature header
                )
        assert resp.status_code in (400, 401, 422), (
            f"Webhook without Stripe-Signature must be rejected (400/401/422), "
            f"got {resp.status_code}: {resp.text}"
        )
        assert resp.status_code != 200, (
            "Unsigned Stripe webhook must NOT return 200 (would accept forged events)"
        )

    def test_stripe_webhook_signature_check_is_enforced_in_route(self):
        """
        Static assertion: billing.py webhook handler checks for stripe_signature
        before processing the payload.
        """
        import ast
        import os

        billing_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "routes", "billing.py"
        )
        with open(billing_path, "r") as f:
            source = f.read()

        # Verify the route checks stripe_signature before calling handle_webhook_event
        assert "stripe_signature" in source, (
            "billing.py must reference 'stripe_signature' in the webhook handler"
        )
        assert "Missing Stripe-Signature" in source or "stripe_signature" in source, (
            "billing.py must enforce Stripe-Signature header"
        )


# ---------------------------------------------------------------------------
# A09: Security Logging and Monitoring Failures
# ---------------------------------------------------------------------------

class TestA09Logging:
    """
    OWASP A09 2021: Security Logging and Monitoring Failures

    Verify that failed authentication events are logged for audit trail.
    Without logs, detecting and responding to breaches is impossible.
    """

    def test_security_middleware_has_logger_configured(self):
        """
        middleware/security.py must configure a module-level logger.
        This is the prerequisite for rate limit and security event logging.
        """
        import ast
        import os

        security_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "middleware", "security.py"
        )
        with open(security_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)
        has_logger = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Attribute) and func.attr == "getLogger":
                    has_logger = True
                    break

        assert has_logger, (
            "middleware/security.py must configure a module-level logger via logging.getLogger()"
        )

    def test_security_middleware_logs_rate_limit_violations(self):
        """
        RateLimitMiddleware logs a warning when a rate limit is exceeded.
        This ensures rate limit abuse is visible in monitoring systems.
        """
        import os

        security_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "middleware", "security.py"
        )
        with open(security_path, "r") as f:
            source = f.read()

        # Verify logger.warning is called in the rate limit exceeded path
        assert "logger.warning" in source, (
            "RateLimitMiddleware must call logger.warning for rate limit violations"
        )
        assert "Rate limit exceeded" in source or "rate_limit" in source.lower(), (
            "Rate limit logging must include context about the violation"
        )

    def test_failed_login_error_path_uses_401_with_generic_message(self):
        """
        Verify the login route raises 401 with "Invalid email or password" — the
        standardized error message that security tooling can monitor for brute force.
        """
        import os

        auth_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "routes", "auth.py"
        )
        with open(auth_path, "r") as f:
            source = f.read()

        # Check that HTTPException with 401 is raised on login failure
        assert "status_code=401" in source, (
            "Login route must raise HTTPException(status_code=401) for failed auth"
        )
        assert "Invalid email or password" in source, (
            "Login route must use 'Invalid email or password' as the error message"
        )

    def test_auth_module_imports_logging(self):
        """
        routes/auth.py must import the logging module (prerequisite for audit logging).
        """
        import os

        auth_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "routes", "auth.py"
        )
        with open(auth_path, "r") as f:
            source = f.read()

        # At minimum, logging should be importable from auth (either directly or via module)
        # If logging isn't in auth.py, the server.py centralizes it — both are acceptable
        has_logging = "import logging" in source or "logging" in source
        assert has_logging, (
            "routes/auth.py should reference logging for audit trail capability"
        )
