"""Admin Authorization and Workspace RBAC Tests for ThookAI.

SEC-06: Verifies that:
- Non-admin users receive 403 on all admin-only routes
- Admin users receive 200 on admin routes with mocked DB data
- Unauthenticated requests to admin routes receive 401
- Workspace role boundaries (viewer/editor/owner) are enforced
- Non-members cannot access workspace resources
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Test users
# ---------------------------------------------------------------------------

REGULAR_USER = {
    "user_id": "user_regular_001",
    "email": "regular@test.com",
    "subscription_tier": "starter",
}

ADMIN_USER = {
    "user_id": "user_admin_001",
    "email": "admin@test.com",
    "role": "admin",
    "subscription_tier": "agency",
}

STUDIO_USER = {
    "user_id": "user_studio_001",
    "email": "studio@test.com",
    "subscription_tier": "studio",
}

AGENCY_USER = {
    "user_id": "user_agency_001",
    "email": "agency@test.com",
    "subscription_tier": "agency",
}

WS_ID = "ws-test-001"
MEMBER_USER_ID = "user_member_001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_mock():
    """Return a fresh MagicMock representing the Motor db object."""
    mock_db = MagicMock()
    return mock_db


def _async_find_one(return_value):
    """Return a coroutine that resolves to *return_value*."""
    return AsyncMock(return_value=return_value)


def _cursor_mock(items=None):
    """Build a mock Motor cursor that supports .to_list() and chaining."""
    if items is None:
        items = []
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    return cursor


# ---------------------------------------------------------------------------
# App factories
# ---------------------------------------------------------------------------


def _make_admin_app():
    """Create minimal FastAPI app with only the admin router.

    Returns (app, get_current_user) so tests can override the auth dependency.
    """
    app = FastAPI()
    # Ensure heavy transitive imports don't break module load
    for stub in ["services.credits", "services.email_service"]:
        if stub not in sys.modules:
            sys.modules[stub] = MagicMock()

    from routes.admin import router as admin_router
    from auth_utils import get_current_user

    app.include_router(admin_router, prefix="/api/admin")
    return app, get_current_user


def _make_agency_app():
    """Create minimal FastAPI app with only the agency router.

    The agency router already declares prefix="/agency" internally.
    Mount under "/api" to replicate the real server layout
    (routes end up at /api/agency/...).
    """
    app = FastAPI()
    for stub in ["services.email_service", "services.credits"]:
        if stub not in sys.modules:
            sys.modules[stub] = MagicMock()

    from routes.agency import router as agency_router
    from auth_utils import get_current_user

    app.include_router(agency_router, prefix="/api")
    return app, get_current_user


# ---------------------------------------------------------------------------
# class TestAdminRouteAuthorization
# ---------------------------------------------------------------------------


class TestAdminRouteAuthorization:
    """SEC-06 — admin-only routes must return 403 for non-admin users.

    Tests:
    1. test_non_admin_user_gets_403_on_stats_overview
    2. test_non_admin_user_gets_403_on_users_list
    3. test_non_admin_user_gets_403_on_user_detail
    4. test_non_admin_user_gets_403_on_change_tier
    5. test_non_admin_user_gets_403_on_grant_credits
    6. test_admin_user_gets_200_on_stats_overview
    7. test_unauthenticated_request_to_admin_returns_401
    """

    def setup_method(self):
        self.app, self.get_current_user = _make_admin_app()

    def _client_as(self, user: dict) -> TestClient:
        """Return a TestClient whose auth dependency is overridden to *user*."""
        self.app.dependency_overrides[self.get_current_user] = lambda: user
        return TestClient(self.app, raise_server_exceptions=False)

    def _unauthenticated_client(self) -> TestClient:
        """Return a TestClient with no auth override."""
        self.app.dependency_overrides.clear()
        return TestClient(self.app, raise_server_exceptions=False)

    # ------------------------------------------------------------------
    # Non-admin user — must get 403 on every admin endpoint
    # ------------------------------------------------------------------

    def test_non_admin_user_gets_403_on_stats_overview(self):
        """Regular user calling GET /api/admin/stats/overview must receive 403."""
        db_mock = _make_db_mock()
        # require_admin does: from database import db; db.users.find_one(...)
        # REGULAR_USER has no "role" key — not admin
        db_mock.users.find_one = _async_find_one(REGULAR_USER)

        # auth_utils imports db lazily inside the function body,
        # so we patch the module attribute on 'database'
        with patch("database.db", db_mock):
            client = self._client_as(REGULAR_USER)
            response = client.get("/api/admin/stats/overview")

        assert response.status_code == 403

    def test_non_admin_user_gets_403_on_users_list(self):
        """Regular user calling GET /api/admin/users must receive 403."""
        db_mock = _make_db_mock()
        db_mock.users.find_one = _async_find_one(REGULAR_USER)

        with patch("database.db", db_mock):
            client = self._client_as(REGULAR_USER)
            response = client.get("/api/admin/users")

        assert response.status_code == 403

    def test_non_admin_user_gets_403_on_user_detail(self):
        """Regular user calling GET /api/admin/users/{id} must receive 403."""
        db_mock = _make_db_mock()
        db_mock.users.find_one = _async_find_one(REGULAR_USER)

        with patch("database.db", db_mock):
            client = self._client_as(REGULAR_USER)
            response = client.get("/api/admin/users/some_user_id")

        assert response.status_code == 403

    def test_non_admin_user_gets_403_on_change_tier(self):
        """Regular user calling POST /api/admin/users/{id}/tier must receive 403.

        The endpoint is @router.post in admin.py — not PUT.
        """
        db_mock = _make_db_mock()
        db_mock.users.find_one = _async_find_one(REGULAR_USER)

        with patch("database.db", db_mock):
            client = self._client_as(REGULAR_USER)
            response = client.post(
                "/api/admin/users/some_user_id/tier",
                json={"tier": "pro"},
            )

        assert response.status_code == 403

    def test_non_admin_user_gets_403_on_grant_credits(self):
        """Regular user calling POST /api/admin/users/{id}/credits must receive 403."""
        db_mock = _make_db_mock()
        db_mock.users.find_one = _async_find_one(REGULAR_USER)

        with patch("database.db", db_mock):
            client = self._client_as(REGULAR_USER)
            response = client.post(
                "/api/admin/users/some_user_id/credits",
                json={"credits": 100, "reason": "test"},
            )

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Admin user — must get 200 on stats endpoint with mocked data
    # ------------------------------------------------------------------

    def test_admin_user_gets_200_on_stats_overview(self):
        """Admin user calling GET /api/admin/stats/overview must receive 200.

        Both auth_utils and routes.admin import db lazily / at module level,
        so we patch 'database.db' and 'routes.admin.db' simultaneously.
        """
        db_mock = _make_db_mock()
        # require_admin: db.users.find_one returns ADMIN_USER (role="admin")
        # stats queries: count_documents and aggregate
        db_mock.users.find_one = _async_find_one(ADMIN_USER)
        db_mock.users.count_documents = AsyncMock(return_value=42)
        db_mock.content_jobs.count_documents = AsyncMock(return_value=100)
        agg_cursor = MagicMock()
        agg_cursor.to_list = AsyncMock(return_value=[{"count": 5}])
        db_mock.content_jobs.aggregate = MagicMock(return_value=agg_cursor)

        # Patch both the lazy-import path (auth_utils) and the module-level import
        with patch("database.db", db_mock), patch("routes.admin.db", db_mock):
            client = self._client_as(ADMIN_USER)
            response = client.get("/api/admin/stats/overview")

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert data["total_users"] == 42

    # ------------------------------------------------------------------
    # Unauthenticated request — must get 401
    # ------------------------------------------------------------------

    def test_unauthenticated_request_to_admin_returns_401(self):
        """Request with no auth token to GET /api/admin/stats/overview must receive 401.

        The default get_current_user dependency raises 401 when no token is provided.
        """
        client = self._unauthenticated_client()
        # No Authorization header or cookie — get_current_user raises 401
        response = client.get("/api/admin/stats/overview")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# class TestWorkspaceRoleEnforcement
# ---------------------------------------------------------------------------


class TestWorkspaceRoleEnforcement:
    """SEC-06 — workspace role boundaries must be enforced.

    Tests:
    1. test_non_member_gets_403_on_workspace_invite
    2. test_viewer_cannot_invite_members
    3. test_owner_can_invite_members
    4. test_non_agency_tier_cannot_create_workspace
    5. test_studio_tier_can_create_workspace
    6. test_non_owner_cannot_change_member_role
    7. test_owner_can_change_member_role
    8. test_non_owner_cannot_remove_member
    """

    WORKSPACE_DOC = {
        "workspace_id": WS_ID,
        "owner_id": "user_owner_001",
        "name": "Test Workspace",
        "description": None,
        "member_count": 2,
        "content_count": 0,
        "settings": {"allow_member_publish": False},
    }

    OWNER_USER = {
        "user_id": "user_owner_001",
        "email": "owner@test.com",
        "subscription_tier": "agency",
    }

    CREATOR_MEMBER_DOC = {
        "workspace_id": WS_ID,
        "user_id": "user_creator_001",
        "email": "creator@test.com",
        "role": "creator",
        "status": "active",
    }

    CREATOR_USER = {
        "user_id": "user_creator_001",
        "email": "creator@test.com",
        "subscription_tier": "studio",
    }

    def setup_method(self):
        self.app, self.get_current_user = _make_agency_app()

    def _client_as(self, user: dict) -> TestClient:
        self.app.dependency_overrides[self.get_current_user] = lambda: user
        return TestClient(self.app, raise_server_exceptions=False)

    # ------------------------------------------------------------------
    # Non-member cannot invite
    # ------------------------------------------------------------------

    def test_non_member_gets_403_on_workspace_invite(self):
        """User not in workspace_members cannot POST invite — must receive 403 or 404."""
        agency_db = _make_db_mock()
        # workspace exists, but owner is someone else
        agency_db.workspaces.find_one = _async_find_one(self.WORKSPACE_DOC)
        # Not a member (find_one returns None)
        agency_db.workspace_members.find_one = _async_find_one(None)

        with patch("routes.agency.db", agency_db):
            client = self._client_as(REGULAR_USER)
            response = client.post(
                f"/api/agency/workspace/{WS_ID}/invite",
                json={"email": "new@example.com", "role": "creator"},
            )

        # Non-member (not owner, not in workspace_members) → 403
        assert response.status_code in (403, 404)

    # ------------------------------------------------------------------
    # Creator (viewer-level) cannot invite
    # ------------------------------------------------------------------

    def test_viewer_cannot_invite_members(self):
        """Workspace creator role cannot POST invite — requires owner/admin/manager."""
        agency_db = _make_db_mock()
        agency_db.workspaces.find_one = _async_find_one(self.WORKSPACE_DOC)
        # Member exists but role is "creator" — not in allowed roles for invite
        agency_db.workspace_members.find_one = _async_find_one(self.CREATOR_MEMBER_DOC)

        with patch("routes.agency.db", agency_db):
            client = self._client_as(self.CREATOR_USER)
            response = client.post(
                f"/api/agency/workspace/{WS_ID}/invite",
                json={"email": "new@example.com", "role": "creator"},
            )

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Owner can invite
    # ------------------------------------------------------------------

    def test_owner_can_invite_members(self):
        """Workspace owner calling POST invite must receive 200."""
        agency_db = _make_db_mock()
        workspace = dict(self.WORKSPACE_DOC)
        workspace["owner_id"] = self.OWNER_USER["user_id"]

        # check_workspace_access: owner match → no workspace_members lookup needed
        agency_db.workspaces.find_one = _async_find_one(workspace)
        # invite_creator: check if invitee already exists (not a member)
        agency_db.workspace_members.find_one = _async_find_one(None)
        agency_db.workspace_members.count_documents = AsyncMock(return_value=1)
        # Get owner for member limit
        agency_db.users.find_one = _async_find_one(self.OWNER_USER)
        # Insert invite
        agency_db.workspace_members.insert_one = AsyncMock(return_value=MagicMock())

        with patch("routes.agency.db", agency_db):
            client = self._client_as(self.OWNER_USER)
            response = client.post(
                f"/api/agency/workspace/{WS_ID}/invite",
                json={"email": "new@example.com", "role": "creator"},
            )

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # Non-agency tier cannot create workspace
    # ------------------------------------------------------------------

    def test_non_agency_tier_cannot_create_workspace(self):
        """User with subscription_tier='starter' calling POST /workspace must receive 403."""
        client = self._client_as(REGULAR_USER)
        response = client.post(
            "/api/agency/workspace",
            json={"name": "My Workspace"},
        )
        # check_agency_tier raises 403 before any DB call
        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Studio tier can create workspace
    # ------------------------------------------------------------------

    def test_studio_tier_can_create_workspace(self):
        """User with subscription_tier='studio' calling POST /workspace must receive 200."""
        agency_db = _make_db_mock()
        agency_db.workspaces.count_documents = AsyncMock(return_value=0)
        agency_db.workspaces.insert_one = AsyncMock(return_value=MagicMock())

        with patch("routes.agency.db", agency_db):
            client = self._client_as(STUDIO_USER)
            response = client.post(
                "/api/agency/workspace",
                json={"name": "Studio Workspace"},
            )

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # Non-owner cannot change member role
    # ------------------------------------------------------------------

    def test_non_owner_cannot_change_member_role(self):
        """Workspace creator-role member cannot PUT role change — requires owner/admin."""
        agency_db = _make_db_mock()
        agency_db.workspaces.find_one = _async_find_one(self.WORKSPACE_DOC)
        # Member is in workspace but role is "creator", not owner/admin
        agency_db.workspace_members.find_one = _async_find_one(self.CREATOR_MEMBER_DOC)

        with patch("routes.agency.db", agency_db):
            client = self._client_as(self.CREATOR_USER)
            response = client.put(
                f"/api/agency/workspace/{WS_ID}/members/{MEMBER_USER_ID}/role",
                json={"role": "manager"},
            )

        # check_workspace_access raises 403 — role "creator" not in ["owner", "admin"]
        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Owner can change member role
    # ------------------------------------------------------------------

    def test_owner_can_change_member_role(self):
        """Workspace owner calling PUT member role must receive 200."""
        agency_db = _make_db_mock()
        workspace = dict(self.WORKSPACE_DOC)
        workspace["owner_id"] = self.OWNER_USER["user_id"]

        # check_workspace_access: owner matches → skip workspace_members lookup
        agency_db.workspaces.find_one = _async_find_one(workspace)
        update_result = MagicMock()
        update_result.modified_count = 1
        agency_db.workspace_members.update_one = AsyncMock(return_value=update_result)

        with patch("routes.agency.db", agency_db):
            client = self._client_as(self.OWNER_USER)
            response = client.put(
                f"/api/agency/workspace/{WS_ID}/members/{MEMBER_USER_ID}/role",
                json={"role": "manager"},
            )

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # Non-owner cannot remove member
    # ------------------------------------------------------------------

    def test_non_owner_cannot_remove_member(self):
        """Workspace creator-role member cannot DELETE another member — requires owner/admin."""
        agency_db = _make_db_mock()
        agency_db.workspaces.find_one = _async_find_one(self.WORKSPACE_DOC)
        # Member is "creator" role — not owner or admin
        agency_db.workspace_members.find_one = _async_find_one(self.CREATOR_MEMBER_DOC)

        with patch("routes.agency.db", agency_db):
            client = self._client_as(self.CREATOR_USER)
            response = client.delete(
                f"/api/agency/workspace/{WS_ID}/members/{MEMBER_USER_ID}"
            )

        # remove_member: role is "creator" (not owner/admin) and
        # member_user_id != current_user["user_id"] → 403
        assert response.status_code == 403
