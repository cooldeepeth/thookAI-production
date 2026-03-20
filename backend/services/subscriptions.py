"""Subscription Service for ThookAI.

Manages subscription tiers and upgrades:
- Free, Pro, Studio, Agency tiers
- Upgrade/downgrade logic
- Feature gating
- Billing integration (placeholder)
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from services.credits import TIER_CONFIGS, add_credits

logger = logging.getLogger(__name__)


async def get_current_subscription(user_id: str) -> Dict[str, Any]:
    """Get user's current subscription details.
    
    Args:
        user_id: User ID
    
    Returns:
        Subscription details with features
    """
    from database import db
    
    user = await db.users.find_one({"user_id": user_id})
    
    if not user:
        return {"success": False, "error": "User not found"}
    
    tier = user.get("subscription_tier", "free")
    tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
    
    expires_at = user.get("subscription_expires")
    is_active = True
    
    if expires_at and tier != "free":
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            is_active = False
    
    # Get usage stats for this period
    from services.credits import get_credit_balance
    credit_info = await get_credit_balance(user_id)
    
    return {
        "success": True,
        "tier": tier,
        "tier_name": tier_config["name"],
        "is_active": is_active,
        "price_monthly": tier_config["price_monthly"],
        "monthly_credits": tier_config["monthly_credits"],
        "current_credits": credit_info.get("credits", 0),
        "features": tier_config["features"],
        "started_at": user.get("subscription_started").isoformat() if user.get("subscription_started") else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "auto_renew": user.get("subscription_auto_renew", True)
    }


async def get_available_tiers(user_id: str = None) -> Dict[str, Any]:
    """Get all available subscription tiers.
    
    Args:
        user_id: Optional user ID to mark current tier
    
    Returns:
        List of available tiers
    """
    from database import db
    
    current_tier = "free"
    if user_id:
        user = await db.users.find_one({"user_id": user_id})
        if user:
            current_tier = user.get("subscription_tier", "free")
    
    tiers = []
    for tier_id, config in TIER_CONFIGS.items():
        tier_data = {
            "id": tier_id,
            "name": config["name"],
            "price_monthly": config["price_monthly"],
            "monthly_credits": config["monthly_credits"],
            "features": config["features"],
            "is_current": tier_id == current_tier,
            "is_upgrade": _tier_rank(tier_id) > _tier_rank(current_tier),
            "is_downgrade": _tier_rank(tier_id) < _tier_rank(current_tier)
        }
        
        # Calculate savings for annual billing
        if config["price_monthly"] > 0:
            tier_data["price_annual"] = int(config["price_monthly"] * 10)  # 2 months free
            tier_data["annual_savings"] = config["price_monthly"] * 2
        
        tiers.append(tier_data)
    
    return {
        "success": True,
        "tiers": tiers,
        "current_tier": current_tier
    }


def _tier_rank(tier: str) -> int:
    """Get numeric rank for tier comparison."""
    ranks = {"free": 0, "pro": 1, "studio": 2, "agency": 3}
    return ranks.get(tier, 0)


async def upgrade_subscription(
    user_id: str,
    new_tier: str,
    billing_period: str = "monthly"
) -> Dict[str, Any]:
    """Upgrade user's subscription tier.
    
    NOTE: This is a placeholder. In production, integrate with Stripe.
    
    Args:
        user_id: User ID
        new_tier: Target tier
        billing_period: monthly or annual
    
    Returns:
        Upgrade result
    """
    from database import db
    
    if new_tier not in TIER_CONFIGS:
        return {"success": False, "error": f"Invalid tier: {new_tier}"}
    
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}
    
    current_tier = user.get("subscription_tier", "free")
    
    if new_tier == current_tier:
        return {"success": False, "error": "Already on this tier"}
    
    new_config = TIER_CONFIGS[new_tier]
    now = datetime.now(timezone.utc)
    
    # Calculate expiry
    if billing_period == "annual":
        expires_at = now + timedelta(days=365)
    else:
        expires_at = now + timedelta(days=30)
    
    # Update subscription
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "subscription_tier": new_tier,
                "subscription_started": now,
                "subscription_expires": expires_at,
                "subscription_billing_period": billing_period,
                "credits": new_config["monthly_credits"],  # Give full month's credits
                "credits_last_refresh": now
            }
        }
    )
    
    # Record the change
    await db.subscription_history.insert_one({
        "history_id": str(uuid.uuid4()),
        "user_id": user_id,
        "from_tier": current_tier,
        "to_tier": new_tier,
        "billing_period": billing_period,
        "created_at": now
    })
    
    is_upgrade = _tier_rank(new_tier) > _tier_rank(current_tier)
    
    return {
        "success": True,
        "previous_tier": current_tier,
        "new_tier": new_tier,
        "tier_name": new_config["name"],
        "is_upgrade": is_upgrade,
        "credits_granted": new_config["monthly_credits"],
        "expires_at": expires_at.isoformat(),
        "message": f"Successfully {'upgraded' if is_upgrade else 'changed'} to {new_config['name']}"
    }


async def cancel_subscription(user_id: str) -> Dict[str, Any]:
    """Cancel subscription (downgrade to free at period end).
    
    Args:
        user_id: User ID
    
    Returns:
        Cancellation result
    """
    from database import db
    
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}
    
    current_tier = user.get("subscription_tier", "free")
    
    if current_tier == "free":
        return {"success": False, "error": "Already on free tier"}
    
    expires_at = user.get("subscription_expires")
    now = datetime.now(timezone.utc)
    
    # Mark for cancellation (will downgrade when expires)
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "subscription_auto_renew": False,
                "subscription_cancelled_at": now
            }
        }
    )
    
    return {
        "success": True,
        "current_tier": current_tier,
        "will_downgrade_at": expires_at.isoformat() if expires_at else None,
        "message": f"Subscription cancelled. You'll retain {TIER_CONFIGS[current_tier]['name']} features until {expires_at.strftime('%B %d, %Y') if expires_at else 'period ends'}"
    }


async def check_daily_limit(user_id: str) -> Dict[str, Any]:
    """Check if user has hit daily content creation limit.
    
    Args:
        user_id: User ID
    
    Returns:
        Limit status
    """
    from database import db
    
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"allowed": False, "error": "User not found"}
    
    tier = user.get("subscription_tier", "free")
    tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
    daily_limit = tier_config["features"]["content_per_day"]
    
    # Count today's content
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
        "upgrade_for_more": tier != "agency"
    }


async def get_feature_limits(user_id: str) -> Dict[str, Any]:
    """Get all feature limits for user's tier.
    
    Args:
        user_id: User ID
    
    Returns:
        Feature limits and usage
    """
    from database import db
    
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}
    
    tier = user.get("subscription_tier", "free")
    tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
    features = tier_config["features"]
    
    # Get current usage for some limits
    persona_count = await db.persona_engines.count_documents({"user_id": user_id})
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    content_today = await db.content_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start}
    })
    
    return {
        "success": True,
        "tier": tier,
        "tier_name": tier_config["name"],
        "limits": {
            "max_personas": {
                "limit": features["max_personas"],
                "used": persona_count,
                "remaining": max(0, features["max_personas"] - persona_count)
            },
            "content_per_day": {
                "limit": features["content_per_day"],
                "used": content_today,
                "remaining": max(0, features["content_per_day"] - content_today)
            },
            "team_members": {
                "limit": features["team_members"],
                "used": 1,  # Placeholder - would need team tracking
                "remaining": features["team_members"] - 1
            },
            "analytics_days": features["analytics_days"]
        },
        "feature_access": {
            "platforms": features["platforms"],
            "series_enabled": features["series_enabled"],
            "repurpose_enabled": features["repurpose_enabled"],
            "voice_enabled": features["voice_enabled"],
            "video_enabled": features["video_enabled"],
            "priority_support": features["priority_support"],
            "api_access": features["api_access"]
        }
    }
