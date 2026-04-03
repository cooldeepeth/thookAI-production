"""Unit tests for qc.validate_media_output().

Tests cover:
- File format validation (PNG for stills, MP4 for video)
- File format mismatch → failure + feedback
- Brand color metadata check (valid vs invalid hex)
- Anti-slop graceful pass when vision API unavailable
- Structured output format (overall_pass, checks, feedback)
- Feedback populated on failure
"""
import asyncio
from unittest.mock import patch
import pytest
from agents.qc import validate_media_output, PLATFORM_MEDIA_SPECS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


PNG_URL = "https://r2.example.com/assets/test-image.png"
MP4_URL = "https://r2.example.com/assets/test-video.mp4"
WRONG_EXT_URL = "https://r2.example.com/assets/test-image.mp4"  # mp4 for a still


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_brand_color_check_pass():
    """Valid brand color + PNG for static_image on linkedin → overall_pass True."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=PNG_URL,
            media_type="static_image",
            platform="linkedin",
            brand_color="#2563EB",
        ))
    assert result["overall_pass"] is True, (
        f"Expected overall_pass=True for valid inputs, got: {result}"
    )


def test_file_format_png_for_still():
    """PNG URL with static_image media type should pass file_format check."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=PNG_URL,
            media_type="static_image",
            platform="linkedin",
        ))
    file_check = next(c for c in result["checks"] if c["name"] == "file_format")
    assert file_check["pass"] is True, f"Expected file_format check to pass for .png still, got: {file_check}"


def test_file_format_mp4_for_video():
    """MP4 URL with short_form_video media type should pass file_format check."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=MP4_URL,
            media_type="short_form_video",
            platform="instagram",
        ))
    file_check = next(c for c in result["checks"] if c["name"] == "file_format")
    assert file_check["pass"] is True, f"Expected file_format check to pass for .mp4 video, got: {file_check}"


# ---------------------------------------------------------------------------
# Failure-path tests
# ---------------------------------------------------------------------------

def test_file_format_mismatch_fails():
    """MP4 URL with static_image media type should fail file_format check."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=WRONG_EXT_URL,
            media_type="static_image",
            platform="linkedin",
        ))
    file_check = next(c for c in result["checks"] if c["name"] == "file_format")
    assert file_check["pass"] is False, (
        f"Expected file_format check to FAIL for mp4 still, got: {file_check}"
    )
    assert result["overall_pass"] is False, "overall_pass should be False when file_format check fails"


def test_invalid_brand_color_fails():
    """Missing or non-hex brand_color should fail brand_consistency check."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=PNG_URL,
            media_type="static_image",
            platform="linkedin",
            brand_color="not-a-color",
        ))
    brand_check = next(c for c in result["checks"] if c["name"] == "brand_consistency")
    assert brand_check["pass"] is False, (
        f"Expected brand_consistency to FAIL for invalid color, got: {brand_check}"
    )


# ---------------------------------------------------------------------------
# Anti-slop graceful degradation
# ---------------------------------------------------------------------------

def test_anti_slop_passes_when_no_vision():
    """anti_slop check should pass gracefully when anthropic_available() returns False."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=PNG_URL,
            media_type="static_image",
            platform="linkedin",
        ))
    slop_check = next(c for c in result["checks"] if c["name"] == "anti_slop")
    assert slop_check["pass"] is True, (
        f"anti_slop should pass gracefully when vision unavailable, got: {slop_check}"
    )
    assert "unavailable" in slop_check["detail"].lower(), (
        "detail should mention 'unavailable' when vision is skipped"
    )


# ---------------------------------------------------------------------------
# Structured output tests
# ---------------------------------------------------------------------------

def test_checks_structure():
    """Result must have exactly 4 checks, each with 'name' and 'pass' keys."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=PNG_URL,
            media_type="static_image",
            platform="linkedin",
        ))
    assert "overall_pass" in result, "Result must have 'overall_pass'"
    assert "checks" in result, "Result must have 'checks'"
    assert "feedback" in result, "Result must have 'feedback'"
    assert len(result["checks"]) == 4, (
        f"Expected exactly 4 checks, got {len(result['checks'])}: {[c['name'] for c in result['checks']]}"
    )
    expected_names = {"platform_dimensions", "brand_consistency", "anti_slop", "file_format"}
    actual_names = {c["name"] for c in result["checks"]}
    assert actual_names == expected_names, (
        f"Expected check names {expected_names}, got {actual_names}"
    )
    for check in result["checks"]:
        assert "name" in check, f"Check missing 'name' key: {check}"
        assert "pass" in check, f"Check missing 'pass' key: {check}"
        assert "detail" in check, f"Check missing 'detail' key: {check}"


def test_feedback_on_failure():
    """Feedback list should be non-empty when a check fails."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=WRONG_EXT_URL,  # mp4 for a still → file_format fail
            media_type="static_image",
            platform="linkedin",
        ))
    assert len(result["feedback"]) >= 1, (
        "feedback should be non-empty when at least one check fails"
    )
    # Feedback should mention the failing check
    all_feedback_text = " ".join(result["feedback"]).lower()
    assert "file_format" in all_feedback_text or "extension" in all_feedback_text, (
        f"Feedback should mention file_format issue, got: {result['feedback']}"
    )


def test_unknown_platform_does_not_crash():
    """Unknown platform should not raise — should use fallback spec."""
    with patch("agents.qc.anthropic_available", return_value=False):
        result = run(validate_media_output(
            media_url=PNG_URL,
            media_type="static_image",
            platform="tiktok",  # Unknown platform
        ))
    assert "overall_pass" in result, "Should return structured result even for unknown platform"


def test_platform_media_specs_completeness():
    """PLATFORM_MEDIA_SPECS should have entries for linkedin, instagram, and x."""
    for platform in ("linkedin", "instagram", "x"):
        assert platform in PLATFORM_MEDIA_SPECS, (
            f"PLATFORM_MEDIA_SPECS missing entry for '{platform}'"
        )
        spec = PLATFORM_MEDIA_SPECS[platform]
        assert "image" in spec, f"No 'image' spec for '{platform}'"
        assert "video" in spec, f"No 'video' spec for '{platform}'"
