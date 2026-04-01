"""
Tests for backend/routes/strategy.py (Phase 14, Plan 01).

Covers DASH-05 and DASH-02 requirements:
  TestGetStrategyFeed          — DASH-05: GET /api/strategy feed with filter/limit/auth
  TestApproveCard              — DASH-05 + DASH-02: POST approve returns generate_payload
  TestDismissCard              — DASH-05: POST dismiss returns suppression info
  TestGeneratePayloadShape     — DASH-02: generate_payload has all ContentCreateRequest fields

All external dependencies (db, handle_approval, handle_dismissal) are mocked.
asyncio_mode=auto (pytest.ini) means no @pytest.mark.asyncio decorator needed.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from server import app
from auth_utils import get_current_user


# ---------------------------------------------------------------------------
# Shared test fixtures and constants
# ---------------------------------------------------------------------------

_TEST_USER = {"user_id": "test_user_strat", "email": "test@example.com"}

SAMPLE_CARD = {
    "recommendation_id": "strat_abc123",
    "user_id": "test_user_strat",
    "status": "pending_approval",
    "topic": "ai in content creation",
    "hook_options": ["Hook A", "Hook B", "Hook C"],
    "platform": "linkedin",
    "why_now": "Why now: Your last 3 posts on AI averaged 2x engagement",
    "signal_source": "performance",
    "generate_payload": {
        "platform": "linkedin",
        "content_type": "post",
        "raw_input": "Write about AI in content creation using contrarian hook",
    },
    "created_at": datetime(2026, 3, 28, 10, 0, 0, tzinfo=timezone.utc),
    "dismissed_at": None,
    "expires_at": None,
    "approved_at": None,
}

SAMPLE_CARD_2 = {
    "recommendation_id": "strat_def456",
    "user_id": "test_user_strat",
    "status": "pending_approval",
    "topic": "founder storytelling",
    "hook_options": ["Hook X"],
    "platform": "x",
    "why_now": "Why now: Founder stories get 3x more saves",
    "signal_source": "trending",
    "generate_payload": {
        "platform": "x",
        "content_type": "thread",
        "raw_input": "Write about founder storytelling",
    },
    "created_at": datetime(2026, 3, 29, 8, 0, 0, tzinfo=timezone.utc),
    "dismissed_at": None,
    "expires_at": None,
    "approved_at": None,
}


def _make_cursor_mock(docs):
    """Return a mock Motor cursor supporting .sort().limit().to_list()."""
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=list(docs))
    return cursor


# ---------------------------------------------------------------------------
# TestGetStrategyFeed — DASH-05
# ---------------------------------------------------------------------------


class TestGetStrategyFeed:
    """GET /api/strategy — strategy feed endpoint."""

    def setup_method(self):
        """Override auth dependency before each test."""
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        """Remove auth override after each test."""
        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_returns_pending_approval_cards_for_user(self):
        """Returns 2 sample pending_approval cards with required fields."""
        mock_db = MagicMock()
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_cursor_mock([dict(SAMPLE_CARD), dict(SAMPLE_CARD_2)])
        )

        with patch("routes.strategy.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/strategy")

        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert len(body["cards"]) == 2
        # Each card must have the required fields
        for card in body["cards"]:
            assert "recommendation_id" in card
            assert "topic" in card
            assert "why_now" in card
            assert "platform" in card
            assert "generate_payload" in card

    @pytest.mark.asyncio
    async def test_filters_by_status_parameter(self):
        """DB query filter includes the requested status value."""
        mock_db = MagicMock()
        cursor = _make_cursor_mock([])
        mock_db.strategy_recommendations.find = MagicMock(return_value=cursor)

        with patch("routes.strategy.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/strategy?status=dismissed")

        assert resp.status_code == 200
        # Verify the filter passed to .find() includes status=dismissed
        call_args = mock_db.strategy_recommendations.find.call_args
        filter_arg = call_args[0][0]
        assert filter_arg.get("status") == "dismissed"
        assert filter_arg.get("user_id") == "test_user_strat"

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self):
        """DB query .limit() is called with the requested limit value."""
        mock_db = MagicMock()
        cursor = _make_cursor_mock([])
        mock_db.strategy_recommendations.find = MagicMock(return_value=cursor)

        with patch("routes.strategy.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/strategy?limit=3")

        assert resp.status_code == 200
        cursor.limit.assert_called_once_with(3)

    @pytest.mark.asyncio
    async def test_serializes_datetime_fields(self):
        """Datetime objects in card fields are serialized to ISO-format strings."""
        card_with_datetimes = dict(SAMPLE_CARD)
        card_with_datetimes["created_at"] = datetime(
            2026, 3, 28, 10, 0, 0, tzinfo=timezone.utc
        )
        card_with_datetimes["dismissed_at"] = datetime(
            2026, 3, 30, 14, 0, 0, tzinfo=timezone.utc
        )

        mock_db = MagicMock()
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_cursor_mock([card_with_datetimes])
        )

        with patch("routes.strategy.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/strategy")

        assert resp.status_code == 200
        card = resp.json()["cards"][0]
        # Must be strings, not datetime objects (which are not JSON-serializable)
        assert isinstance(card["created_at"], str)
        assert isinstance(card["dismissed_at"], str)
        # Should be parseable ISO format
        datetime.fromisoformat(card["created_at"])
        datetime.fromisoformat(card["dismissed_at"])

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self):
        """Request without valid auth returns 401."""
        # Remove the dependency override to test real auth rejection
        app.dependency_overrides.pop(get_current_user, None)

        mock_db = MagicMock()
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_cursor_mock([])
        )

        with patch("routes.strategy.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/strategy")

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestApproveCard — DASH-05 + DASH-02
# ---------------------------------------------------------------------------


class TestApproveCard:
    """POST /api/strategy/{id}/approve — approve endpoint."""

    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_approve_returns_generate_payload(self):
        """Successful approval returns approved=True and generate_payload."""
        approval_result = {
            "approved": True,
            "generate_payload": {
                "platform": "linkedin",
                "content_type": "post",
                "raw_input": "Write about AI in content creation",
            },
        }

        with patch("routes.strategy.handle_approval", AsyncMock(return_value=approval_result)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/strategy/strat_abc123/approve")

        assert resp.status_code == 200
        body = resp.json()
        assert body["approved"] is True
        payload = body["generate_payload"]
        assert payload["platform"] == "linkedin"
        assert payload["content_type"] == "post"
        assert payload["raw_input"] == "Write about AI in content creation"

    @pytest.mark.asyncio
    async def test_approve_not_found_returns_404(self):
        """handle_approval returning error=not_found raises 404."""
        with patch(
            "routes.strategy.handle_approval",
            AsyncMock(return_value={"error": "not_found"}),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/strategy/strat_missing/approve")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_approve_calls_handle_approval_with_correct_args(self):
        """handle_approval is called with the authenticated user_id and the path recommendation_id."""
        mock_approval = AsyncMock(
            return_value={
                "approved": True,
                "generate_payload": {
                    "platform": "x",
                    "content_type": "thread",
                    "raw_input": "test",
                },
            }
        )

        with patch("routes.strategy.handle_approval", mock_approval):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post("/api/strategy/strat_xyz999/approve")

        mock_approval.assert_awaited_once_with(
            user_id="test_user_strat",
            recommendation_id="strat_xyz999",
        )


# ---------------------------------------------------------------------------
# TestDismissCard — DASH-05
# ---------------------------------------------------------------------------


class TestDismissCard:
    """POST /api/strategy/{id}/dismiss — dismiss endpoint."""

    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_dismiss_returns_suppression_info(self):
        """Successful dismissal returns dismissed=True and suppression info."""
        dismissal_result = {
            "dismissed": True,
            "topic_suppressed_until": "2026-04-15T00:00:00+00:00",
            "needs_calibration_prompt": False,
        }

        with patch(
            "routes.strategy.handle_dismissal", AsyncMock(return_value=dismissal_result)
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/strategy/strat_abc123/dismiss")

        assert resp.status_code == 200
        body = resp.json()
        assert body["dismissed"] is True
        assert body["topic_suppressed_until"] == "2026-04-15T00:00:00+00:00"
        assert body["needs_calibration_prompt"] is False

    @pytest.mark.asyncio
    async def test_dismiss_not_found_returns_404(self):
        """handle_dismissal returning error=not_found raises 404."""
        with patch(
            "routes.strategy.handle_dismissal",
            AsyncMock(return_value={"error": "not_found"}),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/strategy/strat_missing/dismiss")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_dismiss_passes_reason_to_handler(self):
        """Reason field from request body is passed to handle_dismissal."""
        mock_dismissal = AsyncMock(
            return_value={
                "dismissed": True,
                "topic_suppressed_until": "2026-04-15T00:00:00+00:00",
                "needs_calibration_prompt": False,
            }
        )

        with patch("routes.strategy.handle_dismissal", mock_dismissal):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/strategy/strat_abc123/dismiss",
                    json={"reason": "not relevant"},
                )

        assert resp.status_code == 200
        mock_dismissal.assert_awaited_once_with(
            user_id="test_user_strat",
            recommendation_id="strat_abc123",
            reason="not relevant",
        )

    @pytest.mark.asyncio
    async def test_dismiss_returns_calibration_prompt_flag(self):
        """needs_calibration_prompt=True is propagated from handle_dismissal."""
        dismissal_result = {
            "dismissed": True,
            "topic_suppressed_until": "2026-04-15T00:00:00+00:00",
            "needs_calibration_prompt": True,
        }

        with patch(
            "routes.strategy.handle_dismissal", AsyncMock(return_value=dismissal_result)
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/strategy/strat_abc123/dismiss")

        assert resp.status_code == 200
        assert resp.json()["needs_calibration_prompt"] is True


# ---------------------------------------------------------------------------
# TestGeneratePayloadShape — DASH-02
# ---------------------------------------------------------------------------


class TestGeneratePayloadShape:
    """Verify generate_payload from approve matches ContentCreateRequest required fields."""

    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_payload_contains_required_content_create_fields(self):
        """Approve response generate_payload contains platform, content_type, raw_input (str types)."""
        approval_result = {
            "approved": True,
            "generate_payload": {
                "platform": "linkedin",
                "content_type": "post",
                "raw_input": "Write about AI trends in 2026 using a contrarian hook",
            },
        }

        with patch(
            "routes.strategy.handle_approval", AsyncMock(return_value=approval_result)
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/strategy/strat_abc123/approve")

        assert resp.status_code == 200
        payload = resp.json()["generate_payload"]

        # All three required ContentCreateRequest fields must be present and be strings
        assert isinstance(payload.get("platform"), str), "platform must be a string"
        assert isinstance(payload.get("content_type"), str), "content_type must be a string"
        assert isinstance(payload.get("raw_input"), str), "raw_input must be a string"
        # Values must be non-empty
        assert payload["platform"]
        assert payload["content_type"]
        assert payload["raw_input"]
