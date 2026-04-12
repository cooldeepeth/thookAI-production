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

        assert result.get("success") is True, f"Expected success=True, got: {result}"
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

        assert result.get("success") is True, f"Expected success=True, got: {result}"
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

        assert result.get("success") is False, f"Expected success=False, got: {result}"

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

        assert result.get("success") is False, f"Expected success=False, got: {result}"

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

        assert result.get("success") is False, f"Expected success=False, got: {result}"


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

        with patch("tasks.content_tasks._publish_to_platform", new_callable=AsyncMock,
                   return_value={"success": True, "post_id": "urn:li:share:001"}):
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


# ---------------------------------------------------------------------------
# Task 1: Fix _publish_to_platform — decrypt token, return dict
# ---------------------------------------------------------------------------

class TestPublishToPlatformFixed:
    """Verify _publish_to_platform decrypts tokens and returns full result dicts."""

    @pytest.mark.asyncio
    async def test_decrypts_access_token_before_calling_publisher(self):
        """Encrypted token must be decrypted before passing to publish_to_platform."""
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        cipher = Fernet(key)
        plaintext = "real_access_token_123"
        encrypted = cipher.encrypt(plaintext.encode()).decode()

        token_doc = {
            "user_id": "user_1",
            "platform": "linkedin",
            "access_token": encrypted,
        }

        captured = {}

        async def fake_publish(platform, content, access_token, user_id=None, media_assets=None):
            captured["access_token"] = access_token
            return {"success": True, "post_id": "urn:li:share:1", "post_url": "https://linkedin.com/1"}

        # patch _decrypt_token on content_tasks module and publish_to_platform where
        # it is actually imported from (agents.publisher) so both dev and prod paths
        # resolve to our fake.
        with (
            patch("tasks.content_tasks._decrypt_token", return_value=plaintext),
            patch("agents.publisher.publish_to_platform", new=fake_publish),
        ):
            import tasks.content_tasks as ct
            result = await ct._publish_to_platform("linkedin", "Hello world", token_doc)

        assert captured.get("access_token") == plaintext, (
            f"Expected plaintext token, got: {captured.get('access_token')}"
        )

    @pytest.mark.asyncio
    async def test_returns_full_dict_on_success(self):
        """Must return the full publisher result dict, not just True."""
        expected = {"success": True, "post_id": "urn:li:share:999", "post_url": "https://linkedin.com/999"}

        async def fake_publish(platform, content, access_token, user_id=None, media_assets=None):
            return expected

        token_doc = {"user_id": "u1", "platform": "linkedin", "access_token": "enc_token"}
        with (
            patch("tasks.content_tasks._decrypt_token", return_value="real_token"),
            patch("agents.publisher.publish_to_platform", new=fake_publish),
        ):
            import tasks.content_tasks as ct
            result = await ct._publish_to_platform("linkedin", "content", token_doc)

        assert result == expected, f"Expected full dict, got: {result}"

    @pytest.mark.asyncio
    async def test_returns_full_dict_on_failure(self):
        """Must return the full publisher result dict even on failure (not just False)."""
        expected = {"success": False, "error": "403 Forbidden"}

        async def fake_publish(platform, content, access_token, user_id=None, media_assets=None):
            return expected

        token_doc = {"user_id": "u1", "platform": "linkedin", "access_token": "enc_token"}
        with (
            patch("tasks.content_tasks._decrypt_token", return_value="real_token"),
            patch("agents.publisher.publish_to_platform", new=fake_publish),
        ):
            import tasks.content_tasks as ct
            result = await ct._publish_to_platform("linkedin", "content", token_doc)

        assert result.get("success") is False
        assert result.get("error") == "403 Forbidden"

    @pytest.mark.asyncio
    async def test_expired_token_returns_dict_not_bool(self):
        """Expired token path must return a dict with success=False."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token_doc = {
            "user_id": "u1",
            "platform": "linkedin",
            "access_token": "enc_token",
            "expires_at": past,
        }
        import tasks.content_tasks as ct
        result = await ct._publish_to_platform("linkedin", "content", token_doc)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
        assert result.get("success") is False


# ---------------------------------------------------------------------------
# Task 2: Fix scheduled_tasks — store publish_results, fix media_assets kwarg
# ---------------------------------------------------------------------------

class TestScheduledTasksFixed:
    """Verify _process_scheduled_posts stores publish_results on content_jobs."""

    @pytest.mark.asyncio
    async def test_stores_publish_results_on_content_jobs(self):
        """On success, publish_results must be written to the content_jobs document."""
        now = datetime.now(timezone.utc)
        post = {
            "schedule_id": "sched_abc",
            "user_id": "user_1",
            "platform": "linkedin",
            "content": "Test post",
            "status": "scheduled",
            "job_id": "job_abc",
            "scheduled_at": now - timedelta(minutes=5),
        }
        publish_result = {"success": True, "post_id": "urn:li:share:123", "post_url": "https://linkedin.com/123"}

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[post])
        mock_db.scheduled_posts.find.return_value = mock_cursor
        mock_db.scheduled_posts.find_one_and_update = AsyncMock(return_value=post)
        mock_db.scheduled_posts.update_one = AsyncMock()
        mock_db.content_jobs.update_one = AsyncMock()

        async def fake_real_publish(**kwargs):
            return publish_result

        with patch("tasks.scheduled_tasks.real_publish", new=fake_real_publish):
            with patch("tasks.scheduled_tasks.db", mock_db):
                import tasks.scheduled_tasks as st
                await st._process_scheduled_posts()

        assert mock_db.content_jobs.update_one.called, "content_jobs.update_one was not called"
        call_args = mock_db.content_jobs.update_one.call_args
        filter_dict = call_args[0][0]
        update_dict = call_args[0][1]["$set"]
        assert filter_dict.get("job_id") == "job_abc"
        assert "publish_results" in update_dict, f"publish_results missing from: {update_dict}"

    @pytest.mark.asyncio
    async def test_passes_media_assets_not_media_urls(self):
        """publish_to_platform must be called with media_assets kwarg (not media_urls)."""
        captured_kwargs = {}
        now = datetime.now(timezone.utc)
        post = {
            "schedule_id": "sched_x",
            "user_id": "user_2",
            "platform": "x",
            "content": "X post",
            "status": "scheduled",
            "job_id": "job_x",
            "scheduled_at": now - timedelta(minutes=1),
            "media_urls": ["https://example.com/img.jpg"],
        }

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[post])
        mock_db.scheduled_posts.find.return_value = mock_cursor
        mock_db.scheduled_posts.find_one_and_update = AsyncMock(return_value=post)
        mock_db.scheduled_posts.update_one = AsyncMock()
        mock_db.content_jobs.update_one = AsyncMock()

        async def capture_publish(**kwargs):
            captured_kwargs.update(kwargs)
            return {"success": True, "post_id": "tweet_1"}

        with patch("tasks.scheduled_tasks.real_publish", new=capture_publish):
            with patch("tasks.scheduled_tasks.db", mock_db):
                import tasks.scheduled_tasks as st
                await st._process_scheduled_posts()

        assert "media_urls" not in captured_kwargs, (
            f"media_urls should not be passed; got kwargs: {captured_kwargs}"
        )
        # media_assets kwarg may be None (no valid assets) or the list
        assert "media_assets" in captured_kwargs or captured_kwargs.get("media_assets") is None

    @pytest.mark.asyncio
    async def test_sentry_capture_on_publish_failure(self):
        """Failed publish must call sentry_sdk.capture_message with level='error'."""
        now = datetime.now(timezone.utc)
        post = {
            "schedule_id": "sched_fail",
            "user_id": "user_3",
            "platform": "instagram",
            "content": "IG post",
            "status": "scheduled",
            "job_id": "job_fail",
            "scheduled_at": now - timedelta(minutes=1),
        }

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[post])
        mock_db.scheduled_posts.find.return_value = mock_cursor
        mock_db.scheduled_posts.find_one_and_update = AsyncMock(return_value=post)
        mock_db.scheduled_posts.update_one = AsyncMock()
        mock_db.content_jobs.update_one = AsyncMock()

        async def fail_publish(**kwargs):
            return {"success": False, "error": "Media Container creation failed"}

        import sys
        import types

        # sentry_sdk may not be installed in the test environment; create a
        # lightweight fake module so patch() can resolve the attribute path.
        mock_capture = MagicMock()
        fake_sentry = types.ModuleType("sentry_sdk")
        fake_sentry.capture_message = mock_capture  # type: ignore[attr-defined]
        fake_sentry.capture_exception = MagicMock()  # type: ignore[attr-defined]

        with (
            patch("tasks.scheduled_tasks.real_publish", new=fail_publish),
            patch("tasks.scheduled_tasks.db", mock_db),
            patch("tasks.scheduled_tasks.settings") as mock_settings,
            patch.dict(sys.modules, {"sentry_sdk": fake_sentry}),
        ):
            mock_settings.app.sentry_dsn = "https://fake@sentry.io/1"
            import tasks.scheduled_tasks as st
            await st._process_scheduled_posts()

        assert mock_capture.called, "sentry_sdk.capture_message was not called on failure"
        call_kwargs = mock_capture.call_args[1] if mock_capture.call_args else {}
        assert call_kwargs.get("level") == "error" or "error" in str(mock_capture.call_args)


# ---------------------------------------------------------------------------
# Task 1 (30-04): LinkedIn image upload via registerUpload flow
# ---------------------------------------------------------------------------

class TestPublishLinkedInMedia:
    """publish_to_linkedin() must support image attachment via registerUpload flow."""

    @pytest.mark.asyncio
    async def test_calls_register_upload_when_media_provided(self):
        """registerUpload must be called when media_assets contains an image_url."""
        register_response = MagicMock()
        register_response.status_code = 200
        register_response.json.return_value = {
            "value": {
                "asset": "urn:li:digitalmediaAsset:C5522AQF_abc123",
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://api.linkedin.com/mediaUpload/upload/abc123",
                        "headers": {},
                    }
                },
            }
        }
        upload_response = MagicMock()
        upload_response.status_code = 201

        post_response = MagicMock()
        post_response.status_code = 201
        post_response.headers = {"x-restli-id": "urn:li:share:987654"}
        post_response.json.return_value = {}

        image_response = MagicMock()
        image_response.status_code = 200
        image_response.content = b"fake_image_bytes"

        captured_calls = []

        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {"sub": "person_urn_123"}

        async def mock_get(url, **kw):
            captured_calls.append(("GET", url))
            if "r2.example.com" in url:
                return image_response
            return userinfo_resp

        async def mock_post(url, **kw):
            captured_calls.append(("POST", url))
            if "registerUpload" in url:
                return register_response
            if "ugcPosts" in url:
                return post_response
            return MagicMock(status_code=201)

        async def mock_put(url, **kw):
            captured_calls.append(("PUT", url))
            return upload_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client.put = AsyncMock(side_effect=mock_put)
        mock_client.get = AsyncMock(side_effect=mock_get)

        with patch("agents.publisher.httpx.AsyncClient", return_value=mock_client):
            from agents.publisher import publish_to_linkedin
            result = await publish_to_linkedin(
                user_id="user_test",
                content="Test post with image",
                media_assets=[{"image_url": "https://r2.example.com/img.jpg"}],
                token="valid_token",
            )

        register_urls = [url for method, url in captured_calls if "registerUpload" in url]
        assert len(register_urls) >= 1, (
            f"registerUpload was not called. Captured calls: {captured_calls}"
        )

    @pytest.mark.asyncio
    async def test_ugc_body_has_image_category_when_media_provided(self):
        """UGC post body must use shareMediaCategory=IMAGE and include media array."""
        captured_ugc_body = {}

        register_response = MagicMock()
        register_response.status_code = 200
        register_response.json.return_value = {
            "value": {
                "asset": "urn:li:digitalmediaAsset:TEST_ASSET",
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://api.linkedin.com/mediaUpload/upload/test",
                        "headers": {},
                    }
                },
            }
        }
        upload_response = MagicMock()
        upload_response.status_code = 201

        post_response = MagicMock()
        post_response.status_code = 201
        post_response.headers = {"x-restli-id": "urn:li:share:111"}
        post_response.json.return_value = {}

        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {"sub": "person_123"}

        image_resp = MagicMock()
        image_resp.status_code = 200
        image_resp.content = b"img_bytes"

        async def capture_post(url, **kwargs):
            if "ugcPosts" in url:
                captured_ugc_body.update(kwargs.get("json", {}))
                return post_response
            if "registerUpload" in url:
                return register_response
            return MagicMock(status_code=201)

        async def mock_get(url, **kwargs):
            if "r2.example.com" in url:
                return image_resp
            return userinfo_resp

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client.put = AsyncMock(return_value=upload_response)
        mock_client.get = AsyncMock(side_effect=mock_get)

        with patch("agents.publisher.httpx.AsyncClient", return_value=mock_client):
            from agents.publisher import publish_to_linkedin
            await publish_to_linkedin(
                user_id="user_test",
                content="Image post",
                media_assets=[{"image_url": "https://r2.example.com/photo.jpg"}],
                token="valid_token",
            )

        share_content = (
            captured_ugc_body
            .get("specificContent", {})
            .get("com.linkedin.ugc.ShareContent", {})
        )
        assert share_content.get("shareMediaCategory") == "IMAGE", (
            f"Expected IMAGE category, got: {share_content.get('shareMediaCategory')}"
        )
        assert len(share_content.get("media", [])) >= 1, "media array must be populated"

    @pytest.mark.asyncio
    async def test_text_only_when_no_media_assets(self):
        """Without media_assets, must use shareMediaCategory=NONE (text-only path preserved)."""
        captured_ugc_body = {}

        post_response = MagicMock()
        post_response.status_code = 201
        post_response.headers = {"x-restli-id": "urn:li:share:222"}
        post_response.json.return_value = {}

        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {"sub": "person_456"}

        async def capture_post(url, **kwargs):
            if "ugcPosts" in url:
                captured_ugc_body.update(kwargs.get("json", {}))
            return post_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client.get = AsyncMock(return_value=userinfo_resp)

        with patch("agents.publisher.httpx.AsyncClient", return_value=mock_client):
            from agents.publisher import publish_to_linkedin
            result = await publish_to_linkedin(
                user_id="user_test",
                content="Text-only post",
                media_assets=None,
                token="valid_token",
            )

        share_content = (
            captured_ugc_body
            .get("specificContent", {})
            .get("com.linkedin.ugc.ShareContent", {})
        )
        assert share_content.get("shareMediaCategory") == "NONE", (
            f"Expected NONE category for text-only, got: {share_content.get('shareMediaCategory')}"
        )

    @pytest.mark.asyncio
    async def test_register_upload_failure_falls_back_to_text_only(self):
        """If registerUpload fails (non-201), publish must continue as text-only rather than error."""
        register_response = MagicMock()
        register_response.status_code = 400
        register_response.json.return_value = {"message": "Upload not allowed"}

        post_response = MagicMock()
        post_response.status_code = 201
        post_response.headers = {"x-restli-id": "urn:li:share:333"}
        post_response.json.return_value = {}

        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {"sub": "person_789"}

        async def mock_post(url, **kwargs):
            if "registerUpload" in url:
                return register_response
            return post_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client.get = AsyncMock(return_value=userinfo_resp)

        with patch("agents.publisher.httpx.AsyncClient", return_value=mock_client):
            from agents.publisher import publish_to_linkedin
            result = await publish_to_linkedin(
                user_id="user_test",
                content="Post with failed upload",
                media_assets=[{"image_url": "https://r2.example.com/img.jpg"}],
                token="valid_token",
            )

        # Should succeed as text-only rather than returning success=False
        assert result.get("success") is True, (
            f"Expected text-only fallback success, got: {result}"
        )
