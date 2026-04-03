"""
Tests for FEAT-06 through FEAT-09:
  FEAT-06 — Persona Sharing (share tokens, public view)
  FEAT-07 — Viral Card (post analysis, shareable card generation)
  FEAT-08 — SSE Notifications (list, mark-read, count, stream)
  FEAT-09 — Outbound Webhooks (CRUD, test ping, supported events)
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from server import app
from auth_utils import get_current_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_mock():
    """Return a MagicMock that satisfies the Motor collection accessor pattern."""
    mock = MagicMock()
    # Any attribute access returns another MagicMock whose async methods are AsyncMock
    for coll_name in (
        "persona_engines",
        "persona_shares",
        "users",
        "viral_cards",
        "notifications",
        "webhook_endpoints",
    ):
        coll = MagicMock()
        coll.find_one = AsyncMock()
        coll.insert_one = AsyncMock()
        coll.update_one = AsyncMock()
        coll.update_many = AsyncMock()
        coll.delete_one = AsyncMock()
        coll.count_documents = AsyncMock()

        # find().sort().limit().to_list() chain
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        cursor.to_list = AsyncMock(return_value=[])
        coll.find = MagicMock(return_value=cursor)

        setattr(mock, coll_name, coll)
    return mock


# ===========================================================================
# FEAT-06 — Persona Sharing
# ===========================================================================

@pytest.mark.asyncio
class TestPersonaSharing:
    """Tests for POST /api/persona/share and GET /api/persona/public/{token}."""

    async def test_create_share_returns_token_and_url(self):
        """Authenticated user with persona gets a share_token and share_url."""
        mock_db = _make_db_mock()

        persona_doc = {
            "user_id": "test-share-user",
            "card": {"personality_archetype": "Builder", "writing_voice_descriptor": "Authentic"},
            "voice_fingerprint": {},
        }
        user_doc = {"user_id": "test-share-user", "subscription_tier": "pro"}

        mock_db.persona_engines.find_one = AsyncMock(return_value=persona_doc)
        mock_db.persona_shares.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value=user_doc)
        mock_db.persona_shares.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id"))

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-share-user"}

        try:
            with patch("routes.persona.db", mock_db):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/persona/share", json={"expiry_days": 30}
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "share_token" in data
        assert "share_url" in data
        assert "/creator/" in data["share_url"]

    async def test_create_share_no_persona_returns_404(self):
        """User without a persona gets 404."""
        mock_db = _make_db_mock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-share-user"}

        try:
            with patch("routes.persona.db", mock_db):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/persona/share", json={"expiry_days": 30}
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 404
        assert "Persona not found" in resp.json()["detail"]

    async def test_create_share_existing_returns_same_token(self):
        """If an active share already exists, return the existing token."""
        from datetime import datetime, timezone, timedelta

        mock_db = _make_db_mock()

        persona_doc = {
            "user_id": "test-share-user",
            "card": {},
            "voice_fingerprint": {},
        }
        existing_share = {
            "share_id": "existing-id",
            "share_token": "existing-token-abc",
            "user_id": "test-share-user",
            "is_active": True,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=10),
            "created_at": datetime.now(timezone.utc),
        }

        mock_db.persona_engines.find_one = AsyncMock(return_value=persona_doc)
        mock_db.persona_shares.find_one = AsyncMock(return_value=existing_share)

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-share-user"}

        try:
            with patch("routes.persona.db", mock_db):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/persona/share", json={"expiry_days": 30}
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["share_token"] == "existing-token-abc"

    async def test_get_public_persona_returns_card(self):
        """GET /api/persona/public/{token} returns persona card without auth."""
        from datetime import datetime, timezone, timedelta

        mock_db = _make_db_mock()

        share_doc = {
            "share_token": "valid-token-123",
            "user_id": "creator-user",
            "is_active": True,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=10),
            "created_at": datetime.now(timezone.utc),
            "view_count": 5,
        }
        persona_doc = {
            "user_id": "creator-user",
            "card": {
                "personality_archetype": "Builder",
                "writing_voice_descriptor": "Direct Innovator",
                "content_pillars": ["Tech", "Leadership"],
                "focus_platforms": ["linkedin"],
            },
            "voice_fingerprint": {
                "vocabulary_complexity": 0.72,
                "emoji_frequency": 0.03,
                "hook_style_preferences": ["Question"],
            },
        }
        user_doc = {"user_id": "creator-user", "name": "Test Creator"}

        # find_one is called multiple times: first for share, then for update, then for persona, then for user
        mock_db.persona_shares.find_one = AsyncMock(return_value=share_doc)
        mock_db.persona_shares.update_one = AsyncMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona_doc)
        mock_db.users.find_one = AsyncMock(return_value=user_doc)

        with patch("routes.persona.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/persona/public/valid-token-123")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "card" in data
        assert data["card"]["personality_archetype"] == "Builder"

    async def test_get_public_persona_invalid_token_returns_404(self):
        """Invalid share token returns 404."""
        mock_db = _make_db_mock()
        mock_db.persona_shares.find_one = AsyncMock(return_value=None)

        with patch("routes.persona.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/persona/public/bad-token-xyz")

        assert resp.status_code == 404


# ===========================================================================
# FEAT-07 — Viral Card
# ===========================================================================

@pytest.mark.asyncio
class TestViralCard:
    """Tests for POST /api/viral-card/analyze and GET /api/viral-card/{card_id}."""

    def _make_llm_mock(self):
        """Return a patched LlmChat that returns a valid card JSON string."""
        card_json = json.dumps({
            "writing_voice_descriptor": "Bold Strategist",
            "content_niche_signature": "Tech Leadership Insights",
            "personality_archetype": "Builder",
            "tone": "Professional yet direct",
            "hook_style": "Bold claim",
            "top_content_format": "Thought leadership posts",
            "content_pillars": ["Tech", "Leadership", "Innovation"],
            "strengths": ["Clarity", "Authority", "Depth"],
            "voice_metrics": {
                "sentence_rhythm": 70,
                "vocabulary_depth": 80,
                "emoji_usage": 10,
                "hook_strength": 75,
                "cta_clarity": 65,
            },
            "audience_vibe": "Tech founders and senior engineers",
        })

        mock_chat_instance = MagicMock()
        mock_chat_instance.with_model = MagicMock(return_value=mock_chat_instance)
        mock_chat_instance.send_message = AsyncMock(return_value=card_json)

        mock_llm_class = MagicMock(return_value=mock_chat_instance)
        return mock_llm_class

    async def test_analyze_returns_card_with_id_and_share_url(self):
        """Valid posts_text (150+ chars) returns card_id starting with 'vc_' and share_url."""
        mock_db = _make_db_mock()
        mock_db.viral_cards.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id"))

        llm_mock = self._make_llm_mock()

        with patch("database.db", mock_db), \
             patch("routes.viral_card.db", mock_db), \
             patch("services.llm_client.LlmChat", llm_mock), \
             patch("services.llm_keys.anthropic_available", return_value=True), \
             patch("services.llm_keys.chat_constructor_key", return_value="fake-key"):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/viral-card/analyze",
                    json={"posts_text": "A" * 150, "platform": "linkedin"},
                )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "card_id" in data
        assert data["card_id"].startswith("vc_")
        assert "share_url" in data
        assert "/discover/" in data["share_url"]

    async def test_analyze_short_text_returns_400(self):
        """Less than 100 chars of posts_text returns 400."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/viral-card/analyze",
                json={"posts_text": "short", "platform": "linkedin"},
            )

        assert resp.status_code == 400
        assert "100 characters" in resp.json()["detail"].lower() or "at least" in resp.json()["detail"].lower()

    async def test_analyze_invalid_platform_returns_400(self):
        """Invalid platform value returns 400."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/viral-card/analyze",
                json={"posts_text": "A" * 150, "platform": "tiktok"},
            )

        assert resp.status_code == 400

    async def test_get_viral_card_returns_saved_card(self):
        """GET /api/viral-card/{card_id} returns a previously generated card."""
        mock_db = _make_db_mock()

        card_doc = {
            "card_id": "vc_abc123",
            "card": {"personality_archetype": "Educator", "writing_voice_descriptor": "Warm Teacher"},
            "name": "TestUser",
            "platform": "linkedin",
            "posts_preview": "Sample post content...",
        }
        mock_db.viral_cards.find_one = AsyncMock(return_value=card_doc)

        # viral_card.py binds db at import time via 'from database import db'
        # so we must patch the module-level name 'routes.viral_card.db'
        with patch("routes.viral_card.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/viral-card/vc_abc123")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["card_id"] == "vc_abc123"

    async def test_get_viral_card_nonexistent_returns_404(self):
        """Non-existent card_id returns 404."""
        mock_db = _make_db_mock()
        mock_db.viral_cards.find_one = AsyncMock(return_value=None)

        with patch("routes.viral_card.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/viral-card/nonexistent")

        assert resp.status_code == 404


# ===========================================================================
# FEAT-08 — SSE Notifications
# ===========================================================================

@pytest.mark.asyncio
class TestSSENotifications:
    """Tests for /api/notifications endpoints."""

    _NOTIF_LIST = [
        {
            "notification_id": "n1",
            "type": "job_completed",
            "message": "Content ready",
            "read": False,
            "created_at": "2025-06-01T00:00:00Z",
        }
    ]

    async def test_list_notifications_returns_list_and_count(self):
        """GET /api/notifications returns notifications list and count."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-notif-user"}

        try:
            # routes/notifications.py does 'from services.notification_service import get_notifications'
            # so we must patch the name as it lives in routes.notifications
            with patch(
                "routes.notifications.get_notifications",
                AsyncMock(return_value=self._NOTIF_LIST),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.get("/api/notifications")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "notifications" in data
        assert "count" in data
        assert data["count"] == 1

    async def test_mark_notification_read(self):
        """POST /api/notifications/{id}/read returns success message."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-notif-user"}

        try:
            with patch(
                "routes.notifications.mark_read",
                AsyncMock(return_value=True),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post("/api/notifications/n1/read")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "read" in data.get("message", "").lower() or "marked" in data.get("message", "").lower()

    async def test_mark_all_notifications_read(self):
        """POST /api/notifications/read-all returns updated count."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-notif-user"}

        try:
            with patch(
                "routes.notifications.mark_all_read",
                AsyncMock(return_value=5),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post("/api/notifications/read-all")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "updated" in data
        assert data["updated"] == 5

    async def test_get_unread_count(self):
        """GET /api/notifications/count returns unread_count integer."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-notif-user"}

        try:
            with patch(
                "routes.notifications.get_unread_count",
                AsyncMock(return_value=3),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.get("/api/notifications/count")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "unread_count" in data
        assert data["unread_count"] == 3

    async def test_sse_stream_returns_text_event_stream(self):
        """GET /api/notifications/stream responds with Content-Type text/event-stream."""
        import asyncio

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-notif-user"}

        # The SSE generator polls every 10 s by default — we mock it to yield one
        # heartbeat then stop so the test completes without hanging.
        async def _fast_generator(user_id: str, request):
            yield ": heartbeat\n\n"

        try:
            with patch("routes.notifications._sse_event_generator", _fast_generator):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    async with client.stream("GET", "/api/notifications/stream") as resp:
                        assert resp.status_code == 200
                        content_type = resp.headers.get("content-type", "")
                        assert "text/event-stream" in content_type
                        # Read one chunk to allow generator to advance, then exit.
                        async for chunk in resp.aiter_bytes():
                            break
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ===========================================================================
# FEAT-09 — Outbound Webhooks
# ===========================================================================

@pytest.mark.asyncio
class TestOutboundWebhooks:
    """Tests for /api/webhooks endpoints."""

    _WEBHOOK_DOC = {
        "webhook_id": "wh_123",
        "url": "https://example.com/hook",
        "events": ["job.completed"],
        "secret": "whsec_test123",
        "created_at": "2025-06-01T00:00:00Z",
    }

    async def test_create_webhook_returns_id_and_secret(self):
        """POST /api/webhooks creates webhook and returns webhook_id and secret."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-webhook-user"}

        try:
            # routes/webhooks.py does 'from services.webhook_service import register_webhook'
            # so patch the name as it lives in routes.webhooks
            with patch(
                "routes.webhooks.register_webhook",
                AsyncMock(return_value=self._WEBHOOK_DOC),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/webhooks",
                        json={
                            "url": "https://example.com/hook",
                            "events": ["job.completed"],
                        },
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "webhook_id" in data
        assert "secret" in data

    async def test_list_webhooks_returns_webhooks_list(self):
        """GET /api/webhooks returns list of user's webhooks."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-webhook-user"}

        try:
            with patch(
                "routes.webhooks.list_webhooks",
                AsyncMock(return_value=[self._WEBHOOK_DOC]),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.get("/api/webhooks")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "webhooks" in data
        assert isinstance(data["webhooks"], list)

    async def test_delete_webhook_returns_deleted_true(self):
        """DELETE /api/webhooks/{id} returns deleted: True."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-webhook-user"}

        try:
            with patch(
                "routes.webhooks.delete_webhook",
                AsyncMock(return_value=True),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.delete("/api/webhooks/wh_123")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("deleted") is True

    async def test_test_webhook_returns_success(self):
        """POST /api/webhooks/{id}/test returns success: True."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-webhook-user"}

        try:
            with patch(
                "routes.webhooks.test_webhook",
                AsyncMock(return_value={"success": True, "status_code": 200}),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post("/api/webhooks/wh_123/test")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("success") is True

    async def test_get_supported_events_includes_job_completed(self):
        """GET /api/webhooks/events returns list containing 'job.completed' event."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/webhooks/events")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "events" in data
        event_names = [e["name"] for e in data["events"]]
        assert "job.completed" in event_names
