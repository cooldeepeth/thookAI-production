"""
Media Generation Tasks for ThookAI

Async Celery tasks for:
- Video generation
- Image generation
- Voice synthesis

These tasks run in background workers to prevent blocking the API.
"""

import logging
import asyncio
from datetime import datetime, timezone
from celery import shared_task
from typing import Dict, Any

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============ VIDEO GENERATION ============

@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_video(
    self,
    job_id: str,
    user_id: str,
    script: str,
    provider: str = "runway",
    style: str = "realistic",
    duration: int = 10
) -> Dict[str, Any]:
    """
    Generate video from script using specified provider.
    
    This is a long-running task (30-120 seconds) that runs in a Celery worker.
    """
    logger.info(f"Starting video generation task for job {job_id}")
    
    async def _generate():
        from database import db
        from services.creative_providers import CreativeProvidersService
        from services.credits import deduct_credits, add_credits, CreditOperation

        try:
            # Update job status
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"video_status": "generating", "video_started_at": datetime.now(timezone.utc)}}
            )

            # Deduct credits
            credit_result = await deduct_credits(
                user_id=user_id,
                operation=CreditOperation.VIDEO_GENERATE,
                description=f"Video generation: {provider}"
            )

            if not credit_result.get("success"):
                raise Exception(credit_result.get("error", "Insufficient credits"))

            # Generate video
            service = CreativeProvidersService()
            result = await service.generate_video(
                script=script,
                provider=provider,
                style=style,
                duration=duration
            )

            if result.get("success"):
                import uuid as _uuid
                completed_at = datetime.now(timezone.utc)
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "video_status": "completed",
                        "video_url": result.get("video_url"),
                        "video_completed_at": completed_at,
                    }}
                )
                # Store in media_assets so /api/media/assets shows AI-generated video
                await db.media_assets.insert_one({
                    "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "job_id": job_id,
                    "type": "video",
                    "url": result.get("video_url"),
                    "provider": provider,
                    "created_at": completed_at,
                })
                return {"success": True, "video_url": result.get("video_url")}
            else:
                raise Exception(result.get("error", "Video generation failed"))

        except Exception as e:
            logger.error(f"Video generation failed for job {job_id}: {e}")
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"video_status": "failed", "video_error": str(e)}}
            )
            # Refund credits on task failure
            try:
                await add_credits(
                    user_id,
                    CreditOperation.VIDEO_GENERATE.value,
                    source="video_task_failure_refund",
                    description=f"Auto-refund for failed video generation task on job {job_id}",
                )
            except Exception as refund_err:
                logger.error(f"Failed to refund video credits for job {job_id}: {refund_err}")
            raise
    
    try:
        return run_async(_generate())
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ============ IMAGE GENERATION ============

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_image(
    self,
    job_id: str,
    user_id: str,
    prompt: str,
    provider: str = "openai",
    style: str = "vivid",
    size: str = "1024x1024"
) -> Dict[str, Any]:
    """
    Generate image from prompt.
    
    Faster than video (5-30 seconds) but still benefits from async processing.
    """
    logger.info(f"Starting image generation task for job {job_id}")
    
    async def _generate():
        from database import db
        from services.creative_providers import CreativeProvidersService
        from services.credits import deduct_credits, add_credits, CreditOperation

        try:
            # Deduct credits
            credit_result = await deduct_credits(
                user_id=user_id,
                operation=CreditOperation.IMAGE_GENERATE,
                description=f"Image generation: {provider}"
            )

            if not credit_result.get("success"):
                raise Exception(credit_result.get("error", "Insufficient credits"))

            # Generate image
            service = CreativeProvidersService()
            result = await service.generate_image(
                prompt=prompt,
                provider=provider,
                style=style,
                size=size
            )

            if result.get("success"):
                import uuid as _uuid
                # Update job with image URL
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$push": {"images": result.get("image_url")}}
                )
                # Store in media_assets so /api/media/assets shows AI-generated images
                await db.media_assets.insert_one({
                    "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "job_id": job_id,
                    "type": "image",
                    "url": result.get("image_url"),
                    "provider": provider,
                    "prompt": prompt[:200],
                    "created_at": datetime.now(timezone.utc),
                })
                return {"success": True, "image_url": result.get("image_url")}
            else:
                raise Exception(result.get("error", "Image generation failed"))

        except Exception as e:
            logger.error(f"Image generation failed for job {job_id}: {e}")
            try:
                await add_credits(
                    user_id,
                    CreditOperation.IMAGE_GENERATE.value,
                    source="image_task_failure_refund",
                    description=f"Auto-refund for failed image generation task on job {job_id}",
                )
            except Exception as refund_err:
                logger.error(f"Failed to refund image credits for job {job_id}: {refund_err}")
            raise
    
    try:
        return run_async(_generate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


# ============ VOICE SYNTHESIS ============

@shared_task(bind=True, max_retries=3, default_retry_delay=20)
def generate_voice(
    self,
    job_id: str,
    user_id: str,
    text: str,
    provider: str = "elevenlabs",
    voice_id: str = None
) -> Dict[str, Any]:
    """
    Generate voice narration from text.
    
    Typically 5-15 seconds for short content.
    """
    logger.info(f"Starting voice generation task for job {job_id}")
    
    async def _generate():
        from database import db
        from services.creative_providers import CreativeProvidersService
        from services.credits import deduct_credits, add_credits, CreditOperation

        try:
            # Deduct credits
            credit_result = await deduct_credits(
                user_id=user_id,
                operation=CreditOperation.VOICE_NARRATION,
                description=f"Voice synthesis: {provider}"
            )

            if not credit_result.get("success"):
                raise Exception(credit_result.get("error", "Insufficient credits"))

            # Generate voice
            service = CreativeProvidersService()
            result = await service.generate_voice(
                text=text,
                provider=provider,
                voice_id=voice_id
            )

            if result.get("success"):
                import uuid as _uuid
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {"voice_url": result.get("audio_url")}}
                )
                # Store in media_assets so /api/media/assets shows AI-generated audio
                await db.media_assets.insert_one({
                    "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "job_id": job_id,
                    "type": "audio",
                    "url": result.get("audio_url"),
                    "provider": provider,
                    "created_at": datetime.now(timezone.utc),
                })
                return {"success": True, "audio_url": result.get("audio_url")}
            else:
                raise Exception(result.get("error", "Voice generation failed"))

        except Exception as e:
            logger.error(f"Voice generation failed for job {job_id}: {e}")
            try:
                await add_credits(
                    user_id,
                    CreditOperation.VOICE_NARRATION.value,
                    source="voice_task_failure_refund",
                    description=f"Auto-refund for failed voice generation task on job {job_id}",
                )
            except Exception as refund_err:
                logger.error(f"Failed to refund voice credits for job {job_id}: {refund_err}")
            raise
    
    try:
        return run_async(_generate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=20 * (2 ** self.request.retries))


# ============ CAROUSEL GENERATION ============

@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_carousel(
    self,
    job_id: str,
    user_id: str,
    slides: list,
    provider: str = "openai",
    style: str = "professional"
) -> Dict[str, Any]:
    """
    Generate carousel images (multiple slides).
    
    Runs image generation for each slide sequentially.
    """
    logger.info(f"Starting carousel generation task for job {job_id} ({len(slides)} slides)")
    
    async def _generate():
        from database import db
        from services.creative_providers import CreativeProvidersService
        from services.credits import deduct_credits, CreditOperation
        
        try:
            # Deduct credits for carousel
            credit_result = await deduct_credits(
                user_id=user_id,
                operation=CreditOperation.CAROUSEL_GENERATE,
                description=f"Carousel ({len(slides)} slides): {provider}"
            )
            
            if not credit_result.get("success"):
                raise Exception(credit_result.get("error", "Insufficient credits"))
            
            # Generate each slide
            service = CreativeProvidersService()
            generated_images = []
            
            for i, slide in enumerate(slides):
                result = await service.generate_image(
                    prompt=slide.get("prompt", slide.get("text", "")),
                    provider=provider,
                    style=style
                )
                
                if result.get("success"):
                    generated_images.append({
                        "slide_number": i + 1,
                        "image_url": result.get("image_url"),
                        "text": slide.get("text", "")
                    })
                else:
                    logger.warning(f"Failed to generate slide {i + 1}: {result.get('error')}")
            
            import uuid as _uuid
            # Update job
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "carousel_images": generated_images,
                    "carousel_status": "completed"
                }}
            )

            # Store each slide in media_assets so /api/media/assets shows carousel images
            for img in generated_images:
                await db.media_assets.insert_one({
                    "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "job_id": job_id,
                    "type": "image",
                    "url": img["image_url"],
                    "provider": provider,
                    "carousel_slide": img["slide_number"],
                    "created_at": datetime.now(timezone.utc),
                })

            return {"success": True, "slides": generated_images}
                
        except Exception as e:
            logger.error(f"Carousel generation failed for job {job_id}: {e}")
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"carousel_status": "failed", "carousel_error": str(e)}}
            )
            raise
    
    try:
        return run_async(_generate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ============ PIPELINE VIDEO GENERATION ============

@shared_task(bind=True, max_retries=2, default_retry_delay=90)
def generate_video_for_job(
    self,
    job_id: str,
    user_id: str,
    content: str,
    style: str = "cinematic",
) -> Dict[str, Any]:
    """
    Generate a video for a content job as part of the pipeline.

    Dispatched by the content pipeline when generate_video=True
    and the user has studio/agency tier.

    Args:
        job_id: The content job to attach the video to.
        user_id: Owner of the job.
        content: Draft text used to derive the video prompt.
        style: One of cinematic, talking_head, slideshow, abstract.
    """
    logger.info("Starting pipeline video generation for job %s (style=%s)", job_id, style)

    async def _generate():
        from database import db
        from agents.video import generate_video as video_generate, generate_avatar_video
        from services.credits import deduct_credits, CreditOperation
        import uuid as _uuid

        try:
            # Mark as generating
            now = datetime.now(timezone.utc)
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"video_status": "generating", "video_started_at": now, "updated_at": now}},
            )

            # Deduct credits
            credit_result = await deduct_credits(
                user_id=user_id,
                operation=CreditOperation.VIDEO_GENERATE,
                description=f"Pipeline video generation ({style})",
                metadata={"job_id": job_id},
            )
            if not credit_result.get("success"):
                raise Exception(credit_result.get("error", "Insufficient credits for video generation"))

            # Build prompt from content
            prompt = f"Create a {style} video visualizing: {content[:500]}"

            # Talking head uses avatar flow; others use standard video generation
            if style == "talking_head":
                persona = await db.persona_engines.find_one({"user_id": user_id}, {"heygen_avatar_id": 1})
                avatar_id = persona.get("heygen_avatar_id") if persona else None
                result = await generate_avatar_video(
                    script=content[:1000],
                    avatar_id=avatar_id,
                    provider=None,
                )
            else:
                result = await video_generate(
                    prompt=prompt,
                    duration=5,
                    provider=None,
                    model=None,
                )

            if result.get("generated"):
                video_url = result.get("video_url")
                completed_at = datetime.now(timezone.utc)

                # Update the content job
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "video_status": "completed",
                        "video_url": video_url,
                        "video_provider": result.get("provider"),
                        "video_completed_at": completed_at,
                        "updated_at": completed_at,
                    }},
                )

                # Store in media_assets collection
                await db.media_assets.insert_one({
                    "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "job_id": job_id,
                    "type": "video",
                    "url": video_url,
                    "provider": result.get("provider"),
                    "style": style,
                    "created_at": completed_at,
                })

                # Create notification
                try:
                    from services.notification_service import create_notification
                    await create_notification(
                        user_id=user_id,
                        type="video_ready",
                        title="Your video is ready",
                        body=f"Video for your {style} content has been generated.",
                        metadata={"job_id": job_id, "video_url": video_url},
                    )
                except Exception as notif_err:
                    logger.warning("Failed to create video notification for job %s: %s", job_id, notif_err)

                logger.info("Video generation completed for job %s: %s", job_id, video_url)
                return {"success": True, "video_url": video_url, "provider": result.get("provider")}
            else:
                error_msg = result.get("error") or result.get("message") or "Video generation failed"
                raise Exception(error_msg)

        except Exception as e:
            logger.error("Video generation failed for job %s: %s", job_id, e)
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "video_status": "failed",
                    "video_error": str(e),
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            raise

    try:
        return run_async(_generate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=90 * (2 ** self.request.retries))


# ============ MEDIA ORCHESTRATION ============

@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def orchestrate_media_job(self, brief_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a multi-model media orchestration pipeline.

    Accepts a serialised MediaBrief dict, reconstructs the dataclass,
    runs the full orchestration pipeline (asset staging, provider calls,
    Remotion render), and stores the result in media_assets.

    On failure: logs error, updates content_jobs with error status.
    Retries once after 120s for transient failures (network, Remotion).

    Args:
        brief_dict: MediaBrief.__dict__ serialised to a plain Python dict.
    """
    job_id = brief_dict.get("job_id", "unknown")
    user_id = brief_dict.get("user_id", "unknown")
    media_type = brief_dict.get("media_type", "unknown")

    logger.info(
        "Starting media orchestration task: job_id=%s media_type=%s user_id=%s",
        job_id, media_type, user_id,
    )

    async def _orchestrate():
        from database import db
        from services.media_orchestrator import MediaBrief, orchestrate
        import uuid as _uuid

        # Reconstruct MediaBrief from dict
        brief = MediaBrief(
            job_id=brief_dict["job_id"],
            user_id=brief_dict["user_id"],
            media_type=brief_dict["media_type"],
            platform=brief_dict.get("platform", "linkedin"),
            content_text=brief_dict.get("content_text", ""),
            persona_card=brief_dict.get("persona_card", {}),
            style=brief_dict.get("style", "minimal"),
            slides=brief_dict.get("slides"),
            data_points=brief_dict.get("data_points"),
            avatar_id=brief_dict.get("avatar_id"),
            voice_id=brief_dict.get("voice_id"),
            video_url=brief_dict.get("video_url"),
            music_url=brief_dict.get("music_url"),
            brand_color=brief_dict.get("brand_color", "#2563EB"),
        )

        try:
            result = await orchestrate(brief)

            result_url = result.get("url")
            completed_at = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )

            # Store in media_assets for display in /api/media/assets
            await db.media_assets.insert_one({
                "asset_id": f"asset_{_uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "job_id": job_id,
                "type": media_type,
                "url": result_url,
                "render_id": result.get("render_id"),
                "media_type": media_type,
                "credits_consumed": result.get("credits_consumed", 0),
                "created_at": completed_at,
            })

            logger.info(
                "Media orchestration completed: job_id=%s url=%s credits=%d",
                job_id, result_url, result.get("credits_consumed", 0),
            )
            return {"success": True, "url": result_url, "media_type": media_type}

        except Exception as e:
            logger.error("Media orchestration failed for job %s: %s", job_id, e)
            # Update content job with error if it exists
            try:
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "media_status": "failed",
                        "media_error": str(e),
                        "updated_at": __import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ),
                    }},
                )
            except Exception as db_err:
                logger.warning(
                    "Failed to update content_jobs with error for job %s: %s", job_id, db_err
                )
            raise

    try:
        return run_async(_orchestrate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)
