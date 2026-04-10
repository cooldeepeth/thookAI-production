"""
Media Routes for ThookAI

Handles file upload URLs and media asset management.
Uses Cloudflare R2 for storage with presigned URLs for direct uploads.
Also exposes POST /media/orchestrate for multi-model media generation.
"""

import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional

from auth_utils import get_current_user
from services.media_storage import (
    generate_upload_url,
    confirm_upload,
    get_user_assets,
    delete_asset,
    VALID_FILE_TYPES
)
from services.media_orchestrator import MediaBrief, MEDIA_TYPE_COST_CAPS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["media"])


class UploadUrlRequest(BaseModel):
    file_type: str
    filename: str
    content_type: str


class ConfirmUploadRequest(BaseModel):
    storage_key: str
    file_type: str
    filename: str
    content_type: str
    file_size_bytes: int
    job_id: Optional[str] = None


@router.post("/upload-url")
async def get_upload_url(
    data: UploadUrlRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a presigned URL for direct file upload to R2.
    
    The client should:
    1. Call this endpoint to get the presigned URL
    2. PUT the file directly to the returned upload_url
    3. Call /media/confirm after successful upload
    
    No credits are deducted for uploads - only for processing.
    """
    result = generate_upload_url(
        user_id=current_user["user_id"],
        file_type=data.file_type,
        filename=data.filename,
        content_type=data.content_type
    )
    
    return {
        "success": True,
        **result
    }


@router.post("/confirm")
async def confirm_upload_endpoint(
    data: ConfirmUploadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm a completed upload and save the asset record.
    
    Call this after successfully uploading to the presigned URL.
    """
    try:
        asset = await confirm_upload(
            user_id=current_user["user_id"],
            storage_key=data.storage_key,
            file_type=data.file_type,
            filename=data.filename,
            content_type=data.content_type,
            file_size_bytes=data.file_size_bytes,
            job_id=data.job_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "media_id": asset["media_id"],
        "public_url": asset["public_url"],
        "asset": asset
    }


@router.get("/assets")
async def list_assets(
    file_type: Optional[str] = Query(None, description=f"Filter by type: {', '.join(VALID_FILE_TYPES)}"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    List the current user's media assets.
    """
    result = await get_user_assets(
        user_id=current_user["user_id"],
        file_type=file_type,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        **result
    }


@router.delete("/assets/{media_id}")
async def delete_asset_endpoint(
    media_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a media asset.

    Only the owner can delete their assets.
    """
    await delete_asset(
        user_id=current_user["user_id"],
        media_id=media_id
    )

    return {
        "success": True,
        "message": "Asset deleted"
    }


# ============================================================
# MEDIA ORCHESTRATION ENDPOINT
# ============================================================

class OrchestrateRequest(BaseModel):
    """Request body for POST /media/orchestrate."""
    media_type: str
    platform: str = "linkedin"
    content_text: str
    style: str = "minimal"
    slides: Optional[List[Dict[str, Any]]] = None
    data_points: Optional[List[Dict[str, Any]]] = None
    avatar_id: Optional[str] = None
    voice_id: Optional[str] = None
    video_url: Optional[str] = None
    music_url: Optional[str] = None
    job_id: Optional[str] = None

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, v: str) -> str:
        valid_types = set(MEDIA_TYPE_COST_CAPS.keys()) | {"auto"}
        if v not in valid_types:
            raise ValueError(
                f"Invalid media_type '{v}'. Must be one of: {', '.join(sorted(valid_types))}"
            )
        return v

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        valid_platforms = {"linkedin", "instagram", "x"}
        if v not in valid_platforms:
            raise ValueError(
                f"Invalid platform '{v}'. Must be one of: {', '.join(sorted(valid_platforms))}"
            )
        return v


@router.post("/orchestrate", status_code=202)
async def orchestrate_media(
    request: OrchestrateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit a multi-model media generation job.

    Validates media_type and platform, loads the user's persona, then
    submits an async Celery task for orchestrated generation.

    Returns 202 Accepted with job_id and status='queued'.
    Poll GET /content/{job_id} for final status and result URL.
    """
    from database import db

    user_id = current_user["user_id"]

    # Load persona card for brand context
    persona_doc = await db.persona_engines.find_one({"user_id": user_id})
    persona_card: Dict[str, Any] = {}
    if persona_doc:
        persona_card = persona_doc.get("card", {})

    # Extract brand color from persona visual aesthetic
    brand_color = (
        persona_card.get("visual_aesthetic", {}).get("primary_color", "#2563EB")
        if isinstance(persona_card.get("visual_aesthetic"), dict)
        else "#2563EB"
    )

    # Generate or use provided job_id
    job_id = request.job_id or f"media_{uuid.uuid4().hex[:16]}"

    # Auto-select format if media_type is "auto" (MEDIA-12)
    media_type = request.media_type
    if media_type == "auto":
        from agents.designer import select_media_format
        format_result = select_media_format(
            platform=request.platform,
            content_text=request.content_text,
            has_data_points=bool(request.data_points),
            has_avatar=bool(request.avatar_id),
        )
        media_type = format_result["media_type"]
        logger.info(
            "Auto-selected media format: %s (reason: %s, confidence: %s)",
            media_type, format_result.get("reason"), format_result.get("confidence"),
        )

    # Build MediaBrief
    brief = MediaBrief(
        job_id=job_id,
        user_id=user_id,
        media_type=media_type,
        platform=request.platform,
        content_text=request.content_text,
        persona_card=persona_card,
        style=request.style,
        slides=request.slides,
        data_points=request.data_points,
        avatar_id=request.avatar_id,
        voice_id=request.voice_id,
        video_url=request.video_url,
        music_url=request.music_url,
        brand_color=brand_color,
    )

    # Submit Celery task (import here to avoid circular dep at module load)
    try:
        from tasks.media_tasks import orchestrate_media_job
        orchestrate_media_job.delay(brief.__dict__)
        logger.info(
            "Queued media orchestration: job_id=%s media_type=%s user_id=%s",
            job_id, request.media_type, user_id,
        )
    except Exception as e:
        logger.error("Failed to queue orchestrate_media_job for job %s: %s", job_id, e)
        raise HTTPException(
            status_code=503,
            detail="Media orchestration task queue unavailable. Please retry.",
        )

    return {"job_id": job_id, "status": "queued"}
