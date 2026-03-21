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
        from services.credits import deduct_credits, CreditOperation
        
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
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "video_status": "completed",
                        "video_url": result.get("video_url"),
                        "video_completed_at": datetime.now(timezone.utc)
                    }}
                )
                return {"success": True, "video_url": result.get("video_url")}
            else:
                raise Exception(result.get("error", "Video generation failed"))
                
        except Exception as e:
            logger.error(f"Video generation failed for job {job_id}: {e}")
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"video_status": "failed", "video_error": str(e)}}
            )
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
        from services.credits import deduct_credits, CreditOperation
        
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
                # Update job with image URL
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$push": {"images": result.get("image_url")}}
                )
                return {"success": True, "image_url": result.get("image_url")}
            else:
                raise Exception(result.get("error", "Image generation failed"))
                
        except Exception as e:
            logger.error(f"Image generation failed for job {job_id}: {e}")
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
        from services.credits import deduct_credits, CreditOperation
        
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
                await db.content_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {"voice_url": result.get("audio_url")}}
                )
                return {"success": True, "audio_url": result.get("audio_url")}
            else:
                raise Exception(result.get("error", "Voice generation failed"))
                
        except Exception as e:
            logger.error(f"Voice generation failed for job {job_id}: {e}")
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
            
            # Update job
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "carousel_images": generated_images,
                    "carousel_status": "completed"
                }}
            )
            
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
