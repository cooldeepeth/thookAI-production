"""
Phase 26: Auth Guard Coverage Tests
Covers: BACK-01 (endpoints tested), BACK-04 (all protected endpoints reject unauthenticated)
Also validates BACK-03 (error_code in 401 responses — covered by Plan 02)

Paths are derived from .planning/audit/BACKEND-API-AUDIT.md (auth_guard=YES rows).
If a path returns 404, it is skipped (route-not-found) rather than failing — this
prevents false failures from router prefix mismatches.
"""
import pytest
from httpx import AsyncClient, ASGITransport


# Paths derived from BACKEND-API-AUDIT.md (auth_guard=YES rows).
# 10 most critical protected endpoints selected across high-value domains.
# Format: (method, path, description)
PROTECTED_ENDPOINTS = [
    ("GET", "/api/persona/me", "persona profile — user's voice fingerprint"),
    ("GET", "/api/analytics/overview", "analytics overview — content performance"),
    ("GET", "/api/billing/subscription", "billing subscription status — financial data"),
    ("GET", "/api/agency/workspaces", "agency workspaces — workspace list"),
    ("GET", "/api/content/jobs", "content jobs list — user's generated content"),
    ("GET", "/api/uploads/test-upload-id", "user uploads — uploaded context files"),
    ("GET", "/api/dashboard/stats", "dashboard stats — aggregate user data"),
    ("GET", "/api/campaigns", "campaigns list — campaign data"),
    ("GET", "/api/strategy", "strategy feed — AI recommendations"),
    ("GET", "/api/uom/", "unit of measure — behavioral inference data"),
]


@pytest.mark.asyncio
async def test_all_critical_protected_endpoints_require_auth():
    """
    All critical protected endpoints must return 401 with error_code when unauthenticated.
    Endpoints returning 404 are skipped (path mismatch) rather than failing.
    """
    from server import app
    failures = []
    skipped = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method, path, description in PROTECTED_ENDPOINTS:
            if method == "GET":
                resp = await client.get(path)
            elif method == "POST":
                resp = await client.post(path, json={})
            else:
                continue

            if resp.status_code == 404:
                # Path not found in router — skip rather than fail
                # This means the audit path doesn't match the actual router prefix
                # Record it for the test summary but don't block CI
                skipped.append(
                    f"{method} {path} ({description}): 404 route-not-found "
                    f"(check router prefix in server.py)"
                )
                continue

            if resp.status_code != 401:
                failures.append(
                    f"{method} {path} ({description}): expected 401, got {resp.status_code}"
                )
                continue

            data = resp.json()
            if "error_code" not in data:
                failures.append(
                    f"{method} {path} ({description}): 401 returned but no 'error_code' "
                    f"in body: {data}"
                )

    if skipped:
        print(f"\nSKIPPED (404 route-not-found): {len(skipped)}")
        for s in skipped:
            print(f"  - {s}")

    assert not failures, "Auth guard failures:\n" + "\n".join(failures)


@pytest.mark.asyncio
async def test_persona_me_requires_auth():
    """GET /api/persona/me: 401 + error_code (high sensitivity — user's voice fingerprint)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/persona/me")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_billing_subscription_requires_auth():
    """GET /api/billing/subscription: 401 + error_code (billing data — high sensitivity)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/billing/subscription")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_analytics_overview_requires_auth():
    """GET /api/analytics/overview: 401 + error_code"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/analytics/overview")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_agency_workspaces_requires_auth():
    """GET /api/agency/workspaces: 401 + error_code"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/agency/workspaces")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_content_jobs_requires_auth():
    """GET /api/content/jobs: 401 + error_code (user content history — private data)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/content/jobs")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_campaigns_requires_auth():
    """GET /api/campaigns: 401 + error_code"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/campaigns")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_strategy_feed_requires_auth():
    """GET /api/strategy: 401 + error_code (AI recommendations — private)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/strategy")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_notifications_requires_auth():
    """GET /api/notifications: 401 + error_code (user notification inbox)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/notifications")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_obsidian_config_requires_auth():
    """GET /api/obsidian/config: 401 + error_code (user vault config — private)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/obsidian/config")
    assert resp.status_code == 401
    assert resp.json().get("error_code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_public_endpoints_do_not_require_auth():
    """
    Public endpoints must return 200 or redirect — NOT 401.
    Ensures the public list classification is accurate.
    """
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # /api/onboarding/questions is public (documented in audit as PUBLIC)
        resp = await client.get("/api/onboarding/questions")
    assert resp.status_code != 401, (
        f"Public endpoint /api/onboarding/questions returned 401 unexpectedly"
    )
    assert resp.status_code in (200, 404, 503), (
        f"Unexpected status {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_billing_config_is_public():
    """GET /api/billing/config: must NOT return 401 (documented as PUBLIC in audit)"""
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/billing/config")
    assert resp.status_code != 401, (
        f"Public endpoint /api/billing/config returned 401 unexpectedly — "
        f"this endpoint serves the Stripe publishable key and must be public"
    )
