"""Admin Dashboard Routes for ThookAI.

Platform stats, user management, and content oversight.
All endpoints require admin role (see auth_utils.require_admin).
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import require_admin
from database import db
from services.credits import TIER_CONFIGS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


# ==================== PYDANTIC MODELS ====================


class ChangeTierRequest(BaseModel):
    tier: str


class GrantCreditsRequest(BaseModel):
    credits: int
    reason: str


# ==================== PLATFORM STATS ====================


@router.get("/stats/overview")
async def admin_stats_overview(
    _admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Platform-wide statistics overview."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # Total users
    total_users = await db.users.count_documents({})

    # New users today
    new_users_today = await db.users.count_documents(
        {"created_at": {"$gte": today_start}}
    )

    # New users last 7 days
    new_users_7d = await db.users.count_documents(
        {"created_at": {"$gte": week_ago}}
    )

    # Active users today (users who created content today)
    active_pipeline = [
        {"$match": {"created_at": {"$gte": today_start}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "count"},
    ]
    active_result = await db.content_jobs.aggregate(active_pipeline).to_list(1)
    active_users_today = active_result[0]["count"] if active_result else 0

    # Total content jobs
    total_content_jobs = await db.content_jobs.count_documents({})

    # Content jobs today
    content_jobs_today = await db.content_jobs.count_documents(
        {"created_at": {"$gte": today_start}}
    )

    # Subscription breakdown
    subscription_breakdown = {}
    for tier_key in TIER_CONFIGS:
        count = await db.users.count_documents({"subscription_tier": tier_key})
        subscription_breakdown[tier_key] = count

    # Users with no explicit tier get counted as free
    no_tier_count = await db.users.count_documents(
        {"subscription_tier": {"$exists": False}}
    )
    subscription_breakdown["starter"] = subscription_breakdown.get("starter", 0) + no_tier_count

    return {
        "total_users": total_users,
        "new_users_today": new_users_today,
        "new_users_7d": new_users_7d,
        "active_users_today": active_users_today,
        "total_content_jobs": total_content_jobs,
        "content_jobs_today": content_jobs_today,
        "subscription_breakdown": subscription_breakdown,
    }


@router.get("/stats/errors")
async def admin_stats_errors(
    _admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Last 50 failed content jobs across all users."""
    cursor = (
        db.content_jobs.find(
            {"status": {"$in": ["failed", "error"]}},
            {
                "_id": 0,
                "job_id": 1,
                "user_id": 1,
                "platform": 1,
                "content_type": 1,
                "status": 1,
                "error": 1,
                "created_at": 1,
            },
        )
        .sort("created_at", -1)
        .limit(50)
    )

    errors: List[Dict[str, Any]] = []
    async for job in cursor:
        errors.append(
            {
                "job_id": job.get("job_id"),
                "user_id": job.get("user_id"),
                "platform": job.get("platform"),
                "content_type": job.get("content_type"),
                "status": job.get("status"),
                "error": job.get("error"),
                "created_at": (
                    job["created_at"].isoformat() if job.get("created_at") else None
                ),
            }
        )

    return {"errors": errors, "total": len(errors)}


# ==================== USER MANAGEMENT ====================


@router.get("/users")
async def admin_list_users(
    page: int = Query(1, ge=1),
    search: str = Query("", max_length=200),
    tier: str = Query("", max_length=20),
    _admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Paginated user list (20 per page). Searchable by email, filterable by tier."""
    per_page = 20
    skip = (page - 1) * per_page

    query: Dict[str, Any] = {}
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
        ]
    if tier:
        query["subscription_tier"] = tier

    total = await db.users.count_documents(query)
    total_pages = max(1, math.ceil(total / per_page))

    cursor = (
        db.users.find(
            query,
            {
                "_id": 0,
                "user_id": 1,
                "email": 1,
                "name": 1,
                "subscription_tier": 1,
                "credits": 1,
                "role": 1,
                "active": 1,
                "created_at": 1,
            },
        )
        .sort("created_at", -1)
        .skip(skip)
        .limit(per_page)
    )

    raw_users: List[Dict[str, Any]] = []
    async for u in cursor:
        raw_users.append(u)

    # Batch job count query — avoids N+1 (one count_documents per user)
    user_ids = [u.get("user_id") for u in raw_users if u.get("user_id")]
    job_counts: Dict[str, int] = {}
    if user_ids:
        pipeline = [
            {"$match": {"user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        ]
        async for doc in db.content_jobs.aggregate(pipeline):
            job_counts[doc["_id"]] = doc["count"]

    users: List[Dict[str, Any]] = []
    for u in raw_users:
        uid = u.get("user_id")
        users.append(
            {
                "user_id": uid,
                "email": u.get("email"),
                "name": u.get("name"),
                "subscription_tier": u.get("subscription_tier", "starter"),
                "credits": u.get("credits", 0),
                "role": u.get("role", "user"),
                "active": u.get("active", True),
                "jobs_count": job_counts.get(uid, 0),
                "created_at": (
                    u["created_at"].isoformat() if u.get("created_at") else None
                ),
            }
        )

    return {
        "users": users,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/users/{user_id}")
async def admin_get_user(
    user_id: str,
    _admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Full user detail including job count."""
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    job_count = await db.content_jobs.count_documents({"user_id": user_id})
    persona = await db.persona_engines.find_one(
        {"user_id": user_id}, {"_id": 0, "card": 1}
    )

    # Remove sensitive fields
    user.pop("password_hash", None)
    user.pop("hashed_password", None)

    return {
        "user": user,
        "jobs_count": job_count,
        "has_persona": persona is not None,
        "persona_card": persona.get("card") if persona else None,
    }


@router.post("/users/{user_id}/tier")
async def admin_change_tier(
    user_id: str,
    body: ChangeTierRequest,
    admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Override a user's subscription tier."""
    if body.tier not in TIER_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {', '.join(TIER_CONFIGS.keys())}",
        )

    result = await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "subscription_tier": body.tier,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(
        "Admin %s changed tier for user %s to %s",
        admin.get("email", admin.get("user_id")),
        user_id,
        body.tier,
    )

    return {"message": f"Tier updated to {body.tier}", "user_id": user_id, "tier": body.tier}


@router.post("/users/{user_id}/credits")
async def admin_grant_credits(
    user_id: str,
    body: GrantCreditsRequest,
    admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Grant credits to a user account."""
    if body.credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    from services.credits import add_credits

    result = await add_credits(
        user_id=user_id,
        amount=body.credits,
        source="admin_grant",
        description=f"Admin grant: {body.reason} (by {admin.get('email', admin.get('user_id'))})",
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to grant credits"))

    logger.info(
        "Admin %s granted %d credits to user %s: %s",
        admin.get("email", admin.get("user_id")),
        body.credits,
        user_id,
        body.reason,
    )

    return {
        "message": f"Granted {body.credits} credits",
        "user_id": user_id,
        "new_balance": result.get("new_balance"),
        "reason": body.reason,
    }


@router.post("/users/{user_id}/suspend")
async def admin_suspend_user(
    user_id: str,
    admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Suspend a user account (set active: False)."""
    # Prevent self-suspension
    if user_id == admin.get("user_id"):
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")

    result = await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "active": False,
                "suspended_at": datetime.now(timezone.utc),
                "suspended_by": admin.get("user_id"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(
        "Admin %s suspended user %s",
        admin.get("email", admin.get("user_id")),
        user_id,
    )

    return {"message": "User suspended", "user_id": user_id, "active": False}


@router.post("/users/{user_id}/unsuspend")
async def admin_unsuspend_user(
    user_id: str,
    admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Unsuspend a user account (set active: True)."""
    result = await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "active": True,
                "updated_at": datetime.now(timezone.utc),
            },
            "$unset": {
                "suspended_at": "",
                "suspended_by": "",
            },
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(
        "Admin %s unsuspended user %s",
        admin.get("email", admin.get("user_id")),
        user_id,
    )

    return {"message": "User unsuspended", "user_id": user_id, "active": True}


# ==================== CONTENT MANAGEMENT ====================


@router.get("/content")
async def admin_list_content(
    status: str = Query("", max_length=20),
    page: int = Query(1, ge=1),
    _admin: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """Filtered content jobs across all users."""
    per_page = 20
    skip = (page - 1) * per_page

    query: Dict[str, Any] = {}
    if status:
        query["status"] = status

    total = await db.content_jobs.count_documents(query)
    total_pages = max(1, math.ceil(total / per_page))

    cursor = (
        db.content_jobs.find(
            query,
            {
                "_id": 0,
                "job_id": 1,
                "user_id": 1,
                "platform": 1,
                "content_type": 1,
                "status": 1,
                "error": 1,
                "raw_input": 1,
                "created_at": 1,
                "updated_at": 1,
            },
        )
        .sort("created_at", -1)
        .skip(skip)
        .limit(per_page)
    )

    jobs: List[Dict[str, Any]] = []
    async for job in cursor:
        jobs.append(
            {
                "job_id": job.get("job_id"),
                "user_id": job.get("user_id"),
                "platform": job.get("platform"),
                "content_type": job.get("content_type"),
                "status": job.get("status"),
                "error": job.get("error"),
                "raw_input": (job.get("raw_input") or "")[:120],
                "created_at": (
                    job["created_at"].isoformat() if job.get("created_at") else None
                ),
                "updated_at": (
                    job["updated_at"].isoformat() if job.get("updated_at") else None
                ),
            }
        )

    return {
        "jobs": jobs,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }
