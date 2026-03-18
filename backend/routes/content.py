from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging
from database import db
from auth_utils import get_current_user
from agents.pipeline import run_agent_pipeline
from agents.learning import capture_learning_signal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

PLATFORM_CONTENT_TYPES = {
    "linkedin": ["post", "carousel_caption", "article"],
    "x": ["tweet", "thread"],
    "instagram": ["feed_caption", "reel_caption"],
}


class ContentCreateRequest(BaseModel):
    platform: str
    content_type: str
    raw_input: str


class ContentStatusUpdate(BaseModel):
    status: str  # approved | rejected
    edited_content: Optional[str] = None
    rejection_reason: Optional[str] = None


@router.post("/create")
async def create_content(
    data: ContentCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    if len(data.raw_input.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please provide more context for your content idea")

    valid_types = PLATFORM_CONTENT_TYPES.get(data.platform.lower(), [])
    if data.content_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid content type for {data.platform}")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    job = {
        "job_id": job_id,
        "user_id": current_user["user_id"],
        "platform": data.platform.lower(),
        "content_type": data.content_type,
        "raw_input": data.raw_input,
        "status": "running",
        "current_agent": "commander",
        "agent_outputs": {},
        "agent_summaries": {},
        "final_content": None,
        "qc_score": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.content_jobs.insert_one(job)

    background_tasks.add_task(
        run_agent_pipeline, job_id, current_user["user_id"],
        data.platform.lower(), data.content_type, data.raw_input
    )
    return {"job_id": job_id, "status": "running"}


@router.get("/job/{job_id}")
async def get_job(job_id: str, current_user: dict = Depends(get_current_user)):
    job = await db.content_jobs.find_one(
        {"job_id": job_id, "user_id": current_user["user_id"]}, {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/job/{job_id}/status")
async def update_job_status(
    job_id: str, data: ContentStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Update content job status (approve/reject) and capture learning signals."""
    job = await db.content_jobs.find_one({"job_id": job_id, "user_id": current_user["user_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check idempotency - don't re-process already approved/rejected jobs
    if job.get("status") in ["approved", "rejected"]:
        return {"message": f"Job already {job.get('status')}", "status": job.get("status")}
    
    user_id = current_user["user_id"]
    original_content = job.get("final_content", "")
    final_content = data.edited_content if data.edited_content else original_content
    
    update = {"status": data.status, "updated_at": datetime.now(timezone.utc)}
    if data.edited_content:
        update["final_content"] = data.edited_content
        update["was_edited"] = True
    
    await db.content_jobs.update_one({"job_id": job_id}, {"$set": update})
    
    # Capture learning signal in background (don't block the response)
    if data.status == "approved":
        action = "edited" if data.edited_content and data.edited_content != original_content else "approved"
        background_tasks.add_task(
            capture_learning_signal,
            user_id=user_id,
            job_id=job_id,
            original_content=original_content,
            final_content=final_content,
            action=action
        )
        logger.info(f"Scheduled learning signal capture for approved job {job_id}")
    
    elif data.status == "rejected":
        background_tasks.add_task(
            capture_learning_signal,
            user_id=user_id,
            job_id=job_id,
            original_content=original_content,
            final_content=final_content,
            action="rejected"
        )
        logger.info(f"Scheduled learning signal capture for rejected job {job_id}")
    
    return {"message": f"Content {data.status}", "status": data.status}


@router.get("/jobs")
async def list_jobs(current_user: dict = Depends(get_current_user), limit: int = 20):
    jobs = await db.content_jobs.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "agent_outputs": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"jobs": jobs}


@router.get("/platform-types")
async def get_platform_types():
    return PLATFORM_CONTENT_TYPES
