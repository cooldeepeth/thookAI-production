"""Viral Hook Predictor Routes for ThookAI.

Handles hook virality prediction and improvement endpoints.
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user
from middleware.feature_flags import require_feature

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/viral",
    tags=["viral"],
    dependencies=[Depends(require_feature("feature_viral_card"))],
)


# ============ PYDANTIC MODELS ============

class PredictRequest(BaseModel):
    content: str
    platform: str = "linkedin"


class ImproveRequest(BaseModel):
    hook: str
    platform: str = "linkedin"
    style: str = "curiosity"  # curiosity, contrarian, story, number


class BatchPredictRequest(BaseModel):
    hooks: List[str]
    platform: str = "linkedin"


# ============ VIRAL PREDICTION ENDPOINTS ============

@router.post("/predict")
async def predict_virality(
    request: PredictRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Predict viral potential of content hook.
    
    Returns:
    - virality_score (0-100)
    - virality_level (high/moderate/low/poor)
    - pattern_analysis with detected patterns
    - improvements and alternative hooks
    """
    from agents.viral_predictor import predict_virality
    
    if not request.content or len(request.content) < 10:
        raise HTTPException(status_code=400, detail="Content too short")
    
    if request.platform not in ["linkedin", "x", "instagram"]:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    return await predict_virality(request.content, request.platform)


@router.post("/improve")
async def improve_hook(
    request: ImproveRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate improved versions of a hook.
    
    Styles:
    - curiosity: Creates intrigue
    - contrarian: Challenges beliefs
    - story: Personal narrative
    - number: Specific numbers/lists
    """
    from agents.viral_predictor import improve_hook
    
    if not request.hook or len(request.hook) < 5:
        raise HTTPException(status_code=400, detail="Hook too short")
    
    valid_styles = ["curiosity", "contrarian", "story", "number"]
    if request.style not in valid_styles:
        raise HTTPException(status_code=400, detail=f"Invalid style. Choose from: {valid_styles}")
    
    return await improve_hook(request.hook, request.platform, request.style)


@router.post("/batch-predict")
async def batch_predict(
    request: BatchPredictRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Predict virality for multiple hooks (A/B testing).
    
    Compares up to 5 hook variations and ranks them.
    """
    from agents.viral_predictor import batch_predict
    
    if not request.hooks or len(request.hooks) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 hooks to compare")
    
    if len(request.hooks) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 hooks per batch")
    
    return await batch_predict(request.hooks, request.platform)


@router.get("/patterns")
async def get_viral_patterns() -> Dict[str, Any]:
    """Get information about viral hook patterns."""
    from agents.viral_predictor import VIRAL_PATTERNS, WEAK_PATTERNS
    
    positive_patterns = []
    for name, config in VIRAL_PATTERNS.items():
        positive_patterns.append({
            "name": name.replace("_", " ").title(),
            "description": config["description"],
            "impact": f"+{int((config['weight'] - 1) * 100)}% score boost"
        })
    
    negative_patterns = []
    for name, config in WEAK_PATTERNS.items():
        negative_patterns.append({
            "name": name.replace("_", " ").title(),
            "reason": config["reason"],
            "impact": f"-{int((1 - config['penalty']) * 100)}% score penalty"
        })
    
    return {
        "positive_patterns": positive_patterns,
        "negative_patterns": negative_patterns,
        "tips": [
            "Start with a curiosity gap or contrarian statement",
            "Use specific numbers when possible",
            "Keep hooks under 150 characters",
            "Avoid weak language (maybe, just, I think)",
            "Don't overuse emojis or punctuation"
        ]
    }
