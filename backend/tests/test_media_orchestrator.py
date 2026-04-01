"""Tests for MediaOrchestrator: R2 staging, Remotion client, and orchestrate().

Verifies:
- _stage_asset_to_r2: HTTP URL download path
- _stage_asset_to_r2: base64 data: URL decode path
- _stage_assets_to_r2: parallel gather of multiple assets
- _call_remotion: POST + poll (queued→rendering→done) with result URL
- _call_remotion: timeout raises RuntimeError
- orchestrate(): unknown media_type raises ValueError
- orchestrate(): unimplemented but valid type raises NotImplementedError
- MediaBrief: all fields set correctly
"""
import asyncio
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


# ============================================================
# MediaBrief construction tests
# ============================================================

class TestMediaBriefCreation:
    """Test that MediaBrief accepts all required and optional fields."""

    def test_media_brief_required_fields(self):
        """MediaBrief can be instantiated with required fields and defaults."""
        from services.media_orchestrator import MediaBrief

        brief = MediaBrief(
            job_id="job_abc",
            user_id="user_123",
            media_type="static_image",
            platform="linkedin",
            content_text="Test content",
            persona_card={"archetype": "Thought Leader"},
        )

        assert brief.job_id == "job_abc"
        assert brief.user_id == "user_123"
        assert brief.media_type == "static_image"
        assert brief.platform == "linkedin"
        assert brief.content_text == "Test content"
        assert brief.persona_card == {"archetype": "Thought Leader"}
        assert brief.style == "minimal"          # default
        assert brief.brand_color == "#2563EB"    # default
        assert brief.slides is None              # optional
        assert brief.voice_id is None            # optional

    def test_media_brief_optional_fields(self):
        """MediaBrief accepts all optional fields."""
        from services.media_orchestrator import MediaBrief

        brief = MediaBrief(
            job_id="job_xyz",
            user_id="user_456",
            media_type="talking_head",
            platform="instagram",
            content_text="Script text",
            persona_card={},
            style="bold",
            avatar_id="heygen_avatar_001",
            voice_id="elevenlabs_voice_001",
            music_url="https://example.com/music.mp3",
            brand_color="#FF5733",
        )

        assert brief.avatar_id == "heygen_avatar_001"
        assert brief.voice_id == "elevenlabs_voice_001"
        assert brief.brand_color == "#FF5733"

    def test_media_type_cost_caps_keys(self):
        """MEDIA_TYPE_COST_CAPS includes all 8 required media types."""
        from services.media_orchestrator import MEDIA_TYPE_COST_CAPS

        required_types = {
            "static_image", "quote_card", "meme", "carousel",
            "infographic", "talking_head", "short_form_video", "text_on_video",
        }
        assert required_types.issubset(set(MEDIA_TYPE_COST_CAPS.keys()))

    def test_media_type_cost_caps_values_positive(self):
        """All cost cap values are positive integers."""
        from services.media_orchestrator import MEDIA_TYPE_COST_CAPS

        for media_type, cap in MEDIA_TYPE_COST_CAPS.items():
            assert isinstance(cap, int), f"{media_type} cap must be int"
            assert cap > 0, f"{media_type} cap must be positive"


# ============================================================
# R2 pre-staging tests
# ============================================================

class TestStageAssetToR2:
    """Test _stage_asset_to_r2 with HTTP URL and base64 data: URL paths."""

    @pytest.mark.asyncio
    async def test_stage_http_url_downloads_and_uploads(self):
        """HTTP URL: downloads bytes via httpx, uploads to R2, returns R2 public URL."""
        fake_bytes = b"fake image content"
        fake_content_type = "image/jpeg"

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.content = fake_bytes
        mock_response.headers = {"content-type": fake_content_type}
        mock_response.raise_for_status = MagicMock()

        # Mock R2 client
        mock_r2 = MagicMock()
        mock_r2.put_object = MagicMock()

        with patch("httpx.AsyncClient") as mock_httpx, \
             patch("services.media_orchestrator.get_r2_client", return_value=mock_r2), \
             patch("services.media_orchestrator.settings") as mock_settings:

            mock_settings.r2.r2_bucket_name = "test-bucket"
            mock_settings.r2.r2_public_url = "https://cdn.example.com"

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.media_orchestrator import _stage_asset_to_r2

            result = await _stage_asset_to_r2(
                "https://provider.example.com/image.jpg",
                "job_abc",
                "background_image",
            )

        # Verify R2 upload was called
        assert mock_r2.put_object.called
        call_kwargs = mock_r2.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert "media/orchestrated/job_abc/background_image" in call_kwargs["Key"]
        assert call_kwargs["Body"] == fake_bytes

        # Verify returned URL starts with R2 public URL
        assert result.startswith("https://cdn.example.com/media/orchestrated/job_abc/")

    @pytest.mark.asyncio
    async def test_stage_base64_data_url_decodes_and_uploads(self):
        """data: URL: decodes base64 content, uploads to R2, returns R2 public URL."""
        raw_bytes = b"PNG image bytes here"
        encoded = base64.b64encode(raw_bytes).decode()
        data_url = f"data:image/png;base64,{encoded}"

        mock_r2 = MagicMock()
        mock_r2.put_object = MagicMock()

        with patch("services.media_orchestrator.get_r2_client", return_value=mock_r2), \
             patch("services.media_orchestrator.settings") as mock_settings:

            mock_settings.r2.r2_bucket_name = "test-bucket"
            mock_settings.r2.r2_public_url = "https://cdn.example.com"

            from services.media_orchestrator import _stage_asset_to_r2

            result = await _stage_asset_to_r2(data_url, "job_xyz", "generated_image")

        # Verify decode: uploaded bytes match original
        call_kwargs = mock_r2.put_object.call_args[1]
        assert call_kwargs["Body"] == raw_bytes
        assert call_kwargs["ContentType"] == "image/png"

        # Verify key pattern
        assert "media/orchestrated/job_xyz/generated_image" in call_kwargs["Key"]

        # Verify returned URL
        assert result.startswith("https://cdn.example.com/media/orchestrated/job_xyz/")

    @pytest.mark.asyncio
    async def test_stage_unsupported_scheme_raises(self):
        """Non-http/data URL scheme raises ValueError."""
        from services.media_orchestrator import _stage_asset_to_r2

        with pytest.raises(ValueError, match="Unsupported asset URL scheme"):
            await _stage_asset_to_r2("ftp://example.com/file.mp3", "job_abc", "track")


class TestStageAssetsToR2:
    """Test _stage_assets_to_r2 with multiple assets (parallel gather)."""

    @pytest.mark.asyncio
    async def test_stage_assets_parallel_staging(self):
        """Multiple assets are staged concurrently via asyncio.gather."""
        staged_calls = []

        async def mock_stage_one(url, job_id, key):
            staged_calls.append((key, url))
            return f"https://cdn.example.com/media/orchestrated/{job_id}/{key}.jpg"

        with patch("services.media_orchestrator._stage_asset_to_r2", side_effect=mock_stage_one):
            from services.media_orchestrator import _stage_assets_to_r2

            result = await _stage_assets_to_r2(
                assets={
                    "background": "https://example.com/bg.jpg",
                    "logo": "https://example.com/logo.png",
                    "overlay": "data:image/png;base64,abc123",
                },
                job_id="job_parallel",
            )

        assert len(result) == 3
        assert "background" in result
        assert "logo" in result
        assert "overlay" in result

    @pytest.mark.asyncio
    async def test_stage_empty_assets_returns_empty_dict(self):
        """Empty assets dict returns empty dict without staging."""
        from services.media_orchestrator import _stage_assets_to_r2

        result = await _stage_assets_to_r2({}, "job_abc")
        assert result == {}


# ============================================================
# Remotion client tests
# ============================================================

class TestCallRemotion:
    """Test _call_remotion: POST render, poll status, timeout."""

    @pytest.mark.asyncio
    async def test_call_remotion_success(self):
        """POST /render → render_id; poll queued → rendering → done with URL."""
        render_id = "render_abc123"
        result_url = "https://cdn.remotion.com/output/render_abc123.mp4"

        poll_responses = [
            {"status": "queued"},
            {"status": "rendering"},
            {"status": "done", "url": result_url},
        ]
        poll_iter = iter(poll_responses)

        mock_post_resp = MagicMock()
        mock_post_resp.raise_for_status = MagicMock()
        mock_post_resp.json = MagicMock(return_value={"render_id": render_id})

        def mock_get_resp():
            data = next(poll_iter)
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=data)
            return resp

        call_count = 0

        async def make_client(*args, **kwargs):
            return mock_client_instance

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_post_resp)
        mock_client_instance.get = AsyncMock(side_effect=lambda url: mock_get_resp())

        with patch("httpx.AsyncClient") as mock_httpx, \
             patch("asyncio.sleep", new=AsyncMock()), \
             patch("services.media_orchestrator.settings") as mock_settings:

            mock_settings.remotion.remotion_service_url = "http://localhost:3001"

            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.media_orchestrator import _call_remotion

            result = await _call_remotion(
                composition_id="StaticImage",
                input_props={"text": "Hello", "brandColor": "#2563EB"},
                render_type="still",
            )

        assert result["url"] == result_url
        assert result["render_id"] == render_id

    @pytest.mark.asyncio
    async def test_call_remotion_failed_status_raises_runtime_error(self):
        """Poll returning 'failed' raises RuntimeError with error message."""
        render_id = "render_failed"

        mock_post_resp = MagicMock()
        mock_post_resp.raise_for_status = MagicMock()
        mock_post_resp.json = MagicMock(return_value={"render_id": render_id})

        mock_poll_resp = MagicMock()
        mock_poll_resp.raise_for_status = MagicMock()
        mock_poll_resp.json = MagicMock(return_value={"status": "failed", "error": "OOM error"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post_resp)
        mock_client.get = AsyncMock(return_value=mock_poll_resp)

        with patch("httpx.AsyncClient") as mock_httpx, \
             patch("asyncio.sleep", new=AsyncMock()), \
             patch("services.media_orchestrator.settings") as mock_settings:

            mock_settings.remotion.remotion_service_url = "http://localhost:3001"

            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.media_orchestrator import _call_remotion

            with pytest.raises(RuntimeError, match="OOM error"):
                await _call_remotion("TestComposition", {})

    @pytest.mark.asyncio
    async def test_call_remotion_timeout_raises_runtime_error(self):
        """asyncio.wait_for timeout raises RuntimeError."""
        mock_post_resp = MagicMock()
        mock_post_resp.raise_for_status = MagicMock()
        mock_post_resp.json = MagicMock(return_value={"render_id": "render_timeout"})

        mock_poll_resp = MagicMock()
        mock_poll_resp.raise_for_status = MagicMock()
        mock_poll_resp.json = MagicMock(return_value={"status": "rendering"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post_resp)
        mock_client.get = AsyncMock(return_value=mock_poll_resp)

        with patch("httpx.AsyncClient") as mock_httpx, \
             patch("asyncio.sleep", new=AsyncMock()), \
             patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()), \
             patch("services.media_orchestrator.settings") as mock_settings:

            mock_settings.remotion.remotion_service_url = "http://localhost:3001"

            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            from services.media_orchestrator import _call_remotion

            with pytest.raises(RuntimeError, match="timed out"):
                await _call_remotion("SlowComposition", {})


# ============================================================
# orchestrate() tests
# ============================================================

class TestOrchestrate:
    """Test orchestrate() — validation and dispatch."""

    @pytest.mark.asyncio
    async def test_orchestrate_invalid_media_type_raises_value_error(self):
        """Unknown media_type raises ValueError with valid types listed."""
        from services.media_orchestrator import MediaBrief, orchestrate

        brief = MediaBrief(
            job_id="job_bad",
            user_id="user_123",
            media_type="hologram",  # not a valid type
            platform="linkedin",
            content_text="Test",
            persona_card={},
        )

        with pytest.raises(ValueError, match="hologram"):
            await orchestrate(brief)

    @pytest.mark.asyncio
    async def test_orchestrate_valid_but_unimplemented_type_raises_not_implemented(self):
        """Valid media_type with no registered handler raises NotImplementedError."""
        from services.media_orchestrator import MediaBrief, orchestrate, _MEDIA_TYPE_HANDLERS

        # Ensure "static_image" has no handler registered (it shouldn't in Plan 02)
        # Save and restore to avoid cross-test pollution
        original_handler = _MEDIA_TYPE_HANDLERS.pop("static_image", None)

        try:
            brief = MediaBrief(
                job_id="job_unimpl",
                user_id="user_123",
                media_type="static_image",
                platform="linkedin",
                content_text="Test",
                persona_card={},
            )

            with pytest.raises(NotImplementedError, match="static_image"):
                await orchestrate(brief)
        finally:
            # Restore original handler if it existed
            if original_handler is not None:
                _MEDIA_TYPE_HANDLERS["static_image"] = original_handler

    @pytest.mark.asyncio
    async def test_orchestrate_dispatches_to_registered_handler(self):
        """Registered handler is called and its result is returned."""
        from services.media_orchestrator import (
            MediaBrief, orchestrate, register_media_handler, _MEDIA_TYPE_HANDLERS
        )

        called_with = {}

        @register_media_handler("test_type_orchestrate")
        async def fake_handler(brief, cost_cap):
            called_with["brief"] = brief
            called_with["cost_cap"] = cost_cap
            return {"url": "https://cdn.example.com/result.jpg", "render_id": "r123", "credits_consumed": 8}

        # Temporarily add to MEDIA_TYPE_COST_CAPS
        from services.media_orchestrator import MEDIA_TYPE_COST_CAPS
        MEDIA_TYPE_COST_CAPS["test_type_orchestrate"] = 15

        try:
            brief = MediaBrief(
                job_id="job_dispatch",
                user_id="user_123",
                media_type="test_type_orchestrate",
                platform="linkedin",
                content_text="Test dispatch",
                persona_card={},
            )

            result = await orchestrate(brief)

            assert result["url"] == "https://cdn.example.com/result.jpg"
            assert result["media_type"] == "test_type_orchestrate"
            assert result["job_id"] == "job_dispatch"
            assert result["credits_consumed"] == 8
            assert called_with["cost_cap"] == 15
        finally:
            # Cleanup test-only entries
            _MEDIA_TYPE_HANDLERS.pop("test_type_orchestrate", None)
            MEDIA_TYPE_COST_CAPS.pop("test_type_orchestrate", None)

    def test_orchestrate_is_coroutine(self):
        """orchestrate() is async (returns a coroutine)."""
        import asyncio
        from services.media_orchestrator import orchestrate, MediaBrief

        brief = MediaBrief(
            job_id="j", user_id="u", media_type="static_image",
            platform="linkedin", content_text="x", persona_card={}
        )
        coro = orchestrate(brief)
        assert asyncio.iscoroutine(coro)
        # Close to avoid warnings
        coro.close()


# ============================================================
# Static format handler tests (Plan 03)
# ============================================================

def _make_brief(**kwargs):
    """Helper to create a MediaBrief with sensible defaults."""
    from services.media_orchestrator import MediaBrief
    defaults = {
        "job_id": "job_test",
        "user_id": "user_test",
        "media_type": "static_image",
        "platform": "linkedin",
        "content_text": "Test content text",
        "persona_card": {"archetype": "Thought Leader"},
        "brand_color": "#2563EB",
        "style": "minimal",
    }
    defaults.update(kwargs)
    return MediaBrief(**defaults)


def _make_ledger_mocks():
    """Return AsyncMock instances for all _ledger_* functions."""
    ledger_stage = AsyncMock(return_value="ledger_id_123")
    ledger_update = AsyncMock(return_value=None)
    ledger_check_cap = AsyncMock(return_value=True)
    ledger_skip_remaining = AsyncMock(return_value=None)
    return ledger_stage, ledger_update, ledger_check_cap, ledger_skip_remaining


class TestStaticImageHandler:
    """Tests for _handle_static_image and orchestrate("static_image")."""

    @pytest.mark.asyncio
    async def test_static_image_full_pipeline(self):
        """static_image: generates image, stages to R2, calls StaticImageCard(layout=standard)."""
        from services.media_orchestrator import orchestrate

        ledger_stage, ledger_update, ledger_check_cap, ledger_skip = _make_ledger_mocks()

        designer_result = {"image_url": "https://cdn.fal.ai/test.png", "generated": True}
        r2_url = "https://r2.example.com/staged.png"
        remotion_result = {"url": "https://r2.example.com/render.png", "render_id": "r123"}

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip), \
             patch("services.media_orchestrator._get_designer", return_value=AsyncMock(return_value=designer_result)), \
             patch("services.media_orchestrator._stage_asset_to_r2", AsyncMock(return_value=r2_url)), \
             patch("services.media_orchestrator._call_remotion", AsyncMock(return_value=remotion_result)):

            from services.media_orchestrator import _call_remotion as mock_remotion
            brief = _make_brief(media_type="static_image")
            result = await orchestrate(brief)

        # Verify result
        assert result["url"] == "https://r2.example.com/render.png"
        assert result["media_type"] == "static_image"
        assert result["job_id"] == "job_test"

        # Verify ledger was called twice (image_generation + remotion_render)
        assert ledger_stage.call_count == 2
        stage_calls = [call[0][2] for call in ledger_stage.call_args_list]
        assert "image_generation" in stage_calls
        assert "remotion_render" in stage_calls

    @pytest.mark.asyncio
    async def test_static_image_remotion_gets_standard_layout(self):
        """static_image: _call_remotion receives layout='standard' in inputProps."""
        from services.media_orchestrator import orchestrate

        ledger_stage, ledger_update, ledger_check_cap, ledger_skip = _make_ledger_mocks()
        call_remotion = AsyncMock(return_value={"url": "https://r2.example.com/render.png", "render_id": "r1"})

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip), \
             patch("services.media_orchestrator._get_designer", return_value=AsyncMock(return_value={"image_url": "https://cdn.fal.ai/t.png"})), \
             patch("services.media_orchestrator._stage_asset_to_r2", AsyncMock(return_value="https://r2.example.com/bg.png")), \
             patch("services.media_orchestrator._call_remotion", call_remotion):

            brief = _make_brief(media_type="static_image")
            await orchestrate(brief)

        # Assert _call_remotion called with StaticImageCard and layout="standard"
        call_remotion.assert_called_once()
        args, kwargs = call_remotion.call_args
        assert args[0] == "StaticImageCard"
        assert args[1]["layout"] == "standard"


class TestQuoteCardHandler:
    """Tests for _handle_quote_card handler."""

    @pytest.mark.asyncio
    async def test_quote_card_uses_quote_layout(self):
        """quote_card: _call_remotion receives layout='quote' in inputProps."""
        from services.media_orchestrator import orchestrate

        ledger_stage, ledger_update, ledger_check_cap, ledger_skip = _make_ledger_mocks()
        call_remotion = AsyncMock(return_value={"url": "https://r2.example.com/render.png", "render_id": "r2"})

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip), \
             patch("services.media_orchestrator._get_designer", return_value=AsyncMock(return_value={"image_url": "https://cdn.fal.ai/bg.png"})), \
             patch("services.media_orchestrator._stage_asset_to_r2", AsyncMock(return_value="https://r2.example.com/bg.png")), \
             patch("services.media_orchestrator._call_remotion", call_remotion):

            brief = _make_brief(media_type="quote_card", content_text="The best way to predict the future is to create it.")
            await orchestrate(brief)

        call_remotion.assert_called_once()
        args, _ = call_remotion.call_args
        assert args[0] == "StaticImageCard"
        assert args[1]["layout"] == "quote"
        # Quote text should be in the "text" field
        assert args[1]["text"] == "The best way to predict the future is to create it."


class TestMemeHandler:
    """Tests for _handle_meme handler — including text splitting."""

    @pytest.mark.asyncio
    async def test_meme_splits_text_on_double_newline(self):
        """meme: content_text split on double-newline into topText and bottomText."""
        from services.media_orchestrator import orchestrate

        ledger_stage, ledger_update, ledger_check_cap, ledger_skip = _make_ledger_mocks()
        call_remotion = AsyncMock(return_value={"url": "https://r2.example.com/render.png", "render_id": "r3"})

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip), \
             patch("services.media_orchestrator._get_designer", return_value=AsyncMock(return_value={"image_url": "https://cdn.fal.ai/meme.png"})), \
             patch("services.media_orchestrator._stage_asset_to_r2", AsyncMock(return_value="https://r2.example.com/meme.png")), \
             patch("services.media_orchestrator._call_remotion", call_remotion):

            brief = _make_brief(media_type="meme", content_text="Top line\n\nBottom line")
            await orchestrate(brief)

        call_remotion.assert_called_once()
        args, _ = call_remotion.call_args
        assert args[0] == "StaticImageCard"
        assert args[1]["layout"] == "meme"
        assert args[1]["topText"] == "Top line"
        assert args[1]["bottomText"] == "Bottom line"

    @pytest.mark.asyncio
    async def test_meme_single_line_no_bottom_text(self):
        """meme: content_text without double-newline -> topText=full text, bottomText=''."""
        from services.media_orchestrator import orchestrate

        ledger_stage, ledger_update, ledger_check_cap, ledger_skip = _make_ledger_mocks()
        call_remotion = AsyncMock(return_value={"url": "https://r2.example.com/render.png", "render_id": "r4"})

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip), \
             patch("services.media_orchestrator._get_designer", return_value=AsyncMock(return_value={"image_url": "https://cdn.fal.ai/meme.png"})), \
             patch("services.media_orchestrator._stage_asset_to_r2", AsyncMock(return_value="https://r2.example.com/meme.png")), \
             patch("services.media_orchestrator._call_remotion", call_remotion):

            brief = _make_brief(media_type="meme", content_text="Only top text")
            await orchestrate(brief)

        args, _ = call_remotion.call_args
        assert args[1]["topText"] == "Only top text"
        assert args[1]["bottomText"] == ""


class TestInfographicHandler:
    """Tests for _handle_infographic handler."""

    @pytest.mark.asyncio
    async def test_infographic_no_image_generation(self):
        """infographic: designer.py is NOT called — pure Remotion composition."""
        from services.media_orchestrator import orchestrate

        ledger_stage, ledger_update, ledger_check_cap, ledger_skip = _make_ledger_mocks()
        call_remotion = AsyncMock(return_value={"url": "https://r2.example.com/infographic.png", "render_id": "r5"})
        designer_mock = MagicMock()  # NOT AsyncMock — should never be awaited

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip), \
             patch("services.media_orchestrator._get_designer", designer_mock), \
             patch("services.media_orchestrator._call_remotion", call_remotion):

            brief = _make_brief(
                media_type="infographic",
                data_points=[{"label": "Users", "value": "1000"}, {"label": "Revenue", "value": "$50k"}],
            )
            await orchestrate(brief)

        # designer was NOT called
        designer_mock.assert_not_called()

        # Remotion was called with Infographic composition
        call_remotion.assert_called_once()
        args, _ = call_remotion.call_args
        assert args[0] == "Infographic"
        assert args[1]["dataPoints"] == [{"label": "Users", "value": "1000"}, {"label": "Revenue", "value": "$50k"}]

    @pytest.mark.asyncio
    async def test_infographic_missing_data_points_raises_value_error(self):
        """infographic: raises ValueError when data_points is None."""
        from services.media_orchestrator import orchestrate

        brief = _make_brief(media_type="infographic", data_points=None)

        with pytest.raises(ValueError, match="data_points"):
            await orchestrate(brief)

    @pytest.mark.asyncio
    async def test_infographic_empty_data_points_raises_value_error(self):
        """infographic: raises ValueError when data_points is empty list."""
        from services.media_orchestrator import orchestrate

        brief = _make_brief(media_type="infographic", data_points=[])

        with pytest.raises(ValueError, match="data_points"):
            await orchestrate(brief)


class TestCostCapEnforcement:
    """Tests for cost cap enforcement across static handlers."""

    @pytest.mark.asyncio
    async def test_cost_cap_exceeded_raises_runtime_error(self):
        """Cost cap exceeded: raises RuntimeError and calls _ledger_skip_remaining."""
        from services.media_orchestrator import orchestrate

        ledger_stage = AsyncMock(return_value="ledger_id_123")
        ledger_update = AsyncMock(return_value=None)
        # Return False on first check — cap already exceeded
        ledger_check_cap = AsyncMock(return_value=False)
        ledger_skip = AsyncMock(return_value=None)

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip):

            brief = _make_brief(media_type="static_image")

            with pytest.raises(RuntimeError, match="Cost cap exceeded"):
                await orchestrate(brief)

        # _ledger_skip_remaining must be called when cap exceeded
        ledger_skip.assert_called_once()

    @pytest.mark.asyncio
    async def test_provider_failure_marks_ledger_failed(self):
        """Provider error: _ledger_update called with status='failed' and reason."""
        from services.media_orchestrator import orchestrate

        ledger_stage = AsyncMock(return_value="ledger_img_id")
        ledger_update = AsyncMock(return_value=None)
        ledger_check_cap = AsyncMock(return_value=True)
        ledger_skip = AsyncMock(return_value=None)

        # Designer raises an exception
        failing_designer = AsyncMock(side_effect=Exception("Provider error"))

        with patch("services.media_orchestrator._ledger_stage", ledger_stage), \
             patch("services.media_orchestrator._ledger_update", ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap", ledger_check_cap), \
             patch("services.media_orchestrator._ledger_skip_remaining", ledger_skip), \
             patch("services.media_orchestrator._get_designer", return_value=failing_designer):

            brief = _make_brief(media_type="static_image")

            with pytest.raises(Exception, match="Provider error"):
                await orchestrate(brief)

        # Verify _ledger_update called with "failed" status and reason containing "Provider error"
        ledger_update.assert_called_once()
        call_args = ledger_update.call_args[0]
        assert call_args[1] == "failed"
        assert "Provider error" in call_args[2]
