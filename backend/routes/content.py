from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging
from database import db
from auth_utils import get_current_user
from agents.pipeline import run_agent_pipeline
from agents.learning import capture_learning_signal

# Celery task imports
from tasks import is_redis_configured, get_task_status as celery_get_task_status
from tasks.media_tasks import generate_image as celery_generate_image
from tasks.media_tasks import generate_voice as celery_generate_voice
from tasks.media_tasks import generate_video as celery_generate_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

PLATFORM_CONTENT_TYPES = {
    "linkedin": ["post", "carousel_caption", "article"],
    "x": ["tweet", "thread"],
    "instagram": ["feed_caption", "reel_caption"],
}


class ContentCreateRequest(BaseModel):
    platform: str
    content_type: str
    raw_input: str
    attachment_url: Optional[str] = None  # For Visual Agent
    upload_ids: Optional[List[str]] = None


class ContentStatusUpdate(BaseModel):
    status: str  # approved | rejected
    edited_content: Optional[str] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None  # Rejection notes


class ImageGenerateRequest(BaseModel):
    job_id: str
    style: str = "minimal"  # minimal, bold, data-viz, personal, cinematic, etc.
    prompt_override: Optional[str] = None
    provider: Optional[str] = None  # openai, stability, fal, replicate, leonardo, ideogram
    model: Optional[str] = None


class CarouselGenerateRequest(BaseModel):
    job_id: str
    style: str = "minimal"
    key_points: Optional[List[str]] = None
    provider: Optional[str] = None


class VoiceGenerateRequest(BaseModel):
    job_id: str
    voice_id: Optional[str] = None
    stability: float = 0.5
    similarity_boost: float = 0.75
    provider: Optional[str] = None  # elevenlabs, openai_tts, playht, murf, google_tts
    model: Optional[str] = None


class VideoGenerateRequest(BaseModel):
    job_id: str
    prompt_override: Optional[str] = None
    duration: int = 5
    provider: Optional[str] = None  # runway, kling, pika, luma
    model: Optional[str] = None


class AvatarVideoRequest(BaseModel):
    job_id: str
    avatar_id: Optional[str] = None
    source_image_url: Optional[str] = None
    provider: Optional[str] = None  # heygen, did


class RegenerateRequest(BaseModel):
    hint: Optional[str] = None  # Additional guidance for regeneration


@router.post("/create")
async def create_content(
    data: ContentCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    if len(data.raw_input.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please provide more context for your content idea")

    valid_types = PLATFORM_CONTENT_TYPES.get(data.platform.lower(), [])
    if data.content_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid content type for {data.platform}")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    job = {
        "job_id": job_id,
        "user_id": current_user["user_id"],
        "platform": data.platform.lower(),
        "content_type": data.content_type,
        "raw_input": data.raw_input,
        "upload_ids": data.upload_ids or [],
        "status": "running",
        "current_agent": "commander",
        "agent_outputs": {},
        "agent_summaries": {},
        "final_content": None,
        "qc_score": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.content_jobs.insert_one(job)

    background_tasks.add_task(
        run_agent_pipeline,
        job_id,
        current_user["user_id"],
        data.platform.lower(),
        data.content_type,
        data.raw_input,
        data.upload_ids or [],
    )
    return {"job_id": job_id, "status": "running"}


@router.get("/job/{job_id}")
async def get_job(job_id: str, current_user: dict = Depends(get_current_user)):
    job = await db.content_jobs.find_one(
        {"job_id": job_id, "user_id": current_user["user_id"]}, {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if isinstance(job.get("final_content"), str):
        job["final_content"] = {"post": job["final_content"]}
    return job


@router.patch("/job/{job_id}/status")
async def update_job_status(
    job_id: str, data: ContentStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Update content job status (approve/reject) and capture learning signals."""
    job = await db.content_jobs.find_one({"job_id": job_id, "user_id": current_user["user_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check idempotency - don't re-process already approved/rejected jobs
    if job.get("status") in ["approved", "rejected"]:
        return {"message": f"Job already {job.get('status')}", "status": job.get("status")}
    
    user_id = current_user["user_id"]
    original_content = job.get("final_content", "")
    final_content = data.edited_content if data.edited_content else original_content
    
    update = {"status": data.status, "updated_at": datetime.now(timezone.utc)}
    if data.edited_content:
        update["final_content"] = data.edited_content
        update["was_edited"] = True
    
    await db.content_jobs.update_one({"job_id": job_id}, {"$set": update})
    
    # Capture learning signal in background (don't block the response)
    if data.status == "approved":
        action = "edited" if data.edited_content and data.edited_content != original_content else "approved"
        background_tasks.add_task(
            capture_learning_signal,
            user_id=user_id,
            job_id=job_id,
            original_content=original_content,
            final_content=final_content,
            action=action
        )
        logger.info(f"Scheduled learning signal capture for approved job {job_id}")
    
    elif data.status == "rejected":
        background_tasks.add_task(
            capture_learning_signal,
            user_id=user_id,
            job_id=job_id,
            original_content=original_content,
            final_content=final_content,
            action="rejected"
        )
        logger.info(f"Scheduled learning signal capture for rejected job {job_id}")
    
    # Fire outbound webhook for job.approved
    if data.status == "approved":
        try:
            import asyncio
            from services.webhook_service import fire_webhook
            asyncio.create_task(fire_webhook(user_id, "job.approved", {
                "job_id": job_id,
                "platform": job.get("platform"),
                "content_type": job.get("content_type"),
                "was_edited": bool(data.edited_content),
            }))
        except Exception:
            logger.warning("Failed to fire job.approved webhook for job %s", job_id)

    return {"message": f"Content {data.status}", "status": data.status}


@router.get("/jobs")
async def list_jobs(current_user: dict = Depends(get_current_user), limit: int = 20):
    jobs = await db.content_jobs.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "agent_outputs": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"jobs": jobs}


@router.get("/jobs/{job_id}/task-status")
async def get_job_task_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a Celery task associated with a content job."""
    job = await db.content_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user["user_id"]
    })
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    celery_task_id = job.get("celery_task_id")
    
    if not celery_task_id:
        # No Celery task - either sync mode or task not started
        return {
            "mode": "sync",
            "status": "completed" if job.get("status") in ["completed", "approved"] else job.get("status", "unknown"),
            "job_status": job.get("status")
        }
    
    # Get task status from Celery
    task_status = await celery_get_task_status(celery_task_id)
    
    return {
        "mode": "async",
        "task_id": celery_task_id,
        "job_status": job.get("status"),
        **task_status
    }


@router.get("/platform-types")
async def get_platform_types():
    return PLATFORM_CONTENT_TYPES


# ============ MEDIA GENERATION ENDPOINTS ============

@router.post("/generate-image")
async def generate_image(
    data: ImageGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate an image for a content job using Designer Agent."""
    from agents.designer import generate_image as designer_generate, get_available_styles
    
    job = await db.content_jobs.find_one({
        "job_id": data.job_id,
        "user_id": current_user["user_id"]
    })
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get persona for style customization
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    persona_card = persona.get("card", {}) if persona else {}
    
    # Build prompt from content or override
    if data.prompt_override:
        prompt = data.prompt_override
    else:
        # Extract key theme from content
        content = job.get("final_content", "") or job.get("raw_input", "")
        commander = job.get("agent_outputs", {}).get("commander", {})
        primary_angle = commander.get("primary_angle", "")
        prompt = f"Visual for: {primary_angle or content[:200]}"
    
    # Try async dispatch via Celery if Redis is available
    if is_redis_configured():
        try:
            task = celery_generate_image.apply_async(
                args=[
                    data.job_id,
                    current_user["user_id"],
                    prompt,
                    data.provider or "openai",
                    data.style,
                    "1024x1024"
                ]
            )
            # Store celery task ID in job for status tracking
            await db.content_jobs.update_one(
                {"job_id": data.job_id},
                {"$set": {
                    "celery_task_id": task.id,
                    "image_status": "queued",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            logger.info(f"Image generation queued: task_id={task.id}, job_id={data.job_id}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=202,
                content={"task_id": task.id, "status": "queued", "job_id": data.job_id}
            )
        except Exception as e:
            logger.warning(f"Celery dispatch failed, falling back to sync: {e}")
    
    # Fallback: synchronous direct agent call
    result = await designer_generate(
        prompt=prompt,
        style=data.style,
        platform=job.get("platform", "linkedin"),
        persona_card=persona_card,
        provider=data.provider,
        model=data.model
    )
    
    # Store in job's media_assets
    if result.get("generated"):
        await db.content_jobs.update_one(
            {"job_id": data.job_id},
            {
                "$push": {"media_assets": {
                    "type": "image",
                    "style": data.style,
                    "image_url": result.get("image_url"),
                    "prompt_used": result.get("prompt_used"),
                    "created_at": datetime.now(timezone.utc)
                }},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
    
    return result


@router.post("/generate-carousel")
async def generate_carousel(
    data: CarouselGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a carousel of slides for a content job."""
    from agents.designer import generate_carousel as designer_carousel
    
    job = await db.content_jobs.find_one({
        "job_id": data.job_id,
        "user_id": current_user["user_id"]
    })
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get persona
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    persona_card = persona.get("card", {}) if persona else {}
    
    # Extract topic and key points
    commander = job.get("agent_outputs", {}).get("commander", {})
    topic = commander.get("primary_angle", "") or job.get("raw_input", "")[:100]
    
    # Use provided key points or extract from content
    if data.key_points:
        key_points = data.key_points
    else:
        thinker = job.get("agent_outputs", {}).get("thinker", {})
        key_points = thinker.get("key_insights", []) or ["Key point 1", "Key point 2", "Key point 3"]
    
    result = await designer_carousel(
        topic=topic,
        key_points=key_points,
        style=data.style,
        platform=job.get("platform", "linkedin"),
        persona_card=persona_card
    )
    
    # Store carousel in job
    if result.get("generated"):
        await db.content_jobs.update_one(
            {"job_id": data.job_id},
            {
                "$set": {
                    "carousel": result,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    return result


@router.post("/narrate")
async def narrate_content(
    data: VoiceGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate voice narration for a content job using Voice Agent."""
    from agents.voice import generate_voice_narration, get_available_voices
    
    job = await db.content_jobs.find_one({
        "job_id": data.job_id,
        "user_id": current_user["user_id"]
    })
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    content = job.get("final_content", "")
    if not content:
        raise HTTPException(status_code=400, detail="No content to narrate. Generate content first.")
    
    # Try async dispatch via Celery if Redis is available
    if is_redis_configured():
        try:
            task = celery_generate_voice.apply_async(
                args=[
                    data.job_id,
                    current_user["user_id"],
                    content,
                    data.provider or "elevenlabs",
                    data.voice_id
                ]
            )
            # Store celery task ID in job for status tracking
            await db.content_jobs.update_one(
                {"job_id": data.job_id},
                {"$set": {
                    "celery_task_id": task.id,
                    "voice_status": "queued",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            logger.info(f"Voice narration queued: task_id={task.id}, job_id={data.job_id}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=202,
                content={"task_id": task.id, "status": "queued", "job_id": data.job_id}
            )
        except Exception as e:
            logger.warning(f"Celery dispatch failed, falling back to sync: {e}")
    
    # Fallback: synchronous direct agent call
    result = await generate_voice_narration(
        text=content,
        voice_id=data.voice_id,
        stability=data.stability,
        similarity_boost=data.similarity_boost,
        provider=data.provider,
        model=data.model
    )
    
    # Store audio in job
    if result.get("generated"):
        await db.content_jobs.update_one(
            {"job_id": data.job_id},
            {
                "$set": {
                    "audio_url": result.get("audio_url"),
                    "voice_used": result.get("voice_used"),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    return result


@router.get("/voices")
async def list_voices(current_user: dict = Depends(get_current_user)):
    """Get available voices for narration from all providers."""
    from agents.voice import get_available_voices, get_user_cloned_voices
    
    default_voices = get_available_voices()
    user_voices = await get_user_cloned_voices()
    
    return {
        "default_voices": default_voices,
        "user_voices": user_voices
    }


@router.get("/image-styles")
async def list_image_styles():
    """Get available image generation styles."""
    from agents.designer import get_available_styles
    return {"styles": get_available_styles()}


# ============ CREATIVE PROVIDERS ============

@router.get("/providers")
async def get_all_providers():
    """Get status of all creative AI providers."""
    from services.creative_providers import (
        get_available_image_providers,
        get_available_video_providers,
        get_available_voice_providers,
        get_provider_status_summary
    )
    
    return {
        "summary": get_provider_status_summary(),
        "image_providers": get_available_image_providers(),
        "video_providers": get_available_video_providers(),
        "voice_providers": get_available_voice_providers()
    }


@router.get("/providers/image")
async def get_image_providers():
    """Get available image generation providers."""
    from services.creative_providers import get_available_image_providers
    return {"providers": get_available_image_providers()}


@router.get("/providers/video")
async def get_video_providers():
    """Get available video generation providers."""
    from services.creative_providers import get_available_video_providers
    return {"providers": get_available_video_providers()}


@router.get("/providers/voice")
async def get_voice_providers():
    """Get available voice/TTS providers."""
    from services.creative_providers import get_available_voice_providers
    return {"providers": get_available_voice_providers()}


# ============ VIDEO GENERATION ============

@router.post("/generate-video")
async def generate_video(
    data: VideoGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a video for a content job."""
    from agents.video import generate_video as video_generate
    
    job = await db.content_jobs.find_one({
        "job_id": data.job_id,
        "user_id": current_user["user_id"]
    })
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build prompt from content or override
    if data.prompt_override:
        prompt = data.prompt_override
    else:
        content = job.get("final_content", "") or job.get("raw_input", "")
        commander = job.get("agent_outputs", {}).get("commander", {})
        primary_angle = commander.get("primary_angle", "")
        prompt = f"Video visualizing: {primary_angle or content[:200]}"
    
    # Try async dispatch via Celery if Redis is available
    if is_redis_configured():
        try:
            task = celery_generate_video.apply_async(
                args=[
                    data.job_id,
                    current_user["user_id"],
                    prompt,
                    data.provider or "runway",
                    "realistic",
                    data.duration
                ]
            )
            # Store celery task ID in job for status tracking
            await db.content_jobs.update_one(
                {"job_id": data.job_id},
                {"$set": {
                    "celery_task_id": task.id,
                    "video_status": "queued",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            logger.info(f"Video generation queued: task_id={task.id}, job_id={data.job_id}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=202,
                content={"task_id": task.id, "status": "queued", "job_id": data.job_id}
            )
        except Exception as e:
            logger.warning(f"Celery dispatch failed, falling back to sync: {e}")
    
    # Fallback: synchronous direct agent call
    result = await video_generate(
        prompt=prompt,
        duration=data.duration,
        provider=data.provider,
        model=data.model
    )
    
    # Store in job
    if result.get("generated"):
        await db.content_jobs.update_one(
            {"job_id": data.job_id},
            {
                "$push": {"video_assets": {
                    "video_url": result.get("video_url"),
                    "provider": result.get("provider"),
                    "duration": result.get("duration"),
                    "prompt_used": result.get("prompt_used"),
                    "created_at": datetime.now(timezone.utc)
                }},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
    
    return result


@router.post("/generate-avatar-video")
async def generate_avatar_video(
    data: AvatarVideoRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate an avatar/talking head video."""
    from agents.video import generate_avatar_video as avatar_generate
    
    job = await db.content_jobs.find_one({
        "job_id": data.job_id,
        "user_id": current_user["user_id"]
    })
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    script = job.get("final_content", "")
    if not script:
        raise HTTPException(status_code=400, detail="No content for avatar. Generate content first.")
    
    result = await avatar_generate(
        script=script,
        avatar_id=data.avatar_id,
        source_image_url=data.source_image_url,
        provider=data.provider
    )
    
    # Store in job
    if result.get("generated"):
        await db.content_jobs.update_one(
            {"job_id": data.job_id},
            {
                "$set": {
                    "avatar_video": {
                        "video_url": result.get("video_url"),
                        "provider": result.get("provider"),
                        "created_at": datetime.now(timezone.utc)
                    },
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    return result


# ============ REGENERATION & VERSION TRACKING ============

@router.patch("/job/{job_id}/regenerate")
async def regenerate_content(
    job_id: str,
    data: RegenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Regenerate content for a job, creating a new version."""
    original_job = await db.content_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user["user_id"]
    })
    if not original_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check regeneration limit (max 5 per raw input)
    regen_count = original_job.get("regeneration_count", 0)
    if regen_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum regenerations reached (5)")
    
    # Create new job as a regeneration
    new_job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Build enhanced raw input with hint
    raw_input = original_job.get("raw_input", "")
    if data.hint:
        raw_input = f"{raw_input}\n\nAdditional guidance: {data.hint}"
    
    # If there was edited content, use it as a hint
    if original_job.get("was_edited") and original_job.get("final_content"):
        raw_input = f"{raw_input}\n\nPrevious approved style reference: {original_job['final_content'][:500]}"
    
    new_job = {
        "job_id": new_job_id,
        "user_id": current_user["user_id"],
        "platform": original_job.get("platform"),
        "content_type": original_job.get("content_type"),
        "raw_input": raw_input,
        "upload_ids": original_job.get("upload_ids") or [],
        "status": "running",
        "current_agent": "commander",
        "agent_outputs": {},
        "agent_summaries": {},
        "final_content": None,
        "qc_score": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "parent_job_id": job_id,
        "version": regen_count + 2,  # Original is version 1
        "regeneration_count": 0
    }
    await db.content_jobs.insert_one(new_job)
    
    # Update original job's regeneration count
    await db.content_jobs.update_one(
        {"job_id": job_id},
        {"$inc": {"regeneration_count": 1}}
    )
    
    # Run pipeline
    background_tasks.add_task(
        run_agent_pipeline,
        new_job_id,
        current_user["user_id"],
        new_job["platform"],
        new_job["content_type"],
        raw_input,
        new_job.get("upload_ids") or [],
    )
    
    return {
        "job_id": new_job_id,
        "status": "running",
        "version": new_job["version"],
        "parent_job_id": job_id
    }


@router.get("/job/{job_id}/history")
async def get_job_history(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get regeneration history for a job."""
    # Find the root job
    job = await db.content_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user["user_id"]
    })
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get root job ID
    root_id = job.get("parent_job_id") or job_id
    
    # Find all versions
    versions = await db.content_jobs.find(
        {
            "user_id": current_user["user_id"],
            "$or": [
                {"job_id": root_id},
                {"parent_job_id": root_id}
            ]
        },
        {"_id": 0, "job_id": 1, "version": 1, "status": 1, "created_at": 1, "qc_score": 1}
    ).sort("version", 1).to_list(10)
    
    return {
        "root_job_id": root_id,
        "versions": versions,
        "total_versions": len(versions)
    }

