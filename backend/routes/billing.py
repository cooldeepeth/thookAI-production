"""Billing Routes for ThookAI.

Handles credits, subscriptions, and Stripe payment integration.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


# ============ PYDANTIC MODELS ============

class UpgradeRequest(BaseModel):
    tier: str
    billing_period: str = "monthly"


class CheckoutRequest(BaseModel):
    tier: str
    billing_period: str = "monthly"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CreditCheckoutRequest(BaseModel):
    package: str  # small, medium, large
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PurchaseCreditsRequest(BaseModel):
    amount: int
    payment_method_id: Optional[str] = None


# ============ STRIPE CONFIG ============

@router.get("/config")
async def get_billing_config() -> Dict[str, Any]:
    """Get Stripe configuration for frontend."""
    from services.stripe_service import get_stripe_config
    return get_stripe_config()


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


@router.post("/credits/checkout")
async def create_credit_checkout(
    request: CreditCheckoutRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create Stripe checkout session for credit purchase."""
    from services.stripe_service import create_credit_checkout
    
    result = await create_credit_checkout(
        user_id=current_user["user_id"],
        email=current_user.get("email", ""),
        package=request.package,
        success_url=request.success_url,
        cancel_url=request.cancel_url
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/credits/purchase")
async def purchase_credits(
    request: PurchaseCreditsRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Direct credit purchase (legacy endpoint).
    
    For Stripe Checkout, use /credits/checkout instead.
    This endpoint is kept for backward compatibility and simulated purchases.
    """
    from services.credits import add_credits
    from services.stripe_service import is_stripe_configured
    
    # Validate amount
    if request.amount < 50:
        raise HTTPException(status_code=400, detail="Minimum purchase is 50 credits")
    if request.amount > 10000:
        raise HTTPException(status_code=400, detail="Maximum purchase is 10,000 credits")
    
    # Calculate price
    price = request.amount * 0.10
    
    if is_stripe_configured():
        # Redirect to Stripe checkout for real payments
        return {
            "success": False,
            "redirect": True,
            "message": "Use /billing/credits/checkout for Stripe payments"
        }
    
    # Simulated mode - add credits directly
    result = await add_credits(
        user_id=current_user["user_id"],
        amount=request.amount,
        source="purchase",
        description=f"Purchased {request.amount} credits for ${price:.2f} (simulated)"
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return {
        **result,
        "price": price,
        "payment_status": "simulated"
    }


# ============ SUBSCRIPTION ENDPOINTS ============

@router.get("/subscription")
async def get_subscription(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current subscription details."""
    from services.subscriptions import get_current_subscription
    from services.stripe_service import get_subscription_status
    
    # Get local subscription data
    local_sub = await get_current_subscription(current_user["user_id"])
    
    # Get Stripe subscription status if available
    stripe_sub = await get_subscription_status(current_user["user_id"])
    
    return {
        **local_sub,
        "stripe_status": stripe_sub.get("status") if stripe_sub.get("has_subscription") else None,
        "cancel_at_period_end": stripe_sub.get("cancel_at_period_end", False)
    }


@router.get("/subscription/tiers")
async def get_available_tiers(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all available subscription tiers with pricing."""
    from services.subscriptions import get_available_tiers
    from services.stripe_service import TIER_PRICING
    
    tiers = await get_available_tiers(current_user["user_id"])
    
    # Add pricing info
    for tier_data in tiers.get("tiers", []):
        tier_name = tier_data.get("id", "")
        pricing = TIER_PRICING.get(tier_name, {})
        tier_data["price_monthly"] = pricing.get("monthly", 0) / 100
        tier_data["price_annual"] = pricing.get("annual", 0) / 100
        tier_data["credits_per_month"] = pricing.get("credits", 50)
    
    return tiers


@router.post("/subscription/checkout")
async def create_subscription_checkout(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create Stripe checkout session for subscription."""
    from services.stripe_service import create_checkout_session
    
    valid_tiers = ["pro", "studio", "agency"]
    if request.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose from: {valid_tiers}")
    
    if request.billing_period not in ["monthly", "annual"]:
        raise HTTPException(status_code=400, detail="Billing period must be 'monthly' or 'annual'")
    
    result = await create_checkout_session(
        user_id=current_user["user_id"],
        email=current_user.get("email", ""),
        tier=request.tier,
        billing_period=request.billing_period,
        success_url=request.success_url,
        cancel_url=request.cancel_url
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upgrade subscription tier.
    
    For Stripe Checkout, use /subscription/checkout instead.
    This endpoint handles simulated upgrades when Stripe is not configured.
    """
    from services.subscriptions import upgrade_subscription as do_upgrade
    from services.stripe_service import is_stripe_configured, create_checkout_session
    
    valid_tiers = ["free", "pro", "studio", "agency"]
    if request.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose from: {valid_tiers}")
    
    if request.billing_period not in ["monthly", "annual"]:
        raise HTTPException(status_code=400, detail="Billing period must be 'monthly' or 'annual'")
    
    # For paid tiers with Stripe, redirect to checkout
    if request.tier != "free" and is_stripe_configured():
        result = await create_checkout_session(
            user_id=current_user["user_id"],
            email=current_user.get("email", ""),
            tier=request.tier,
            billing_period=request.billing_period
        )
        return {
            "success": True,
            "redirect": True,
            "checkout_url": result.get("checkout_url"),
            "message": "Redirecting to Stripe checkout"
        }
    
    # Simulated upgrade (or downgrade to free)
    result = await do_upgrade(
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
    from services.subscriptions import cancel_subscription as local_cancel
    from services.stripe_service import cancel_stripe_subscription, is_stripe_configured
    
    if is_stripe_configured():
        # Cancel in Stripe (at period end)
        result = await cancel_stripe_subscription(current_user["user_id"], at_period_end=True)
        if not result.get("success") and "No active subscription" not in result.get("error", ""):
            raise HTTPException(status_code=400, detail=result.get("error"))
    
    # Also update local database
    result = await local_cancel(current_user["user_id"])
    
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


# ============ CUSTOMER PORTAL ============

@router.post("/portal")
async def create_customer_portal(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create Stripe Customer Portal session for self-service billing management."""
    from services.stripe_service import create_customer_portal_session
    
    result = await create_customer_portal_session(current_user["user_id"])
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# ============ STRIPE WEBHOOKS ============

@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
) -> Dict[str, Any]:
    """
    Handle Stripe webhook events.
    
    Configure webhook URL in Stripe Dashboard:
    https://yourdomain.com/api/billing/webhook/stripe
    """
    from services.stripe_service import handle_webhook_event
    
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    
    payload = await request.body()
    
    result = await handle_webhook_event(payload, stripe_signature)
    
    if not result.get("success"):
        logger.error(f"Webhook processing failed: {result.get('error')}")
        # Return 200 anyway to prevent Stripe from retrying
        # Log the error for investigation
    
    return {"received": True}


# ============ SIMULATE ENDPOINTS (Development Only) ============

@router.post("/simulate/upgrade")
async def simulate_upgrade(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Simulate subscription upgrade (for testing when Stripe is not configured).
    
    WARNING: This should be disabled in production!
    """
    from config import settings
    from services.subscriptions import upgrade_subscription as do_upgrade
    from services.stripe_service import TIER_PRICING
    
    if settings.app.is_production:
        raise HTTPException(status_code=403, detail="Simulated upgrades disabled in production")
    
    valid_tiers = ["free", "pro", "studio", "agency"]
    if request.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose from: {valid_tiers}")
    
    # Get credits for tier
    credits = TIER_PRICING.get(request.tier, {}).get("credits", 50)
    
    # Update user directly
    await db.users.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {
            "subscription_tier": request.tier,
            "credits": credits,
            "credit_allowance": credits,
            "subscription_status": "active" if request.tier != "free" else "none",
            "subscription_updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {
        "success": True,
        "simulated": True,
        "new_tier": request.tier,
        "credits": credits,
        "message": f"Simulated upgrade to {request.tier} tier"
    }


@router.post("/simulate/credits")
async def simulate_add_credits(
    amount: int = Query(100, description="Credits to add"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Add credits directly (for testing when Stripe is not configured).
    
    WARNING: This should be disabled in production!
    """
    from config import settings
    from services.credits import add_credits
    
    if settings.app.is_production:
        raise HTTPException(status_code=403, detail="Simulated credits disabled in production")
    
    result = await add_credits(
        user_id=current_user["user_id"],
        amount=amount,
        source="simulated",
        description=f"Simulated credit addition: {amount} credits"
    )
    
    return {**result, "simulated": True}
