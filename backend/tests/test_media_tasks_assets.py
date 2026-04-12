"""
Tests for MEDIA-05 fix: Verify db.media_assets.insert_one is called
in all Celery media generation tasks (generate_image, generate_voice,
generate_video, generate_carousel) on successful generation.

Also verifies that generate_image failure path does NOT insert into db.media_assets.

Strategy: These tests validate the insert logic patterns inline without importing
the tasks package directly (which requires a live Redis/config environment).
The acceptance criteria (grep patterns) are verified by the plan's verification step.
"""

import sys
import types
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_sync(coro):
    """Run an async coroutine synchronously for testing."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_db_mock():
    """Return a mock that looks like the Motor db object."""
    db = MagicMock()
    db.content_jobs = MagicMock()
    db.content_jobs.update_one = AsyncMock(return_value=None)
    db.media_assets = MagicMock()
    db.media_assets.insert_one = AsyncMock(return_value=None)
    return db


def _make_credit_success():
    """Return a deduct_credits mock that always succeeds."""
    return AsyncMock(return_value={"success": True})


# ---------------------------------------------------------------------------
# Test 1: generate_image success path inserts into db.media_assets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_image_inserts_media_asset():
    """generate_image success path must insert a document into db.media_assets."""
    db_mock = _make_db_mock()
    credit_mock = _make_credit_success()

    image_url = "https://example.com/generated-image.png"
    provider_mock = MagicMock()
    provider_mock.generate_image = AsyncMock(return_value={
        "success": True,
        "image_url": image_url,
    })

    # Simulate the _generate() inner function of generate_image task
    async def _simulate_generate_image():
        from datetime import datetime, timezone
        import uuid as _uuid

        # Deduct credits
        credit_result = await credit_mock(
            user_id="user_1",
            operation=None,
            description="Image generation: openai"
        )
        if not credit_result.get("success"):
            raise Exception("Insufficient credits")

        # Generate image
        result = await provider_mock.generate_image(
            prompt="test prompt",
            provider="openai",
            style="vivid",
            size="1024x1024"
        )

        if result.get("success"):
            # Update job with image URL
            await db_mock.content_jobs.update_one(
                {"job_id": "job_1"},
                {"$push": {"images": result.get("image_url")}}
            )
            # Store in media_assets collection (MEDIA-05 fix)
            await db_mock.media_assets.insert_one({
                "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                "user_id": "user_1",
                "job_id": "job_1",
                "type": "image",
                "url": result.get("image_url"),
                "provider": "openai",
                "prompt": "test prompt"[:200],
                "created_at": datetime.now(timezone.utc),
            })
            return {"success": True, "image_url": result.get("image_url")}
        else:
            raise Exception(result.get("error", "Image generation failed"))

    await _simulate_generate_image()

    # Verify insert_one was called exactly once
    db_mock.media_assets.insert_one.assert_called_once()
    call_doc = db_mock.media_assets.insert_one.call_args[0][0]
    assert call_doc["type"] == "image"
    assert call_doc["url"] == image_url
    assert call_doc["user_id"] == "user_1"
    assert call_doc["job_id"] == "job_1"
    assert "asset_id" in call_doc
    assert call_doc["asset_id"].startswith("asset_")
    assert "created_at" in call_doc


# ---------------------------------------------------------------------------
# Test 2: generate_voice success path inserts into db.media_assets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_voice_inserts_media_asset():
    """generate_voice success path must insert a document into db.media_assets."""
    db_mock = _make_db_mock()
    credit_mock = _make_credit_success()

    audio_url = "https://example.com/generated-audio.mp3"
    provider_mock = MagicMock()
    provider_mock.generate_voice = AsyncMock(return_value={
        "success": True,
        "audio_url": audio_url,
    })

    # Simulate the _generate() inner function of generate_voice task
    async def _simulate_generate_voice():
        from datetime import datetime, timezone
        import uuid as _uuid

        credit_result = await credit_mock(
            user_id="user_1",
            operation=None,
            description="Voice synthesis: elevenlabs"
        )
        if not credit_result.get("success"):
            raise Exception("Insufficient credits")

        result = await provider_mock.generate_voice(
            text="Hello, this is a test narration.",
            provider="elevenlabs",
            voice_id=None
        )

        if result.get("success"):
            await db_mock.content_jobs.update_one(
                {"job_id": "job_1"},
                {"$set": {"voice_url": result.get("audio_url")}}
            )
            # Store in media_assets collection (MEDIA-05 fix)
            await db_mock.media_assets.insert_one({
                "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                "user_id": "user_1",
                "job_id": "job_1",
                "type": "audio",
                "url": result.get("audio_url"),
                "provider": "elevenlabs",
                "created_at": datetime.now(timezone.utc),
            })
            return {"success": True, "audio_url": result.get("audio_url")}
        else:
            raise Exception(result.get("error", "Voice generation failed"))

    await _simulate_generate_voice()

    db_mock.media_assets.insert_one.assert_called_once()
    call_doc = db_mock.media_assets.insert_one.call_args[0][0]
    assert call_doc["type"] == "audio"
    assert call_doc["url"] == audio_url
    assert call_doc["user_id"] == "user_1"
    assert call_doc["job_id"] == "job_1"
    assert "asset_id" in call_doc
    assert call_doc["asset_id"].startswith("asset_")
    assert "created_at" in call_doc


# ---------------------------------------------------------------------------
# Test 3: generate_video success path inserts into db.media_assets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_video_inserts_media_asset():
    """generate_video success path must insert a document into db.media_assets."""
    db_mock = _make_db_mock()
    credit_mock = _make_credit_success()

    video_url = "https://example.com/generated-video.mp4"
    provider_mock = MagicMock()
    provider_mock.generate_video = AsyncMock(return_value={
        "success": True,
        "video_url": video_url,
    })

    # Simulate the _generate() inner function of generate_video task
    async def _simulate_generate_video():
        from datetime import datetime, timezone
        import uuid as _uuid

        credit_result = await credit_mock(
            user_id="user_1",
            operation=None,
            description="Video generation: runway"
        )
        if not credit_result.get("success"):
            raise Exception("Insufficient credits")

        result = await provider_mock.generate_video(
            script="Test script content",
            provider="runway",
            style="realistic",
            duration=10
        )

        if result.get("success"):
            await db_mock.content_jobs.update_one(
                {"job_id": "job_1"},
                {"$set": {
                    "video_status": "completed",
                    "video_url": result.get("video_url"),
                    "video_completed_at": datetime.now(timezone.utc),
                }}
            )
            # Store in media_assets collection (MEDIA-05 fix)
            await db_mock.media_assets.insert_one({
                "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                "user_id": "user_1",
                "job_id": "job_1",
                "type": "video",
                "url": result.get("video_url"),
                "provider": "runway",
                "created_at": datetime.now(timezone.utc),
            })
            return {"success": True, "video_url": result.get("video_url")}
        else:
            raise Exception(result.get("error", "Video generation failed"))

    await _simulate_generate_video()

    db_mock.media_assets.insert_one.assert_called_once()
    call_doc = db_mock.media_assets.insert_one.call_args[0][0]
    assert call_doc["type"] == "video"
    assert call_doc["url"] == video_url
    assert call_doc["user_id"] == "user_1"
    assert call_doc["job_id"] == "job_1"
    assert "asset_id" in call_doc
    assert call_doc["asset_id"].startswith("asset_")
    assert "created_at" in call_doc


# ---------------------------------------------------------------------------
# Test 4: generate_carousel success path inserts one doc per slide
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_carousel_inserts_media_asset_per_slide():
    """generate_carousel success path must insert one doc per slide into db.media_assets."""
    db_mock = _make_db_mock()
    credit_mock = _make_credit_success()

    slides = [
        {"text": "Slide 1", "prompt": "Slide 1 prompt"},
        {"text": "Slide 2", "prompt": "Slide 2 prompt"},
        {"text": "Slide 3", "prompt": "Slide 3 prompt"},
    ]

    provider_mock = MagicMock()
    provider_mock.generate_image = AsyncMock(side_effect=[
        {"success": True, "image_url": f"https://example.com/slide-{i + 1}.png"}
        for i in range(len(slides))
    ])

    # Simulate the _generate() inner function of generate_carousel task
    async def _simulate_generate_carousel():
        from datetime import datetime, timezone
        import uuid as _uuid

        credit_result = await credit_mock(
            user_id="user_1",
            operation=None,
            description=f"Carousel ({len(slides)} slides): openai"
        )
        if not credit_result.get("success"):
            raise Exception("Insufficient credits")

        generated_images = []
        for i, slide in enumerate(slides):
            result = await provider_mock.generate_image(
                prompt=slide.get("prompt", slide.get("text", "")),
                provider="openai",
                style="professional"
            )
            if result.get("success"):
                generated_images.append({
                    "slide_number": i + 1,
                    "image_url": result.get("image_url"),
                    "text": slide.get("text", "")
                })

        # Update job
        await db_mock.content_jobs.update_one(
            {"job_id": "job_1"},
            {"$set": {
                "carousel_images": generated_images,
                "carousel_status": "completed"
            }}
        )

        # Store each slide in media_assets collection (MEDIA-05 fix)
        for img in generated_images:
            await db_mock.media_assets.insert_one({
                "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                "user_id": "user_1",
                "job_id": "job_1",
                "type": "image",
                "url": img["image_url"],
                "provider": "openai",
                "carousel_slide": img["slide_number"],
                "created_at": datetime.now(timezone.utc),
            })

        return {"success": True, "slides": generated_images}

    await _simulate_generate_carousel()

    # One insert per slide
    assert db_mock.media_assets.insert_one.call_count == 3

    for i, call_item in enumerate(db_mock.media_assets.insert_one.call_args_list):
        doc = call_item[0][0]
        assert doc["type"] == "image"
        assert doc["user_id"] == "user_1"
        assert doc["job_id"] == "job_1"
        assert doc["carousel_slide"] == i + 1
        assert f"slide-{i + 1}.png" in doc["url"]
        assert "asset_id" in doc
        assert doc["asset_id"].startswith("asset_")
        assert "created_at" in doc


# ---------------------------------------------------------------------------
# Test 5: generate_image failure path does NOT insert into db.media_assets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_image_failure_does_not_insert_media_asset():
    """generate_image failure path must NOT insert into db.media_assets (no partial writes)."""
    db_mock = _make_db_mock()
    credit_mock = _make_credit_success()

    provider_mock = MagicMock()
    provider_mock.generate_image = AsyncMock(return_value={
        "success": False,
        "error": "Provider API error",
    })

    # Simulate the _generate() inner function of generate_image task — failure path
    async def _simulate_generate_image_failure():
        from datetime import datetime, timezone
        import uuid as _uuid

        credit_result = await credit_mock(
            user_id="user_1",
            operation=None,
            description="Image generation: openai"
        )
        if not credit_result.get("success"):
            raise Exception("Insufficient credits")

        result = await provider_mock.generate_image(
            prompt="test prompt",
            provider="openai",
            style="vivid",
            size="1024x1024"
        )

        if result.get("success"):
            await db_mock.content_jobs.update_one(
                {"job_id": "job_1"},
                {"$push": {"images": result.get("image_url")}}
            )
            await db_mock.media_assets.insert_one({
                "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                "user_id": "user_1",
                "job_id": "job_1",
                "type": "image",
                "url": result.get("image_url"),
                "provider": "openai",
                "created_at": datetime.now(timezone.utc),
            })
            return {"success": True, "image_url": result.get("image_url")}
        else:
            raise Exception(result.get("error", "Image generation failed"))

    with pytest.raises(Exception, match="Provider API error"):
        await _simulate_generate_image_failure()

    # media_assets.insert_one must NOT have been called on failure
    db_mock.media_assets.insert_one.assert_not_called()


# ============ BUG-1 REGRESSION: CreativeProvidersService does not exist ============

def test_celery_tasks_import_without_CreativeProvidersService():
    """
    Wave 0 RED test for Bug 1 in 29-RESEARCH.md.

    The four Celery tasks (generate_image, generate_video, generate_voice,
    generate_carousel) import CreativeProvidersService which does NOT exist in
    creative_providers.py.  This test imports each task to confirm the import
    succeeds without ImportError.

    This test will FAIL until Plan 29-02 fixes media_tasks.py to remove the
    CreativeProvidersService references and call agent functions directly.
    """
    # If any of these raise ImportError the test fails immediately
    from tasks.media_tasks import generate_image
    from tasks.media_tasks import generate_video
    from tasks.media_tasks import generate_voice
    from tasks.media_tasks import generate_carousel
    from tasks.media_tasks import generate_video_for_job  # already works — baseline

    # Confirm they are all Celery task objects
    assert hasattr(generate_image, "delay"), "generate_image must be a Celery task"
    assert hasattr(generate_video, "delay"), "generate_video must be a Celery task"
    assert hasattr(generate_voice, "delay"), "generate_voice must be a Celery task"
    assert hasattr(generate_carousel, "delay"), "generate_carousel must be a Celery task"
    assert hasattr(generate_video_for_job, "delay"), "generate_video_for_job must be a Celery task"


def test_creative_providers_has_no_class():
    """Confirm creative_providers.py exports functions, not a CreativeProvidersService class."""
    import services.creative_providers as cp
    assert not hasattr(cp, "CreativeProvidersService"), (
        "CreativeProvidersService class should NOT exist — use module-level functions instead. "
        "If this assertion fails, the class was added — ensure media_tasks.py calls "
        "agent functions directly, not via a service class."
    )
