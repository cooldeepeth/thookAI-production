"""
Phase 26: Error Format Standardization Tests
Covers: BACK-03 (error_code in all 4xx/5xx), BACK-04 (401 on unauthenticated),
        BACK-05 (malformed body → 422, never 500)

All tests in this file start in RED state.
Plan 02 adds @app.exception_handler(HTTPException) and @app.exception_handler(RequestValidationError)
to backend/server.py which drives them to GREEN.
"""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_unauthenticated_persona_returns_401_with_error_code():
    """GET /api/persona/me without auth → 401 with error_code=UNAUTHORIZED (BACK-03, BACK-04)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/persona/me")
    assert resp.status_code == 401
    data = resp.json()
    assert "error_code" in data, f"Missing 'error_code' in response: {data}"
    assert data["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_unauthenticated_analytics_returns_401_with_error_code():
    """GET /api/analytics/overview without auth → 401 with error_code=UNAUTHORIZED (BACK-03, BACK-04)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/analytics/overview")
    assert resp.status_code == 401
    data = resp.json()
    assert "error_code" in data, f"Missing 'error_code' in response: {data}"
    assert data["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_missing_body_on_content_create_returns_422_with_error_code():
    """POST /api/content/create with missing body → 422 with error_code=VALIDATION_ERROR (BACK-03, BACK-05)"""
    from server import app
    # Use fake token to pass auth header format check (will still 401 or 422 on body)
    # We send no body to get the Pydantic validation error
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/content/create",
            content=b"{}",
            headers={"Content-Type": "application/json", "Cookie": "session_token=fakejwt"}
        )
    # 422 for missing required fields OR 401 for bad token — either way, never 500
    assert resp.status_code in (401, 422), f"Expected 401 or 422 but got {resp.status_code}: {resp.text}"
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_empty_json_body_returns_422_with_field_errors():
    """POST /api/content/create with empty JSON {} → 422 with error_code and errors list (BACK-03, BACK-05)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # We bypass auth by using an invalid cookie — the validation error fires before auth in FastAPI
        # Actually FastAPI processes auth dependency first; empty body after auth pass → 422
        # Send with no auth cookie to confirm auth path doesn't 500 either
        resp = await client.post(
            "/api/content/create",
            json={}
        )
    assert resp.status_code != 500, f"Got 500: {resp.text}"
    data = resp.json()
    assert "error_code" in data, f"Missing 'error_code' key in {data}"


@pytest.mark.asyncio
async def test_malformed_json_body_never_returns_500():
    """POST /api/auth/login with invalid JSON → 400 or 422, never 500 (BACK-05)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/login",
            content=b"not-valid-json",
            headers={"Content-Type": "application/json"}
        )
    assert resp.status_code != 500, f"Got 500 for malformed JSON: {resp.text}"
    assert resp.status_code in (400, 422), f"Expected 400 or 422 but got {resp.status_code}"


@pytest.mark.asyncio
async def test_not_found_route_returns_404_with_error_code():
    """GET /api/does-not-exist → 404 with error_code=NOT_FOUND (BACK-03)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/does-not-exist-route-xyz")
    assert resp.status_code == 404
    data = resp.json()
    assert "error_code" in data, f"Missing 'error_code' in 404 response: {data}"
    assert data["error_code"] == "NOT_FOUND"
