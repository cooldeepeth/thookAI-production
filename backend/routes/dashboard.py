"""Dashboard routes for ThookAI.

Provides aggregated stats and insights for the dashboard.
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from database import db
from auth_utils import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get aggregated dashboard statistics for the current user.
    
    Returns:
    - posts_created: Total approved content count
    - credits: User's credit balance
    - platforms_count: Number of connected platforms
    - persona_score: Trust score from UOM (0-10 scale)
    - learning_signals_count: Number of learning signals captured
    - recent_jobs: Last 3 content jobs
    """
    user_id = current_user["user_id"]
    
    # Parallel queries for performance
    # Query 1: Count approved content
    posts_created = await db.content_jobs.count_documents({
        "user_id": user_id,
        "status": "approved"
    })
    
    # Query 2: Get user data (credits, platforms)
    user_data = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0, "credits": 1, "platforms_connected": 1}
    )
    credits = user_data.get("credits", 100) if user_data else 100
    platforms_connected = user_data.get("platforms_connected", []) if user_data else []
    
    # Query 3: Get persona data (UOM trust, learning signals)
    persona_data = await db.persona_engines.find_one(
        {"user_id": user_id},
        {"_id": 0, "uom": 1, "learning_signals": 1}
    )
    
    # Calculate persona score from UOM trust (0-1 -> 0-10)
    persona_score = None
    learning_signals_count = 0
    
    if persona_data:
        uom = persona_data.get("uom", {})
        trust = uom.get("trust_in_thook")
        if trust is not None:
            persona_score = round(trust * 10, 1)
        
        learning = persona_data.get("learning_signals", {})
        learning_signals_count = learning.get("approved_count", 0) + learning.get("rejected_count", 0)
    
    # Query 4: Get last 3 content jobs
    recent_jobs_cursor = db.content_jobs.find(
        {"user_id": user_id},
        {
            "_id": 0,
            "job_id": 1,
            "platform": 1,
            "content_type": 1,
            "status": 1,
            "final_content": 1,
            "created_at": 1,
            "qc_score": 1
        }
    ).sort("created_at", -1).limit(3)
    
    recent_jobs = []
    async for job in recent_jobs_cursor:
        recent_jobs.append({
            "job_id": job.get("job_id"),
            "platform": job.get("platform"),
            "content_type": job.get("content_type"),
            "status": job.get("status"),
            "preview": job.get("final_content", "")[:100] + "..." if job.get("final_content") else None,
            "created_at": job.get("created_at").isoformat() if job.get("created_at") else None,
            "persona_match": job.get("qc_score", {}).get("personaMatch") if job.get("qc_score") else None
        })
    
    return {
        "posts_created": posts_created,
        "credits": credits,
        "platforms_count": len(platforms_connected),
        "platforms_connected": platforms_connected,
        "persona_score": persona_score,
        "learning_signals_count": learning_signals_count,
        "recent_jobs": recent_jobs
    }


@router.get("/activity")
async def get_activity_feed(current_user: dict = Depends(get_current_user), limit: int = 10) -> Dict[str, Any]:
    """Get recent activity feed for the user.
    
    Includes:
    - Content creation events
    - Approval/rejection events
    - Learning signal events
    """
    user_id = current_user["user_id"]
    
    # Get recent content jobs with all statuses
    jobs_cursor = db.content_jobs.find(
        {"user_id": user_id},
        {
            "_id": 0,
            "job_id": 1,
            "platform": 1,
            "content_type": 1,
            "status": 1,
            "created_at": 1,
            "updated_at": 1
        }
    ).sort("updated_at", -1).limit(limit)
    
    activities = []
    async for job in jobs_cursor:
        activity_type = "created"
        if job.get("status") == "approved":
            activity_type = "approved"
        elif job.get("status") == "rejected":
            activity_type = "rejected"
        elif job.get("status") == "reviewing":
            activity_type = "ready_for_review"
        
        activities.append({
            "type": activity_type,
            "job_id": job.get("job_id"),
            "platform": job.get("platform"),
            "content_type": job.get("content_type"),
            "timestamp": job.get("updated_at", job.get("created_at")).isoformat() if job.get("updated_at") or job.get("created_at") else None
        })
    
    return {
        "activities": activities,
        "total": len(activities)
    }


@router.get("/learning-insights")
async def get_learning_insights(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get AI learning insights for the user.
    
    Shows what the AI has learned about the user's preferences.
    """
    from agents.learning import get_learning_insights
    return await get_learning_insights(current_user["user_id"])
