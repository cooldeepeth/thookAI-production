"""Credit System Service for ThookAI.

Manages usage-based credits for AI operations:
- Credit balance tracking
- Usage history
- Credit deductions per operation
- Starter hard caps (video/carousel)
- Custom plan builder pricing with volume discounts
"""
import uuid
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from pymongo import ReturnDocument

logger = logging.getLogger(__name__)


class CreditOperation(Enum):
    """Credit costs per operation type.

    Pricing Strategy (March 2026):
    - Text operations: High margin (80%+) to encourage usage
    - Image operations: Good margin (60-75%)
    - Voice/Video: Premium pricing to cover API costs

    Real API costs per operation:
    - CONTENT_CREATE: ~$0.07 (5 agents chain)
    - IMAGE_GENERATE: ~$0.08 (DALL-E/Stable Diffusion)
    - VOICE_NARRATION: ~$0.25 (ElevenLabs)
    - VIDEO_GENERATE: ~$1.50 (Runway Gen-3)
    """
    CONTENT_CREATE = 10      # Full content generation pipeline (~86% margin)
    CONTENT_REGENERATE = 4   # Regenerate existing content (~80% margin)
    IMAGE_GENERATE = 8       # Single image generation (~74% margin)
    CAROUSEL_GENERATE = 15   # Multi-image carousel (~59% margin)
    VOICE_NARRATION = 12     # Text-to-speech (~45% margin)
    VIDEO_GENERATE = 50      # Video creation (~45% margin)
    REPURPOSE = 3            # Repurpose to another platform (~88% margin)
    SERIES_PLAN = 6          # Create series plan
    AI_INSIGHTS = 2          # Generate AI insights
    VIRAL_PREDICT = 1        # Viral hook prediction


# ============ STARTER TIER CONFIG ============

STARTER_CONFIG = {
    "name": "Starter",
    "signup_credits": 200,
    "monthly_credits": 0,       # No monthly refresh for starter
    "features": {
        "max_personas": 1,
        "platforms": ["linkedin"],
        "content_per_day": 5,
        "team_members": 1,
        "analytics_days": 7,
        "series_enabled": False,
        "repurpose_enabled": False,
        "voice_enabled": False,
        "video_enabled": True,   # Allowed but hard-capped
        "video_max": 2,          # Hard cap: max 2 videos total on starter
        "carousel_max": 5,       # Hard cap: max 5 carousels total on starter
        "priority_support": False,
        "api_access": False
    }
}

# ============ VOLUME PRICING ============

# Price per credit in USD, tiered by total monthly credits
VOLUME_TIERS = [
    {"up_to": 500,   "price_per_credit": 0.06},
    {"up_to": 1500,  "price_per_credit": 0.05},
    {"up_to": 5000,  "price_per_credit": 0.035},
    {"up_to": None,  "price_per_credit": 0.03},   # 5000+
]

# Feature unlock thresholds based on monthly spend
FEATURE_THRESHOLDS = {
    "base": {
        # Any paid plan gets these
        "min_monthly_usd": 0,
        "max_personas": 3,
        "platforms": ["linkedin", "x", "instagram"],
        "content_per_day": 50,
        "team_members": 1,
        "analytics_days": 30,
        "series_enabled": True,
        "repurpose_enabled": True,
        "voice_enabled": False,
        "video_enabled": True,
        "priority_support": False,
        "api_access": False
    },
    "growth": {
        "min_monthly_usd": 79,
        "max_personas": 10,
        "platforms": ["linkedin", "x", "instagram"],
        "content_per_day": 100,
        "team_members": 5,
        "analytics_days": 90,
        "series_enabled": True,
        "repurpose_enabled": True,
        "voice_enabled": True,
        "video_enabled": True,
        "priority_support": True,
        "api_access": False
    },
    "scale": {
        "min_monthly_usd": 149,
        "max_personas": 25,
        "platforms": ["linkedin", "x", "instagram"],
        "content_per_day": 200,
        "team_members": 10,
        "analytics_days": 365,
        "series_enabled": True,
        "repurpose_enabled": True,
        "voice_enabled": True,
        "video_enabled": True,
        "priority_support": True,
        "api_access": True
    }
}

# ============ LEGACY TIER_CONFIGS (for backward compatibility) ============
# Code that reads TIER_CONFIGS["free"] or TIER_CONFIGS["starter"] will still work.
# Custom plan users have their config stored in user.plan_config in MongoDB.

TIER_CONFIGS = {
    "starter": {
        "name": "Starter",
        "monthly_credits": 0,
        "price_monthly": 0,
        "features": STARTER_CONFIG["features"]
    },
    "custom": {
        # Placeholder — real config comes from user.plan_config in DB
        "name": "Custom",
        "monthly_credits": 500,
        "price_monthly": 30,
        "features": FEATURE_THRESHOLDS["base"]
    }
}

# Keep "free" as alias for starter (backward compat for existing users in DB)
TIER_CONFIGS["free"] = TIER_CONFIGS["starter"]


# ============ PLAN BUILDER ============

def calculate_plan_credits(
    text_posts: int = 0,
    images: int = 0,
    videos: int = 0,
    carousels: int = 0,
    repurposes: int = 0,
    voice_narrations: int = 0,
    series_plans: int = 0
) -> int:
    """Calculate total monthly credits needed from usage quantities."""
    return (
        text_posts * CreditOperation.CONTENT_CREATE.value +
        images * CreditOperation.IMAGE_GENERATE.value +
        videos * CreditOperation.VIDEO_GENERATE.value +
        carousels * CreditOperation.CAROUSEL_GENERATE.value +
        repurposes * CreditOperation.REPURPOSE.value +
        voice_narrations * CreditOperation.VOICE_NARRATION.value +
        series_plans * CreditOperation.SERIES_PLAN.value
    )


def calculate_plan_price(total_credits: int) -> float:
    """Calculate monthly price in USD from total credits using volume tiers.

    Returns price rounded up to nearest dollar.
    """
    if total_credits <= 0:
        return 0.0

    for tier in VOLUME_TIERS:
        if tier["up_to"] is None or total_credits <= tier["up_to"]:
            raw = total_credits * tier["price_per_credit"]
            return math.ceil(raw)  # Round up to nearest dollar
    return 0.0


def get_features_for_price(monthly_usd: float) -> Dict[str, Any]:
    """Determine feature set based on monthly spend."""
    result = dict(FEATURE_THRESHOLDS["base"])
    for _level, threshold in FEATURE_THRESHOLDS.items():
        if monthly_usd >= threshold["min_monthly_usd"]:
            result = {k: v for k, v in threshold.items() if k != "min_monthly_usd"}
    return result


def build_plan_preview(
    text_posts: int = 0,
    images: int = 0,
    videos: int = 0,
    carousels: int = 0,
    repurposes: int = 0,
    voice_narrations: int = 0,
    series_plans: int = 0
) -> Dict[str, Any]:
    """Build a full plan preview for the frontend plan builder.

    Returns credits breakdown, monthly price, and unlocked features.
    """
    breakdown = {
        "text_posts": {"qty": text_posts, "credits_each": CreditOperation.CONTENT_CREATE.value, "subtotal": text_posts * CreditOperation.CONTENT_CREATE.value},
        "images": {"qty": images, "credits_each": CreditOperation.IMAGE_GENERATE.value, "subtotal": images * CreditOperation.IMAGE_GENERATE.value},
        "videos": {"qty": videos, "credits_each": CreditOperation.VIDEO_GENERATE.value, "subtotal": videos * CreditOperation.VIDEO_GENERATE.value},
        "carousels": {"qty": carousels, "credits_each": CreditOperation.CAROUSEL_GENERATE.value, "subtotal": carousels * CreditOperation.CAROUSEL_GENERATE.value},
        "repurposes": {"qty": repurposes, "credits_each": CreditOperation.REPURPOSE.value, "subtotal": repurposes * CreditOperation.REPURPOSE.value},
        "voice_narrations": {"qty": voice_narrations, "credits_each": CreditOperation.VOICE_NARRATION.value, "subtotal": voice_narrations * CreditOperation.VOICE_NARRATION.value},
        "series_plans": {"qty": series_plans, "credits_each": CreditOperation.SERIES_PLAN.value, "subtotal": series_plans * CreditOperation.SERIES_PLAN.value},
    }

    total_credits = sum(item["subtotal"] for item in breakdown.values())
    monthly_price = calculate_plan_price(total_credits)
    features = get_features_for_price(monthly_price)

    # Determine volume tier label
    volume_label = "standard"
    for vt in VOLUME_TIERS:
        if vt["up_to"] is None or total_credits <= vt["up_to"]:
            rate = vt["price_per_credit"]
            if rate <= 0.03:
                volume_label = "scale"
            elif rate <= 0.035:
                volume_label = "growth"
            elif rate <= 0.05:
                volume_label = "pro"
            break

    return {
        "breakdown": breakdown,
        "total_credits": total_credits,
        "monthly_price_usd": monthly_price,
        "price_per_credit": next(
            (t["price_per_credit"] for t in VOLUME_TIERS
             if t["up_to"] is None or total_credits <= t["up_to"]),
            0.06
        ),
        "volume_tier": volume_label,
        "features": features
    }


# ============ STARTER HARD CAP ENFORCEMENT ============

async def _check_starter_caps(user_id: str, operation: CreditOperation) -> Optional[str]:
    """Check if a starter user has hit their hard caps on video/carousel.

    Returns an error message if capped, or None if allowed.
    """
    from database import db

    if operation == CreditOperation.VIDEO_GENERATE:
        cap = STARTER_CONFIG["features"]["video_max"]
        count = await db.credit_transactions.count_documents({
            "user_id": user_id,
            "operation": "VIDEO_GENERATE",
            "type": "deduction"
        })
        if count >= cap:
            return f"Starter accounts are limited to {cap} video generations. Upgrade to a paid plan for unlimited videos."

    elif operation == CreditOperation.CAROUSEL_GENERATE:
        cap = STARTER_CONFIG["features"]["carousel_max"]
        count = await db.credit_transactions.count_documents({
            "user_id": user_id,
            "operation": "CAROUSEL_GENERATE",
            "type": "deduction"
        })
        if count >= cap:
            return f"Starter accounts are limited to {cap} carousel generations. Upgrade to a paid plan for unlimited carousels."

    return None


# ============ CREDIT BALANCE ============

async def get_credit_balance(user_id: str) -> Dict[str, Any]:
    """Get user's current credit balance and tier info."""
    from database import db

    user = await db.users.find_one({"user_id": user_id})

    if not user:
        return {"success": False, "error": "User not found"}

    tier = user.get("subscription_tier", "starter")
    plan_config = user.get("plan_config")
    now = datetime.now(timezone.utc)

    # Determine monthly credits and tier config
    if plan_config:
        monthly_credits = plan_config.get("monthly_credits", 0)
        tier_name = "Custom"
    elif tier in TIER_CONFIGS:
        tier_config = TIER_CONFIGS[tier]
        monthly_credits = tier_config["monthly_credits"]
        tier_name = tier_config["name"]
    else:
        # Unknown tier, fall back to starter
        monthly_credits = 0
        tier_name = "Starter"

    credits = user.get("credits", 0)

    # Check if credits need refresh (monthly reset for paid plans)
    if monthly_credits > 0:
        last_refresh = user.get("credits_last_refresh")
        if last_refresh:
            if isinstance(last_refresh, str):
                last_refresh = datetime.fromisoformat(last_refresh)
            if last_refresh.tzinfo is None:
                last_refresh = last_refresh.replace(tzinfo=timezone.utc)

            days_since_refresh = (now - last_refresh).days
            if days_since_refresh >= 30:
                credits = monthly_credits
                await db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"credits": credits, "credits_last_refresh": now}}
                )

    # Calculate usage this period
    period_start = user.get("credits_last_refresh", now - timedelta(days=30))
    usage_cursor = db.credit_transactions.find({
        "user_id": user_id,
        "created_at": {"$gte": period_start},
        "type": "deduction"
    })

    total_used = 0
    async for tx in usage_cursor:
        total_used += tx.get("amount", 0)

    # Low balance warning
    effective_allowance = monthly_credits if monthly_credits > 0 else STARTER_CONFIG["signup_credits"]
    low_balance_threshold = effective_allowance * 0.2
    is_low_balance = credits < low_balance_threshold

    return {
        "success": True,
        "credits": credits,
        "monthly_allowance": monthly_credits,
        "used_this_period": total_used,
        "tier": tier,
        "tier_name": tier_name,
        "is_low_balance": is_low_balance,
        "low_balance_threshold": int(low_balance_threshold),
        "next_refresh": (period_start + timedelta(days=30)).isoformat() if period_start and monthly_credits > 0 else None,
        "plan_config": plan_config
    }


# ============ CREDIT DEDUCTION ============

async def deduct_credits(
    user_id: str,
    operation: CreditOperation,
    description: str = None,
    metadata: Dict = None
) -> Dict[str, Any]:
    """Deduct credits for an operation atomically.

    Uses MongoDB find_one_and_update with a credits >= amount filter to prevent
    race conditions where concurrent requests could both read the same balance
    and both succeed, producing a negative credit balance.

    For starter users, also enforces hard caps on video/carousel.
    """
    from database import db

    amount = operation.value

    # Read user once to check existence, tier, and starter caps
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}

    tier = user.get("subscription_tier", "starter")
    current_credits = user.get("credits", 0)

    # Enforce starter hard caps (count query — doesn't need atomicity)
    if tier in ("starter", "free"):
        cap_error = await _check_starter_caps(user_id, operation)
        if cap_error:
            return {
                "success": False,
                "error": cap_error,
                "upgrade_required": True,
                "operation": operation.name
            }

    # Atomic deduction: filter ensures credits >= amount before decrementing.
    # If two concurrent requests race, only one will match the filter; the other
    # gets None back and returns the "not enough credits" error — balance never
    # goes negative.
    result = await db.users.find_one_and_update(
        {"user_id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}},
        return_document=ReturnDocument.AFTER
    )

    if result is None:
        # Either user not found or insufficient credits
        return {
            "success": False,
            "error": f"Not enough credits. This operation requires {amount} credits but you only have {current_credits} available.",
            "required": amount,
            "available": current_credits,
            "operation": operation.name,
            "upgrade_required": tier in ("starter", "free")
        }

    new_balance = result.get("credits", 0)
    now = datetime.now(timezone.utc)

    # Record transaction
    transaction = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "deduction",
        "operation": operation.name,
        "amount": amount,
        "balance_after": new_balance,
        "description": description or f"{operation.name} operation",
        "metadata": metadata or {},
        "created_at": now
    }

    await db.credit_transactions.insert_one(transaction)

    return {
        "success": True,
        "credits_used": amount,
        "new_balance": new_balance,
        "operation": operation.name
    }


# ============ ADD CREDITS ============

async def add_credits(
    user_id: str,
    amount: int,
    source: str,
    description: str = None
) -> Dict[str, Any]:
    """Add credits to user account."""
    from database import db

    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}

    current_credits = user.get("credits", 0)
    new_balance = current_credits + amount
    now = datetime.now(timezone.utc)

    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"credits": new_balance}}
    )

    transaction = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "addition",
        "source": source,
        "amount": amount,
        "balance_after": new_balance,
        "description": description or f"Credits added: {source}",
        "created_at": now
    }

    await db.credit_transactions.insert_one(transaction)

    return {
        "success": True,
        "credits_added": amount,
        "new_balance": new_balance,
        "source": source
    }


# ============ USAGE HISTORY ============

async def get_usage_history(
    user_id: str,
    days: int = 30,
    limit: int = 50
) -> Dict[str, Any]:
    """Get credit usage history."""
    from database import db

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    cursor = db.credit_transactions.find(
        {"user_id": user_id, "created_at": {"$gte": cutoff}}
    ).sort("created_at", -1).limit(limit)

    transactions = []
    by_operation = {}
    total_deducted = 0
    total_added = 0

    async for tx in cursor:
        tx_data = {
            "transaction_id": tx.get("transaction_id"),
            "type": tx.get("type"),
            "operation": tx.get("operation"),
            "source": tx.get("source"),
            "amount": tx.get("amount"),
            "balance_after": tx.get("balance_after"),
            "description": tx.get("description"),
            "created_at": tx.get("created_at").isoformat() if tx.get("created_at") else None
        }
        transactions.append(tx_data)

        if tx.get("type") == "deduction":
            total_deducted += tx.get("amount", 0)
            op = tx.get("operation", "unknown")
            by_operation[op] = by_operation.get(op, 0) + tx.get("amount", 0)
        else:
            total_added += tx.get("amount", 0)

    return {
        "success": True,
        "period_days": days,
        "transactions": transactions,
        "summary": {
            "total_deducted": total_deducted,
            "total_added": total_added,
            "net_change": total_added - total_deducted,
            "by_operation": by_operation
        }
    }


# ============ FEATURE ACCESS ============

async def check_feature_access(user_id: str, feature: str) -> Dict[str, Any]:
    """Check if user's tier/plan allows access to a feature."""
    from database import db

    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"allowed": False, "error": "User not found"}

    tier = user.get("subscription_tier", "starter")
    plan_config = user.get("plan_config")

    # Get features from plan config or tier config
    if plan_config and plan_config.get("features"):
        features = plan_config["features"]
    elif tier in TIER_CONFIGS:
        features = TIER_CONFIGS[tier].get("features", {})
    else:
        features = STARTER_CONFIG["features"]

    feature_value = features.get(feature)

    if feature_value is None:
        return {"allowed": False, "error": f"Unknown feature: {feature}"}

    if isinstance(feature_value, bool):
        return {
            "allowed": feature_value,
            "tier": tier,
            "upgrade_required": not feature_value
        }

    return {
        "allowed": True,
        "tier": tier,
        "limit": feature_value
    }


# ============ UTILITY FUNCTIONS ============

def get_operation_cost(operation_name: str) -> int:
    """Get credit cost for an operation."""
    try:
        op = CreditOperation[operation_name.upper()]
        return op.value
    except KeyError:
        return 0


def get_all_tiers() -> List[Dict[str, Any]]:
    """Get available tier info (starter + plan builder pricing)."""
    tiers = [
        {
            "id": "starter",
            "name": "Starter",
            "monthly_credits": 0,
            "signup_credits": STARTER_CONFIG["signup_credits"],
            "price_monthly": 0,
            "features": STARTER_CONFIG["features"],
            "description": "Try ThookAI with 200 free credits"
        },
        {
            "id": "custom",
            "name": "Custom Plan",
            "monthly_credits": None,  # Varies
            "price_monthly": None,    # Varies
            "features": None,         # Varies by price
            "description": "Build your own plan — pick your usage, we calculate the price",
            "plan_builder": True,
            "volume_tiers": VOLUME_TIERS,
            "feature_thresholds": {
                k: {"min_monthly_usd": v["min_monthly_usd"]}
                for k, v in FEATURE_THRESHOLDS.items()
            },
            "operation_costs": {op.name.lower(): op.value for op in CreditOperation}
        }
    ]
    return tiers
