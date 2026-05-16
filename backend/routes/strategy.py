"""
ThookAI Strategy Routes

Endpoints:
- GET  /api/strategy               — List strategy recommendation cards (filterable by status)
- POST /api/strategy/{id}/approve  — Approve a card and get generate_payload for content creation
- POST /api/strategy/{id}/dismiss  — Dismiss a card with optional reason
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user
from database import db
from agents.strategist import handle_approval, handle_dismissal
from middleware.feature_flags import require_feature

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/strategy",
    tags=["strategy"],
    dependencies=[Depends(require_feature("feature_strategy_dashboard"))],
)


class DismissRequest(BaseModel):
    """Optional body for the dismiss endpoint."""

    reason: Optional[str] = None


def _serialize_card(card: dict) -> dict:
    """Serialize datetime fields in a strategy card to ISO format strings."""
    datetime_fields = ("created_at", "dismissed_at", "expires_at", "approved_at")
    for field in datetime_fields:
        value = card.get(field)
        if isinstance(value, datetime):
            card[field] = value.isoformat()
    return card


@router.get("")
async def get_strategy_feed(
    status: str = "pending_approval",
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """
    Return strategy recommendation cards for the authenticated user.

    Query params:
    - status: Filter by card status (default: pending_approval; use 'dismissed' for history)
    - limit: Max results to return (default 20)
    """
    user_id = current_user["user_id"]

    cards = (
        await db.strategy_recommendations.find(
            {"user_id": user_id, "status": status},
            {"_id": 0},
        )
        .sort("created_at", -1)
        .limit(limit)
        .to_list(limit)
    )

    # Serialize datetime objects for JSON response
    cards = [_serialize_card(card) for card in cards]

    logger.info(
        "Strategy feed requested: user=%s status=%s count=%d",
        user_id,
        status,
        len(cards),
    )
    return {"cards": cards, "count": len(cards)}


@router.post("/{recommendation_id}/approve")
async def approve_card(
    recommendation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Approve a strategy recommendation card.

    Returns generate_payload with platform, content_type, and raw_input so
    the frontend can immediately call POST /api/content/create (DASH-02).
    """
    user_id = current_user["user_id"]

    result = await handle_approval(
        user_id=user_id,
        recommendation_id=recommendation_id,
    )

    if result.get("error") == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Recommendation not found or already actioned",
        )

    logger.info(
        "Strategy card approved: user=%s recommendation_id=%s",
        user_id,
        recommendation_id,
    )
    return result


@router.post("/{recommendation_id}/dismiss")
async def dismiss_card(
    recommendation_id: str,
    body: Optional[DismissRequest] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Dismiss a strategy recommendation card.

    Optional body:
    - reason: Why the user dismissed the card (used for cadence calibration)

    Returns suppression info and a flag indicating whether a calibration
    prompt should be shown.
    """
    user_id = current_user["user_id"]
    reason = body.reason if body else None

    result = await handle_dismissal(
        user_id=user_id,
        recommendation_id=recommendation_id,
        reason=reason,
    )

    if result.get("error") == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Recommendation not found or already actioned",
        )

    logger.info(
        "Strategy card dismissed: user=%s recommendation_id=%s reason=%s",
        user_id,
        recommendation_id,
        reason,
    )
    return result
