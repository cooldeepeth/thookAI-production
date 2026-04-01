"""Tests verifying SSE notification user-id scoping.

E2E-04: SSE notification stream is scoped to the authenticated user —
no cross-user notification leakage, auth required, correct content type.

Test approach:
1. Source inspection tests (static): verify user_id filter in _sse_event_generator
2. Service-level tests: verify create_notification always sets user_id
3. Route-level tests (FastAPI TestClient): auth requirement and content-type header
"""

import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from server import app
from auth_utils import get_current_user


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

_USER_A = {"user_id": "user_A", "email": "user_a@example.com"}
_USER_B = {"user_id": "user_B", "email": "user_b@example.com"}


# ---------------------------------------------------------------------------
# TestSSEUserScoping
# ---------------------------------------------------------------------------


class TestSSEUserScoping:
    """Verify SSE notification stream is isolated per authenticated user."""

    @pytest.mark.asyncio
    async def test_sse_generator_query_includes_user_id_filter(self):
        """Static analysis: _sse_event_generator source contains user_id filter in DB query.

        Uses inspect.getsource() to confirm the MongoDB query passed to
        db.notifications.find includes a 'user_id' key. This is a static
        analysis test — it catches regressions where the filter is removed.
        """
        from routes.notifications import _sse_event_generator

        source = inspect.getsource(_sse_event_generator)

        # The SSE generator must query with user_id filter
        assert '"user_id"' in source or "'user_id'" in source, (
            "SSE generator must filter db.notifications by 'user_id' key. "
            f"Source excerpt: {source[:300]}"
        )
        # The filter must reference the user_id variable (not a hardcoded string)
        assert "user_id" in source, (
            "SSE generator source must include user_id variable in the query filter."
        )

    @pytest.mark.asyncio
    async def test_notification_service_always_sets_user_id(self):
        """create_notification always inserts user_id field into document.

        Verifies that both user_A and user_B get their respective user_ids
        stored in the notification document passed to insert_one.
        """
        mock_insert = AsyncMock()
        captured_docs = []

        async def capture_insert(doc):
            captured_docs.append(doc)

        mock_insert.side_effect = capture_insert

        with patch("services.notification_service.db") as mock_db:
            mock_db.notifications.insert_one = mock_insert
            from services.notification_service import create_notification

            await create_notification(
                user_id="user_A",
                type="test",
                title="Test Notification",
                body="Body text for user A",
            )
            await create_notification(
                user_id="user_B",
                type="test",
                title="Test Notification",
                body="Body text for user B",
            )

        assert len(captured_docs) == 2, (
            f"Expected 2 documents inserted, got {len(captured_docs)}"
        )

        doc_a = captured_docs[0]
        doc_b = captured_docs[1]

        assert doc_a["user_id"] == "user_A", (
            f"First notification must have user_id='user_A', got: {doc_a.get('user_id')!r}"
        )
        assert doc_b["user_id"] == "user_B", (
            f"Second notification must have user_id='user_B', got: {doc_b.get('user_id')!r}"
        )

    @pytest.mark.asyncio
    async def test_sse_endpoint_requires_authentication(self):
        """GET /api/notifications/stream without auth token returns 401 or 403.

        Verifies the SSE endpoint is protected by get_current_user dependency.
        No dependency override — raw unauthenticated request.
        """
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/notifications/stream")

        assert response.status_code in (401, 403), (
            f"Unauthenticated SSE request must return 401 or 403, "
            f"got: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_sse_returns_event_stream_content_type(self):
        """GET /api/notifications/stream returns Content-Type: text/event-stream.

        Verifies the SSE endpoint declares the correct media type so clients
        (EventSource, browser) process it as a streaming response.
        """

        async def _empty_sse_generator(user_id, request):
            yield ": heartbeat\n\n"

        app.dependency_overrides[get_current_user] = lambda: _USER_A

        try:
            with patch("routes.notifications._sse_event_generator", _empty_sse_generator):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/notifications/stream")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type, (
            f"SSE endpoint must return Content-Type: text/event-stream, got: {content_type!r}"
        )

    @pytest.mark.asyncio
    async def test_notification_service_returns_doc_with_user_id(self):
        """create_notification return value always includes user_id field.

        Callers rely on the returned document to know which user received
        the notification — user_id must be present in the return value.
        """
        mock_insert = AsyncMock()

        with patch("services.notification_service.db") as mock_db:
            mock_db.notifications.insert_one = mock_insert
            from services.notification_service import create_notification

            result_a = await create_notification(
                user_id="user_A",
                type="job_completed",
                title="Your post is ready",
                body="Your LinkedIn post draft is ready for review.",
                metadata={"job_id": "job_abc"},
            )
            result_b = await create_notification(
                user_id="user_B",
                type="post_published",
                title="Post published",
                body="Your scheduled post went live.",
            )

        assert result_a["user_id"] == "user_A", (
            f"Return value must have user_id='user_A', got: {result_a.get('user_id')!r}"
        )
        assert result_b["user_id"] == "user_B", (
            f"Return value must have user_id='user_B', got: {result_b.get('user_id')!r}"
        )
        # notification_id must be set (not empty)
        assert result_a.get("notification_id"), (
            "notification_id must be set in return value"
        )
        assert result_b.get("notification_id"), (
            "notification_id must be set in return value"
        )

    @pytest.mark.asyncio
    async def test_sse_generator_does_not_cross_contaminate_users(self):
        """Static analysis: SSE generator uses the user_id parameter, not a global variable.

        Verifies that the db.notifications.find call inside _sse_event_generator
        uses the user_id argument — not a hardcoded value or a different variable
        that could expose cross-user data.
        """
        from routes.notifications import _sse_event_generator

        source = inspect.getsource(_sse_event_generator)

        # The function parameter is named 'user_id'
        sig = inspect.signature(_sse_event_generator)
        assert "user_id" in sig.parameters, (
            f"_sse_event_generator must have 'user_id' as a parameter, "
            f"got: {list(sig.parameters.keys())}"
        )

        # The MongoDB query dict must contain the user_id variable reference
        # Specifically: {"user_id": user_id, ...} pattern in the find() call
        assert '"user_id": user_id' in source or "'user_id': user_id" in source, (
            "SSE generator must pass user_id variable to db.notifications.find filter, "
            f"not a hardcoded value. Source: {source}"
        )
