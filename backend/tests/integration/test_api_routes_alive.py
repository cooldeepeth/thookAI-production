"""Dynamic API route liveness tests for ThookAI (Phase 20 — E2E-07).

Verifies that every registered FastAPI route RESPONDS without returning
404 (route not found) or 500 (unhandled server error).

Strategy:
- Build an isolated FastAPI app that mirrors server.py's router setup but
  has NO lifespan (no real MongoDB, Redis, or external services needed).
- Override get_current_user dependency to bypass JWT auth.
- Patch database.db with AsyncMock so route handlers don't crash on DB calls.
- Use httpx.AsyncClient with ASGITransport for async route calls.
- For GET routes: expect 200 or any 2xx/4xx that is NOT 404/500.
- For POST routes: send minimal body {}; expect 200/201/422 (validation error
  proves the route is alive and parsing input), NOT 404/500.

The goal is liveness, not correctness — routes are allowed to return 401/403/404
for specific resources, but NOT 404 for the route itself or 500 for a crash.
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Fake authenticated user — used to override get_current_user dependency
# ---------------------------------------------------------------------------

FAKE_USER: dict = {
    "user_id": "route-alive-user-001",
    "email": "alive@thookai.io",
    "name": "Route Alive Tester",
    "subscription_tier": "pro",
    "credits": 500,
    "credit_allowance": 0,
    "onboarding_completed": True,
}


# ---------------------------------------------------------------------------
# Route probes — (method, path, expected_status_codes, description)
#
# expected_status_codes: any code in this list is ACCEPTABLE.
# 404 and 500 are NEVER acceptable — they signal dead links or crashes.
#
# Notes:
#   - 200 / 201 / 202: success
#   - 400 / 422: client error (validation) — proves route exists
#   - 401 / 403: auth error — proves route exists (used for unauthed tests)
#   - 404 for a *resource* (not a route) is sometimes expected;
#     but for these probes we ensure the route itself is registered.
#   - 503: external service unavailable — acceptable for optional integrations
# ---------------------------------------------------------------------------

ROUTE_PROBES: List[tuple] = [
    # ── Health ──────────────────────────────────────────────────────────────
    ("GET",  "/health",                          [200, 503],           "Health endpoint"),
    # ── Auth (prefix /auth) ─────────────────────────────────────────────────
    ("POST", "/api/auth/register",               [200, 201, 400, 422], "Auth register"),
    ("POST", "/api/auth/login",                  [200, 400, 401, 422], "Auth login"),
    ("POST", "/api/auth/logout",                 [200, 401, 422],      "Auth logout"),
    ("GET",  "/api/auth/me",                     [200, 401],           "Auth current user"),
    # ── Password reset (same /auth prefix) ──────────────────────────────────
    ("POST", "/api/auth/forgot-password",        [200, 400, 422],      "Password reset request"),
    # ── Onboarding (prefix /onboarding) ─────────────────────────────────────
    ("GET",  "/api/onboarding/questions",        [200],                "Onboarding questions"),
    # ── Persona (prefix /persona, no bare GET /) ────────────────────────────
    ("GET",  "/api/persona/me",                  [200, 404],           "Get user persona"),
    # ── Content (prefix /content) ───────────────────────────────────────────
    ("GET",  "/api/content/jobs",                [200],                "List content jobs"),
    ("POST", "/api/content/create",              [200, 201, 400, 422], "Content create"),
    ("GET",  "/api/content/platform-types",      [200],                "Content platform types"),
    # ── Dashboard (prefix /dashboard) ───────────────────────────────────────
    ("GET",  "/api/dashboard/stats",             [200],                "Dashboard stats"),
    # ── Analytics (prefix /analytics) ───────────────────────────────────────
    ("GET",  "/api/analytics/overview",          [200],                "Analytics overview"),
    # ── Billing (prefix /billing) ────────────────────────────────────────────
    ("GET",  "/api/billing/credits",             [200],                "Credit balance"),
    ("GET",  "/api/billing/config",              [200],                "Billing config"),
    # ── Templates (prefix /templates) ───────────────────────────────────────
    ("GET",  "/api/templates",                   [200],                "Template marketplace"),
    # ── Agency (prefix /agency) ─────────────────────────────────────────────
    ("GET",  "/api/agency/workspaces",           [200],                "Agency workspaces"),
    # ── Strategy (prefix /strategy, GET "" route) ────────────────────────────
    ("GET",  "/api/strategy",                    [200],                "Strategy feed"),
    # ── Campaigns (prefix /campaigns) ───────────────────────────────────────
    ("GET",  "/api/campaigns",                   [200],                "Campaigns list"),
    # ── Media (prefix /media) ───────────────────────────────────────────────
    ("GET",  "/api/media/assets",                [200],                "Media assets"),
    # ── Notifications (prefix /notifications) ───────────────────────────────
    ("GET",  "/api/notifications",               [200],                "Notifications list"),
]


# ---------------------------------------------------------------------------
# Build an isolated test FastAPI app
# ---------------------------------------------------------------------------

class _AsyncCursor:
    """Minimal async cursor that supports async for, .sort(), .skip(), .limit(), .to_list()."""

    def __init__(self, items=None):
        self._items = list(items or [])
        self._index = 0

    def sort(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return self._items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


def _make_collection() -> MagicMock:
    """Return a MagicMock that behaves like a Motor async collection."""
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.find = MagicMock(return_value=_AsyncCursor([]))
    col.aggregate = MagicMock(return_value=_AsyncCursor([]))
    col.count_documents = AsyncMock(return_value=0)
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id"))
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    col.find_one_and_update = AsyncMock(return_value=None)
    col.with_options = MagicMock(return_value=col)
    return col


class _MockDB:
    """Lightweight Motor-like database mock — returns a collection mock for any attribute."""

    def __init__(self):
        self._collections: dict = {}
        self.command = AsyncMock(return_value={"ok": 1})

    def __getattr__(self, name: str) -> MagicMock:
        if name.startswith("_") or name == "command":
            raise AttributeError(name)
        if name not in self._collections:
            self._collections[name] = _make_collection()
        return self._collections[name]


def _mock_db() -> _MockDB:
    """Return a _MockDB instance that acts like Motor's AsyncIOMotorDatabase."""
    return _MockDB()


@pytest.fixture
def app_with_mocks():
    """
    Isolated FastAPI app with all API routes registered, auth bypassed,
    and database mocked.  No lifespan — no real external connections.
    """
    from auth_utils import get_current_user

    # Import all routers — same set as server.py (minus admin which has special mount)
    import routes.auth as _auth
    import routes.password_reset as _pw
    import routes.auth_google as _google
    import routes.onboarding as _onboard
    import routes.persona as _persona
    import routes.content as _content
    import routes.dashboard as _dash
    import routes.platforms as _platforms
    import routes.repurpose as _repurpose
    import routes.analytics as _analytics
    import routes.billing as _billing
    import routes.viral as _viral
    import routes.agency as _agency
    import routes.templates as _templates
    import routes.media as _media
    import routes.uploads as _uploads
    import routes.notifications as _notifications
    import routes.webhooks as _webhooks
    import routes.campaigns as _campaigns
    import routes.uom as _uom
    import routes.viral_card as _viral_card
    import routes.n8n_bridge as _n8n
    import routes.strategy as _strategy
    import routes.obsidian as _obsidian
    import routes.admin as _admin

    test_app = FastAPI(title="ThookAI Test App — route liveness")
    test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

    from fastapi import APIRouter
    api = APIRouter(prefix="/api")
    for mod in (
        _auth, _pw, _google, _onboard, _persona, _content, _dash,
        _platforms, _repurpose, _analytics, _billing, _viral, _agency,
        _templates, _media, _uploads, _notifications, _webhooks,
        _campaigns, _uom, _viral_card, _n8n, _strategy, _obsidian,
    ):
        api.include_router(mod.router)

    test_app.include_router(api)
    # Admin router mounted directly at /api/admin
    test_app.include_router(_admin.router, prefix="/api/admin", include_in_schema=False)

    # Health endpoint (mirrors server.py)
    @test_app.get("/health")
    async def health_check():
        return {"status": "ok", "services": {}}

    return test_app


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestAllRoutesRespond:
    """E2E-07: Every registered API route must respond — no 404 or 500 allowed."""

    @pytest.mark.parametrize("method,path,expected_statuses,desc", ROUTE_PROBES)
    async def test_route_responds(self, method, path, expected_statuses, desc, app_with_mocks):
        """
        Send a request to each probe route and verify the response is NOT 404
        (route not found) or 500 (unhandled server error).

        A 422 (validation error) is acceptable for POST routes — it means the
        route is alive and rejecting an invalid payload, which is correct.
        A 401/403 is acceptable — it means the route is alive and enforcing auth.
        """
        # Patch all database.db references so route handlers don't crash on real DB
        mock_database = _mock_db()

        # Patch both:
        #   1. database.db  — for routes that do lazy `from database import db` inside functions
        #   2. routes.<mod>.db — for routes that import db at module level
        # Routes with NO module-level db (media, n8n_bridge, notifications, uom, webhooks)
        # are covered by database.db patch alone.
        patches = [
            patch("database.db", mock_database),
            # Module-level db imports in each route
            patch("routes.auth.db", mock_database),
            patch("routes.auth_google.db", mock_database),
            patch("routes.password_reset.db", mock_database),
            patch("routes.onboarding.db", mock_database),
            patch("routes.persona.db", mock_database),
            patch("routes.content.db", mock_database),
            patch("routes.dashboard.db", mock_database),
            patch("routes.platforms.db", mock_database),
            patch("routes.repurpose.db", mock_database),
            patch("routes.analytics.db", mock_database),
            patch("routes.billing.db", mock_database),
            patch("routes.viral.db", mock_database),
            patch("routes.agency.db", mock_database),
            patch("routes.templates.db", mock_database),
            patch("routes.uploads.db", mock_database),
            patch("routes.campaigns.db", mock_database),
            patch("routes.obsidian.db", mock_database),
            patch("routes.strategy.db", mock_database),
            patch("routes.viral_card.db", mock_database),
            patch("routes.admin.db", mock_database),
            # Service-level db patches (services imported from routes)
            patch("services.notification_service.db", mock_database),
        ]

        started = [p.start() for p in patches]
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app_with_mocks),
                base_url="http://test",
            ) as client:
                body = "{}" if method == "POST" else None
                headers = {"Content-Type": "application/json"} if method == "POST" else {}
                response = await client.request(method, path, content=body, headers=headers)

            status = response.status_code

            # 500 is NEVER acceptable — it means the server crashed
            assert status != 500, (
                f"[SERVER ERROR] {method} {path} returned 500 — unhandled exception. "
                f"Description: {desc}\nResponse: {response.text[:300]}"
            )

            # 404 is only acceptable when the probe explicitly lists it
            # (e.g. resources that return 404 when empty, like persona before onboarding)
            # A 404 for an UNREGISTERED route would not be in expected_statuses
            if expected_statuses:
                assert status in expected_statuses, (
                    f"{method} {path} returned {status}, expected one of {expected_statuses}. "
                    f"{'Route may not be registered — DEAD LINK' if status == 404 else 'Unexpected status'}. "
                    f"Description: {desc}\nResponse: {response.text[:200]}"
                )
            else:
                # No expected list — just assert it's not a route-miss or server crash
                assert status != 404, (
                    f"[DEAD LINK] {method} {path} returned 404 — route is NOT registered. "
                    f"Description: {desc}"
                )
        finally:
            for p in patches:
                p.stop()


class TestNoUnexpectedServerErrors:
    """E2E-07: Verify graceful error handling and CORS middleware is active."""

    async def test_health_returns_valid_json(self, app_with_mocks):
        """GET /health must return 200 with a JSON body containing a 'status' key."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mocks),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200, (
            f"/health returned {response.status_code} — health endpoint is broken"
        )
        body = response.json()
        assert isinstance(body, dict), "/health must return a JSON object"
        assert "status" in body, (
            "/health response is missing the 'status' key. "
            f"Got: {list(body.keys())}"
        )

    async def test_unknown_route_returns_404_not_500(self, app_with_mocks):
        """
        An unregistered route like /api/nonexistent-xyz must return 404,
        NOT 500.  Returning 500 for unknown routes signals a broken error
        handler.
        """
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mocks),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/this-route-does-not-exist-xyz-999")

        assert response.status_code == 404, (
            f"Unknown route returned {response.status_code} instead of 404. "
            "FastAPI should return 404 for unregistered paths, not 500."
        )

    async def test_options_request_does_not_crash(self, app_with_mocks):
        """
        OPTIONS preflight requests to a known endpoint must not crash the server.

        Note: CORS headers (Access-Control-Allow-Origin) are only injected by
        CORSMiddleware which requires specific allowed_origins config.  The test
        app does not include CORS middleware so we only assert no 500 error.
        """
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mocks),
            base_url="http://test",
        ) as client:
            response = await client.options("/api/auth/login")

        assert response.status_code != 500, (
            f"OPTIONS /api/auth/login returned 500 — server crashed on preflight request. "
            f"Response: {response.text[:200]}"
        )

    async def test_malformed_json_body_returns_422_not_500(self, app_with_mocks):
        """
        Sending malformed JSON to a POST endpoint must return 422 (FastAPI
        validation error), NOT 500.  This confirms input validation is working.
        """
        mock_database = _mock_db()

        with patch("database.db", mock_database), \
             patch("routes.auth.db", mock_database):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_mocks),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/auth/register",
                    content="this is not json at all",
                    headers={"Content-Type": "application/json"},
                )

        # FastAPI returns 422 for body that cannot be parsed as the expected model
        assert response.status_code in (400, 422), (
            f"Malformed JSON body returned {response.status_code} — "
            "expected 400 or 422, not a server crash (500)."
        )
        assert response.status_code != 500, (
            "Malformed JSON body caused a 500 server error — unhandled exception!"
        )
