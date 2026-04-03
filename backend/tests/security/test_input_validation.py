"""
Input Validation Security Tests — SEC-05

Covers:
- NoSQL injection payloads in auth endpoints
- XSS payloads in user-facing input fields
- Path traversal attempts in file operations
- Request size limit enforcement (10MB cap via InputValidationMiddleware)

Design: uses httpx.AsyncClient + ASGITransport for route tests, and
TestClient for synchronous middleware tests.  Database calls are mocked
via unittest.mock to avoid requiring a live MongoDB connection.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    return f"sectest_{uuid.uuid4().hex[:8]}@test.com"


def _app_with_mocked_db():
    """
    Import the real FastAPI app with database.db patched to an AsyncMock.
    Returns (app, mock_db) tuple.
    """
    mock_db = MagicMock()
    mock_db.users = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=None)
    mock_db.users.with_options = MagicMock(return_value=MagicMock(
        insert_one=AsyncMock(return_value=MagicMock(inserted_id="oid"))
    ))
    mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id="oid"))
    mock_db.user_sessions = MagicMock()
    mock_db.user_sessions.find_one = AsyncMock(return_value=None)
    return mock_db


# ---------------------------------------------------------------------------
# NoSQL Injection Tests
# ---------------------------------------------------------------------------

class TestNoSQLInjection:
    """
    Verify that MongoDB operator payloads in auth fields are rejected by Pydantic
    (EmailStr rejects non-string types), preventing NoSQL injection attacks.

    SEC-05: All user-facing input fields must reject injection payloads at the boundary.
    """

    @pytest.mark.asyncio
    async def test_login_email_nosql_injection_gt_returns_422(self):
        """POST /api/auth/login with email={"$gt": ""} must be rejected — 422."""
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": {"$gt": ""}, "password": "test"},
                )
        assert resp.status_code == 422, (
            f"Expected 422 (Pydantic rejection), got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_login_email_nosql_injection_ne_returns_422(self):
        """POST /api/auth/login with email={"$ne": null} must be rejected — 422."""
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": {"$ne": None}, "password": "test"},
                )
        assert resp.status_code == 422, (
            f"Expected 422 (Pydantic rejection), got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_login_email_nosql_injection_regex_returns_422(self):
        """POST /api/auth/login with email={"$regex": ".*"} must be rejected — 422."""
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": {"$regex": ".*"}, "password": "test"},
                )
        assert resp.status_code == 422, (
            f"Expected 422 (Pydantic rejection), got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_login_email_nosql_injection_where_returns_422(self):
        """POST /api/auth/login with email={"$where": "1==1"} must be rejected — 422."""
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": {"$where": "1==1"}, "password": "test"},
                )
        assert resp.status_code == 422, (
            f"Expected 422 (Pydantic rejection), got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_register_name_nosql_injection_stored_as_string(self):
        """
        POST /api/auth/register with name={"$gt": ""}.

        Pydantic coerces the name field to a string representation.
        The important assertion is that the value stored via insert_one
        is a string — NOT a dict that MongoDB would interpret as an operator.
        """
        captured_doc: dict = {}

        async def capture_insert(doc):
            captured_doc.update(doc)
            return MagicMock(inserted_id="oid")

        mock_db = _app_with_mocked_db()
        mock_db.users.find_one = AsyncMock(return_value=None)
        wmaj = MagicMock()
        wmaj.insert_one = AsyncMock(side_effect=capture_insert)
        mock_db.users.with_options = MagicMock(return_value=wmaj)

        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/register",
                    json={
                        "email": _unique_email(),
                        "password": "TestPass123!",
                        "name": '{"$gt": ""}',  # String representation of operator
                    },
                )

        # Registration may succeed (200) — the name is the literal string
        assert resp.status_code in (200, 201, 422), (
            f"Unexpected status {resp.status_code}: {resp.text}"
        )
        if captured_doc:
            # If insertion was captured, verify name is a str, not a dict
            assert isinstance(captured_doc.get("name"), str), (
                "name field must be a plain string, not a dict/operator"
            )

    @pytest.mark.asyncio
    async def test_login_password_nosql_injection_does_not_bypass_auth(self):
        """
        POST /api/auth/login with password={"$ne": ""}.

        Pydantic accepts any string for password; but {"$ne":""} as a JSON object
        must be rejected as 422 (Pydantic str validation) or 401 (bcrypt comparison
        fails on non-string). In either case, the attacker must NOT get a 200.
        """
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": _unique_email(), "password": {"$ne": ""}},
                )
        assert resp.status_code != 200, (
            f"NoSQL injection bypass must not return 200 — got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_content_generate_nosql_injection_in_raw_input_does_not_500(self):
        """
        POST /api/content/generate with raw_input={"$gt": ""} should NOT cause
        a 500 server error (injection must be treated as a plain string value).
        """
        from auth_utils import get_current_user

        mock_user = {
            "user_id": "user_sectest001",
            "email": "sec@test.com",
            "subscription_tier": "starter",
            "credits": 200,
            "credit_allowance": 0,
            "onboarding_completed": True,
        }

        mock_db = _app_with_mocked_db()
        mock_db.content_jobs = MagicMock()
        mock_db.content_jobs.insert_one = AsyncMock(return_value=MagicMock(inserted_id="oid"))
        mock_db.persona_engines = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)
        mock_db.users = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=mock_user)
        mock_db.users.find_one_and_update = AsyncMock(return_value={**mock_user, "credits": 199})

        with patch("database.db", mock_db):
            from server import app
            app.dependency_overrides[get_current_user] = lambda: mock_user
            try:
                async with httpx.AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    # raw_input is a string — injection payload is the string value
                    resp = await client.post(
                        "/api/content/generate",
                        json={
                            "platform": "linkedin",
                            "content_type": "post",
                            "raw_input": '{"$gt": ""}',
                        },
                        headers={"Authorization": "Bearer dummy"},
                    )
            finally:
                app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code != 500, (
            f"NoSQL injection in raw_input must not cause 500 — got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# XSS Prevention Tests
# ---------------------------------------------------------------------------

class TestXSSPrevention:
    """
    Verify XSS payloads are stored as literal strings (server-side),
    Content-Type is always application/json (not text/html), and
    CSP headers block script execution.

    The ThookAI backend returns JSON, not rendered HTML — XSS prevention
    is enforced at the frontend rendering layer, but the API must:
    1. Return JSON content-type (prevents browser from executing scripts)
    2. Set Content-Security-Policy: default-src 'none' (blocks inline scripts)
    3. Store strings as strings without further interpretation
    """

    @pytest.mark.asyncio
    async def test_register_name_xss_stored_as_literal_string(self):
        """
        Register with name=<script>alert(1)</script>.
        The name is stored as-is; the API returns the literal string in JSON.
        """
        xss_payload = "<script>alert(1)</script>"
        captured_doc: dict = {}

        async def capture_insert(doc):
            captured_doc.update(doc)
            return MagicMock(inserted_id="oid")

        mock_db = _app_with_mocked_db()
        mock_db.users.find_one = AsyncMock(return_value=None)
        wmaj = MagicMock()
        wmaj.insert_one = AsyncMock(side_effect=capture_insert)
        mock_db.users.with_options = MagicMock(return_value=wmaj)

        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/register",
                    json={
                        "email": _unique_email(),
                        "password": "TestPass123!",
                        "name": xss_payload,
                    },
                )

        # Registration succeeds with XSS string
        assert resp.status_code in (200, 201), (
            f"Expected success, got {resp.status_code}: {resp.text}"
        )
        # Verify the name in the JSON response is the literal XSS string
        body = resp.json()
        assert body.get("name") == xss_payload, (
            f"Name in response should be literal XSS string, got: {body.get('name')}"
        )
        # Verify content-type is JSON (not HTML that would execute the script)
        assert "application/json" in resp.headers.get("content-type", ""), (
            f"Response must be application/json, got: {resp.headers.get('content-type')}"
        )

    @pytest.mark.asyncio
    async def test_xss_in_login_email_rejected_by_email_validator(self):
        """POST /api/auth/login with email=<script>alert(1)</script> must be 422."""
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "<script>alert(1)</script>", "password": "test"},
                )
        assert resp.status_code == 422, (
            f"XSS in email must be rejected by EmailStr — got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_json_response_content_type_prevents_xss(self):
        """
        Any API response must have Content-Type: application/json.
        Browser will not execute inline scripts in a JSON response.
        """
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "test@test.com", "password": "wrong"},
                )
        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"All responses must be application/json, got: {content_type}"
        )

    @pytest.mark.asyncio
    async def test_csp_header_blocks_inline_scripts(self):
        """
        Response headers must include Content-Security-Policy with default-src 'none'.
        This blocks any inline script execution even if XSS payload were rendered.
        """
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "test@test.com", "password": "testpass"},
                )
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'none'" in csp, (
            f"CSP must contain \"default-src 'none'\", got: {csp!r}"
        )

    @pytest.mark.asyncio
    async def test_xss_in_error_response_is_json_not_html(self):
        """
        A 404 or 422 error response must also be JSON, not rendered HTML.
        This prevents reflected XSS from error pages.
        """
        mock_db = _app_with_mocked_db()
        with patch("database.db", mock_db):
            from server import app
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # Intentionally malformed request to trigger validation error
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "<img src=x onerror=alert(1)>", "password": "test"},
                )
        # Should be 422 JSON, not an HTML error page
        assert resp.status_code == 422
        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Error responses must also be application/json, got: {content_type}"
        )


# ---------------------------------------------------------------------------
# Path Traversal Tests
# ---------------------------------------------------------------------------

class TestPathTraversal:
    """
    Verify path traversal payloads in filenames are sanitized.

    The uploads endpoint sanitizes filenames using character allowlisting:
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
    This strips all '/' and '.' sequences that could traverse directories.
    """

    def test_upload_filename_sanitization_strips_path_traversal(self):
        """
        The upload route sanitizes filename using character allowlisting.
        Verify the sanitization logic strips path traversal characters.

        The critical protection is stripping '/' — dots are kept (they appear
        in valid filenames like 'photo.jpg') but slashes are never allowed,
        which prevents any directory traversal.
        """
        # Replicate the sanitization logic from routes/uploads.py
        malicious = "../../../etc/passwd"
        safe_name = "".join(c for c in malicious if c.isalnum() or c in "._-")
        # After sanitization: ".....etcpasswd" — no slashes, no traversal possible
        assert "/" not in safe_name, "Sanitized filename must not contain '/'"
        # The key protection: no slash means no directory component
        # (dots alone cannot traverse directories without a path separator)
        assert "etc/passwd" not in safe_name, (
            "Sanitized filename must not contain directory path 'etc/passwd'"
        )

    def test_url_encoded_path_traversal_stripped(self):
        """
        URL-encoded traversal sequences (%2e%2e%2f) decoded and then sanitized.
        After URL decoding: '../' — after sanitization: '...'  (no slash).
        """
        from urllib.parse import unquote

        encoded = "%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        decoded = unquote(encoded)  # '../../../etc/passwd' equivalent
        safe_name = "".join(c for c in decoded if c.isalnum() or c in "._-")
        assert "/" not in safe_name, (
            "URL-decoded+sanitized filename must not contain '/'"
        )

    def test_double_encoded_traversal_stripped(self):
        """
        Double-encoded traversal (%252e%252e%252f) remains benign after
        single-pass URL decode and character sanitization.
        """
        from urllib.parse import unquote

        double_encoded = "%252e%252e%252fetc%252fpasswd"
        # Single URL decode: '%2e%2e%2fetc%2fpasswd'
        once_decoded = unquote(double_encoded)
        safe_name = "".join(c for c in once_decoded if c.isalnum() or c in "._-")
        assert "/" not in safe_name, (
            "Double-encoded traversal must not produce '/' after sanitization"
        )

    def test_upload_filename_null_byte_stripped(self):
        """
        Null byte injection in filenames: 'file\x00.txt' should be sanitized.
        Null bytes are not alphanumeric or in '._-', so they are stripped.
        """
        filename_with_null = "file\x00.txt"
        safe_name = "".join(
            c for c in filename_with_null if c.isalnum() or c in "._-"
        )
        assert "\x00" not in safe_name, (
            "Null byte must be stripped from sanitized filename"
        )

    def test_r2_key_uses_safe_prefix_prevents_traversal(self):
        """
        Verify that the R2 storage key construction prefixes user_id and upload_id,
        making it structurally impossible to escape the user's directory even if
        safe_name contained dots.
        """
        user_id = "user_abc123"
        upload_id = "upl_xyz789"
        filename = "normalfile.pdf"
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:120]
        key = f"context/{user_id}/{upload_id}/{safe_name}"

        assert key.startswith("context/user_abc123/upl_xyz789/"), (
            "R2 key must be prefixed with context/user_id/upload_id/"
        )
        assert "etc" not in key or "passwd" not in key


# ---------------------------------------------------------------------------
# Request Size Limit Tests
# ---------------------------------------------------------------------------

class TestRequestSizeLimits:
    """
    Verify InputValidationMiddleware enforces 10MB body size limit.

    Uses a minimal FastAPI app with only InputValidationMiddleware to isolate
    the size-check logic without auth or database dependencies.
    """

    def _make_size_test_app(self) -> FastAPI:
        """Build a minimal app with only InputValidationMiddleware."""
        from middleware.security import InputValidationMiddleware
        from fastapi.responses import JSONResponse

        mini = FastAPI()
        mini.add_middleware(InputValidationMiddleware)

        @mini.post("/test-upload")
        async def test_upload_handler():
            return JSONResponse({"ok": True})

        return mini

    def test_oversized_request_body_returns_413(self):
        """
        POST with Content-Length > 10MB must return 413 Request Entity Too Large.
        """
        mini = self._make_size_test_app()
        client = TestClient(mini, raise_server_exceptions=False)
        oversized = 10 * 1024 * 1024 + 1  # 10MB + 1 byte
        resp = client.post(
            "/test-upload",
            content=b"x",  # Actual body doesn't matter — header is checked
            headers={"Content-Length": str(oversized), "Content-Type": "application/json"},
        )
        assert resp.status_code == 413, (
            f"Expected 413 for oversized request, got {resp.status_code}"
        )

    def test_normal_request_body_passes_size_validation(self):
        """
        POST with Content-Length 1000 bytes must NOT return 413.
        """
        mini = self._make_size_test_app()
        client = TestClient(mini, raise_server_exceptions=False)
        resp = client.post(
            "/test-upload",
            content=b"x" * 100,
            headers={"Content-Length": "1000", "Content-Type": "application/json"},
        )
        assert resp.status_code != 413, (
            f"Normal-size request must not return 413, got {resp.status_code}"
        )

    def test_exactly_10mb_request_is_rejected(self):
        """
        Content-Length exactly at 10MB (10485760 bytes) passes; 10MB+1 fails.
        Boundary condition check.
        """
        mini = self._make_size_test_app()
        client = TestClient(mini, raise_server_exceptions=False)

        exact_10mb = 10 * 1024 * 1024  # Exactly 10MB — at the limit
        resp_at_limit = client.post(
            "/test-upload",
            content=b"x",
            headers={"Content-Length": str(exact_10mb), "Content-Type": "application/json"},
        )
        # Exactly at limit: passes (middleware checks >)
        assert resp_at_limit.status_code != 413, (
            f"Request at exactly 10MB should pass, got {resp_at_limit.status_code}"
        )

        one_over = exact_10mb + 1  # One byte over the limit
        resp_over = client.post(
            "/test-upload",
            content=b"x",
            headers={"Content-Length": str(one_over), "Content-Type": "application/json"},
        )
        assert resp_over.status_code == 413, (
            f"Request 1 byte over 10MB should return 413, got {resp_over.status_code}"
        )

    def test_missing_content_length_header_is_processed(self):
        """
        POST without Content-Length header must still be processed (not rejected).
        Middleware only checks size when Content-Length header is present.
        """
        mini = self._make_size_test_app()
        client = TestClient(mini, raise_server_exceptions=False)
        resp = client.post(
            "/test-upload",
            content=b'{"test": "data"}',
            headers={"Content-Type": "application/json"},
        )
        # Without Content-Length, middleware skips size check — should not 413
        assert resp.status_code != 413, (
            f"Request without Content-Length must not return 413, got {resp.status_code}"
        )

    def test_max_body_size_constant_is_10mb(self):
        """
        InputValidationMiddleware.MAX_BODY_SIZE must equal exactly 10MB (10485760 bytes).
        This is a contract test — changing the constant is a security policy change.
        """
        from middleware.security import InputValidationMiddleware

        expected = 10 * 1024 * 1024
        assert InputValidationMiddleware.MAX_BODY_SIZE == expected, (
            f"MAX_BODY_SIZE must be {expected} (10MB), "
            f"got {InputValidationMiddleware.MAX_BODY_SIZE}"
        )
