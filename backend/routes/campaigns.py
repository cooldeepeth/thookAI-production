"""
ThookAI Campaign / Project Grouping Routes

Allows users to group content jobs under named campaigns for better
organisation, tracking, and aggregate statistics.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4
import logging

from database import db
from auth_utils import get_current_user
from middleware.feature_flags import require_feature

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(require_feature("feature_campaigns"))],
)


# ==================== REQUEST / RESPONSE MODELS ====================


class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    platform: Optional[str] = None  # linkedin | x | instagram | None (multi-platform)
    start_date: Optional[str] = None  # ISO date string
    end_date: Optional[str] = None
    goal: Optional[str] = Field(None, max_length=300)


class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    platform: Optional[str] = None
    status: Optional[str] = None  # active | paused | completed | archived
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    goal: Optional[str] = Field(None, max_length=300)


VALID_STATUSES = {"active", "paused", "completed", "archived"}
VALID_PLATFORMS = {"linkedin", "x", "instagram"}


# ==================== HELPERS ====================


def _campaign_projection():
    """Standard MongoDB projection – exclude Mongo _id."""
    return {"_id": 0}


async def _get_campaign_or_404(campaign_id: str, user_id: str):
    """Fetch a campaign owned by user_id, raising 404 if missing or archived."""
    campaign = await db.campaigns.find_one(
        {"campaign_id": campaign_id, "user_id": user_id},
        _campaign_projection(),
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


# ==================== ENDPOINTS ====================


@router.post("")
async def create_campaign(
    data: CampaignCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new campaign / project grouping."""
    if data.platform and data.platform.lower() not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}",
        )

    now = datetime.now(timezone.utc)
    campaign_id = f"camp_{uuid4().hex[:12]}"

    campaign = {
        "campaign_id": campaign_id,
        "user_id": current_user["user_id"],
        "name": data.name.strip(),
        "description": (data.description or "").strip(),
        "platform": data.platform.lower() if data.platform else None,
        "status": "active",
        "start_date": data.start_date,
        "end_date": data.end_date,
        "goal": (data.goal or "").strip() or None,
        "content_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    await db.campaigns.insert_one(campaign)
    logger.info(f"Campaign created: {campaign_id} by user {current_user['user_id']}")

    # Remove Mongo _id before returning
    campaign.pop("_id", None)
    return campaign


@router.get("")
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    current_user: dict = Depends(get_current_user),
):
    """List all campaigns for the authenticated user."""
    query = {"user_id": current_user["user_id"]}

    # By default, exclude archived campaigns unless explicitly requested
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status filter")
        query["status"] = status
    else:
        query["status"] = {"$ne": "archived"}

    if platform:
        query["platform"] = platform.lower()

    campaigns = (
        await db.campaigns.find(query, _campaign_projection())
        .sort("created_at", -1)
        .to_list(100)
    )
    return {"campaigns": campaigns, "total": len(campaigns)}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a single campaign with its associated content jobs."""
    campaign = await _get_campaign_or_404(campaign_id, current_user["user_id"])

    # Fetch content jobs linked to this campaign
    jobs = (
        await db.content_jobs.find(
            {"campaign_id": campaign_id, "user_id": current_user["user_id"]},
            {"_id": 0, "agent_outputs": 0},
        )
        .sort("created_at", -1)
        .to_list(200)
    )

    return {**campaign, "content_jobs": jobs}


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update campaign details."""
    await _get_campaign_or_404(campaign_id, current_user["user_id"])

    update: dict = {"updated_at": datetime.now(timezone.utc)}

    if data.name is not None:
        update["name"] = data.name.strip()
    if data.description is not None:
        update["description"] = data.description.strip()
    if data.platform is not None:
        if data.platform and data.platform.lower() not in VALID_PLATFORMS:
            raise HTTPException(status_code=400, detail="Invalid platform")
        update["platform"] = data.platform.lower() if data.platform else None
    if data.status is not None:
        if data.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
            )
        update["status"] = data.status
    if data.start_date is not None:
        update["start_date"] = data.start_date
    if data.end_date is not None:
        update["end_date"] = data.end_date
    if data.goal is not None:
        update["goal"] = data.goal.strip() or None

    await db.campaigns.update_one(
        {"campaign_id": campaign_id, "user_id": current_user["user_id"]},
        {"$set": update},
    )

    updated = await db.campaigns.find_one(
        {"campaign_id": campaign_id}, _campaign_projection()
    )
    return updated


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Soft-delete a campaign by setting status to 'archived'.

    Content jobs are NOT deleted — they simply lose their campaign association
    if the campaign is later purged.
    """
    campaign = await _get_campaign_or_404(campaign_id, current_user["user_id"])

    if campaign.get("status") == "archived":
        return {"message": "Campaign already archived", "campaign_id": campaign_id}

    await db.campaigns.update_one(
        {"campaign_id": campaign_id, "user_id": current_user["user_id"]},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}},
    )
    logger.info(f"Campaign archived: {campaign_id}")
    return {"message": "Campaign archived", "campaign_id": campaign_id}


# ==================== CONTENT ASSOCIATION ====================


@router.post("/{campaign_id}/add-content/{job_id}")
async def add_content_to_campaign(
    campaign_id: str,
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Assign an existing content job to a campaign."""
    campaign = await _get_campaign_or_404(campaign_id, current_user["user_id"])

    if campaign.get("status") == "archived":
        raise HTTPException(status_code=400, detail="Cannot add content to an archived campaign")

    # Verify the job belongs to the user
    job = await db.content_jobs.find_one(
        {"job_id": job_id, "user_id": current_user["user_id"]}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Content job not found")

    # Check if already assigned to this campaign
    if job.get("campaign_id") == campaign_id:
        return {"message": "Content already in this campaign", "job_id": job_id}

    # Decrement old campaign's content_count if job was in a different campaign
    old_campaign_id = job.get("campaign_id")
    if old_campaign_id and old_campaign_id != campaign_id:
        await db.campaigns.update_one(
            {"campaign_id": old_campaign_id, "user_id": current_user["user_id"]},
            {"$inc": {"content_count": -1}},
        )

    # Assign the job to this campaign
    await db.content_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"campaign_id": campaign_id, "updated_at": datetime.now(timezone.utc)}},
    )

    # Increment campaign content_count
    await db.campaigns.update_one(
        {"campaign_id": campaign_id},
        {"$inc": {"content_count": 1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )

    return {"message": "Content added to campaign", "job_id": job_id, "campaign_id": campaign_id}


@router.delete("/{campaign_id}/content/{job_id}")
async def remove_content_from_campaign(
    campaign_id: str,
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a content job from a campaign (unlinks, does not delete the job)."""
    await _get_campaign_or_404(campaign_id, current_user["user_id"])

    job = await db.content_jobs.find_one(
        {"job_id": job_id, "user_id": current_user["user_id"]}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Content job not found")

    if job.get("campaign_id") != campaign_id:
        raise HTTPException(status_code=400, detail="Content job is not in this campaign")

    await db.content_jobs.update_one(
        {"job_id": job_id},
        {"$unset": {"campaign_id": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )

    await db.campaigns.update_one(
        {"campaign_id": campaign_id},
        {"$inc": {"content_count": -1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )

    return {"message": "Content removed from campaign", "job_id": job_id}


# ==================== STATS ====================


@router.get("/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Aggregate stats for a campaign's content jobs."""
    await _get_campaign_or_404(campaign_id, current_user["user_id"])

    jobs = await db.content_jobs.find(
        {"campaign_id": campaign_id, "user_id": current_user["user_id"]},
        {"_id": 0, "status": 1, "platform": 1, "qc_score": 1, "created_at": 1},
    ).to_list(500)

    total = len(jobs)
    status_counts: dict = {}
    platform_counts: dict = {}
    qc_scores: list = []

    for job in jobs:
        s = job.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

        p = job.get("platform", "unknown")
        platform_counts[p] = platform_counts.get(p, 0) + 1

        score = job.get("qc_score")
        if score is not None:
            qc_scores.append(score)

    avg_qc = round(sum(qc_scores) / len(qc_scores), 2) if qc_scores else None

    return {
        "campaign_id": campaign_id,
        "total_content": total,
        "by_status": status_counts,
        "by_platform": platform_counts,
        "average_qc_score": avg_qc,
    }
