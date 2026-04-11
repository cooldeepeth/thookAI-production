"""
Phase 26: Credit Refund on Media Endpoint Failures
Covers: BACK-06 (credits refunded when image/carousel/voice/video generation fails)

All tests start in RED state.
Plan 04 adds try/except refund blocks to the sync fallback paths in
backend/routes/content.py which drives them to GREEN.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def _make_user():
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "subscription_tier": "pro",
        "credits": 100,
    }


def _make_job(job_id="job_test001"):
    return {
        "job_id": job_id,
        "user_id": "test_user_123",
        "platform": "linkedin",
        "final_content": "Test content for narration.",
        "raw_input": "test input",
        "agent_outputs": {"commander": {"primary_angle": "Test angle"}},
    }


@pytest.mark.asyncio
async def test_image_generation_failure_refunds_credits():
    """generate_image sync path: failure → add_credits called with IMAGE_GENERATE.value=8 (BACK-06)"""
    from httpx import AsyncClient, ASGITransport
    from auth_utils import get_current_user

    with (
        patch("routes.content.is_redis_configured", return_value=False),
        patch("routes.content.db") as mock_db,
        patch("services.credits.deduct_credits", new_callable=AsyncMock) as mock_deduct,
        patch("services.credits.add_credits", new_callable=AsyncMock) as mock_refund,
        patch("agents.designer.generate_image", new_callable=AsyncMock) as mock_gen,
    ):
        mock_db.content_jobs.find_one = AsyncMock(return_value=_make_job())
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)
        mock_deduct.return_value = {"success": True, "credits_remaining": 92}
        mock_gen.side_effect = RuntimeError("Provider API down")

        from server import app
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/content/generate-image",
                    json={"job_id": "job_test001", "style": "minimal"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    # Must return 500 (not 200) and must have called add_credits (refund)
    assert resp.status_code == 500, f"Expected 500 but got {resp.status_code}: {resp.text}"
    mock_refund.assert_called_once()
    call_args = mock_refund.call_args
    assert call_args.args[1] == 8 or call_args.kwargs.get("amount") == 8, \
        f"Expected refund of 8 credits (IMAGE_GENERATE), got: {call_args}"


@pytest.mark.asyncio
async def test_carousel_generation_failure_refunds_credits():
    """generate_carousel sync path: failure → add_credits called with CAROUSEL_GENERATE.value=15 (BACK-06)"""
    from auth_utils import get_current_user

    with (
        patch("routes.content.db") as mock_db,
        patch("services.credits.deduct_credits", new_callable=AsyncMock) as mock_deduct,
        patch("services.credits.add_credits", new_callable=AsyncMock) as mock_refund,
        patch("agents.designer.generate_carousel", new_callable=AsyncMock) as mock_gen,
    ):
        mock_db.content_jobs.find_one = AsyncMock(return_value=_make_job())
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)
        mock_deduct.return_value = {"success": True, "credits_remaining": 85}
        mock_gen.side_effect = RuntimeError("Carousel provider error")

        from httpx import AsyncClient, ASGITransport
        from server import app
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/content/generate-carousel",
                    json={"job_id": "job_test001", "style": "minimal"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 500, f"Expected 500 but got {resp.status_code}"
    mock_refund.assert_called_once()
    call_args = mock_refund.call_args
    assert call_args.args[1] == 15 or call_args.kwargs.get("amount") == 15, \
        f"Expected refund of 15 credits (CAROUSEL_GENERATE), got: {call_args}"


@pytest.mark.asyncio
async def test_narrate_failure_refunds_credits():
    """narrate_content sync path (no Redis): failure → add_credits called with VOICE_NARRATION.value=12 (BACK-06)"""
    from auth_utils import get_current_user

    with (
        patch("routes.content.is_redis_configured", return_value=False),
        patch("routes.content.db") as mock_db,
        patch("services.credits.deduct_credits", new_callable=AsyncMock) as mock_deduct,
        patch("services.credits.add_credits", new_callable=AsyncMock) as mock_refund,
        patch("agents.voice.generate_voice_narration", new_callable=AsyncMock) as mock_gen,
    ):
        mock_db.content_jobs.find_one = AsyncMock(return_value=_make_job())
        mock_deduct.return_value = {"success": True, "credits_remaining": 88}
        mock_gen.side_effect = RuntimeError("ElevenLabs quota exceeded")

        from httpx import AsyncClient, ASGITransport
        from server import app
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/content/narrate",
                    json={"job_id": "job_test001"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 500, f"Expected 500 but got {resp.status_code}"
    mock_refund.assert_called_once()
    call_args = mock_refund.call_args
    assert call_args.args[1] == 12 or call_args.kwargs.get("amount") == 12, \
        f"Expected refund of 12 credits (VOICE_NARRATION), got: {call_args}"


@pytest.mark.asyncio
async def test_video_generation_failure_refunds_credits():
    """generate_video sync path (no Redis): failure → add_credits called with VIDEO_GENERATE.value=50 (BACK-06)"""
    from auth_utils import get_current_user

    with (
        patch("routes.content.is_redis_configured", return_value=False),
        patch("routes.content.db") as mock_db,
        patch("services.credits.deduct_credits", new_callable=AsyncMock) as mock_deduct,
        patch("services.credits.add_credits", new_callable=AsyncMock) as mock_refund,
        patch("agents.video.generate_video", new_callable=AsyncMock) as mock_gen,
    ):
        mock_db.content_jobs.find_one = AsyncMock(return_value=_make_job())
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)
        mock_deduct.return_value = {"success": True, "credits_remaining": 50}
        mock_gen.side_effect = RuntimeError("Runway API unavailable")

        from httpx import AsyncClient, ASGITransport
        from server import app
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/content/generate-video",
                    json={"job_id": "job_test001"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 500, f"Expected 500 but got {resp.status_code}"
    mock_refund.assert_called_once()
    call_args = mock_refund.call_args
    assert call_args.args[1] == 50 or call_args.kwargs.get("amount") == 50, \
        f"Expected refund of 50 credits (VIDEO_GENERATE), got: {call_args}"
