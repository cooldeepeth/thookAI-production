"""Billing Routes for ThookAI.

Handles credits, custom plan subscriptions, and Stripe payment integration.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


# ============ PYDANTIC MODELS ============

class PlanBuilderRequest(BaseModel):
    """Request to preview or subscribe to a custom plan."""
    text_posts: int = 0
    images: int = 0
    videos: int = 0
    carousels: int = 0
    repurposes: int = 0
    voice_narrations: int = 0
    series_plans: int = 0


class PlanCheckoutRequest(BaseModel):
    """Request to create checkout for a custom plan."""
    text_posts: int = 0
    images: int = 0
    videos: int = 0
    carousels: int = 0
    repurposes: int = 0
    voice_narrations: int = 0
    series_plans: int = 0
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
    """Get Stripe configuration and pricing info for frontend."""
    from services.stripe_service import get_stripe_config
    return get_stripe_config()


# ============ PLAN BUILDER ============

@router.post("/plan/preview")
async def preview_plan(request: PlanBuilderRequest) -> Dict[str, Any]:
    """Preview a custom plan — returns credits breakdown, price, and features.

    This is the core endpoint for the plan builder UI. No auth required
    so the pricing page works for unauthenticated visitors.
    """
    from services.credits import build_plan_preview

    preview = build_plan_preview(
        text_posts=request.text_posts,
        images=request.images,
        videos=request.videos,
        carousels=request.carousels,
        repurposes=request.repurposes,
        voice_narrations=request.voice_narrations,
        series_plans=request.series_plans,
    )

    return {"success": True, **preview}


@router.post("/plan/checkout")
async def create_plan_checkout(
    request: PlanCheckoutRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create Stripe checkout session for a custom plan subscription."""
    from services.credits import build_plan_preview
    from services.stripe_service import create_custom_plan_checkout

    preview = build_plan_preview(
        text_posts=request.text_posts,
        images=request.images,
        videos=request.videos,
        carousels=request.carousels,
        repurposes=request.repurposes,
        voice_narrations=request.voice_narrations,
        series_plans=request.series_plans,
    )

    total_credits = preview["total_credits"]
    monthly_price_usd = preview["monthly_price_usd"]

    if total_credits <= 0:
        raise HTTPException(status_code=400, detail="Select at least one operation for your plan")

    # Build plan config to store in user record
    plan_config = {
        "monthly_credits": total_credits,
        "monthly_price_usd": monthly_price_usd,
        "selections": {
            "text_posts": request.text_posts,
            "images": request.images,
            "videos": request.videos,
            "carousels": request.carousels,
            "repurposes": request.repurposes,
            "voice_narrations": request.voice_narrations,
            "series_plans": request.series_plans,
        },
        "features": preview["features"],
        "volume_tier": preview["volume_tier"],
        "price_per_credit": preview["price_per_credit"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    monthly_price_cents = int(monthly_price_usd * 100)

    result = await create_custom_plan_checkout(
        user_id=current_user["user_id"],
        email=current_user.get("email", ""),
        monthly_credits=total_credits,
        monthly_price_cents=monthly_price_cents,
        plan_config=plan_config,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.post("/plan/modify")
async def modify_plan(
    request: PlanCheckoutRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Modify an existing subscription to a new custom plan configuration."""
    from services.credits import build_plan_preview
    from services.stripe_service import modify_subscription

    preview = build_plan_preview(
        text_posts=request.text_posts,
        images=request.images,
        videos=request.videos,
        carousels=request.carousels,
        repurposes=request.repurposes,
        voice_narrations=request.voice_narrations,
        series_plans=request.series_plans,
    )

    total_credits = preview["total_credits"]
    monthly_price_usd = preview["monthly_price_usd"]

    if total_credits <= 0:
        raise HTTPException(status_code=400, detail="Select at least one operation for your plan")

    plan_config = {
        "monthly_credits": total_credits,
        "monthly_price_usd": monthly_price_usd,
        "selections": {
            "text_posts": request.text_posts,
            "images": request.images,
            "videos": request.videos,
            "carousels": request.carousels,
            "repurposes": request.repurposes,
            "voice_narrations": request.voice_narrations,
            "series_plans": request.series_plans,
        },
        "features": preview["features"],
        "volume_tier": preview["volume_tier"],
        "price_per_credit": preview["price_per_credit"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    monthly_price_cents = int(monthly_price_usd * 100)

    result = await modify_subscription(
        user_id=current_user["user_id"],
        monthly_credits=total_credits,
        monthly_price_cents=monthly_price_cents,
        plan_config=plan_config,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


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
    """Direct credit purchase (simulated mode fallback)."""
    from services.credits import add_credits
    from services.stripe_service import is_stripe_configured

    if request.amount < 50:
        raise HTTPException(status_code=400, detail="Minimum purchase is 50 credits")
    if request.amount > 10000:
        raise HTTPException(status_code=400, detail="Maximum purchase is 10,000 credits")

    price = request.amount * 0.06

    if is_stripe_configured():
        return {
            "success": False,
            "redirect": True,
            "message": "Use /billing/credits/checkout for Stripe payments"
        }

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


# ============ PAYMENT HISTORY ============

@router.get("/payments")
async def get_payment_history(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's payment history from db.payments."""
    payments = await db.payments.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    return {"success": True, "payments": payments}


# ============ SUBSCRIPTION ENDPOINTS ============

@router.get("/subscription")
async def get_subscription(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current subscription details."""
    from services.subscriptions import get_current_subscription
    from services.stripe_service import get_subscription_status

    local_sub = await get_current_subscription(current_user["user_id"])
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
    """Get available plans and pricing info."""
    from services.subscriptions import get_available_tiers
    return await get_available_tiers(current_user["user_id"])


@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel subscription (downgrade to starter at period end)."""
    from services.subscriptions import cancel_subscription as local_cancel
    from services.stripe_service import cancel_stripe_subscription, is_stripe_configured

    if is_stripe_configured():
        result = await cancel_stripe_subscription(current_user["user_id"], at_period_end=True)
        if not result.get("success") and "No active subscription" not in result.get("error", ""):
            raise HTTPException(status_code=400, detail=result.get("error"))

    result = await local_cancel(current_user["user_id"])

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/subscription/limits")
async def get_feature_limits(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all feature limits for current tier/plan."""
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
    """Create Stripe Customer Portal session."""
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
    """Handle Stripe webhook events."""
    from config import settings
    from services.stripe_service import handle_webhook_event

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    if not settings.stripe.webhook_secret:
        allowed_envs = {"development", "test"}
        if settings.app.environment not in allowed_envs:
            logger.error("Stripe webhook secret not configured in %s — rejecting webhook", settings.app.environment)
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        logger.warning("Stripe webhook secret not configured — skipping signature verification in %s", settings.app.environment)

    payload = await request.body()

    result = await handle_webhook_event(payload, stripe_signature)

    if not result.get("success"):
        logger.error(f"Webhook processing failed: {result.get('error')}")

    return {"received": True}


# ============ SIMULATE ENDPOINTS (Development Only) ============

@router.post("/simulate/upgrade")
async def simulate_upgrade(
    request: PlanBuilderRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Simulate custom plan activation (development/test only)."""
    from config import settings
    from services.credits import build_plan_preview

    if settings.app.environment not in ("development", "test"):
        raise HTTPException(status_code=403, detail="Simulation endpoints are only available in development and test environments")

    preview = build_plan_preview(
        text_posts=request.text_posts,
        images=request.images,
        videos=request.videos,
        carousels=request.carousels,
        repurposes=request.repurposes,
        voice_narrations=request.voice_narrations,
        series_plans=request.series_plans,
    )

    total_credits = preview["total_credits"]
    if total_credits <= 0:
        # Simulate downgrade to starter
        await db.users.update_one(
            {"user_id": current_user["user_id"]},
            {"$set": {
                "subscription_tier": "starter",
                "plan_config": None,
                "credits": 0,
                "credit_allowance": 0,
                "subscription_status": "none",
                "subscription_updated_at": datetime.now(timezone.utc)
            }}
        )
        return {"success": True, "simulated": True, "new_tier": "starter", "credits": 0}

    plan_config = {
        "monthly_credits": total_credits,
        "monthly_price_usd": preview["monthly_price_usd"],
        "selections": {
            "text_posts": request.text_posts,
            "images": request.images,
            "videos": request.videos,
            "carousels": request.carousels,
            "repurposes": request.repurposes,
            "voice_narrations": request.voice_narrations,
            "series_plans": request.series_plans,
        },
        "features": preview["features"],
        "volume_tier": preview["volume_tier"],
    }

    await db.users.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {
            "subscription_tier": "custom",
            "plan_config": plan_config,
            "credits": total_credits,
            "credit_allowance": total_credits,
            "subscription_status": "active",
            "subscription_updated_at": datetime.now(timezone.utc)
        }}
    )

    return {
        "success": True,
        "simulated": True,
        "new_tier": "custom",
        "credits": total_credits,
        "monthly_price_usd": preview["monthly_price_usd"],
        "features": preview["features"]
    }


@router.post("/simulate/credits")
async def simulate_add_credits(
    amount: int = Query(100, description="Credits to add"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Add credits directly (development/test only)."""
    from config import settings
    from services.credits import add_credits

    if settings.app.environment not in ("development", "test"):
        raise HTTPException(status_code=403, detail="Simulation endpoints are only available in development and test environments")

    result = await add_credits(
        user_id=current_user["user_id"],
        amount=amount,
        source="simulated",
        description=f"Simulated credit addition: {amount} credits"
    )

    return {**result, "simulated": True}
