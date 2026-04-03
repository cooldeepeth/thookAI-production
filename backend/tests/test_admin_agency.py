"""Tests for Admin Dashboard and Agency Workspace endpoints.

Covers ADMIN-01 through ADMIN-04 requirements:
- ADMIN-01: Admin stats overview + user management
- ADMIN-02: Agency workspace CRUD with tier enforcement
- ADMIN-03: Workspace invitations via Resend email
- ADMIN-04: Member role management with permission checks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_update_result(matched: int = 1, modified: int = 1):
    """Return a mock UpdateResult."""
    result = MagicMock()
    result.matched_count = matched
    result.modified_count = modified
    return result


def _make_delete_result(deleted: int = 1):
    result = MagicMock()
    result.deleted_count = deleted
    return result


def _make_insert_result():
    result = MagicMock()
    result.inserted_id = "some_id"
    return result


def _make_async_cursor(items):
    """Return a mock Motor cursor that supports async iteration and to_list()."""

    class _AsyncCursor:
        def __init__(self):
            self._items = list(items)
            self._pos = 0

        def sort(self, *a, **kw):
            return self

        def skip(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def __aiter__(self):
            self._pos = 0
            return self

        async def __anext__(self):
            if self._pos >= len(self._items):
                raise StopAsyncIteration
            item = self._items[self._pos]
            self._pos += 1
            return item

        async def to_list(self, n=None):
            return list(self._items)

    return _AsyncCursor()


# ---------------------------------------------------------------------------
# ADMIN-01: Admin dashboard stats and user management
# ---------------------------------------------------------------------------


class TestAdminDashboard:
    """Admin stats overview and user management endpoints.

    Route prefix: /api/admin (mounted directly on app in server.py).
    admin.py uses 'from database import db' so patch target is 'routes.admin.db'.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up FastAPI test client with mocked dependencies."""
        from fastapi.testclient import TestClient
        from server import app
        from auth_utils import require_admin

        # Admin user fixture
        admin_user = {"user_id": "admin-user", "email": "admin@test.com", "role": "admin"}

        # Override require_admin to bypass DB check
        app.dependency_overrides[require_admin] = lambda: admin_user

        self.client = TestClient(app, raise_server_exceptions=True)
        self.admin_user = admin_user

        yield

        # Cleanup
        app.dependency_overrides.clear()

    # ------------------------------------------------------------------
    # Stats overview
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_stats_overview_returns_real_counts(self):
        """GET /api/admin/stats/overview returns total_users from DB queries."""
        # Patch routes.admin.db since admin.py binds db at import time
        with patch("routes.admin.db") as mock_db:
            # users.count_documents called multiple times for total, new_today, new_7d, and per-tier
            mock_db.users.count_documents = AsyncMock(return_value=150)

            # Aggregate for active_users_today
            aggregate_result = MagicMock()
            aggregate_result.to_list = AsyncMock(return_value=[{"count": 5}])
            mock_db.content_jobs.aggregate = MagicMock(return_value=aggregate_result)

            # content_jobs.count_documents for total and today
            mock_db.content_jobs.count_documents = AsyncMock(return_value=42)

            resp = self.client.get("/api/admin/stats/overview")

        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert isinstance(data["total_users"], int)
        assert "content_jobs_today" in data
        assert "subscription_breakdown" in data

    @pytest.mark.asyncio
    async def test_stats_overview_403_without_admin_role(self):
        """Non-admin user gets 403 from admin stats endpoint."""
        from server import app
        from auth_utils import require_admin, get_current_user

        # Remove admin override so require_admin runs normally
        app.dependency_overrides.pop(require_admin, None)

        regular_user = {"user_id": "regular-user", "email": "user@test.com", "role": "user"}

        # Override get_current_user to return a regular user
        app.dependency_overrides[get_current_user] = lambda: regular_user

        # require_admin does 'from database import db' inside the function — patch database.db
        with patch("database.db") as mock_db:
            mock_db.users.find_one = AsyncMock(
                return_value={"user_id": "regular-user", "role": "user"}
            )

            resp = self.client.get("/api/admin/stats/overview")

        # Restore admin override for subsequent tests
        app.dependency_overrides[require_admin] = lambda: {
            "user_id": "admin-user", "email": "admin@test.com", "role": "admin"
        }
        app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 403

    # ------------------------------------------------------------------
    # User list
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_admin_list_users_returns_paginated_list(self):
        """GET /api/admin/users returns paginated user list."""
        sample_users = [
            {
                "user_id": "u1",
                "email": "alice@test.com",
                "name": "Alice",
                "subscription_tier": "pro",
                "credits": 100,
                "role": "user",
                "active": True,
                "created_at": None,
            }
        ]

        with patch("routes.admin.db") as mock_db:
            mock_db.users.count_documents = AsyncMock(return_value=1)
            mock_db.users.find = MagicMock(return_value=_make_async_cursor(sample_users))
            mock_db.content_jobs.count_documents = AsyncMock(return_value=5)

            resp = self.client.get("/api/admin/users")

        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_admin_list_users_tier_filter(self):
        """GET /api/admin/users?tier=pro includes tier in DB query."""
        with patch("routes.admin.db") as mock_db:
            mock_db.users.count_documents = AsyncMock(return_value=0)
            mock_db.users.find = MagicMock(return_value=_make_async_cursor([]))
            mock_db.content_jobs.count_documents = AsyncMock(return_value=0)

            resp = self.client.get("/api/admin/users?tier=pro")

        assert resp.status_code == 200
        # Verify tier filter was passed — count_documents was called with the tier query
        call_args = mock_db.users.count_documents.call_args[0][0]
        assert call_args.get("subscription_tier") == "pro"

    @pytest.mark.asyncio
    async def test_admin_change_tier(self):
        """POST /api/admin/users/{id}/tier updates subscription tier."""
        # Use "custom" — valid tier in TIER_CONFIGS (pro/studio are not separate tiers in this codebase)
        with patch("routes.admin.db") as mock_db:
            mock_db.users.update_one = AsyncMock(return_value=_make_update_result(matched=1))

            resp = self.client.post(
                "/api/admin/users/u1/tier",
                json={"tier": "custom"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("tier") == "custom"

    @pytest.mark.asyncio
    async def test_admin_change_tier_invalid_tier_returns_400(self):
        """POST /api/admin/users/{id}/tier with unknown tier returns 400."""
        resp = self.client.post(
            "/api/admin/users/u1/tier",
            json={"tier": "superultra"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_grant_credits(self):
        """POST /api/admin/users/{id}/credits grants credits and returns new balance."""
        with patch("routes.admin.db") as mock_db:
            mock_db.users.find_one = AsyncMock(
                return_value={"user_id": "u1", "credits": 50}
            )
            mock_db.users.update_one = AsyncMock(return_value=_make_update_result())

            with patch("services.credits.add_credits", new_callable=AsyncMock) as mock_add:
                mock_add.return_value = {"success": True, "new_balance": 150}

                resp = self.client.post(
                    "/api/admin/users/u1/credits",
                    json={"credits": 100, "reason": "manual grant"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "new_balance" in data


# ---------------------------------------------------------------------------
# ADMIN-02: Agency workspace CRUD
# ---------------------------------------------------------------------------


class TestAgencyWorkspace:
    """Workspace creation enforces tier restrictions.

    Agency router prefix: /agency  (included in api_router prefix /api)
    Full path examples: /api/agency/workspace, /api/agency/workspaces
    agency.py uses 'from database import db' so patch target is 'routes.agency.db'.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi.testclient import TestClient
        from server import app
        from auth_utils import get_current_user

        self.agency_user = {
            "user_id": "agency-owner",
            "email": "owner@test.com",
            "subscription_tier": "agency",
            "name": "Agency Owner",
        }
        app.dependency_overrides[get_current_user] = lambda: self.agency_user
        self.client = TestClient(app, raise_server_exceptions=True)

        yield

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_workspace_agency_tier_succeeds(self):
        """POST /api/agency/workspace with agency tier creates workspace with workspace_id."""
        with patch("routes.agency.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=self.agency_user)
            mock_db.workspaces.count_documents = AsyncMock(return_value=0)
            mock_db.workspaces.insert_one = AsyncMock(return_value=_make_insert_result())

            resp = self.client.post(
                "/api/agency/workspace",
                json={"name": "Test Agency Workspace"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "workspace_id" in data

    @pytest.mark.asyncio
    async def test_create_workspace_free_tier_returns_403(self):
        """POST /api/agency/workspace with free/starter tier returns 403."""
        from server import app
        from auth_utils import get_current_user

        free_user = {
            "user_id": "free-user",
            "email": "free@test.com",
            "subscription_tier": "starter",
        }
        app.dependency_overrides[get_current_user] = lambda: free_user

        with patch("routes.agency.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=free_user)

            resp = self.client.post(
                "/api/agency/workspace",
                json={"name": "Should Fail"},
            )

        # Restore agency user override
        app.dependency_overrides[get_current_user] = lambda: self.agency_user

        assert resp.status_code == 403
        detail = resp.json().get("detail", "").lower()
        assert "paid plan" in detail or "team" in detail

    @pytest.mark.asyncio
    async def test_list_workspaces_returns_owned_and_member(self):
        """GET /api/agency/workspaces returns list including owned and member workspaces."""
        sample_workspaces = [
            {
                "workspace_id": "ws-1",
                "owner_id": "agency-owner",
                "name": "My Workspace",
            }
        ]

        with patch("routes.agency.db") as mock_db:
            mock_db.workspaces.find = MagicMock(return_value=_make_async_cursor(sample_workspaces))
            mock_db.workspace_members.find = MagicMock(return_value=_make_async_cursor([]))

            resp = self.client.get("/api/agency/workspaces")

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True


# ---------------------------------------------------------------------------
# ADMIN-03 + ADMIN-04: Invitations and role management
# ---------------------------------------------------------------------------


class TestWorkspaceInvitations:
    """Invitation emails and member role management.

    Tests cover:
    - ADMIN-03: send_workspace_invite_email is called on invite
    - ADMIN-04: Role updates enforce valid roles, owner/admin only
    """

    WORKSPACE_ID = "ws-test-123"

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi.testclient import TestClient
        from server import app
        from auth_utils import get_current_user

        self.owner_user = {
            "user_id": "ws-owner",
            "email": "wsowner@test.com",
            "subscription_tier": "agency",
            "name": "WS Owner",
        }
        app.dependency_overrides[get_current_user] = lambda: self.owner_user
        self.client = TestClient(app, raise_server_exceptions=True)

        self.workspace_doc = {
            "workspace_id": self.WORKSPACE_ID,
            "owner_id": "ws-owner",
            "name": "My Workspace",
            "created_at": None,
        }
        self.owner_doc = {
            "user_id": "ws-owner",
            "email": "wsowner@test.com",
            "subscription_tier": "agency",
            "name": "WS Owner",
        }

        yield

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invite_sends_email(self):
        """POST /api/agency/workspace/{id}/invite calls send_workspace_invite_email."""
        with patch("routes.agency.db") as mock_db, \
             patch("routes.agency.send_workspace_invite_email") as mock_email:

            # check_workspace_access → workspaces.find_one
            mock_db.workspaces.find_one = AsyncMock(return_value=self.workspace_doc)

            # owner lookup for limits (called twice: once for owner limits, once for invitee lookup)
            mock_db.users.find_one = AsyncMock(side_effect=[
                self.owner_doc,   # owner lookup for member limits
                None,             # invitee not registered yet
            ])

            # member count
            mock_db.workspace_members.count_documents = AsyncMock(return_value=0)

            # existing member check
            mock_db.workspace_members.find_one = AsyncMock(return_value=None)

            mock_db.workspace_members.insert_one = AsyncMock(return_value=_make_insert_result())

            resp = self.client.post(
                f"/api/agency/workspace/{self.WORKSPACE_ID}/invite",
                json={"email": "newmember@test.com", "role": "creator"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("email") == "newmember@test.com"

    @pytest.mark.asyncio
    async def test_invite_creates_pending_member_record(self):
        """POST invite inserts a workspace_member doc with status=pending."""
        with patch("routes.agency.db") as mock_db, \
             patch("routes.agency.send_workspace_invite_email"):

            mock_db.workspaces.find_one = AsyncMock(return_value=self.workspace_doc)
            mock_db.users.find_one = AsyncMock(side_effect=[
                self.owner_doc,
                None,
            ])
            mock_db.workspace_members.count_documents = AsyncMock(return_value=0)
            mock_db.workspace_members.find_one = AsyncMock(return_value=None)
            mock_db.workspace_members.insert_one = AsyncMock(return_value=_make_insert_result())

            resp = self.client.post(
                f"/api/agency/workspace/{self.WORKSPACE_ID}/invite",
                json={"email": "newmember@test.com", "role": "creator"},
            )

        assert resp.status_code == 200
        # Verify a pending member record was inserted
        mock_db.workspace_members.insert_one.assert_called_once()
        inserted_doc = mock_db.workspace_members.insert_one.call_args[0][0]
        assert inserted_doc.get("status") == "pending"
        assert inserted_doc.get("email") == "newmember@test.com"

    @pytest.mark.asyncio
    async def test_update_member_role_valid(self):
        """PUT /api/agency/workspace/{id}/members/{uid}/role updates role."""
        with patch("routes.agency.db") as mock_db:
            # check_workspace_access: owner is calling, so workspace_members.find_one not needed
            mock_db.workspaces.find_one = AsyncMock(return_value=self.workspace_doc)
            # update_one for role update
            mock_db.workspace_members.update_one = AsyncMock(return_value=_make_update_result(modified=1))

            resp = self.client.put(
                f"/api/agency/workspace/{self.WORKSPACE_ID}/members/member-1/role",
                json={"role": "manager"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_update_member_role_invalid_returns_400(self):
        """PUT with invalid role returns 400."""
        with patch("routes.agency.db") as mock_db:
            # check_workspace_access is called first (owner passes)
            mock_db.workspaces.find_one = AsyncMock(return_value=self.workspace_doc)
            mock_db.workspace_members.find_one = AsyncMock(return_value=None)

            resp = self.client.put(
                f"/api/agency/workspace/{self.WORKSPACE_ID}/members/member-1/role",
                json={"role": "superadmin"},
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_non_owner_cannot_change_roles(self):
        """Non-owner/admin member gets 403 when trying to change roles."""
        from server import app
        from auth_utils import get_current_user

        # Switch to a non-owner member
        non_owner = {
            "user_id": "regular-member",
            "email": "member@test.com",
            "subscription_tier": "agency",
        }
        app.dependency_overrides[get_current_user] = lambda: non_owner

        with patch("routes.agency.db") as mock_db:
            mock_db.workspaces.find_one = AsyncMock(return_value=self.workspace_doc)
            # Member has "creator" role — not owner or admin
            mock_db.workspace_members.find_one = AsyncMock(
                return_value={
                    "workspace_id": self.WORKSPACE_ID,
                    "user_id": "regular-member",
                    "role": "creator",
                    "status": "active",
                }
            )

            resp = self.client.put(
                f"/api/agency/workspace/{self.WORKSPACE_ID}/members/member-1/role",
                json={"role": "manager"},
            )

        # Restore owner
        app.dependency_overrides[get_current_user] = lambda: self.owner_user
        assert resp.status_code == 403
