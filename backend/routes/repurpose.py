"""Repurpose and Series Routes for ThookAI.

Handles content repurposing and series planning endpoints.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["content-repurpose"])


# ============ PYDANTIC MODELS ============

class RepurposeRequest(BaseModel):
    job_id: str
    target_platforms: List[str]


class SeriesPlanRequest(BaseModel):
    topic: str
    template_type: str
    num_posts: int = 5
    platform: str = "linkedin"
    custom_angle: Optional[str] = None


class SeriesSaveRequest(BaseModel):
    plan: Dict[str, Any]
    start_date: Optional[str] = None


class CreateSeriesPostRequest(BaseModel):
    series_id: str
    post_number: int


# ============ REPURPOSE ENDPOINTS ============

@router.post("/repurpose")
async def repurpose_content(
    request: RepurposeRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Repurpose approved content to multiple platforms.
    
    Creates new content jobs for each target platform.
    """
    from agents.repurpose import bulk_repurpose
    
    user_id = current_user["user_id"]
    
    # Validate target platforms
    valid_platforms = ["linkedin", "x", "instagram"]
    invalid = [p for p in request.target_platforms if p not in valid_platforms]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid platforms: {invalid}")
    
    result = await bulk_repurpose(
        user_id=user_id,
        source_job_id=request.job_id,
        target_platforms=request.target_platforms
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Repurpose failed"))
    
    return result


@router.get("/repurpose/preview/{job_id}")
async def preview_repurpose(
    job_id: str,
    platforms: str = Query("x,instagram", description="Comma-separated target platforms"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Preview how content would be repurposed without creating jobs."""
    from agents.repurpose import repurpose_content
    
    user_id = current_user["user_id"]
    
    # Get source content
    job = await db.content_jobs.find_one({
        "job_id": job_id,
        "user_id": user_id,
        "status": {"$in": ["approved", "published", "reviewing", "completed"]}
    })
    
    if not job:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Get persona
    persona = await db.persona_engines.find_one({"user_id": user_id})
    persona_card = persona.get("card") if persona else None
    
    target_platforms = [p.strip() for p in platforms.split(",") if p.strip()]
    
    result = await repurpose_content(
        source_content=job.get("final_content", ""),
        source_platform=job.get("platform", "linkedin"),
        target_platforms=target_platforms,
        persona_card=persona_card
    )
    
    return {
        "source_job_id": job_id,
        "source_platform": job.get("platform"),
        "source_preview": job.get("final_content", "")[:200] + "...",
        "repurposed_previews": result.get("repurposed", {}),
        "is_preview": True
    }


@router.get("/repurpose/suggestions")
async def get_repurpose_suggestions(
    limit: int = Query(5, description="Max suggestions"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get suggestions for content that can be repurposed."""
    from agents.repurpose import get_repurpose_suggestions
    return await get_repurpose_suggestions(current_user["user_id"], limit)


# ============ SERIES ENDPOINTS ============

@router.get("/series/templates")
async def get_series_templates() -> Dict[str, Any]:
    """Get available series templates."""
    from agents.series_planner import get_series_templates
    return get_series_templates()


@router.post("/series/plan")
async def create_series_plan(
    request: SeriesPlanRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a content series plan."""
    from agents.series_planner import create_series_plan
    
    # Get persona
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    persona_card = persona.get("card") if persona else None
    
    result = await create_series_plan(
        topic=request.topic,
        template_type=request.template_type,
        num_posts=request.num_posts,
        platform=request.platform,
        persona_card=persona_card,
        custom_angle=request.custom_angle
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Plan creation failed"))
    
    return result


@router.post("/series/save")
async def save_series(
    request: SeriesSaveRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Save a series plan to start working on it."""
    from agents.series_planner import save_series
    
    start_date = None
    if request.start_date:
        start_date = datetime.fromisoformat(request.start_date.replace("Z", "+00:00"))
    
    return await save_series(
        user_id=current_user["user_id"],
        plan=request.plan,
        start_date=start_date
    )


@router.get("/series")
async def list_series(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, description="Max series to return"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """List user's content series."""
    from agents.series_planner import get_user_series
    return await get_user_series(
        user_id=current_user["user_id"],
        status=status,
        limit=limit
    )


@router.get("/series/{series_id}")
async def get_series(
    series_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed series information."""
    from agents.series_planner import get_series_detail
    
    result = await get_series_detail(current_user["user_id"], series_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Series not found"))
    
    return result


@router.post("/series/create-post")
async def create_series_post(
    request: CreateSeriesPostRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a content job for a specific series post."""
    from agents.series_planner import create_series_post
    
    result = await create_series_post(
        user_id=current_user["user_id"],
        series_id=request.series_id,
        post_number=request.post_number
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Post creation failed"))
    
    return result


@router.delete("/series/{series_id}")
async def delete_series(
    series_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a series (keeps any created content jobs)."""
    result = await db.content_series.delete_one({
        "series_id": series_id,
        "user_id": current_user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Series not found")
    
    return {"message": "Series deleted", "series_id": series_id}


# ============ ANTI-REPETITION V2 ENDPOINTS ============

@router.get("/diversity/score")
async def get_diversity_score(
    days: int = Query(30, description="Days to analyze"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get content diversity score and analysis."""
    from agents.anti_repetition import get_content_diversity_score
    return await get_content_diversity_score(current_user["user_id"], days)


@router.get("/diversity/hook-analysis")
async def get_hook_analysis(
    limit: int = Query(10, description="Posts to analyze"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analyze hook patterns and fatigue."""
    from agents.anti_repetition import analyze_hook_fatigue
    return await analyze_hook_fatigue(current_user["user_id"], limit)


@router.post("/diversity/suggestions")
async def get_variation_suggestions(
    job_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get AI suggestions to make content more unique."""
    from agents.anti_repetition import get_variation_suggestions
    
    # Get the job
    job = await db.content_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user["user_id"]
    })
    
    if not job:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return await get_variation_suggestions(
        user_id=current_user["user_id"],
        draft_content=job.get("final_content", ""),
        platform=job.get("platform", "linkedin")
    )
