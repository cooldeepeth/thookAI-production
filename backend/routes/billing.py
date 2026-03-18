"""Billing Routes for ThookAI.

Handles credits, subscriptions, and billing endpoints.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


# ============ PYDANTIC MODELS ============

class UpgradeRequest(BaseModel):
    tier: str
    billing_period: str = "monthly"


class PurchaseCreditsRequest(BaseModel):
    amount: int
    payment_method_id: Optional[str] = None


# ============ CREDIT ENDPOINTS ============

@router.get("/credits")
async def get_credits(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current credit balance and info."""
    from services.credits import get_credit_balance
    return await get_credit_balance(current_user["user_id"])


@router.get("/credits/usage")
async def get_credit_usage(
    days: int = Query(30, description="Days to look back"),
    limit: int = Query(50, description="Max transactions"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get credit usage history."""
    from services.credits import get_usage_history
    return await get_usage_history(current_user["user_id"], days, limit)


@router.post("/credits/purchase")
async def purchase_credits(
    request: PurchaseCreditsRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Purchase additional credits.
    
    NOTE: This is a placeholder. In production, integrate with Stripe.
    """
    from services.credits import add_credits
    
    # Validate amount
    if request.amount < 50:
        raise HTTPException(status_code=400, detail="Minimum purchase is 50 credits")
    if request.amount > 10000:
        raise HTTPException(status_code=400, detail="Maximum purchase is 10,000 credits")
    
    # Calculate price (placeholder: $0.10 per credit)
    price = request.amount * 0.10
    
    # In production: Process payment via Stripe here
    # For now, just add credits (simulating successful payment)
    
    result = await add_credits(
        user_id=current_user["user_id"],
        amount=request.amount,
        source="purchase",
        description=f"Purchased {request.amount} credits for ${price:.2f}"
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return {
        **result,
        "price": price,
        "payment_status": "simulated"  # Would be "succeeded" with real payment
    }


@router.get("/credits/costs")
async def get_operation_costs() -> Dict[str, Any]:
    """Get credit costs for all operations."""
    from services.credits import CreditOperation
    
    costs = {}
    for op in CreditOperation:
        costs[op.name.lower()] = {
            "credits": op.value,
            "name": op.name.replace("_", " ").title()
        }
    
    return {"costs": costs}


# ============ SUBSCRIPTION ENDPOINTS ============

@router.get("/subscription")
async def get_subscription(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current subscription details."""
    from services.subscriptions import get_current_subscription
    return await get_current_subscription(current_user["user_id"])


@router.get("/subscription/tiers")
async def get_available_tiers(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all available subscription tiers."""
    from services.subscriptions import get_available_tiers
    return await get_available_tiers(current_user["user_id"])


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Upgrade subscription tier.
    
    NOTE: This is a placeholder. In production, integrate with Stripe.
    """
    from services.subscriptions import upgrade_subscription
    
    valid_tiers = ["free", "pro", "studio", "agency"]
    if request.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose from: {valid_tiers}")
    
    if request.billing_period not in ["monthly", "annual"]:
        raise HTTPException(status_code=400, detail="Billing period must be 'monthly' or 'annual'")
    
    result = await upgrade_subscription(
        user_id=current_user["user_id"],
        new_tier=request.tier,
        billing_period=request.billing_period
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel subscription (downgrade to free at period end)."""
    from services.subscriptions import cancel_subscription
    
    result = await cancel_subscription(current_user["user_id"])
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/subscription/limits")
async def get_feature_limits(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all feature limits for current tier."""
    from services.subscriptions import get_feature_limits
    return await get_feature_limits(current_user["user_id"])


@router.get("/subscription/daily-limit")
async def check_daily_limit(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check daily content creation limit."""
    from services.subscriptions import check_daily_limit
    return await check_daily_limit(current_user["user_id"])
