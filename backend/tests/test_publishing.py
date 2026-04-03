"""Tests for the publishing dispatch pipeline.

Verifies that:
- _publish_to_platform() delegates to agents/publisher.py which makes real HTTP requests
  to the correct LinkedIn, X, and Instagram API endpoints (not simulating).
- process_scheduled_posts() picks up due posts and publishes them via _publish_to_platform.
- Error cases (HTTP failures, network errors, missing tokens) are handled gracefully.

All tests mock httpx.AsyncClient (NOT agents.publisher.publish_to_platform) so the
real publisher.py HTTP dispatch code path runs end-to-end.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
import httpx


# ---------------------------------------------------------------------------
# Helper: build a mock httpx response
# ---------------------------------------------------------------------------

def _make_response(status_code: int, json_data: dict = None, headers: dict = None):
    """Create a mock httpx.Response."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or {}
    mock_resp.text = str(json_data or {})
    mock_resp.headers = headers or {}
    return mock_resp


# ---------------------------------------------------------------------------
# Test _publish_to_platform → publisher.py → httpx (LinkedIn)
# ---------------------------------------------------------------------------

class TestPublishLinkedIn:
    """Verify LinkedIn publishing uses the correct API endpoint and auth header."""

    @pytest.mark.asyncio
    async def test_publish_to_platform_linkedin_sends_correct_request(self):
        """_publish_to_platform delegates to publisher.py which POSTs to LinkedIn UGC endpoint."""
        # Profile lookup response (LinkedIn returns sub-based URN)
        profile_response = _make_response(200, {"sub": "user_urn_123", "name": "Test User"})
        # UGC post creation response with restli id header
        ugc_response = _make_response(201, {}, headers={"x-restli-id": "urn:li:share:999"})

        captured_calls = []

        async def mock_post(url, **kwargs):
            captured_calls.append(("POST", url, kwargs))
            return ugc_response

        async def mock_get(url, **kwargs):
            return profile_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post
        mock_client.get = mock_get

        token = {"access_token": "tok_linkedin_test", "user_id": "u1"}

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.settings") as mock_settings:
                mock_settings.app.is_production = False
                from tasks.content_tasks import _publish_to_platform
                result = await _publish_to_platform(
                    platform="linkedin",
                    content="Test LinkedIn post",
                    token=token,
                )

        assert result is True
        # Ensure a POST was made to the LinkedIn UGC endpoint
        post_urls = [url for method, url, kwargs in captured_calls if method == "POST"]
        assert any("api.linkedin.com/v2/ugcPosts" in url for url in post_urls), (
            f"Expected POST to api.linkedin.com/v2/ugcPosts, got: {post_urls}"
        )
        # Ensure Bearer auth header was sent
        ugc_call = next(
            (kwargs for method, url, kwargs in captured_calls
             if method == "POST" and "ugcPosts" in url),
            None,
        )
        assert ugc_call is not None
        headers = ugc_call.get("headers", {})
        assert headers.get("Authorization") == "Bearer tok_linkedin_test", (
            f"Expected Bearer tok_linkedin_test, got: {headers.get('Authorization')}"
        )

    @pytest.mark.asyncio
    async def test_publish_to_linkedin_no_simulation(self):
        """The publisher must NOT log '[SIMULATED]' — real HTTP calls only."""
        import logging

        profile_response = _make_response(200, {"sub": "urn_sub", "name": "Test"})
        ugc_response = _make_response(201, {}, headers={"x-restli-id": "urn:li:share:1"})

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=ugc_response)
        mock_client.get = AsyncMock(return_value=profile_response)

        token = {"access_token": "tok_test", "user_id": "u1"}

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.settings") as mock_settings:
                mock_settings.app.is_production = True
                with patch("logging.Logger.warning") as mock_warn:
                    from tasks.content_tasks import _publish_to_platform
                    result = await _publish_to_platform(
                        platform="linkedin",
                        content="No simulation please",
                        token=token,
                    )

        # '[SIMULATED]' must not appear in any warning log calls
        for warn_call in mock_warn.call_args_list:
            args = warn_call[0]
            if args:
                assert "[SIMULATED]" not in str(args[0]), (
                    "Found [SIMULATED] in log output — production path must use real publisher"
                )


# ---------------------------------------------------------------------------
# Test _publish_to_platform → publisher.py → httpx (X/Twitter)
# ---------------------------------------------------------------------------

class TestPublishX:
    """Verify X/Twitter publishing uses the correct API endpoint and auth header."""

    @pytest.mark.asyncio
    async def test_publish_to_platform_x_sends_correct_request(self):
        """_publish_to_platform delegates to publisher.py which POSTs to X/Twitter v2 tweets endpoint."""
        tweet_response = _make_response(201, {"data": {"id": "tweet_123", "text": "Test"}})

        captured_calls = []

        async def mock_post(url, **kwargs):
            captured_calls.append(("POST", url, kwargs))
            return tweet_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        token = {"access_token": "tok_x_test", "user_id": "u2"}

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.settings") as mock_settings:
                mock_settings.app.is_production = False
                from tasks.content_tasks import _publish_to_platform
                result = await _publish_to_platform(
                    platform="x",
                    content="Test tweet",
                    token=token,
                )

        assert result is True
        post_urls = [url for method, url, kwargs in captured_calls if method == "POST"]
        assert any("api.twitter.com/2/tweets" in url for url in post_urls), (
            f"Expected POST to api.twitter.com/2/tweets, got: {post_urls}"
        )
        # Verify Bearer auth header
        x_call = next(
            (kwargs for method, url, kwargs in captured_calls
             if method == "POST" and "twitter.com/2/tweets" in url),
            None,
        )
        assert x_call is not None
        headers = x_call.get("headers", {})
        assert headers.get("Authorization") == "Bearer tok_x_test", (
            f"Expected Bearer tok_x_test, got: {headers.get('Authorization')}"
        )


# ---------------------------------------------------------------------------
# Test _publish_to_platform → publisher.py → httpx (Instagram)
# ---------------------------------------------------------------------------

class TestPublishInstagram:
    """Verify Instagram publishing uses the correct Graph API endpoint with access_token."""

    @pytest.mark.asyncio
    async def test_publish_to_platform_instagram_sends_correct_request(self):
        """publisher.py publish_to_instagram calls graph.facebook.com with access_token param."""
        container_response = _make_response(200, {"id": "container_123"})
        status_response = _make_response(200, {"status_code": "FINISHED"})
        publish_response = _make_response(200, {"id": "ig_post_123"})
        permalink_response = _make_response(200, {"permalink": "https://www.instagram.com/p/abc/"})

        # Track all HTTP calls
        post_calls = []
        get_calls = []

        async def mock_post(url, **kwargs):
            post_calls.append((url, kwargs))
            if "media_publish" in url:
                return publish_response
            return container_response

        async def mock_get(url, **kwargs):
            get_calls.append((url, kwargs))
            if "status_code" in str(kwargs.get("params", {})):
                return status_response
            return permalink_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post
        mock_client.get = mock_get

        # Instagram publisher does a direct DB lookup for instagram_account_id
        mock_token_doc = {
            "user_id": "u3",
            "platform": "instagram",
            "instagram_account_id": "ig_acct_456",
            "access_token": "tok_ig_test",
        }

        with patch("httpx.AsyncClient", return_value=mock_client):
            # publisher.py imports db via `from database import db` inside publish_to_instagram
            with patch("database.db") as mock_db:
                mock_db.platform_tokens.find_one = AsyncMock(return_value=mock_token_doc)
                # Call publish_to_platform directly (it routes to publish_to_instagram)
                from agents.publisher import publish_to_platform
                result = await publish_to_platform(
                    platform="instagram",
                    content="Test Instagram caption",
                    access_token="tok_ig_test",
                    user_id="u3",
                    media_assets=[{"type": "image", "url": "https://example.com/img.jpg"}],
                )

        # Check that graph.facebook.com was called
        all_urls = [url for url, kwargs in post_calls] + [url for url, kwargs in get_calls]
        assert any("graph.facebook.com" in url for url in all_urls), (
            f"Expected call to graph.facebook.com, got URLs: {all_urls}"
        )
        # access_token should appear as a query param in at least one call
        all_params = [
            str(kwargs.get("params", {}))
            for _, kwargs in post_calls + get_calls
        ]
        assert any("tok_ig_test" in params or "access_token" in params for params in all_params), (
            "Expected access_token in Instagram API call params"
        )


# ---------------------------------------------------------------------------
# Test error handling
# ---------------------------------------------------------------------------

class TestPublishErrorHandling:
    """Verify _publish_to_platform handles HTTP and network errors gracefully."""

    @pytest.mark.asyncio
    async def test_publish_http_failure_returns_false(self):
        """HTTP error from platform API should cause _publish_to_platform to return False."""
        # LinkedIn: profile lookup succeeds but ugcPosts returns 500
        profile_response = _make_response(200, {"sub": "sub_123", "name": "Test"})
        error_response = _make_response(500, {"message": "Internal Server Error"})

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=error_response)
        mock_client.get = AsyncMock(return_value=profile_response)

        token = {"access_token": "tok_fail", "user_id": "u4"}

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.settings") as mock_settings:
                mock_settings.app.is_production = False
                from tasks.content_tasks import _publish_to_platform
                result = await _publish_to_platform(
                    platform="linkedin",
                    content="This will fail",
                    token=token,
                )

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_network_error_returns_false(self):
        """Network error (ConnectError) should cause _publish_to_platform to return False."""

        async def mock_get(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        token = {"access_token": "tok_net_fail", "user_id": "u5"}

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("config.settings") as mock_settings:
                mock_settings.app.is_production = False
                from tasks.content_tasks import _publish_to_platform
                result = await _publish_to_platform(
                    platform="linkedin",
                    content="Network failure test",
                    token=token,
                )

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_expired_token_returns_false(self):
        """An already-expired token should be caught by _publish_to_platform before any HTTP call."""
        expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
        token = {
            "access_token": "tok_expired",
            "user_id": "u6",
            "expires_at": expired_at,
        }

        with patch("config.settings") as mock_settings:
            mock_settings.app.is_production = False
            from tasks.content_tasks import _publish_to_platform
            result = await _publish_to_platform(
                platform="linkedin",
                content="Should not reach API",
                token=token,
            )

        assert result is False


# ---------------------------------------------------------------------------
# Test process_scheduled_posts
# ---------------------------------------------------------------------------

class TestProcessScheduledPosts:
    """Verify process_scheduled_posts picks up due posts and publishes/fails them."""

    @pytest.mark.asyncio
    async def test_process_scheduled_posts_publishes_due_posts(self):
        """Due scheduled posts should be published and status updated to 'published'."""
        now = datetime.now(timezone.utc)
        due_post = {
            "schedule_id": "sched_001",
            "user_id": "user_abc",
            "platform": "linkedin",
            "content": "Scheduled post content",
            "status": "scheduled",
            "scheduled_at": now - timedelta(minutes=10),
            "job_id": "job_001",
        }

        platform_token = {
            "user_id": "user_abc",
            "platform": "linkedin",
            "access_token": "tok_sched",
            "user_id": "user_abc",
        }

        # Mock DB
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[due_post])
        mock_db.scheduled_posts.find.return_value = mock_cursor
        mock_db.platform_tokens.find_one = AsyncMock(return_value=platform_token)

        update_result = MagicMock()
        mock_db.scheduled_posts.update_one = AsyncMock(return_value=update_result)

        with patch("tasks.content_tasks._publish_to_platform", new_callable=AsyncMock, return_value=True):
            # Import the inner async function and pass mock_db directly
            import tasks.content_tasks as ct_module
            result = await ct_module._run_scheduled_posts_inner(mock_db)

        # Status should have been updated to 'published'
        update_call_args = mock_db.scheduled_posts.update_one.call_args_list
        assert len(update_call_args) >= 1
        set_data = update_call_args[0][0][1]["$set"]
        assert set_data["status"] == "published", (
            f"Expected status='published', got: {set_data.get('status')}"
        )

    @pytest.mark.asyncio
    async def test_process_scheduled_posts_fails_without_token(self):
        """Due post with no platform token should be marked as 'failed'."""
        now = datetime.now(timezone.utc)
        due_post = {
            "schedule_id": "sched_002",
            "user_id": "user_xyz",
            "platform": "x",
            "content": "Post without token",
            "status": "scheduled",
            "scheduled_at": now - timedelta(minutes=5),
            "job_id": "job_002",
        }

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[due_post])
        mock_db.scheduled_posts.find.return_value = mock_cursor
        # No token found
        mock_db.platform_tokens.find_one = AsyncMock(return_value=None)
        mock_db.scheduled_posts.update_one = AsyncMock()

        import tasks.content_tasks as ct_module
        result = await ct_module._run_scheduled_posts_inner(mock_db)

        update_call_args = mock_db.scheduled_posts.update_one.call_args_list
        assert len(update_call_args) >= 1
        set_data = update_call_args[0][0][1]["$set"]
        assert set_data["status"] == "failed", (
            f"Expected status='failed', got: {set_data.get('status')}"
        )
        assert "Platform not connected" in set_data.get("error", ""), (
            f"Expected 'Platform not connected' in error, got: {set_data.get('error')}"
        )
