"""Comprehensive tests for MediaOrchestrator — all 8 format handlers.

Covers:
- TestOrchestrateDispatch: orchestrate() routes to correct handler or raises ValueError
- TestStaticImageHandler: designer → R2 staging → Remotion StaticImageCard
- TestQuoteCardHandler: quote layout, brand_color passthrough
- TestMemeHandler: top/bottom text split, single-line fallback
- TestInfographicHandler: data_points passthrough, Infographic composition
- TestCarouselHandler: per-slide generation, all slides staged to R2, ImageCarousel
- TestTalkingHeadHandler: voice → avatar → Remotion TalkingHeadOverlay
- TestShortFormVideoHandler: voice + B-roll + optional music → ShortFormVideo
- TestTextOnVideoHandler: user-supplied video staged → ShortFormVideo with text overlay
- TestCreditLedgerPartialFailure: partial failure accounting, cap enforcement
- TestR2Staging: HTTP URL download, base64 decode, parallel gather

All tests mock out every external call (designers, voice, avatar, video agents,
R2 client, Remotion service, MongoDB). No network calls are made.
"""

import asyncio
import base64
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Ensure the backend directory is on the path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ============================================================
# HELPER: MediaBrief factory
# ============================================================

def make_brief(**kwargs):
    """Return a MediaBrief with sensible defaults — override any field via kwargs."""
    from services.media_orchestrator import MediaBrief

    defaults = dict(
        job_id="job_test_001",
        user_id="user_test_001",
        media_type="static_image",
        platform="linkedin",
        content_text="Why founders build the wrong things first",
        persona_card={"name": "Alex Chen", "title": "Founder", "archetype": "Thought Leader"},
        style="minimal",
        brand_color="#2563EB",
    )
    defaults.update(kwargs)
    return MediaBrief(**defaults)


# ============================================================
# HELPER: common mock setups
# ============================================================

def _make_mock_db():
    """Return a mock db with media_pipeline_ledger collection."""
    mock_db = MagicMock()
    mock_db.media_pipeline_ledger.insert_one = AsyncMock()
    mock_db.media_pipeline_ledger.update_one = AsyncMock()
    mock_db.media_pipeline_ledger.update_many = AsyncMock()

    # Aggregate returns an async cursor (empty by default — cap always passes)
    async def _agg_cursor_empty(pipeline):
        return
        yield  # pragma: no cover — makes this an async generator

    mock_db.media_pipeline_ledger.aggregate = MagicMock(
        side_effect=lambda p: _agg_cursor_empty(p)
    )
    return mock_db


def _designer_mock(image_url="https://provider.example.com/image.jpg"):
    """Return an async callable that mimics generate_image()."""
    async def _generate(**kwargs):
        return {"image_url": image_url}
    return _generate


def _voice_mock(audio_url="https://provider.example.com/voice.mp3"):
    """Return an async callable that mimics generate_voice_narration()."""
    async def _generate(**kwargs):
        return {"audio_url": audio_url}
    return _generate


def _avatar_mock(video_url="https://provider.example.com/avatar.mp4", duration=10.0):
    """Return an async callable that mimics generate_avatar_video()."""
    async def _generate(**kwargs):
        return {"video_url": video_url, "duration": duration}
    return _generate


def _broll_mock(video_url="https://provider.example.com/broll.mp4"):
    """Return an async callable that mimics generate_video()."""
    async def _generate(**kwargs):
        return {"video_url": video_url}
    return _generate


_STAGED_URL_TPL = "https://r2.example.com/staged/{key}"
_REMOTION_OUTPUT_URL = "https://r2.example.com/rendered/output.mp4"


async def _mock_stage_asset(asset_url, job_id, asset_key):
    return _STAGED_URL_TPL.format(key=asset_key)


async def _mock_call_remotion(composition_id, input_props, render_type="still"):
    return {"url": _REMOTION_OUTPUT_URL, "render_id": "render_abc123"}


# ============================================================
# TestOrchestrateDispatch
# ============================================================

class TestOrchestrateDispatch:
    """orchestrate() routes media_type to the correct handler."""

    @pytest.mark.asyncio
    async def test_orchestrate_dispatches_static_image(self):
        """orchestrate() calls _handle_static_image for media_type='static_image'."""
        brief = make_brief(media_type="static_image")

        handler_called = []

        async def fake_static_handler(b, cap):
            handler_called.append(b.media_type)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid", "credits_consumed": 13}

        with patch("services.media_orchestrator._MEDIA_TYPE_HANDLERS",
                   {"static_image": fake_static_handler}), \
             patch("services.media_orchestrator.MEDIA_TYPE_COST_CAPS",
                   {"static_image": 15}), \
             patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("agents.qc.validate_media_output", new_callable=AsyncMock,
                   return_value={"passed": True}):

            from services.media_orchestrator import orchestrate
            await orchestrate(brief)

        assert handler_called == ["static_image"]

    @pytest.mark.asyncio
    async def test_orchestrate_dispatches_carousel(self):
        """orchestrate() calls the carousel handler for media_type='carousel'."""
        brief = make_brief(
            media_type="carousel",
            slides=[{"text": "Slide 1"}, {"text": "Slide 2"}],
        )

        handler_called = []

        async def fake_carousel(b, cap):
            handler_called.append(b.media_type)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid", "credits_consumed": 21}

        with patch("services.media_orchestrator._MEDIA_TYPE_HANDLERS",
                   {"carousel": fake_carousel}), \
             patch("services.media_orchestrator.MEDIA_TYPE_COST_CAPS", {"carousel": 40}), \
             patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("agents.qc.validate_media_output", new_callable=AsyncMock,
                   return_value={"passed": True}):

            from services.media_orchestrator import orchestrate
            await orchestrate(brief)

        assert handler_called == ["carousel"]

    @pytest.mark.asyncio
    async def test_orchestrate_dispatches_talking_head(self):
        """orchestrate() calls the talking_head handler for media_type='talking_head'."""
        brief = make_brief(media_type="talking_head", avatar_id="heygen_001")

        handler_called = []

        async def fake_talking_head(b, cap):
            handler_called.append(b.media_type)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid", "credits_consumed": 55}

        with patch("services.media_orchestrator._MEDIA_TYPE_HANDLERS",
                   {"talking_head": fake_talking_head}), \
             patch("services.media_orchestrator.MEDIA_TYPE_COST_CAPS", {"talking_head": 80}), \
             patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("agents.qc.validate_media_output", new_callable=AsyncMock,
                   return_value={"passed": True}):

            from services.media_orchestrator import orchestrate
            await orchestrate(brief)

        assert handler_called == ["talking_head"]

    @pytest.mark.asyncio
    async def test_orchestrate_raises_for_unknown_type(self):
        """orchestrate() raises ValueError for an unrecognised media_type."""
        brief = make_brief(media_type="hologram")

        from services.media_orchestrator import orchestrate
        with pytest.raises(ValueError, match="Unknown media_type"):
            await orchestrate(brief)


# ============================================================
# TestStaticImageHandler
# ============================================================

class TestStaticImageHandler:
    """Tests for _handle_static_image."""

    @pytest.mark.asyncio
    async def test_static_image_calls_designer_then_remotion(self):
        """_handle_static_image calls designer, stages to R2, calls Remotion StaticImageCard."""
        brief = make_brief(media_type="static_image")
        stage_calls = []
        remotion_calls = []

        async def mock_stage(url, job_id, key):
            stage_calls.append((url, key))
            return _STAGED_URL_TPL.format(key=key)

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_calls.append((composition_id, input_props))
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2", side_effect=mock_stage), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_static_image, MEDIA_TYPE_COST_CAPS
            result = await _handle_static_image(brief, MEDIA_TYPE_COST_CAPS["static_image"])

        # R2 staging was called with the designer image URL
        assert len(stage_calls) == 1
        assert stage_calls[0][0] == "https://provider.example.com/image.jpg"
        assert stage_calls[0][1] == "background_image"

        # Remotion was called with StaticImageCard composition
        assert len(remotion_calls) == 1
        assert remotion_calls[0][0] == "StaticImageCard"

    @pytest.mark.asyncio
    async def test_static_image_ledger_records_image_generation_stage(self):
        """_handle_static_image records image_generation stage in ledger."""
        brief = make_brief(media_type="static_image")
        ledger_stages_recorded = []

        async def mock_ledger_stage(job_id, user_id, stage, provider, credits):
            ledger_stages_recorded.append((stage, credits))
            return "ledger_id_001"

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion), \
             patch("services.media_orchestrator._ledger_stage",
                   side_effect=mock_ledger_stage), \
             patch("services.media_orchestrator._ledger_update", new_callable=AsyncMock), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=True), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   new_callable=AsyncMock):

            from services.media_orchestrator import _handle_static_image, STAGE_COSTS, MEDIA_TYPE_COST_CAPS
            await _handle_static_image(brief, MEDIA_TYPE_COST_CAPS["static_image"])

        stage_names = [s[0] for s in ledger_stages_recorded]
        assert "image_generation" in stage_names

        # Credit cost matches STAGE_COSTS
        image_gen_entry = next(s for s in ledger_stages_recorded if s[0] == "image_generation")
        assert image_gen_entry[1] == STAGE_COSTS["image_generation"]

    @pytest.mark.asyncio
    async def test_static_image_returns_rendered_url(self):
        """_handle_static_image result contains 'url' pointing to Remotion output."""
        brief = make_brief(media_type="static_image")

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion):

            from services.media_orchestrator import _handle_static_image, MEDIA_TYPE_COST_CAPS
            result = await _handle_static_image(brief, MEDIA_TYPE_COST_CAPS["static_image"])

        assert "url" in result
        assert result["url"] == _REMOTION_OUTPUT_URL


# ============================================================
# TestQuoteCardHandler
# ============================================================

class TestQuoteCardHandler:
    """Tests for _handle_quote_card."""

    @pytest.mark.asyncio
    async def test_quote_card_uses_quote_layout_composition(self):
        """_handle_quote_card passes layout='quote' to Remotion."""
        brief = make_brief(media_type="quote_card")
        remotion_calls = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_calls.append((composition_id, input_props))
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_quote_card, MEDIA_TYPE_COST_CAPS
            await _handle_quote_card(brief, MEDIA_TYPE_COST_CAPS["quote_card"])

        assert len(remotion_calls) == 1
        assert remotion_calls[0][0] == "StaticImageCard"
        assert remotion_calls[0][1]["layout"] == "quote"

    @pytest.mark.asyncio
    async def test_quote_card_passes_brand_color_from_brief(self):
        """_handle_quote_card passes brief.brand_color to Remotion input_props."""
        brief = make_brief(media_type="quote_card", brand_color="#FF5733")
        remotion_calls = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_calls.append(input_props)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_quote_card, MEDIA_TYPE_COST_CAPS
            await _handle_quote_card(brief, MEDIA_TYPE_COST_CAPS["quote_card"])

        assert remotion_calls[0]["brandColor"] == "#FF5733"


# ============================================================
# TestMemeHandler
# ============================================================

class TestMemeHandler:
    """Tests for _handle_meme."""

    @pytest.mark.asyncio
    async def test_meme_splits_content_into_top_bottom(self):
        """content_text with double newline is split into topText + bottomText."""
        brief = make_brief(
            media_type="meme",
            content_text="When your CEO says\n\nship it anyway",
        )
        remotion_props = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_props.append(input_props)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_meme, MEDIA_TYPE_COST_CAPS
            await _handle_meme(brief, MEDIA_TYPE_COST_CAPS["meme"])

        assert len(remotion_props) == 1
        assert remotion_props[0]["topText"] == "When your CEO says"
        assert remotion_props[0]["bottomText"] == "ship it anyway"
        assert remotion_props[0]["layout"] == "meme"

    @pytest.mark.asyncio
    async def test_meme_single_line_has_no_bottom_text(self):
        """content_text without double newline gives empty bottomText."""
        brief = make_brief(
            media_type="meme",
            content_text="Ship it",
        )
        remotion_props = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_props.append(input_props)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_meme, MEDIA_TYPE_COST_CAPS
            await _handle_meme(brief, MEDIA_TYPE_COST_CAPS["meme"])

        bottom = remotion_props[0].get("bottomText", "")
        assert bottom == ""


# ============================================================
# TestInfographicHandler
# ============================================================

class TestInfographicHandler:
    """Tests for _handle_infographic."""

    @pytest.mark.asyncio
    async def test_infographic_passes_data_points(self):
        """_handle_infographic passes data_points to Remotion Infographic composition."""
        data_pts = [
            {"label": "Revenue", "value": "10M"},
            {"label": "ARR Growth", "value": "3x"},
        ]
        brief = make_brief(media_type="infographic", data_points=data_pts)
        remotion_calls = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_calls.append((composition_id, input_props))
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_infographic, MEDIA_TYPE_COST_CAPS
            await _handle_infographic(brief, MEDIA_TYPE_COST_CAPS["infographic"])

        assert len(remotion_calls) == 1
        assert remotion_calls[0][1]["dataPoints"] == data_pts

    @pytest.mark.asyncio
    async def test_infographic_uses_correct_composition(self):
        """_handle_infographic calls Remotion with 'Infographic' composition."""
        brief = make_brief(
            media_type="infographic",
            data_points=[{"label": "X", "value": "1"}],
        )
        composition_used = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            composition_used.append(composition_id)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_infographic, MEDIA_TYPE_COST_CAPS
            await _handle_infographic(brief, MEDIA_TYPE_COST_CAPS["infographic"])

        assert composition_used == ["Infographic"]

    @pytest.mark.asyncio
    async def test_infographic_raises_when_no_data_points(self):
        """_handle_infographic raises ValueError when data_points is None."""
        brief = make_brief(media_type="infographic", data_points=None)

        from services.media_orchestrator import _handle_infographic, MEDIA_TYPE_COST_CAPS
        with pytest.raises(ValueError, match="data_points"):
            await _handle_infographic(brief, MEDIA_TYPE_COST_CAPS["infographic"])


# ============================================================
# TestCarouselHandler
# ============================================================

class TestCarouselHandler:
    """Tests for _handle_carousel."""

    @pytest.mark.asyncio
    async def test_carousel_generates_per_slide_images(self):
        """_handle_carousel calls designer once per slide."""
        slides = [{"text": f"Slide {i}"} for i in range(3)]
        brief = make_brief(media_type="carousel", slides=slides)

        designer_call_count = []

        async def mock_generate(**kwargs):
            designer_call_count.append(1)
            return {"image_url": "https://provider.example.com/img.jpg"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_carousel",
                   return_value=mock_generate), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion):

            from services.media_orchestrator import _handle_carousel, MEDIA_TYPE_COST_CAPS
            await _handle_carousel(brief, MEDIA_TYPE_COST_CAPS["carousel"])

        assert len(designer_call_count) == 3

    @pytest.mark.asyncio
    async def test_carousel_stages_all_slide_assets_to_r2(self):
        """_handle_carousel stages each slide image to R2."""
        slides = [{"text": "A"}, {"text": "B"}, {"text": "C"}]
        brief = make_brief(media_type="carousel", slides=slides)

        staged_keys = []

        async def mock_stage(asset_url, job_id, key):
            staged_keys.append(key)
            return _STAGED_URL_TPL.format(key=key)

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_carousel",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=mock_stage), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion):

            from services.media_orchestrator import _handle_carousel, MEDIA_TYPE_COST_CAPS
            await _handle_carousel(brief, MEDIA_TYPE_COST_CAPS["carousel"])

        # One staging call per slide (slide_0, slide_1, slide_2)
        slide_keys = [k for k in staged_keys if k.startswith("slide_")]
        assert len(slide_keys) == 3

    @pytest.mark.asyncio
    async def test_carousel_calls_remotion_with_slides_array(self):
        """_handle_carousel passes a 'slides' array to Remotion ImageCarousel."""
        slides = [{"text": "S1"}, {"text": "S2"}]
        brief = make_brief(media_type="carousel", slides=slides)

        remotion_calls = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_calls.append((composition_id, input_props))
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_carousel",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_carousel, MEDIA_TYPE_COST_CAPS
            await _handle_carousel(brief, MEDIA_TYPE_COST_CAPS["carousel"])

        assert len(remotion_calls) == 1
        assert remotion_calls[0][0] == "ImageCarousel"
        assert "slides" in remotion_calls[0][1]
        assert len(remotion_calls[0][1]["slides"]) == 2


# ============================================================
# TestTalkingHeadHandler
# ============================================================

class TestTalkingHeadHandler:
    """Tests for _handle_talking_head."""

    @pytest.mark.asyncio
    async def test_talking_head_calls_avatar_then_remotion(self):
        """_handle_talking_head calls avatar generation then Remotion TalkingHeadOverlay."""
        brief = make_brief(media_type="talking_head", avatar_id="heygen_001")

        avatar_called = []
        remotion_calls = []

        async def mock_avatar(**kwargs):
            avatar_called.append(kwargs.get("avatar_id"))
            return {"video_url": "https://heygen.example.com/avatar.mp4", "duration": 15.0}

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_calls.append((composition_id, input_props))
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_avatar_video",
                   return_value=mock_avatar), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_talking_head, MEDIA_TYPE_COST_CAPS
            await _handle_talking_head(brief, MEDIA_TYPE_COST_CAPS["talking_head"])

        assert len(avatar_called) == 1
        assert avatar_called[0] == "heygen_001"
        assert len(remotion_calls) == 1
        assert remotion_calls[0][0] == "TalkingHeadOverlay"

    @pytest.mark.asyncio
    async def test_talking_head_stages_avatar_to_r2(self):
        """_handle_talking_head stages the avatar video URL to R2 before Remotion."""
        brief = make_brief(media_type="talking_head", avatar_id="heygen_001")
        staged = []

        async def mock_stage(asset_url, job_id, key):
            staged.append((asset_url, key))
            return _STAGED_URL_TPL.format(key=key)

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_avatar_video",
                   return_value=_avatar_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=mock_stage), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion):

            from services.media_orchestrator import _handle_talking_head, MEDIA_TYPE_COST_CAPS
            await _handle_talking_head(brief, MEDIA_TYPE_COST_CAPS["talking_head"])

        asset_keys = [s[1] for s in staged]
        assert "avatar_video" in asset_keys

    @pytest.mark.asyncio
    async def test_talking_head_ledger_records_avatar_stage(self):
        """_handle_talking_head records avatar_generation stage in ledger."""
        brief = make_brief(media_type="talking_head", avatar_id="heygen_001")
        stages_recorded = []

        async def mock_ledger_stage(job_id, user_id, stage, provider, credits):
            stages_recorded.append(stage)
            return f"lid_{stage}"

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_avatar_video",
                   return_value=_avatar_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion), \
             patch("services.media_orchestrator._ledger_stage",
                   side_effect=mock_ledger_stage), \
             patch("services.media_orchestrator._ledger_update", new_callable=AsyncMock), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=True), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   new_callable=AsyncMock):

            from services.media_orchestrator import _handle_talking_head, MEDIA_TYPE_COST_CAPS
            await _handle_talking_head(brief, MEDIA_TYPE_COST_CAPS["talking_head"])

        assert "avatar_generation" in stages_recorded
        assert "remotion_render" in stages_recorded


# ============================================================
# TestShortFormVideoHandler
# ============================================================

class TestShortFormVideoHandler:
    """Tests for _handle_short_form_video."""

    @pytest.mark.asyncio
    async def test_short_form_generates_voice_broll_and_renders(self):
        """_handle_short_form_video calls voice, B-roll, and Remotion."""
        brief = make_brief(media_type="short_form_video", voice_id="el_001")

        voice_called = []
        broll_called = []
        remotion_calls = []

        async def mock_voice(**kwargs):
            voice_called.append(1)
            return {"audio_url": "https://provider.example.com/voice.mp3"}

        async def mock_broll(**kwargs):
            broll_called.append(1)
            return {"video_url": "https://provider.example.com/broll.mp4"}

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_calls.append(composition_id)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_voice",
                   return_value=mock_voice), \
             patch("services.media_orchestrator._get_broll_video",
                   return_value=mock_broll), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_short_form_video, MEDIA_TYPE_COST_CAPS
            await _handle_short_form_video(brief, MEDIA_TYPE_COST_CAPS["short_form_video"])

        assert len(voice_called) == 1
        assert len(broll_called) == 1
        assert len(remotion_calls) == 1
        assert remotion_calls[0] == "ShortFormVideo"

    @pytest.mark.asyncio
    async def test_short_form_stages_music_when_provided(self):
        """When brief.music_url is set, it is passed to Remotion input_props."""
        brief = make_brief(
            media_type="short_form_video",
            music_url="https://example.com/music.mp3",
        )
        remotion_props = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_props.append(input_props)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_voice",
                   return_value=_voice_mock()), \
             patch("services.media_orchestrator._get_broll_video",
                   return_value=_broll_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_short_form_video, MEDIA_TYPE_COST_CAPS
            await _handle_short_form_video(brief, MEDIA_TYPE_COST_CAPS["short_form_video"])

        # musicUrl should be passed through to Remotion
        assert remotion_props[0]["musicUrl"] == "https://example.com/music.mp3"

    @pytest.mark.asyncio
    async def test_short_form_ledger_records_all_stages(self):
        """_handle_short_form_video records voice_generation and broll_generation in ledger."""
        brief = make_brief(media_type="short_form_video")
        stages_recorded = []

        async def mock_ledger_stage(job_id, user_id, stage, provider, credits):
            stages_recorded.append(stage)
            return f"lid_{stage}"

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_voice",
                   return_value=_voice_mock()), \
             patch("services.media_orchestrator._get_broll_video",
                   return_value=_broll_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion), \
             patch("services.media_orchestrator._ledger_stage",
                   side_effect=mock_ledger_stage), \
             patch("services.media_orchestrator._ledger_update", new_callable=AsyncMock), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=True), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   new_callable=AsyncMock):

            from services.media_orchestrator import _handle_short_form_video, MEDIA_TYPE_COST_CAPS
            await _handle_short_form_video(brief, MEDIA_TYPE_COST_CAPS["short_form_video"])

        assert "voice_generation" in stages_recorded
        assert "broll_generation" in stages_recorded


# ============================================================
# TestTextOnVideoHandler
# ============================================================

class TestTextOnVideoHandler:
    """Tests for _handle_text_on_video."""

    @pytest.mark.asyncio
    async def test_text_on_video_uses_user_uploaded_video(self):
        """_handle_text_on_video stages brief.video_url to R2 and passes it to Remotion."""
        brief = make_brief(
            media_type="text_on_video",
            video_url="https://user.example.com/my_video.mp4",
        )
        staged = []
        remotion_props = []

        async def mock_stage(asset_url, job_id, key):
            staged.append((asset_url, key))
            return _STAGED_URL_TPL.format(key=key)

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_props.append(input_props)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=mock_stage), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_text_on_video, MEDIA_TYPE_COST_CAPS
            await _handle_text_on_video(brief, MEDIA_TYPE_COST_CAPS["text_on_video"])

        # The user video was staged
        staged_urls = [s[0] for s in staged]
        assert "https://user.example.com/my_video.mp4" in staged_urls

        # Remotion received the staged R2 URL (not the original user URL)
        assert remotion_props[0]["segments"][0]["url"] == _STAGED_URL_TPL.format(key="input_video")

    @pytest.mark.asyncio
    async def test_text_on_video_generates_text_overlay(self):
        """_handle_text_on_video includes content_text in the Remotion segment."""
        brief = make_brief(
            media_type="text_on_video",
            video_url="https://user.example.com/clip.mp4",
            content_text="Join the waitlist today",
        )
        remotion_props = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_props.append(input_props)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion):

            from services.media_orchestrator import _handle_text_on_video, MEDIA_TYPE_COST_CAPS
            await _handle_text_on_video(brief, MEDIA_TYPE_COST_CAPS["text_on_video"])

        # The content_text is in the segment's text field
        segments = remotion_props[0]["segments"]
        assert any(seg.get("text") == "Join the waitlist today" for seg in segments)

    @pytest.mark.asyncio
    async def test_text_on_video_raises_when_no_video_url(self):
        """_handle_text_on_video raises ValueError when video_url is None."""
        brief = make_brief(media_type="text_on_video", video_url=None)

        from services.media_orchestrator import _handle_text_on_video, MEDIA_TYPE_COST_CAPS
        with pytest.raises(ValueError, match="video_url"):
            await _handle_text_on_video(brief, MEDIA_TYPE_COST_CAPS["text_on_video"])


# ============================================================
# TestCreditLedgerPartialFailure
# ============================================================

class TestCreditLedgerPartialFailure:
    """Credit ledger partial-failure accounting tests."""

    @pytest.mark.asyncio
    async def test_provider_failure_marks_stage_as_failed(self):
        """When designer raises, the image_generation ledger entry is marked 'failed'."""
        brief = make_brief(media_type="static_image")
        update_calls = []

        async def mock_ledger_stage(job_id, user_id, stage, provider, credits):
            return f"lid_{stage}"

        async def mock_ledger_update(ledger_id, status, reason=None):
            update_calls.append((ledger_id, status))

        async def failing_designer(**kwargs):
            raise RuntimeError("Provider timeout")

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=failing_designer), \
             patch("services.media_orchestrator._ledger_stage",
                   side_effect=mock_ledger_stage), \
             patch("services.media_orchestrator._ledger_update",
                   side_effect=mock_ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=True), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   new_callable=AsyncMock):

            from services.media_orchestrator import _handle_static_image, MEDIA_TYPE_COST_CAPS
            with pytest.raises(RuntimeError):
                await _handle_static_image(brief, MEDIA_TYPE_COST_CAPS["static_image"])

        # image_generation ledger entry should be marked 'failed'
        failed_entries = [(lid, st) for lid, st in update_calls if st == "failed"]
        assert any("image_generation" in lid for lid, _ in failed_entries)

    @pytest.mark.asyncio
    async def test_provider_failure_skips_remaining_stages(self):
        """When designer raises, _ledger_skip_remaining is called with a reason."""
        brief = make_brief(media_type="static_image")
        skip_calls = []

        async def mock_ledger_stage(job_id, user_id, stage, provider, credits):
            return f"lid_{stage}"

        async def mock_skip(job_id, reason):
            skip_calls.append((job_id, reason))

        async def failing_designer(**kwargs):
            raise RuntimeError("GPU OOM")

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=failing_designer), \
             patch("services.media_orchestrator._ledger_stage",
                   side_effect=mock_ledger_stage), \
             patch("services.media_orchestrator._ledger_update", new_callable=AsyncMock), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=True), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   side_effect=mock_skip):

            from services.media_orchestrator import _handle_static_image, MEDIA_TYPE_COST_CAPS
            with pytest.raises(RuntimeError):
                await _handle_static_image(brief, MEDIA_TYPE_COST_CAPS["static_image"])

        assert len(skip_calls) >= 1
        # Reason should mention provider failure
        reason = skip_calls[0][1]
        assert "image_generation" in reason.lower() or "failed" in reason.lower()

    @pytest.mark.asyncio
    async def test_cost_cap_exceeded_aborts_pipeline(self):
        """When _ledger_check_cap returns False, the handler raises without calling Remotion."""
        brief = make_brief(media_type="static_image")
        remotion_called = []

        async def mock_remotion(composition_id, input_props, render_type="still"):
            remotion_called.append(1)
            return {"url": _REMOTION_OUTPUT_URL, "render_id": "rid"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=_designer_mock()), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion", side_effect=mock_remotion), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=False), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   new_callable=AsyncMock):

            from services.media_orchestrator import _handle_static_image, MEDIA_TYPE_COST_CAPS
            with pytest.raises(RuntimeError, match="Cost cap"):
                await _handle_static_image(brief, MEDIA_TYPE_COST_CAPS["static_image"])

        # Remotion should NOT have been called — pipeline aborted
        assert len(remotion_called) == 0

    @pytest.mark.asyncio
    async def test_partial_failure_user_charged_only_for_completed(self):
        """voice succeeds → consumed; avatar fails → failed; remaining → skipped."""
        brief = make_brief(media_type="talking_head", avatar_id="heygen_001")
        update_statuses = {}

        async def mock_ledger_stage(job_id, user_id, stage, provider, credits):
            return f"lid_{stage}"

        async def mock_ledger_update(ledger_id, status, reason=None):
            # Track which stages got which status
            stage = ledger_id.replace("lid_", "")
            update_statuses[stage] = status

        async def failing_avatar(**kwargs):
            raise RuntimeError("HeyGen API down")

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_avatar_video",
                   return_value=failing_avatar), \
             patch("services.media_orchestrator._ledger_stage",
                   side_effect=mock_ledger_stage), \
             patch("services.media_orchestrator._ledger_update",
                   side_effect=mock_ledger_update), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=True), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   new_callable=AsyncMock):

            from services.media_orchestrator import _handle_talking_head, MEDIA_TYPE_COST_CAPS
            with pytest.raises(RuntimeError):
                await _handle_talking_head(brief, MEDIA_TYPE_COST_CAPS["talking_head"])

        # avatar_generation must be marked 'failed'
        assert update_statuses.get("avatar_generation") == "failed"
        # remotion_render should NOT be consumed (pipeline aborted before it)
        assert update_statuses.get("remotion_render") != "consumed"

    @pytest.mark.asyncio
    async def test_ledger_stage_called_before_every_provider(self):
        """_ledger_stage is called BEFORE the provider function, not after."""
        brief = make_brief(media_type="static_image")
        call_order = []

        async def mock_ledger_stage(job_id, user_id, stage, provider, credits):
            call_order.append(f"ledger_stage:{stage}")
            return f"lid_{stage}"

        async def mock_designer(**kwargs):
            call_order.append("designer_called")
            return {"image_url": "https://example.com/img.jpg"}

        with patch("services.media_orchestrator.db", _make_mock_db()), \
             patch("services.media_orchestrator._get_designer",
                   return_value=mock_designer), \
             patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=_mock_stage_asset), \
             patch("services.media_orchestrator._call_remotion",
                   side_effect=_mock_call_remotion), \
             patch("services.media_orchestrator._ledger_stage",
                   side_effect=mock_ledger_stage), \
             patch("services.media_orchestrator._ledger_update", new_callable=AsyncMock), \
             patch("services.media_orchestrator._ledger_check_cap",
                   new_callable=AsyncMock, return_value=True), \
             patch("services.media_orchestrator._ledger_skip_remaining",
                   new_callable=AsyncMock):

            from services.media_orchestrator import _handle_static_image, MEDIA_TYPE_COST_CAPS
            await _handle_static_image(brief, MEDIA_TYPE_COST_CAPS["static_image"])

        # image_generation ledger entry must appear before the designer call
        img_gen_pos = call_order.index("ledger_stage:image_generation")
        designer_pos = call_order.index("designer_called")
        assert img_gen_pos < designer_pos, "Ledger must be written before calling provider"

    def test_all_8_types_have_cost_caps_defined(self):
        """MEDIA_TYPE_COST_CAPS contains all 8 required media types."""
        from services.media_orchestrator import MEDIA_TYPE_COST_CAPS

        required = {
            "static_image",
            "quote_card",
            "meme",
            "carousel",
            "infographic",
            "talking_head",
            "short_form_video",
            "text_on_video",
        }
        assert required == set(MEDIA_TYPE_COST_CAPS.keys())

    def test_stage_costs_are_positive_integers(self):
        """All STAGE_COSTS values are positive integers."""
        from services.media_orchestrator import STAGE_COSTS

        for stage, cost in STAGE_COSTS.items():
            assert isinstance(cost, int), f"STAGE_COSTS[{stage!r}] must be int, got {type(cost)}"
            assert cost > 0, f"STAGE_COSTS[{stage!r}] must be positive, got {cost}"

    def test_no_type_cost_cap_below_minimum_stage_cost(self):
        """Each media type's cost cap must be at least as large as the cheapest stage cost."""
        from services.media_orchestrator import MEDIA_TYPE_COST_CAPS, STAGE_COSTS

        min_stage_cost = min(STAGE_COSTS.values())
        for media_type, cap in MEDIA_TYPE_COST_CAPS.items():
            assert cap >= min_stage_cost, (
                f"Cost cap for {media_type!r} ({cap}) is below the minimum single-stage cost ({min_stage_cost})"
            )


# ============================================================
# TestR2Staging
# ============================================================

class TestR2Staging:
    """Tests for _stage_asset_to_r2 and _stage_assets_to_r2."""

    @pytest.mark.asyncio
    async def test_stage_http_url_downloads_and_uploads(self):
        """HTTP URL: downloads via httpx, uploads to R2, returns R2 public URL."""
        fake_bytes = b"fake image content bytes"
        fake_content_type = "image/jpeg"

        mock_response = MagicMock()
        mock_response.content = fake_bytes
        mock_response.headers = {"content-type": fake_content_type}
        mock_response.raise_for_status = MagicMock()

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
                "job_http_test",
                "background_image",
            )

        # R2 upload called
        assert mock_r2.put_object.called
        call_kwargs = mock_r2.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Body"] == fake_bytes
        assert "media/orchestrated/job_http_test/background_image" in call_kwargs["Key"]

        # Returned URL starts with R2 public URL
        assert result.startswith("https://cdn.example.com/media/orchestrated/job_http_test/")

    @pytest.mark.asyncio
    async def test_stage_base64_data_url_decodes(self):
        """data: URL: decodes base64 bytes, uploads to R2, returns R2 public URL."""
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
            result = await _stage_asset_to_r2(data_url, "job_b64_test", "generated_image")

        call_kwargs = mock_r2.put_object.call_args[1]
        # Decoded bytes match original
        assert call_kwargs["Body"] == raw_bytes
        assert call_kwargs["ContentType"] == "image/png"
        # Key contains correct job_id and asset_key
        assert "media/orchestrated/job_b64_test/generated_image" in call_kwargs["Key"]
        # Returned URL starts with R2 public URL
        assert result.startswith("https://cdn.example.com/media/orchestrated/job_b64_test/")

    @pytest.mark.asyncio
    async def test_stage_returns_r2_public_url(self):
        """_stage_asset_to_r2 result starts with the configured R2 public URL prefix."""
        raw_bytes = b"some content"
        encoded = base64.b64encode(raw_bytes).decode()
        data_url = f"data:image/jpeg;base64,{encoded}"

        mock_r2 = MagicMock()
        mock_r2.put_object = MagicMock()

        with patch("services.media_orchestrator.get_r2_client", return_value=mock_r2), \
             patch("services.media_orchestrator.settings") as mock_settings:

            mock_settings.r2.r2_bucket_name = "bucket"
            mock_settings.r2.r2_public_url = "https://r2.mycdn.io"

            from services.media_orchestrator import _stage_asset_to_r2
            result = await _stage_asset_to_r2(data_url, "job_url_test", "test_asset")

        assert result.startswith("https://r2.mycdn.io/")

    @pytest.mark.asyncio
    async def test_stage_assets_parallel_processes_multiple(self):
        """_stage_assets_to_r2 stages multiple assets concurrently and returns all R2 URLs."""
        staged_calls = []

        async def mock_stage_one(url, job_id, key):
            staged_calls.append(key)
            return f"https://cdn.example.com/media/orchestrated/{job_id}/{key}.jpg"

        with patch("services.media_orchestrator._stage_asset_to_r2",
                   side_effect=mock_stage_one):

            from services.media_orchestrator import _stage_assets_to_r2
            result = await _stage_assets_to_r2(
                assets={
                    "background": "https://example.com/bg.jpg",
                    "logo": "https://example.com/logo.png",
                    "overlay": "data:image/png;base64,abc123",
                },
                job_id="job_parallel_test",
            )

        # All 3 assets staged
        assert len(result) == 3
        assert len(staged_calls) == 3
        assert "background" in result
        assert "logo" in result
        assert "overlay" in result
