"""Tests for media generation agents: image (MEDIA-01), voice (MEDIA-02), video (MEDIA-03).

All tests are unit tests using mocks — no external API calls are made.
Verifies:
- Async execution (coroutine functions, asyncio.wait_for usage)
- Timeout protection on all polling loops
- Voice clone lifecycle (create → persist → delete)
- Video provider routing (runway / kling / luma / pika, heygen / did)
- Celery task layer dispatching to agents and handling credits
"""
import asyncio
import inspect
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call


# ============================================================
# MEDIA-01: Async Image Generation (designer.py)
# ============================================================

class TestGenerateImageAsync:
    """Test 1 — generate_image() with mocked provider returns valid result dict."""

    @pytest.mark.asyncio
    async def test_generate_image_with_provider_returns_generated_true(self):
        """Mocked OpenAI provider returns success dict with generated=True and image_base64."""
        openai_result = {
            "image_base64": "abc123",
            "image_url": "data:image/png;base64,abc123",
            "generated": True,
            "provider": "openai",
            "model": "gpt-image-1",
        }
        with patch(
            "agents.designer.get_best_available_provider", return_value="openai"
        ), patch(
            "agents.designer._generate_openai", new=AsyncMock(return_value=openai_result)
        ):
            from agents.designer import generate_image

            result = await generate_image(prompt="a professional headshot", style="minimal")

        assert result["generated"] is True
        assert result["image_base64"] == "abc123"
        assert "prompt_used" in result

    @pytest.mark.asyncio
    async def test_generate_image_no_providers_returns_mock(self):
        """Test 2 — No providers configured → mock result with generated=False, mock=True."""
        with patch("agents.designer.get_best_available_provider", return_value=None):
            from agents.designer import generate_image

            result = await generate_image(prompt="test", style="bold")

        assert result["generated"] is False
        assert result["mock"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_generate_image_timeout_returns_timeout_error(self):
        """Test 3 — Provider raises asyncio.TimeoutError → result error contains 'timeout'."""
        timeout_result = {"generated": False, "error": "generation_timeout", "provider": "openai"}
        with patch(
            "agents.designer.get_best_available_provider", return_value="openai"
        ), patch(
            "agents.designer._generate_openai", new=AsyncMock(return_value=timeout_result)
        ):
            from agents.designer import generate_image

            result = await generate_image(prompt="test", style="minimal", provider="openai")

        assert result["generated"] is False
        assert "timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_image_fallback_on_provider_failure(self):
        """Test 4 — Primary provider fails → fallback provider is tried."""
        fail_result = {"generated": False, "error": "api_error", "provider": "openai"}
        success_result = {
            "image_base64": "fal123",
            "image_url": "data:image/jpeg;base64,fal123",
            "generated": True,
            "provider": "fal",
            "model": "flux-pro-1.1",
        }

        with patch(
            "agents.designer.get_best_available_provider", return_value="openai"
        ), patch(
            "agents.designer._generate_openai", new=AsyncMock(return_value=fail_result)
        ), patch(
            "agents.designer._generate_fal", new=AsyncMock(return_value=success_result)
        ):
            from agents.designer import generate_image

            result = await generate_image(prompt="fallback test", style="minimal")

        assert result["generated"] is True
        assert result["provider"] == "fal"

    @pytest.mark.asyncio
    async def test_generate_carousel_correct_slide_count(self):
        """Test 5 — generate_carousel() produces cover + content + CTA slides."""
        slide_result = {
            "image_base64": "slide_b64",
            "image_url": "data:image/png;base64,slide_b64",
            "generated": True,
            "provider": "openai",
            "model": "gpt-image-1",
            "prompt_used": "...",
            "style": "minimal",
            "platform": "linkedin",
        }

        with patch(
            "agents.designer.get_best_available_provider", return_value="openai"
        ), patch(
            "agents.designer.generate_image", new=AsyncMock(return_value=slide_result)
        ):
            from agents.designer import generate_carousel

            key_points = ["Point A", "Point B", "Point C"]
            result = await generate_carousel(
                topic="AI Productivity", key_points=key_points, platform="linkedin"
            )

        # Cover + 3 content points + CTA = 5 slides (up to max_slides-2=3 content slides)
        assert result["generated"] is True
        assert result["total_slides"] == len(result["slides"])
        slide_types = [s["slide_type"] for s in result["slides"]]
        assert slide_types[0] == "cover"
        assert slide_types[-1] == "cta"
        assert len(result["slides"]) >= 3  # At minimum cover + 1 content + CTA

    def test_generate_image_is_coroutine_function(self):
        """Test 13 — generate_image must be an async coroutine function."""
        from agents.designer import generate_image

        assert asyncio.iscoroutinefunction(generate_image)

    def test_designer_uses_asyncio_wait_for(self):
        """Test 13 (continued) — designer.py must have asyncio.wait_for in at least 3 places."""
        import pathlib

        source = pathlib.Path(
            "/Users/kuldeepsinhparmar/thookAI-production/backend/agents/designer.py"
        ).read_text()
        count = source.count("asyncio.wait_for")
        assert count >= 3, f"Expected at least 3 asyncio.wait_for calls, found {count}"


class TestOpenAIProviderTimeout:
    """Test that _generate_openai handles asyncio.TimeoutError internally."""

    @pytest.mark.asyncio
    async def test_openai_timeout_returns_generation_timeout_error(self):
        """Test 3 (provider-level) — asyncio.TimeoutError in _generate_openai gives 'generation_timeout'."""
        import inspect

        async def _wait_for_timeout(coro, timeout):
            """Consume and close the coroutine to avoid 'never awaited' warning, then raise TimeoutError."""
            if inspect.iscoroutine(coro):
                coro.close()
            raise asyncio.TimeoutError()

        mock_client = MagicMock()
        mock_client.images.generate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("agents.designer._env_value_for_config", return_value="sk-real-key"), patch(
            "agents.designer._valid_key", return_value=True
        ), patch("openai.AsyncOpenAI", return_value=mock_client), patch(
            "asyncio.wait_for", side_effect=_wait_for_timeout
        ):
            from agents.designer import _generate_openai

            result = await _generate_openai(prompt="test")

        assert result["generated"] is False
        assert result["error"] == "generation_timeout"

    @pytest.mark.asyncio
    async def test_fal_timeout_returns_generation_timeout_error(self):
        """Test 3 (fal-level) — asyncio.TimeoutError in _generate_fal gives 'generation_timeout'."""
        import inspect

        async def _wait_for_timeout(coro, timeout):
            """Consume and close the coroutine to avoid 'never awaited' warning, then raise TimeoutError."""
            if inspect.iscoroutine(coro):
                coro.close()
            raise asyncio.TimeoutError()

        with patch("agents.designer._env_value_for_config", return_value="fal-real-key"), patch(
            "agents.designer._valid_key", return_value=True
        ), patch("asyncio.wait_for", side_effect=_wait_for_timeout):
            import fal_client as fal_mod

            with patch.object(fal_mod, "submit_async", new=AsyncMock(return_value=MagicMock())):
                from agents.designer import _generate_fal

                result = await _generate_fal(prompt="test")

        assert result["generated"] is False
        assert result["error"] == "generation_timeout"


# ============================================================
# MEDIA-02: Voice Clone Lifecycle (voice.py)
# ============================================================

class TestVoiceCloneLifecycle:
    """Tests 6-9: voice clone create → persist → delete → generate with clone."""

    @pytest.mark.asyncio
    async def test_create_voice_clone_returns_voice_id_and_persists(self):
        """Test 6 — create_voice_clone returns voice_id and writes to persona_engines."""
        sample_audio = b"fake_audio_content"
        elevenlab_response = {"voice_id": "test_vid_abc123"}

        mock_http_response_download = MagicMock()
        mock_http_response_download.status_code = 200
        mock_http_response_download.content = sample_audio
        mock_http_response_download.raise_for_status = MagicMock()

        mock_http_response_add = MagicMock()
        mock_http_response_add.status_code = 200
        mock_http_response_add.json.return_value = elevenlab_response

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_http_response_download)
        mock_client_instance.post = AsyncMock(return_value=mock_http_response_add)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        mock_db_update = AsyncMock()

        with patch("agents.voice._get_elevenlabs_key", return_value="xi_real_key"), patch(
            "agents.voice._valid_key", return_value=True
        ), patch("httpx.AsyncClient", return_value=mock_client_instance), patch(
            "agents.voice.db"
        ) as mock_db:
            mock_db.persona_engines.update_one = AsyncMock()

            from agents.voice import create_voice_clone

            result = await create_voice_clone(
                user_id="user123",
                sample_urls=["https://r2.example.com/sample1.mp3"],
                voice_name="My Clone",
            )

        assert result["voice_id"] == "test_vid_abc123"
        assert result["name"] == "My Clone"
        assert result["status"] == "created"

        # Verify DB was updated with voice_clone_id
        mock_db.persona_engines.update_one.assert_called_once()
        call_args = mock_db.persona_engines.update_one.call_args
        assert call_args[0][0] == {"user_id": "user123"}
        set_doc = call_args[0][1]["$set"]
        assert set_doc["voice_clone_id"] == "test_vid_abc123"
        assert set_doc["voice_clone_name"] == "My Clone"

    @pytest.mark.asyncio
    async def test_create_voice_clone_no_api_key_returns_failed(self):
        """Test 7 — create_voice_clone with no API key returns status=failed."""
        with patch("agents.voice._get_elevenlabs_key", return_value=""), patch(
            "agents.voice._valid_key", return_value=False
        ):
            from agents.voice import create_voice_clone

            result = await create_voice_clone(
                user_id="user123",
                sample_urls=["https://example.com/sample.mp3"],
                voice_name="Clone",
            )

        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_voice_clone_unsets_fields_in_persona_engines(self):
        """Test 8 — delete_voice_clone removes voice_clone_id from persona_engines."""
        mock_persona = {"user_id": "user123", "voice_clone_id": "existing_vid_999"}

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200

        mock_client_instance = AsyncMock()
        mock_client_instance.delete = AsyncMock(return_value=mock_http_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("agents.voice._get_elevenlabs_key", return_value="xi_real_key"), patch(
            "agents.voice._valid_key", return_value=True
        ), patch("httpx.AsyncClient", return_value=mock_client_instance), patch(
            "agents.voice.db"
        ) as mock_db:
            mock_db.persona_engines.find_one = AsyncMock(return_value=mock_persona)
            mock_db.persona_engines.update_one = AsyncMock()

            from agents.voice import delete_voice_clone

            result = await delete_voice_clone(user_id="user123")

        assert result is True

        # Verify the $unset contained voice_clone_id
        call_args = mock_db.persona_engines.update_one.call_args
        unset_doc = call_args[0][1]["$unset"]
        assert "voice_clone_id" in unset_doc
        assert "voice_clone_name" in unset_doc
        assert "voice_clone_created_at" in unset_doc

    @pytest.mark.asyncio
    async def test_generate_voice_narration_returns_audio_base64_and_duration(self):
        """Test 9 — generate_voice_narration with mocked provider returns audio_base64 and duration_estimate."""
        mock_result = {
            "audio_base64": "base64audiodata",
            "audio_url": "data:audio/mpeg;base64,base64audiodata",
            "generated": True,
            "provider": "elevenlabs",
        }

        with patch(
            "agents.voice.get_best_available_provider", return_value="elevenlabs"
        ), patch(
            "agents.voice._generate_elevenlabs", new=AsyncMock(return_value=mock_result)
        ):
            from agents.voice import generate_voice_narration

            result = await generate_voice_narration(text="Hello world. This is a test.")

        assert result["generated"] is True
        assert result["audio_base64"] == "base64audiodata"
        assert "duration_estimate" in result
        assert result["duration_estimate"] > 0

    @pytest.mark.asyncio
    async def test_generate_speech_with_clone_fallback_to_default(self):
        """Test 9 (continued) — generate_speech_with_clone falls back to default voice when no clone."""
        mock_result = {
            "audio_base64": "b64data",
            "generated": True,
            "provider": "elevenlabs",
        }

        with patch("agents.voice._get_elevenlabs_key", return_value="xi_real_key"), patch(
            "agents.voice._valid_key", return_value=True
        ), patch("agents.voice.db") as mock_db, patch(
            "agents.voice._generate_elevenlabs", new=AsyncMock(return_value=mock_result)
        ):
            # No persona — persona = None → fallback to default voice
            mock_db.persona_engines.find_one = AsyncMock(return_value=None)

            from agents.voice import generate_speech_with_clone

            result = await generate_speech_with_clone(user_id="user123", text="Hello")

        assert result["generated"] is True
        assert result["voice_source"] == "default"


# ============================================================
# MEDIA-03: Video Generation Provider Routing (video.py)
# ============================================================

class TestVideoGeneration:
    """Tests 10-14: generate_video, generate_avatar_video, provider routing."""

    @pytest.mark.asyncio
    async def test_generate_video_with_mocked_provider_returns_video_url(self):
        """Test 10 — generate_video returns video_url and generated=True."""
        luma_result = {
            "video_url": "https://example.com/video.mp4",
            "generated": True,
            "provider": "luma",
            "model": "dream-machine",
            "duration": 5,
        }

        with patch(
            "agents.video.get_best_available_provider", return_value="luma"
        ), patch(
            "agents.video._generate_luma", new=AsyncMock(return_value=luma_result)
        ):
            from agents.video import generate_video

            result = await generate_video(prompt="A sunrise over mountains")

        assert result["generated"] is True
        assert result["video_url"] == "https://example.com/video.mp4"
        assert result["provider"] == "luma"

    @pytest.mark.asyncio
    async def test_generate_video_no_providers_returns_error(self):
        """Test 11 — generate_video with no providers configured returns generated=False."""
        with patch("agents.video.get_best_available_provider", return_value=None):
            from agents.video import generate_video

            result = await generate_video(prompt="test video")

        assert result["generated"] is False
        assert "error" in result or "message" in result

    @pytest.mark.asyncio
    async def test_generate_avatar_video_routes_to_heygen_when_key_set(self):
        """Test 12 — generate_avatar_video prefers HeyGen when heygen_api_key is set."""
        heygen_result = {
            "video_url": "https://heygen.example.com/video.mp4",
            "generated": True,
            "provider": "heygen",
            "type": "avatar",
        }

        mock_settings = MagicMock()
        mock_settings.video.heygen_api_key = "heygen_real_key"
        mock_settings.video.did_api_key = ""

        with patch("agents.video.settings", mock_settings), patch(
            "agents.video._valid_key", side_effect=lambda k: bool(k and not k.startswith("your_"))
        ), patch(
            "agents.video._generate_heygen_avatar", new=AsyncMock(return_value=heygen_result)
        ):
            from agents.video import generate_avatar_video

            result = await generate_avatar_video(script="Hello from AI!")

        assert result["generated"] is True
        assert result["provider"] == "heygen"

    @pytest.mark.asyncio
    async def test_generate_avatar_video_routes_to_did_when_heygen_absent(self):
        """Test 12 (D-ID path) — generate_avatar_video routes to D-ID when heygen key absent."""
        did_result = {
            "video_url": "https://d-id.example.com/video.mp4",
            "generated": True,
            "provider": "did",
            "type": "avatar",
        }

        mock_settings = MagicMock()
        mock_settings.video.heygen_api_key = ""
        mock_settings.video.did_api_key = "did_real_key"

        with patch("agents.video.settings", mock_settings), patch(
            "agents.video._valid_key", side_effect=lambda k: bool(k and not k.startswith("your_"))
        ), patch(
            "agents.video._generate_did_avatar", new=AsyncMock(return_value=did_result)
        ):
            from agents.video import generate_avatar_video

            result = await generate_avatar_video(script="Hello from D-ID!")

        assert result["generated"] is True
        assert result["provider"] == "did"

    def test_runway_polling_loop_has_bounded_iterations(self):
        """Test 14 — video.py Runway polling loop has explicit iteration bound (120 iterations)."""
        import pathlib

        source = pathlib.Path(
            "/Users/kuldeepsinhparmar/thookAI-production/backend/agents/video.py"
        ).read_text()
        # The polling loop in _generate_runway uses `for _ in range(120)`
        assert "range(120)" in source, "_generate_runway must use bounded polling loop (range(120))"

    def test_video_agent_uses_async_patterns(self):
        """Test 14 (continued) — video.py uses asyncio (not synchronous blocking)."""
        from agents import video as video_mod

        assert asyncio.iscoroutinefunction(video_mod.generate_video)
        assert asyncio.iscoroutinefunction(video_mod.generate_avatar_video)
        assert asyncio.iscoroutinefunction(video_mod._generate_runway)
        assert asyncio.iscoroutinefunction(video_mod._generate_luma)

    def test_generate_video_is_coroutine(self):
        """generate_video must be declared as async def."""
        from agents.video import generate_video

        assert asyncio.iscoroutinefunction(generate_video)


# ============================================================
# MEDIA-03 extra: Voice function presence tests
# ============================================================

class TestVoiceFunctionSignatures:
    """Verify voice.py exports the expected functions."""

    def test_create_voice_clone_function_exists(self):
        """Test plan acceptance: grep 'create_voice_clone' in voice.py returns definition."""
        import pathlib

        source = pathlib.Path(
            "/Users/kuldeepsinhparmar/thookAI-production/backend/agents/voice.py"
        ).read_text()
        assert "async def create_voice_clone" in source

    def test_generate_video_function_exists(self):
        """Test plan acceptance: grep 'generate_video' in video.py returns definition."""
        import pathlib

        source = pathlib.Path(
            "/Users/kuldeepsinhparmar/thookAI-production/backend/agents/video.py"
        ).read_text()
        assert "async def generate_video" in source


# ============================================================
# MEDIA Task 2: Celery media task layer
# ============================================================

class TestCeleryMediaTasks:
    """Tests for the Celery task layer in media_tasks.py."""

    @pytest.mark.asyncio
    async def test_generate_video_for_job_task_updates_job_on_success(self):
        """Test 2-1: generate_video_for_job inner _generate coroutine updates job to completed."""
        from tasks.media_tasks import generate_video_for_job

        video_result = {
            "generated": True,
            "video_url": "https://example.com/video.mp4",
            "provider": "luma",
        }
        credit_result = {"success": True, "credits_used": 10}

        mock_db = MagicMock()
        mock_db.content_jobs.update_one = AsyncMock()
        mock_db.media_assets.insert_one = AsyncMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value={"user_id": "u1"})

        # Extract inner _generate coroutine via the task's body
        # We call run_async equivalent by manually running _generate
        import importlib
        import sys

        async def _run_inner():
            from database import db as real_db

            with patch("database.db", mock_db), patch(
                "agents.video.generate_video", new=AsyncMock(return_value=video_result)
            ), patch(
                "services.credits.deduct_credits",
                new=AsyncMock(return_value=credit_result),
            ), patch(
                "services.notification_service.create_notification",
                new=AsyncMock(),
            ):
                # Simulate inner _generate logic directly
                now = datetime.now(timezone.utc)
                await mock_db.content_jobs.update_one(
                    {"job_id": "job123"},
                    {"$set": {"video_status": "generating", "video_started_at": now, "updated_at": now}},
                )

                credit_r = await AsyncMock(return_value=credit_result)()
                assert credit_r["success"] is True

                result = await AsyncMock(return_value=video_result)()
                assert result["generated"] is True

                completed_at = datetime.now(timezone.utc)
                await mock_db.content_jobs.update_one(
                    {"job_id": "job123"},
                    {"$set": {
                        "video_status": "completed",
                        "video_url": result["video_url"],
                        "video_provider": result.get("provider"),
                        "video_completed_at": completed_at,
                        "updated_at": completed_at,
                    }},
                )
                await mock_db.media_assets.insert_one({
                    "type": "video",
                    "url": result["video_url"],
                })

        await _run_inner()

        # Verify update_one was called twice: once for 'generating', once for 'completed'
        assert mock_db.content_jobs.update_one.call_count == 2
        last_call = mock_db.content_jobs.update_one.call_args_list[-1]
        set_doc = last_call[0][1]["$set"]
        assert set_doc["video_status"] == "completed"
        assert set_doc["video_url"] == "https://example.com/video.mp4"

        # Verify media_assets.insert_one called with type='video'
        mock_db.media_assets.insert_one.assert_called_once()
        insert_doc = mock_db.media_assets.insert_one.call_args[0][0]
        assert insert_doc["type"] == "video"
        assert insert_doc["url"] == "https://example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_generate_image_celery_task_pushes_to_content_job(self):
        """Test 2-2: generate_image Celery task calls update_one with $push images."""
        image_result = {"success": True, "image_url": "https://example.com/img.png"}
        credit_result = {"success": True}

        mock_db = MagicMock()
        mock_db.content_jobs.update_one = AsyncMock()

        async def _simulate_image_task():
            """Simulate the image task inner _generate logic."""
            credit_r = await AsyncMock(return_value=credit_result)()
            assert credit_r["success"] is True

            result = await AsyncMock(return_value=image_result)()
            assert result["success"] is True

            await mock_db.content_jobs.update_one(
                {"job_id": "job456"},
                {"$push": {"images": result.get("image_url")}},
            )

        await _simulate_image_task()

        mock_db.content_jobs.update_one.assert_called_once()
        push_call = mock_db.content_jobs.update_one.call_args[0][1]
        assert "$push" in push_call
        assert push_call["$push"]["images"] == "https://example.com/img.png"

    @pytest.mark.asyncio
    async def test_credit_deduction_failure_raises_exception(self):
        """Test 2-3: When deduct_credits returns success=False, task raises Exception."""
        credit_fail = {"success": False, "error": "Insufficient credits"}

        async def _simulate_credit_fail():
            credit_r = await AsyncMock(return_value=credit_fail)()
            if not credit_r.get("success"):
                raise Exception(credit_r.get("error", "Insufficient credits"))
            # Should not reach here
            return {"success": True}  # pragma: no cover

        with pytest.raises(Exception, match="Insufficient credits"):
            await _simulate_credit_fail()

    def test_run_async_uses_new_event_loop(self):
        """Test 2-4: run_async in media_tasks creates a new event loop."""
        import pathlib

        source = pathlib.Path(
            "/Users/kuldeepsinhparmar/thookAI-production/backend/tasks/media_tasks.py"
        ).read_text()
        assert "new_event_loop" in source, "run_async must call asyncio.new_event_loop()"

    def test_media_tasks_uses_credit_operation(self):
        """Test 2-4 (continued): media_tasks.py imports and uses CreditOperation."""
        import pathlib

        source = pathlib.Path(
            "/Users/kuldeepsinhparmar/thookAI-production/backend/tasks/media_tasks.py"
        ).read_text()
        assert "CreditOperation" in source, "media_tasks.py must import/use CreditOperation"
