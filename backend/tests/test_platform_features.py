"""Tests for platform feature endpoints: FEAT-01 through FEAT-05.

Covers:
  FEAT-01 - Content repurposing endpoint
  FEAT-02 - Campaign CRUD
  FEAT-03 - Template marketplace
  FEAT-04 - Content export (single + bulk CSV)
  FEAT-05 - Post history import
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from server import app
from auth_utils import get_current_user

# ---------------------------------------------------------------------------
# Shared auth override
# ---------------------------------------------------------------------------

_TEST_USER = {"user_id": "test-user-feat", "email": "feat@test.com"}


def _override_current_user():
    return _TEST_USER


# ---------------------------------------------------------------------------
# FEAT-01: Repurpose Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRepurposeEndpoints:
    """Tests for POST /api/content/repurpose and GET /api/content/repurpose/preview/{job_id}."""

    async def test_repurpose_success(self):
        """POST /api/content/repurpose calls bulk_repurpose and returns success."""
        mock_result = {
            "success": True,
            "jobs": [
                {"job_id": "rp_1", "platform": "x"},
                {"job_id": "rp_2", "platform": "instagram"},
            ],
        }
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("agents.repurpose.bulk_repurpose", new=AsyncMock(return_value=mock_result)):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/content/repurpose",
                        json={"job_id": "job_123", "target_platforms": ["x", "instagram"]},
                    )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "jobs" in data
            assert len(data["jobs"]) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_repurpose_invalid_platform_returns_400(self):
        """POST /api/content/repurpose with invalid platform returns 400."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/content/repurpose",
                    json={"job_id": "job_123", "target_platforms": ["tiktok", "facebook"]},
                )
            assert response.status_code == 400
            assert "Invalid platforms" in response.json().get("detail", "")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_repurpose_preview_no_jobs_created(self):
        """GET /api/content/repurpose/preview/{job_id} returns preview without creating jobs."""
        mock_job = {
            "job_id": "job_preview_123",
            "user_id": "test-user-feat",
            "platform": "linkedin",
            "status": "approved",
            "final_content": {"text": "Great post about startups"},
        }
        mock_repurpose_result = {
            "success": True,
            "repurposed": {
                "x": {"text": "Startup post adapted for X"},
                "instagram": {"text": "Startup post adapted for Instagram"},
            },
        }
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.repurpose.db") as mock_db:
                mock_db.content_jobs.find_one = AsyncMock(return_value=mock_job)
                mock_db.persona_engines.find_one = AsyncMock(return_value=None)
                with patch(
                    "agents.repurpose.repurpose_content",
                    new=AsyncMock(return_value=mock_repurpose_result),
                ):
                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        response = await client.get(
                            "/api/content/repurpose/preview/job_preview_123?platforms=x,instagram"
                        )
            assert response.status_code == 200
            data = response.json()
            assert data["is_preview"] is True
            assert "repurposed_previews" in data
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# FEAT-02: Campaign Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCampaignEndpoints:
    """Tests for CRUD operations on /api/campaigns."""

    _SAMPLE_CAMPAIGN = {
        "campaign_id": "camp_abc123def456",
        "user_id": "test-user-feat",
        "name": "Q1 Growth Campaign",
        "description": "First quarter content push",
        "platform": "linkedin",
        "status": "active",
        "start_date": None,
        "end_date": None,
        "goal": None,
        "content_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    async def test_create_campaign_success(self):
        """POST /api/campaigns creates campaign with campaign_id starting with 'camp_' and status 'active'."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.campaigns.db") as mock_db:
                mock_db.campaigns.insert_one = AsyncMock(return_value=MagicMock())
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/campaigns",
                        json={"name": "Q1 Growth Campaign", "platform": "linkedin"},
                    )
            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"].startswith("camp_")
            assert data["status"] == "active"
            assert data["name"] == "Q1 Growth Campaign"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_list_campaigns(self):
        """GET /api/campaigns returns list of user's campaigns."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.campaigns.db") as mock_db:
                # Build mock cursor chain
                mock_cursor = MagicMock()
                mock_cursor.sort.return_value = mock_cursor
                mock_cursor.to_list = AsyncMock(return_value=[self._SAMPLE_CAMPAIGN])
                mock_db.campaigns.find.return_value = mock_cursor
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/campaigns")
            assert response.status_code == 200
            data = response.json()
            assert "campaigns" in data
            assert isinstance(data["campaigns"], list)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_get_single_campaign(self):
        """GET /api/campaigns/{id} returns a single campaign."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.campaigns.db") as mock_db:
                mock_db.campaigns.find_one = AsyncMock(return_value=self._SAMPLE_CAMPAIGN)
                mock_content_cursor = MagicMock()
                mock_content_cursor.sort.return_value = mock_content_cursor
                mock_content_cursor.to_list = AsyncMock(return_value=[])
                mock_db.content_jobs.find.return_value = mock_content_cursor
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/campaigns/camp_abc123def456")
            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"] == "camp_abc123def456"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_get_nonexistent_campaign_returns_404(self):
        """GET /api/campaigns/{id} for non-existent campaign returns 404."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.campaigns.db") as mock_db:
                mock_db.campaigns.find_one = AsyncMock(return_value=None)
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/campaigns/camp_nonexistent")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_update_campaign(self):
        """PUT /api/campaigns/{id} updates name/status fields."""
        updated = {**self._SAMPLE_CAMPAIGN, "name": "Updated Campaign Name", "status": "paused"}
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.campaigns.db") as mock_db:
                # First call is _get_campaign_or_404, second is fetching updated
                mock_db.campaigns.find_one = AsyncMock(
                    side_effect=[self._SAMPLE_CAMPAIGN, updated]
                )
                mock_db.campaigns.update_one = AsyncMock(return_value=MagicMock())
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.put(
                        "/api/campaigns/camp_abc123def456",
                        json={"name": "Updated Campaign Name", "status": "paused"},
                    )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Campaign Name"
            assert data["status"] == "paused"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_delete_campaign(self):
        """DELETE /api/campaigns/{id} archives the campaign."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.campaigns.db") as mock_db:
                mock_db.campaigns.find_one = AsyncMock(return_value=self._SAMPLE_CAMPAIGN)
                mock_db.campaigns.update_one = AsyncMock(return_value=MagicMock())
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.delete("/api/campaigns/camp_abc123def456")
            assert response.status_code == 200
            data = response.json()
            assert "archived" in data.get("message", "").lower() or "campaign_id" in data
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_create_campaign_invalid_platform_returns_400(self):
        """POST /api/campaigns with invalid platform returns 400."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/campaigns",
                    json={"name": "Bad Campaign", "platform": "tiktok"},
                )
            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# FEAT-03: Template Marketplace Endpoints
# ---------------------------------------------------------------------------

_SAMPLE_TEMPLATES = [
    {
        "template_id": "tmpl_001",
        "title": "Thought Leadership Hook",
        "category": "thought_leadership",
        "hook_type": "bold_claim",
        "platform": "linkedin",
        "hook": "Most people get this wrong...",
        "structure_preview": "Here is why...\n\nThe real answer is...",
        "upvotes": 42,
        "uses_count": 120,
        "views_count": 500,
        "is_active": True,
        "user_upvoted": False,
    },
    {
        "template_id": "tmpl_002",
        "title": "Storytelling Opener",
        "category": "storytelling",
        "hook_type": "story_opener",
        "platform": "linkedin",
        "hook": "I remember the day...",
        "structure_preview": "It was 2020...\n\nEverything changed...",
        "upvotes": 30,
        "uses_count": 80,
        "views_count": 300,
        "is_active": True,
        "user_upvoted": False,
    },
]


@pytest.mark.asyncio
class TestTemplateEndpoints:
    """Tests for /api/templates list, filter, single, and use-template endpoints."""

    async def test_list_templates(self):
        """GET /api/templates returns list of templates with category and hook_type fields."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.templates.db") as mock_db:
                mock_cursor = MagicMock()
                mock_cursor.sort.return_value = mock_cursor
                mock_cursor.skip.return_value = mock_cursor
                mock_cursor.limit.return_value = mock_cursor
                mock_cursor.to_list = AsyncMock(return_value=_SAMPLE_TEMPLATES)
                mock_db.templates.find.return_value = mock_cursor
                mock_db.templates.count_documents = AsyncMock(return_value=2)
                mock_upvote_cursor = MagicMock()
                mock_upvote_cursor.to_list = AsyncMock(return_value=[])
                mock_db.template_upvotes.find.return_value = mock_upvote_cursor
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/templates")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "templates" in data
            templates = data["templates"]
            assert len(templates) > 0
            assert "category" in templates[0]
            assert "hook_type" in templates[0]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_list_templates_filter_by_category(self):
        """GET /api/templates?category=thought_leadership filters by category."""
        filtered = [t for t in _SAMPLE_TEMPLATES if t["category"] == "thought_leadership"]
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.templates.db") as mock_db:
                mock_cursor = MagicMock()
                mock_cursor.sort.return_value = mock_cursor
                mock_cursor.skip.return_value = mock_cursor
                mock_cursor.limit.return_value = mock_cursor
                mock_cursor.to_list = AsyncMock(return_value=filtered)
                mock_db.templates.find.return_value = mock_cursor
                mock_db.templates.count_documents = AsyncMock(return_value=1)
                mock_upvote_cursor = MagicMock()
                mock_upvote_cursor.to_list = AsyncMock(return_value=[])
                mock_db.template_upvotes.find.return_value = mock_upvote_cursor
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/templates?category=thought_leadership")
            assert response.status_code == 200
            data = response.json()
            # Verify category filter was included in find() call
            call_args = mock_db.templates.find.call_args
            query_arg = call_args[0][0] if call_args[0] else call_args[1].get("filter", {})
            assert query_arg.get("category") == "thought_leadership"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_get_single_template(self):
        """GET /api/templates/{id} returns single template details."""
        sample = _SAMPLE_TEMPLATES[0]
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.templates.db") as mock_db:
                mock_db.templates.find_one = AsyncMock(return_value=sample)
                mock_db.template_upvotes.find_one = AsyncMock(return_value=None)
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/templates/tmpl_001")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "template" in data
            assert data["template"]["template_id"] == "tmpl_001"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_use_template_returns_prefill(self):
        """POST /api/templates/{id}/use returns content suitable for generation form pre-fill."""
        sample = _SAMPLE_TEMPLATES[0]
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.templates.db") as mock_db:
                mock_db.templates.find_one = AsyncMock(return_value=sample)
                mock_db.templates.update_one = AsyncMock(return_value=MagicMock())
                mock_db.template_usage.insert_one = AsyncMock(return_value=MagicMock())
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post("/api/templates/tmpl_001/use", json={})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "prefill" in data
            prefill = data["prefill"]
            assert "platform" in prefill
            assert "raw_input" in prefill
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# FEAT-04: Content Export Endpoints
# ---------------------------------------------------------------------------

_SAMPLE_JOB = {
    "job_id": "test-job-export",
    "user_id": "test-user-feat",
    "platform": "linkedin",
    "content_type": "post",
    "status": "approved",
    "final_content": {"text": "This is the exported post content."},
    "raw_input": "Write about AI trends",
    "was_edited": False,
    "created_at": datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
}


@pytest.mark.asyncio
class TestContentExportEndpoints:
    """Tests for GET /api/content/job/{job_id}/export and GET /api/content/export/bulk."""

    async def test_export_single_job_text(self):
        """GET /api/content/job/{job_id}/export?format=text returns PlainTextResponse."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.content.db") as mock_db:
                mock_db.content_jobs.find_one = AsyncMock(return_value=_SAMPLE_JOB)
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        f"/api/content/job/{_SAMPLE_JOB['job_id']}/export?format=text"
                    )
            assert response.status_code == 200
            assert "text/plain" in response.headers.get("content-type", "")
            content_disposition = response.headers.get("content-disposition", "")
            assert "thookai-test-job-export.txt" in content_disposition
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_export_single_job_json(self):
        """GET /api/content/job/{job_id}/export?format=json returns JSON with Content-Disposition."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.content.db") as mock_db:
                mock_db.content_jobs.find_one = AsyncMock(return_value=_SAMPLE_JOB)
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        f"/api/content/job/{_SAMPLE_JOB['job_id']}/export?format=json"
                    )
            assert response.status_code == 200
            content_disposition = response.headers.get("content-disposition", "")
            assert ".json" in content_disposition
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_export_single_job_not_found(self):
        """GET /api/content/job/nonexistent/export returns 404."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.content.db") as mock_db:
                mock_db.content_jobs.find_one = AsyncMock(return_value=None)
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/content/job/nonexistent/export?format=text")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_bulk_export_csv(self):
        """GET /api/content/export/bulk?format=csv returns CSV StreamingResponse with header row."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.content.db") as mock_db:
                mock_cursor = MagicMock()
                mock_cursor.sort.return_value = mock_cursor
                mock_cursor.to_list = AsyncMock(return_value=[_SAMPLE_JOB])
                mock_db.content_jobs.find.return_value = mock_cursor
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/content/export/bulk?format=csv")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/csv" in content_type
            content_disposition = response.headers.get("content-disposition", "")
            assert "thookai-export.csv" in content_disposition
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_bulk_export_csv_with_date_filter(self):
        """GET /api/content/export/bulk?format=csv&from_date=...&to_date=... applies date filter."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.content.db") as mock_db:
                mock_cursor = MagicMock()
                mock_cursor.sort.return_value = mock_cursor
                mock_cursor.to_list = AsyncMock(return_value=[])
                mock_db.content_jobs.find.return_value = mock_cursor
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/api/content/export/bulk?format=csv&from_date=2025-01-01&to_date=2025-12-31"
                    )
            assert response.status_code == 200
            # Verify the query contained a created_at date filter
            call_args = mock_db.content_jobs.find.call_args
            query_arg = call_args[0][0] if call_args[0] else {}
            assert "created_at" in query_arg
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_bulk_export_csv_empty_returns_header_only(self):
        """GET /api/content/export/bulk for user with no jobs returns CSV with only header row."""
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.content.db") as mock_db:
                mock_cursor = MagicMock()
                mock_cursor.sort.return_value = mock_cursor
                mock_cursor.to_list = AsyncMock(return_value=[])
                mock_db.content_jobs.find.return_value = mock_cursor
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/content/export/bulk?format=csv")
            assert response.status_code == 200
            # Content should only have the header row
            content = response.text
            lines = [l for l in content.strip().split("\n") if l.strip()]
            assert len(lines) == 1  # Only header row
            assert "platform" in lines[0].lower() or "date" in lines[0].lower()
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# FEAT-05: Post History Import
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPostHistoryImport:
    """Tests for POST /api/onboarding/import-history."""

    async def test_import_history_success(self):
        """POST /api/onboarding/import-history calls process_bulk_import with valid posts."""
        mock_result = {"imported": 3, "skipped": 0, "persona_updated": True}
        mock_persona = {"user_id": "test-user-feat", "card": {"archetype": "Educator"}}
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.onboarding.db") as mock_db:
                mock_db.persona_engines.find_one = AsyncMock(return_value=mock_persona)
                with patch(
                    "agents.learning.process_bulk_import",
                    new=AsyncMock(return_value=mock_result),
                ):
                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        response = await client.post(
                            "/api/onboarding/import-history",
                            json={
                                "posts": [
                                    {"content": "Post 1 about startups", "platform": "linkedin"},
                                    {"content": "Post 2 about fundraising", "platform": "x"},
                                    {"content": "Post 3 about product", "platform": "linkedin"},
                                ],
                                "source": "manual",
                            },
                        )
            assert response.status_code == 200
            data = response.json()
            assert data["imported"] == 3
            assert "message" in data
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_import_history_empty_posts_returns_400(self):
        """POST /api/onboarding/import-history with empty posts returns 400."""
        mock_persona = {"user_id": "test-user-feat", "card": {}}
        app.dependency_overrides[get_current_user] = _override_current_user
        try:
            with patch("routes.onboarding.db") as mock_db:
                mock_db.persona_engines.find_one = AsyncMock(return_value=mock_persona)
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/onboarding/import-history",
                        json={"posts": [], "source": "manual"},
                    )
            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_import_history_calls_process_bulk_import_with_correct_user(self):
        """Verify process_bulk_import is called with the authenticated user's user_id."""
        mock_result = {"imported": 2, "skipped": 0, "persona_updated": False}
        mock_persona = {"user_id": "test-user-feat", "card": {}}
        captured_args = {}
        app.dependency_overrides[get_current_user] = _override_current_user

        async def mock_process_bulk_import(user_id, valid_posts, source="manual_paste"):
            captured_args["user_id"] = user_id
            captured_args["valid_posts"] = valid_posts
            return mock_result

        try:
            with patch("routes.onboarding.db") as mock_db:
                mock_db.persona_engines.find_one = AsyncMock(return_value=mock_persona)
                with patch(
                    "agents.learning.process_bulk_import",
                    new=mock_process_bulk_import,
                ):
                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        await client.post(
                            "/api/onboarding/import-history",
                            json={
                                "posts": [
                                    {"content": "Post A", "platform": "linkedin"},
                                    {"content": "Post B", "platform": "x"},
                                ],
                                "source": "manual",
                            },
                        )
            assert captured_args.get("user_id") == "test-user-feat"
            assert len(captured_args.get("valid_posts", [])) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)
