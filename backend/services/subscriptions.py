"""Subscription Service for ThookAI.

Manages subscription tiers and upgrades:
- Starter (free) and Custom (plan builder) tiers
- Upgrade/downgrade logic
- Feature gating
- Stripe integration
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from services.credits import TIER_CONFIGS, STARTER_CONFIG, add_credits

logger = logging.getLogger(__name__)


async def get_current_subscription(user_id: str) -> Dict[str, Any]:
    """Get user's current subscription details."""
    from database import db

    user = await db.users.find_one({"user_id": user_id})

    if not user:
        return {"success": False, "error": "User not found"}

    tier = user.get("subscription_tier", "starter")
    plan_config = user.get("plan_config")

    # Get config from plan_config (custom) or TIER_CONFIGS (starter)
    if plan_config:
        tier_name = "Custom"
        monthly_credits = plan_config.get("monthly_credits", 0)
        price_monthly = plan_config.get("monthly_price_usd", 0)
        features = plan_config.get("features", {})
    elif tier in TIER_CONFIGS:
        tc = TIER_CONFIGS[tier]
        tier_name = tc["name"]
        monthly_credits = tc["monthly_credits"]
        price_monthly = tc.get("price_monthly", 0)
        features = tc["features"]
    else:
        tier_name = "Starter"
        monthly_credits = 0
        price_monthly = 0
        features = STARTER_CONFIG["features"]

    expires_at = user.get("subscription_expires")
    is_active = True

    if expires_at and tier not in ("starter", "free"):
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            is_active = False

    from services.credits import get_credit_balance
    credit_info = await get_credit_balance(user_id)

    return {
        "success": True,
        "tier": tier,
        "tier_name": tier_name,
        "is_active": is_active,
        "price_monthly": price_monthly,
        "monthly_credits": monthly_credits,
        "current_credits": credit_info.get("credits", 0),
        "features": features,
        "plan_config": plan_config,
        "started_at": user.get("subscription_started").isoformat() if user.get("subscription_started") else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "auto_renew": user.get("subscription_auto_renew", True)
    }


async def get_available_tiers(user_id: str = None) -> Dict[str, Any]:
    """Get available tiers/plans for the pricing page."""
    from database import db
    from services.credits import get_all_tiers

    current_tier = "starter"
    plan_config = None
    if user_id:
        user = await db.users.find_one({"user_id": user_id})
        if user:
            current_tier = user.get("subscription_tier", "starter")
            plan_config = user.get("plan_config")

    tiers = get_all_tiers()

    # Mark current tier
    for t in tiers:
        t["is_current"] = (t["id"] == current_tier)

    return {
        "success": True,
        "tiers": tiers,
        "current_tier": current_tier,
        "current_plan_config": plan_config
    }


def _tier_rank(tier: str) -> int:
    """Get numeric rank for tier comparison."""
    ranks = {"starter": 0, "free": 0, "custom": 1}
    return ranks.get(tier, 0)


async def upgrade_subscription(
    user_id: str,
    new_tier: str,
    billing_period: str = "monthly",
    plan_config: Dict = None
) -> Dict[str, Any]:
    """Upgrade user's subscription.

    For custom plans, plan_config should contain the plan builder selections.
    """
    from database import db

    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}

    current_tier = user.get("subscription_tier", "starter")
    now = datetime.now(timezone.utc)

    if new_tier == "starter":
        # Downgrade to starter — clear paid-plan fields and reset credits
        # to the starter signup allotment (200 one-time credits).
        monthly_credits = 0
        from services.credits import STARTER_CONFIG
        update = {
            "subscription_tier": "starter",
            "plan_config": None,
            "credit_allowance": 0,
            "credits": STARTER_CONFIG["signup_credits"],
            "credits_refreshed_at": now,
            "credits_last_refresh": now,
            "subscription_started": now,
            "subscription_billing_period": None,
            "subscription_expires": None,
        }
    elif new_tier == "custom" and plan_config:
        monthly_credits = plan_config.get("monthly_credits", 500)
        update = {
            "subscription_tier": "custom",
            "plan_config": plan_config,
            "credits": monthly_credits,
            "credit_allowance": monthly_credits,
            "credits_last_refresh": now,
            "subscription_started": now,
            "subscription_billing_period": billing_period,
        }

        if billing_period == "annual":
            update["subscription_expires"] = now + timedelta(days=365)
        else:
            update["subscription_expires"] = now + timedelta(days=30)
    else:
        return {"success": False, "error": f"Invalid tier: {new_tier}. Use 'starter' or 'custom' with plan_config."}

    await db.users.update_one({"user_id": user_id}, {"$set": update})

    await db.subscription_history.insert_one({
        "history_id": str(uuid.uuid4()),
        "user_id": user_id,
        "from_tier": current_tier,
        "to_tier": new_tier,
        "billing_period": billing_period,
        "plan_config": plan_config,
        "created_at": now
    })

    is_upgrade = _tier_rank(new_tier) > _tier_rank(current_tier)

    return {
        "success": True,
        "previous_tier": current_tier,
        "new_tier": new_tier,
        "is_upgrade": is_upgrade,
        "credits_granted": monthly_credits if new_tier == "custom" else 0,
        "message": f"Successfully {'upgraded' if is_upgrade else 'changed'} subscription"
    }


async def cancel_subscription(user_id: str) -> Dict[str, Any]:
    """Cancel subscription (downgrade to starter at period end)."""
    from database import db

    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}

    current_tier = user.get("subscription_tier", "starter")

    if current_tier in ("starter", "free"):
        return {"success": False, "error": "No active subscription to cancel"}

    expires_at = user.get("subscription_expires")
    now = datetime.now(timezone.utc)

    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "subscription_auto_renew": False,
            "subscription_cancelled_at": now
        }}
    )

    return {
        "success": True,
        "current_tier": current_tier,
        "will_downgrade_at": expires_at.isoformat() if expires_at else None,
        "message": f"Subscription cancelled. You'll retain your plan until {expires_at.strftime('%B %d, %Y') if expires_at else 'period ends'}"
    }


async def check_daily_limit(user_id: str) -> Dict[str, Any]:
    """Check if user has hit daily content creation limit."""
    from database import db

    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"allowed": False, "error": "User not found"}

    tier = user.get("subscription_tier", "starter")
    plan_config = user.get("plan_config")

    # Get daily limit from plan config or tier config
    if plan_config and plan_config.get("features"):
        daily_limit = plan_config["features"].get("content_per_day", 50)
    elif tier in TIER_CONFIGS:
        daily_limit = TIER_CONFIGS[tier]["features"]["content_per_day"]
    else:
        daily_limit = STARTER_CONFIG["features"]["content_per_day"]

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    today_count = await db.content_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start}
    })

    remaining = max(0, daily_limit - today_count)

    return {
        "allowed": today_count < daily_limit,
        "today_count": today_count,
        "daily_limit": daily_limit,
        "remaining": remaining,
        "tier": tier,
        "upgrade_available": tier in ("starter", "free")
    }


async def get_feature_limits(user_id: str) -> Dict[str, Any]:
    """Get all feature limits for user's tier/plan."""
    from database import db

    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}

    tier = user.get("subscription_tier", "starter")
    plan_config = user.get("plan_config")

    if plan_config and plan_config.get("features"):
        features = plan_config["features"]
        tier_name = "Custom"
    elif tier in TIER_CONFIGS:
        features = TIER_CONFIGS[tier]["features"]
        tier_name = TIER_CONFIGS[tier]["name"]
    else:
        features = STARTER_CONFIG["features"]
        tier_name = "Starter"

    persona_count = await db.persona_engines.count_documents({"user_id": user_id})

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    content_today = await db.content_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start}
    })

    return {
        "success": True,
        "tier": tier,
        "tier_name": tier_name,
        "limits": {
            "max_personas": {
                "limit": features.get("max_personas", 1),
                "used": persona_count,
                "remaining": max(0, features.get("max_personas", 1) - persona_count)
            },
            "content_per_day": {
                "limit": features.get("content_per_day", 5),
                "used": content_today,
                "remaining": max(0, features.get("content_per_day", 5) - content_today)
            },
            "team_members": {
                "limit": features.get("team_members", 1),
                "used": 1,
                "remaining": features.get("team_members", 1) - 1
            },
            "analytics_days": features.get("analytics_days", 7)
        },
        "feature_access": {
            "platforms": features.get("platforms", ["linkedin"]),
            "series_enabled": features.get("series_enabled", False),
            "repurpose_enabled": features.get("repurpose_enabled", False),
            "voice_enabled": features.get("voice_enabled", False),
            "video_enabled": features.get("video_enabled", False),
            "priority_support": features.get("priority_support", False),
            "api_access": features.get("api_access", False)
        }
    }
