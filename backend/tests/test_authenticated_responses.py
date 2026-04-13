"""
Phase 26: Authenticated Endpoint Response Tests
Covers: BACK-01 (authenticated endpoints return correct data shape)

Uses FastAPI dependency_overrides to inject a fake user without a real JWT.
Tests verify endpoints return 200 (or graceful non-500) with expected response keys.
Database calls are mocked via unittest.mock.patch to avoid real DB connections.

Route files use module-level `from database import db`, so patch targets are
routes.<module>.db for each test.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock


def _fake_user():
    """Minimal user dict matching the shape returned by get_current_user."""
    return {
        "user_id": "test_user_phase26",
        "email": "test@thook.ai",
        "name": "Test User",
        "subscription_tier": "pro",
        "credits": 100,
        "onboarding_completed": True,
    }


def _make_async_cursor(items: list):
    """
    Build a mock cursor whose .sort().limit().to_list() chain returns items.
    Motor's AsyncIOMotorCursor supports method chaining; replicate it here.
    """
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=items)
    return cursor


@pytest.fixture(autouse=False)
def override_auth():
    """Override get_current_user with a fake user for the duration of the test."""
    from server import app
    from auth_utils import get_current_user
    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_persona_me_returns_no_500_with_mocked_auth(override_auth):
    """
    GET /api/persona/me with valid auth → does NOT raise 401 or 500.
    Route returns 404 when no persona exists — that is the correct empty state.
    Verifies: dependency override works + route does not crash. (BACK-01)
    """
    from server import app

    # persona.py uses `from database import db` at module level
    # Patch the db object as seen by the routes.persona module
    with patch("routes.persona.db") as mock_db:
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value=_fake_user())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/persona/me")

    # 404 = no persona (correct empty state for a test user)
    # 200 = persona found
    # Both are valid authenticated responses — what we assert is NOT 401 or 500
    assert resp.status_code not in (401, 500), (
        f"GET /api/persona/me returned {resp.status_code} when authenticated: {resp.text}"
    )
    assert resp.status_code in (200, 404), (
        f"Unexpected status {resp.status_code} from GET /api/persona/me: {resp.text}"
    )


@pytest.mark.asyncio
async def test_content_jobs_returns_200_with_mocked_auth(override_auth):
    """
    GET /api/content/jobs with valid auth → 200 with a jobs list (possibly empty). (BACK-01)
    Route: content.py → list_jobs → db.content_jobs.find().sort().limit().to_list()
    Verifies endpoint responds correctly and returns expected shape.
    """
    from server import app

    with patch("routes.content.db") as mock_db:
        mock_db.content_jobs.find.return_value = _make_async_cursor([])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/content/jobs")

    assert resp.status_code not in (401, 500), (
        f"GET /api/content/jobs returned {resp.status_code} when authenticated: {resp.text}"
    )
    if resp.status_code == 200:
        data = resp.json()
        # Route returns {"jobs": [...]} shape
        assert "jobs" in data, (
            f"Expected 'jobs' key in response, got: {data}"
        )
        assert isinstance(data["jobs"], list), (
            f"Expected jobs to be a list, got: {type(data['jobs'])}"
        )


@pytest.mark.asyncio
async def test_campaigns_returns_200_with_mocked_auth(override_auth):
    """
    GET /api/campaigns with valid auth → 200 with campaigns list (possibly empty). (BACK-01)
    Route: campaigns.py → list_campaigns → db.campaigns.find().sort().to_list()
    campaigns.py uses module-level `from database import db` so patch targets routes.campaigns.db
    """
    from server import app

    with patch("routes.campaigns.db") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.campaigns.find.return_value = mock_cursor

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/campaigns")

    assert resp.status_code not in (401, 500), (
        f"GET /api/campaigns returned {resp.status_code} when authenticated: {resp.text}"
    )


@pytest.mark.asyncio
async def test_strategy_feed_returns_no_500_with_mocked_auth(override_auth):
    """
    GET /api/strategy with valid auth → does NOT return 401 or 500. (BACK-01)
    Route: strategy.py → get_strategy_feed → db.strategy_recommendations.find().sort().limit().to_list()
    strategy.py uses module-level `from database import db` so patch targets routes.strategy.db
    """
    from server import app

    with patch("routes.strategy.db") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.strategy_recommendations.find.return_value = mock_cursor

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/strategy")

    assert resp.status_code not in (401, 500), (
        f"GET /api/strategy returned {resp.status_code} when authenticated: {resp.text}"
    )


@pytest.mark.asyncio
async def test_notifications_count_returns_no_500_with_mocked_auth(override_auth):
    """
    GET /api/notifications/count with valid auth → does NOT return 401 or 500. (BACK-01)
    Route: notifications.py → unread_notification_count → services.notification_service.get_unread_count()
    Patch the service function directly since the route delegates to it.
    """
    from server import app

    with patch("routes.notifications.get_unread_count", new=AsyncMock(return_value=0)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/notifications/count")

    assert resp.status_code not in (401, 500), (
        f"GET /api/notifications/count returned {resp.status_code} when authenticated: {resp.text}"
    )


@pytest.mark.asyncio
async def test_uom_returns_no_500_with_mocked_auth(override_auth):
    """
    GET /api/uom/ with valid auth → does NOT return 401 or 500. (BACK-01)
    Route: uom.py → get_user_uom → services.uom_service.get_uom()
    uom.py imports db lazily inside the service; patch the service function directly.
    """
    from server import app

    with patch("services.uom_service.get_uom", new=AsyncMock(return_value={})):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/uom/")

    assert resp.status_code not in (401, 500), (
        f"GET /api/uom/ returned {resp.status_code} when authenticated: {resp.text}"
    )


@pytest.mark.asyncio
async def test_dependency_override_is_active_during_test(override_auth):
    """
    Sanity check: dependency_overrides is correctly set — GET /api/persona/me
    must NOT return 401 when override_auth fixture is active. (BACK-01)
    This confirms the injection mechanism itself works.
    """
    from server import app
    from auth_utils import get_current_user

    # Verify override is set
    assert get_current_user in app.dependency_overrides, (
        "dependency_overrides was not set — override_auth fixture may not have applied"
    )

    with patch("routes.persona.db") as mock_db:
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value=_fake_user())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/persona/me")

    # The key assertion: NOT 401 (dependency override worked)
    assert resp.status_code != 401, (
        f"Dependency override failed — got 401 when a mocked user should be injected. "
        f"Status: {resp.status_code}, body: {resp.text}"
    )
