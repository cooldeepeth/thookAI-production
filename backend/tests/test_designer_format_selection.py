"""Unit tests for designer.select_media_format().

Tests cover:
- Platform-specific format preferences (LinkedIn, Instagram, X)
- Content angle to format mapping
- Capability bonuses (data_points, avatar, long content)
- Return structure (reason, alternatives, confidence)
- Edge cases (unknown platform, unknown angle)
"""
import asyncio
import pytest
from agents.designer import (
    select_media_format,
    PLATFORM_FORMAT_PREFERENCES,
    CONTENT_ANGLE_FORMAT_MAP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run a coroutine synchronously (pytest-asyncio not required for pure-logic tests)."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Platform-preference tests
# ---------------------------------------------------------------------------

def test_linkedin_favors_carousel_for_how_to():
    """LinkedIn + how_to should pick carousel or infographic (both preferred)."""
    result = run(select_media_format(
        platform="linkedin",
        content_text="How to build a personal brand in 30 days",
        content_angle="how_to",
    ))
    assert result["media_type"] in ["carousel", "infographic"], (
        f"Expected carousel or infographic for linkedin/how_to, got {result['media_type']}"
    )


def test_instagram_favors_video_for_storytelling():
    """Instagram + storytelling should pick short_form_video or carousel."""
    result = run(select_media_format(
        platform="instagram",
        content_text="My journey from burnout to building a thriving business",
        content_angle="storytelling",
    ))
    assert result["media_type"] in ["short_form_video", "carousel"], (
        f"Expected short_form_video or carousel for instagram/storytelling, got {result['media_type']}"
    )


def test_x_favors_meme_for_contrarian():
    """X + contrarian should pick meme or quote_card."""
    result = run(select_media_format(
        platform="x",
        content_text="Unpopular opinion: cold outreach still works in 2025",
        content_angle="contrarian",
    ))
    assert result["media_type"] in ["meme", "quote_card"], (
        f"Expected meme or quote_card for x/contrarian, got {result['media_type']}"
    )


def test_linkedin_avoids_meme():
    """LinkedIn should never recommend meme (it's in the avoid list)."""
    result = run(select_media_format(
        platform="linkedin",
        content_text="Professional thought leadership post",
        content_angle="thought_leadership",
    ))
    # meme should not be the primary pick on LinkedIn
    assert result["media_type"] != "meme", (
        "LinkedIn should avoid meme — it's in the avoid list"
    )


# ---------------------------------------------------------------------------
# Capability bonus tests
# ---------------------------------------------------------------------------

def test_data_points_boost_infographic():
    """has_data_points=True should push infographic to the top for data_insight on LinkedIn."""
    result = run(select_media_format(
        platform="linkedin",
        content_text="Data shows 73% of leaders fail due to poor communication",
        content_angle="data_insight",
        has_data_points=True,
    ))
    assert result["media_type"] == "infographic", (
        f"Expected infographic when has_data_points=True, got {result['media_type']}"
    )


def test_avatar_boosts_talking_head():
    """has_avatar=True should push talking_head to the top for personal on Instagram."""
    result = run(select_media_format(
        platform="instagram",
        content_text="Let me tell you about the day that changed everything",
        content_angle="personal",
        has_avatar=True,
    ))
    assert result["media_type"] == "talking_head", (
        f"Expected talking_head when has_avatar=True for instagram/personal, got {result['media_type']}"
    )


# ---------------------------------------------------------------------------
# Return structure tests
# ---------------------------------------------------------------------------

def test_reason_field_not_empty():
    """reason must be a non-empty string explaining the choice."""
    result = run(select_media_format(platform="linkedin", content_text="test"))
    assert isinstance(result["reason"], str) and len(result["reason"]) > 0, (
        "reason field should be a non-empty string"
    )


def test_confidence_in_range():
    """confidence must be a float between 0.0 and 1.0 inclusive."""
    result = run(select_media_format(platform="linkedin", content_text="test"))
    confidence = result["confidence"]
    assert isinstance(confidence, float), f"confidence should be a float, got {type(confidence)}"
    assert 0.0 <= confidence <= 1.0, f"confidence {confidence} is out of [0, 1] range"


def test_alternatives_returned():
    """At least 1 alternative should be returned and the primary pick must not be in it."""
    result = run(select_media_format(platform="linkedin", content_text="test post"))
    alternatives = result["alternatives"]
    assert len(alternatives) >= 1, "At least 1 alternative should be returned"
    assert result["media_type"] not in alternatives, (
        "Primary pick should not appear in alternatives list"
    )


def test_result_has_all_required_keys():
    """Result dict must contain media_type, reason, alternatives, confidence."""
    result = run(select_media_format(platform="linkedin", content_text="test"))
    for key in ("media_type", "reason", "alternatives", "confidence"):
        assert key in result, f"Expected key '{key}' in result dict"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_unknown_platform_defaults_gracefully():
    """Unknown platform should not crash — falls back to linkedin preferences."""
    result = run(select_media_format(platform="tiktok", content_text="test post"))
    assert "media_type" in result, "Should return a valid media_type even for unknown platform"
    assert isinstance(result["media_type"], str) and len(result["media_type"]) > 0


def test_unknown_angle_defaults_to_static_image_candidate():
    """Unknown content angle should fall back gracefully and return a valid media_type."""
    result = run(select_media_format(
        platform="linkedin",
        content_text="generic post",
        content_angle="unknown_angle_xyz",
    ))
    assert "media_type" in result, "Should return a valid media_type even for unknown angle"
    assert isinstance(result["media_type"], str) and len(result["media_type"]) > 0


def test_long_content_boosts_video():
    """Content longer than 500 chars should give short_form_video a score bonus."""
    long_text = "A" * 600
    result = run(select_media_format(
        platform="instagram",
        content_text=long_text,
        content_angle="storytelling",
    ))
    # short_form_video should rank very highly for instagram/storytelling + long content
    # Either primary pick or top alternative
    assert (
        result["media_type"] == "short_form_video"
        or "short_form_video" in result["alternatives"]
    ), "short_form_video should rank highly for long instagram/storytelling content"
