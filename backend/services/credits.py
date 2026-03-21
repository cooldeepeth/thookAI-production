"""Credit System Service for ThookAI.

Manages usage-based credits for AI operations:
- Credit balance tracking
- Usage history
- Credit deductions per operation
- Low balance alerts
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

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
    CONTENT_REGENERATE = 4   # Regenerate existing content (~80% margin) - was 5
    IMAGE_GENERATE = 8       # Single image generation (~74% margin)
    CAROUSEL_GENERATE = 15   # Multi-image carousel (~59% margin)
    VOICE_NARRATION = 12     # Text-to-speech (~45% margin) - was 8, adjusted for uniqueness
    VIDEO_GENERATE = 50      # Video creation (~45% margin)
    REPURPOSE = 3            # Repurpose to another platform (~88% margin)
    SERIES_PLAN = 6          # Create series plan - was 5, adjusted for uniqueness
    AI_INSIGHTS = 2          # Generate AI insights
    VIRAL_PREDICT = 1        # Viral hook prediction


# Tier configurations
TIER_CONFIGS = {
    "free": {
        "name": "Free",
        "monthly_credits": 50,
        "price_monthly": 0,
        "features": {
            "max_personas": 1,
            "platforms": ["linkedin"],
            "content_per_day": 3,
            "team_members": 1,
            "analytics_days": 7,
            "series_enabled": False,
            "repurpose_enabled": False,
            "voice_enabled": False,
            "video_enabled": False,
            "priority_support": False,
            "api_access": False
        }
    },
    "pro": {
        "name": "Pro",
        "monthly_credits": 500,
        "price_monthly": 29,
        "features": {
            "max_personas": 3,
            "platforms": ["linkedin", "x", "instagram"],
            "content_per_day": 20,
            "team_members": 1,
            "analytics_days": 30,
            "series_enabled": True,
            "repurpose_enabled": True,
            "voice_enabled": True,
            "video_enabled": False,
            "priority_support": False,
            "api_access": False
        }
    },
    "studio": {
        "name": "Studio",
        "monthly_credits": 2000,
        "price_monthly": 79,
        "features": {
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
        }
    },
    "agency": {
        "name": "Agency",
        "monthly_credits": 10000,
        "price_monthly": 199,
        "features": {
            "max_personas": 50,
            "platforms": ["linkedin", "x", "instagram"],
            "content_per_day": 500,
            "team_members": 20,
            "analytics_days": 365,
            "series_enabled": True,
            "repurpose_enabled": True,
            "voice_enabled": True,
            "video_enabled": True,
            "priority_support": True,
            "api_access": True
        }
    }
}


async def get_credit_balance(user_id: str) -> Dict[str, Any]:
    """Get user's current credit balance and tier info.
    
    Args:
        user_id: User ID
    
    Returns:
        Credit balance and subscription info
    """
    from database import db
    
    user = await db.users.find_one({"user_id": user_id})
    
    if not user:
        return {"success": False, "error": "User not found"}
    
    tier = user.get("subscription_tier", "free")
    tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
    credits = user.get("credits", tier_config["monthly_credits"])
    
    # Check if credits need refresh (monthly reset)
    last_refresh = user.get("credits_last_refresh")
    now = datetime.now(timezone.utc)
    
    if last_refresh:
        # Ensure timezone awareness
        if isinstance(last_refresh, str):
            last_refresh = datetime.fromisoformat(last_refresh)
        if last_refresh.tzinfo is None:
            last_refresh = last_refresh.replace(tzinfo=timezone.utc)
        
        days_since_refresh = (now - last_refresh).days
        if days_since_refresh >= 30:
            # Reset credits for the month
            credits = tier_config["monthly_credits"]
            await db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "credits": credits,
                        "credits_last_refresh": now
                    }
                }
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
    low_balance_threshold = tier_config["monthly_credits"] * 0.2  # 20%
    is_low_balance = credits < low_balance_threshold
    
    return {
        "success": True,
        "credits": credits,
        "monthly_allowance": tier_config["monthly_credits"],
        "used_this_period": total_used,
        "tier": tier,
        "tier_name": tier_config["name"],
        "is_low_balance": is_low_balance,
        "low_balance_threshold": int(low_balance_threshold),
        "next_refresh": (period_start + timedelta(days=30)).isoformat() if period_start else None
    }


async def deduct_credits(
    user_id: str,
    operation: CreditOperation,
    description: str = None,
    metadata: Dict = None
) -> Dict[str, Any]:
    """Deduct credits for an operation.
    
    Args:
        user_id: User ID
        operation: Type of operation
        description: Optional description
        metadata: Optional metadata (job_id, etc.)
    
    Returns:
        Result with new balance
    """
    from database import db
    
    amount = operation.value
    
    # Get current balance
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}
    
    tier = user.get("subscription_tier", "free")
    tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
    current_credits = user.get("credits", tier_config["monthly_credits"])
    
    # Check if enough credits
    if current_credits < amount:
        return {
            "success": False,
            "error": "Insufficient credits",
            "required": amount,
            "available": current_credits,
            "operation": operation.name
        }
    
    # Deduct credits
    new_balance = current_credits - amount
    now = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"credits": new_balance}}
    )
    
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


async def add_credits(
    user_id: str,
    amount: int,
    source: str,
    description: str = None
) -> Dict[str, Any]:
    """Add credits to user account.
    
    Args:
        user_id: User ID
        amount: Credits to add
        source: Source (purchase, bonus, refund, etc.)
        description: Optional description
    
    Returns:
        Result with new balance
    """
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
    
    # Record transaction
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


async def get_usage_history(
    user_id: str,
    days: int = 30,
    limit: int = 50
) -> Dict[str, Any]:
    """Get credit usage history.
    
    Args:
        user_id: User ID
        days: Days to look back
        limit: Max transactions to return
    
    Returns:
        Usage history with breakdown
    """
    from database import db
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    cursor = db.credit_transactions.find(
        {
            "user_id": user_id,
            "created_at": {"$gte": cutoff}
        }
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


async def check_feature_access(user_id: str, feature: str) -> Dict[str, Any]:
    """Check if user's tier allows access to a feature.
    
    Args:
        user_id: User ID
        feature: Feature name from tier config
    
    Returns:
        Access status
    """
    from database import db
    
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"allowed": False, "error": "User not found"}
    
    tier = user.get("subscription_tier", "free")
    tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
    features = tier_config.get("features", {})
    
    feature_value = features.get(feature)
    
    if feature_value is None:
        return {"allowed": False, "error": f"Unknown feature: {feature}"}
    
    # Boolean features
    if isinstance(feature_value, bool):
        return {
            "allowed": feature_value,
            "tier": tier,
            "upgrade_required": not feature_value
        }
    
    # Numeric features (limits)
    return {
        "allowed": True,
        "tier": tier,
        "limit": feature_value
    }


def get_operation_cost(operation_name: str) -> int:
    """Get credit cost for an operation.
    
    Args:
        operation_name: Name of the operation
    
    Returns:
        Credit cost
    """
    try:
        op = CreditOperation[operation_name.upper()]
        return op.value
    except KeyError:
        return 0


def get_all_tiers() -> List[Dict[str, Any]]:
    """Get all available subscription tiers.
    
    Returns:
        List of tier configurations
    """
    tiers = []
    for tier_id, config in TIER_CONFIGS.items():
        tiers.append({
            "id": tier_id,
            "name": config["name"],
            "monthly_credits": config["monthly_credits"],
            "price_monthly": config["price_monthly"],
            "features": config["features"]
        })
    return tiers
