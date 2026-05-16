"""Analytics Routes for ThookAI.

Handles analytics, insights, and persona refinement endpoints.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user
from middleware.feature_flags import require_feature

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_feature("feature_strategy_dashboard"))],
)


# ============ PYDANTIC MODELS ============

class PersonaUpdateItem(BaseModel):
    field: str
    value: str


class ApplyRefinementsRequest(BaseModel):
    updates: List[PersonaUpdateItem]


# ============ ANALYTICS ENDPOINTS ============

@router.get("/overview")
async def get_analytics_overview(
    days: int = Query(30, description="Days to analyze"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get overview analytics for user's content."""
    from agents.analyst import get_analytics_overview
    return await get_analytics_overview(current_user["user_id"], days)


@router.get("/content/{job_id}")
async def get_content_analytics(
    job_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get analytics for a specific content piece."""
    from agents.analyst import get_content_analytics
    
    result = await get_content_analytics(current_user["user_id"], job_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Content not found"))
    
    return result


@router.get("/trends")
async def get_performance_trends(
    days: int = Query(30, description="Days to analyze"),
    granularity: str = Query("week", description="week or month"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get performance trends over time."""
    from agents.analyst import get_performance_trends
    return await get_performance_trends(current_user["user_id"], days, granularity)


@router.get("/insights")
async def get_insights(
    days: int = Query(30, description="Days to analyze"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get AI-powered insights and recommendations."""
    from agents.analyst import generate_insights
    return await generate_insights(current_user["user_id"], days)


# ============ LEARNING ENDPOINTS ============

@router.get("/learning")
async def get_learning_insights(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get learning insights from user interactions."""
    from agents.learning import get_learning_insights
    return await get_learning_insights(current_user["user_id"])


# ============ PERSONA REFINEMENT ENDPOINTS ============

@router.get("/persona/evolution")
async def get_persona_evolution(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get persona evolution timeline."""
    from services.persona_refinement import get_persona_evolution_timeline
    
    result = await get_persona_evolution_timeline(current_user["user_id"])
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Persona not found"))
    
    return result


@router.get("/persona/voice-evolution")
async def get_voice_evolution(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analyze how user's content voice has evolved."""
    from services.persona_refinement import analyze_voice_evolution
    return await analyze_voice_evolution(current_user["user_id"])


@router.get("/persona/suggestions")
async def get_persona_suggestions(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get AI suggestions for persona updates."""
    import asyncio
    from services.persona_refinement import suggest_persona_updates
    try:
        return await asyncio.wait_for(
            suggest_persona_updates(current_user["user_id"]),
            timeout=12.0,
        )
    except asyncio.TimeoutError:
        return {"success": False, "should_update": False, "confidence": 0, "suggestions": [], "message": "Suggestion generation timed out. Try again later."}


@router.post("/persona/refine")
async def apply_persona_refinements(
    request: ApplyRefinementsRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Apply persona refinements."""
    from services.persona_refinement import apply_persona_refinements
    
    updates = [{"field": u.field, "value": u.value} for u in request.updates]
    result = await apply_persona_refinements(current_user["user_id"], updates)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Refinement failed"))
    
    return result


# ============ OPTIMAL POSTING TIMES ============

@router.get("/optimal-times")
async def get_optimal_posting_times(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns the user's calculated optimal posting times per platform."""
    user_id = current_user["user_id"]
    persona = await db.persona_engines.find_one({"user_id": user_id})
    optimal_times = persona.get("optimal_posting_times", {}) if persona else {}
    last_calculated = persona.get("optimal_times_calculated_at") if persona else None

    if not optimal_times:
        return {
            "optimal_times": {},
            "message": "Optimal times are calculated after 10+ published posts with performance data.",
            "last_calculated_at": None,
        }

    return {
        "optimal_times": optimal_times,
        "last_calculated_at": last_calculated.isoformat() if hasattr(last_calculated, "isoformat") else last_calculated,
    }


# ============ PATTERN FATIGUE SHIELD ============

@router.get("/fatigue-shield")
async def get_fatigue_shield(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get Pattern Fatigue Shield status and recommendations."""
    from services.persona_refinement import get_pattern_fatigue_shield
    return await get_pattern_fatigue_shield(current_user["user_id"])
