from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from database import db
from auth_utils import get_current_user
from middleware.feature_flags import require_feature
from services.sanitize import sanitize_text
import uuid

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    dependencies=[Depends(require_feature("feature_templates"))],
)

# Template categories
CATEGORIES = [
    "thought_leadership",
    "storytelling",
    "how_to",
    "listicle",
    "contrarian",
    "case_study",
    "personal_journey",
    "industry_insights",
    "tips_and_tricks",
    "behind_the_scenes"
]

# Hook types for filtering
HOOK_TYPES = [
    "question",
    "bold_claim",
    "story_opener",
    "statistic",
    "contrarian",
    "curiosity_gap",
    "direct_address",
    "number_list"
]


class CreateTemplateRequest(BaseModel):
    job_id: str  # Content job to publish as template
    title: str
    category: str
    description: Optional[str] = None
    tags: List[str] = []


class UseTemplateRequest(BaseModel):
    platform: Optional[str] = None  # Override platform


# ============ ADMIN SEED ============

@router.post("/admin/seed")
async def seed_templates(current_user: dict = Depends(get_current_user)):
    """Seed the template marketplace with curated starter templates (admin only)."""
    # Check if user has admin role
    user = await db.users.find_one({"user_id": current_user["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if already seeded
    count = await db.templates.count_documents({})
    if count > 10:
        return {"success": True, "message": "Already seeded", "count": count}

    # Run seed logic
    from scripts.seed_templates import get_seed_templates
    templates = get_seed_templates()
    result = await db.templates.insert_many(templates)
    return {
        "success": True,
        "message": "Templates seeded successfully",
        "inserted": len(result.inserted_ids)
    }


# ============ BROWSE TEMPLATES ============

@router.get("")
async def list_templates(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    hook_type: Optional[str] = None,
    sort: str = Query("popular", enum=["popular", "recent", "most_used"]),
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Browse the templates marketplace with filtering and sorting."""
    query = {"is_active": True}
    
    if platform:
        query["platform"] = platform.lower()
    if category:
        query["category"] = category
    if hook_type:
        query["hook_type"] = hook_type
    
    # Determine sort order
    sort_field = "upvotes"  # default: popular
    if sort == "recent":
        sort_field = "created_at"
    elif sort == "most_used":
        sort_field = "uses_count"
    
    templates = await db.templates.find(
        query,
        {"_id": 0}
    ).sort(sort_field, -1).skip(offset).limit(limit).to_list(limit)
    
    total = await db.templates.count_documents(query)
    
    # Check if user has upvoted each template
    user_upvotes = await db.template_upvotes.find({
        "user_id": current_user["user_id"],
        "template_id": {"$in": [t["template_id"] for t in templates]}
    }).to_list(100)
    
    upvoted_ids = {u["template_id"] for u in user_upvotes}
    for t in templates:
        t["user_upvoted"] = t["template_id"] in upvoted_ids
    
    return {
        "success": True,
        "templates": templates,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "platform": platform,
            "category": category,
            "hook_type": hook_type,
            "sort": sort
        }
    }


@router.get("/categories")
async def get_categories():
    """Get available template categories."""
    return {
        "success": True,
        "categories": CATEGORIES,
        "hook_types": HOOK_TYPES
    }


@router.get("/featured")
async def get_featured_templates(current_user: dict = Depends(get_current_user)):
    """Get featured/trending templates."""
    # Get top templates by engagement (upvotes + uses)
    pipeline = [
        {"$match": {"is_active": True}},
        {"$addFields": {"score": {"$add": ["$upvotes", {"$multiply": ["$uses_count", 2]}]}}},
        {"$sort": {"score": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0}}
    ]
    
    featured = await db.templates.aggregate(pipeline).to_list(10)
    
    # Get recent trending (high activity in last 7 days)
    recent = await db.templates.find(
        {"is_active": True},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    return {
        "success": True,
        "featured": featured,
        "recent": recent
    }


# ============ MY TEMPLATES (must be before wildcard routes) ============

@router.get("/my/published")
async def get_my_published_templates(current_user: dict = Depends(get_current_user)):
    """Get templates published by current user."""
    templates = await db.templates.find(
        {"author_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return {
        "success": True,
        "templates": templates,
        "total": len(templates)
    }


@router.get("/my/used")
async def get_my_used_templates(current_user: dict = Depends(get_current_user)):
    """Get templates the current user has used."""
    usages = await db.template_usage.find(
        {"user_id": current_user["user_id"]}
    ).sort("used_at", -1).to_list(50)
    
    template_ids = list(set(u["template_id"] for u in usages))
    
    templates = await db.templates.find(
        {"template_id": {"$in": template_ids}},
        {"_id": 0}
    ).to_list(50)
    
    return {
        "success": True,
        "templates": templates,
        "total": len(templates)
    }


# ============ SINGLE TEMPLATE (wildcard - must be after specific routes) ============

@router.get("/{template_id}")
async def get_template(template_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single template with full details."""
    template = await db.templates.find_one(
        {"template_id": template_id, "is_active": True},
        {"_id": 0}
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if user upvoted
    upvote = await db.template_upvotes.find_one({
        "user_id": current_user["user_id"],
        "template_id": template_id
    })
    template["user_upvoted"] = upvote is not None
    
    return {
        "success": True,
        "template": template
    }


# ============ PUBLISH TEMPLATES ============

@router.post("")
async def publish_template(data: CreateTemplateRequest, current_user: dict = Depends(get_current_user)):
    """Publish approved content as an anonymized template."""
    # Validate category
    if data.category not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Choose from: {', '.join(CATEGORIES)}"
        )
    
    # Get the content job
    job = await db.content_jobs.find_one({
        "job_id": data.job_id,
        "user_id": current_user["user_id"]
    })
    
    if not job:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if job.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved content can be published as templates")
    
    # Check if already published
    existing = await db.templates.find_one({
        "source_job_id": data.job_id
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="This content is already published as a template")
    
    # Get author's persona for archetype
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    archetype = persona.get("card", {}).get("personality_archetype", "Creator") if persona else "Creator"
    
    # Detect hook type from content
    draft = job.get("draft", "")
    hook_type = _detect_hook_type(draft)
    
    # Extract structure (first line as hook, rest as body preview)
    lines = draft.strip().split("\n")
    hook = lines[0] if lines else ""
    body_preview = "\n".join(lines[1:4]) if len(lines) > 1 else ""
    
    template_id = str(uuid.uuid4())
    # SECR-02: sanitize free-text fields before storage (html.escape — XSS guard)
    template = {
        "template_id": template_id,
        "title": sanitize_text(data.title),
        "description": sanitize_text(data.description),
        "category": data.category,
        "platform": job.get("platform", "linkedin"),
        "hook_type": sanitize_text(hook_type) if isinstance(hook_type, str) else hook_type,
        "tags": data.tags,

        # Content structure (anonymized)
        "hook": sanitize_text(hook[:200]),  # Truncate for preview
        "structure_preview": sanitize_text(body_preview[:500]),
        "word_count": job.get("word_count", 0),
        "has_media": bool(job.get("media_assets")),
        
        # Author info (anonymized)
        "author_archetype": archetype,
        "author_id": current_user["user_id"],  # For admin purposes only, not exposed
        
        # Engagement metrics
        "upvotes": 0,
        "uses_count": 0,
        "views_count": 0,
        
        # Metadata
        "source_job_id": data.job_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "is_active": True
    }
    
    await db.templates.insert_one(template)
    
    return {
        "success": True,
        "template_id": template_id,
        "title": data.title,
        "message": "Template published successfully"
    }


def _detect_hook_type(content: str) -> str:
    """Detect the hook type from content."""
    first_line = content.strip().split("\n")[0].lower() if content else ""
    
    if first_line.endswith("?"):
        return "question"
    if any(word in first_line for word in ["most people", "everyone thinks", "contrary to"]):
        return "contrarian"
    if any(first_line.startswith(str(n)) for n in range(1, 20)):
        return "number_list"
    if any(word in first_line for word in ["%", "million", "billion", "study shows"]):
        return "statistic"
    if any(word in first_line for word in ["i remember", "last year", "when i", "story"]):
        return "story_opener"
    if any(word in first_line for word in ["you", "your", "here's why"]):
        return "direct_address"
    if "..." in first_line or "👇" in first_line:
        return "curiosity_gap"
    
    return "bold_claim"


# ============ USE TEMPLATES ============

@router.post("/{template_id}/use")
async def use_template(
    template_id: str,
    data: UseTemplateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Import a template into Content Studio as a new draft."""
    template = await db.templates.find_one({
        "template_id": template_id,
        "is_active": True
    })
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Increment use count
    await db.templates.update_one(
        {"template_id": template_id},
        {
            "$inc": {"uses_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    # Log usage
    await db.template_usage.insert_one({
        "usage_id": str(uuid.uuid4()),
        "template_id": template_id,
        "user_id": current_user["user_id"],
        "used_at": datetime.now(timezone.utc)
    })
    
    # Return template data for Content Studio prefill
    return {
        "success": True,
        "prefill": {
            "platform": data.platform or template["platform"],
            "raw_input": f"[Template: {template['title']}]\n\nHook inspiration: {template['hook']}\n\nStructure:\n{template['structure_preview']}",
            "template_id": template_id,
            "category": template["category"],
            "hook_type": template["hook_type"]
        },
        "message": "Template ready for use"
    }


# ============ ENGAGEMENT ============

@router.post("/{template_id}/upvote")
async def upvote_template(template_id: str, current_user: dict = Depends(get_current_user)):
    """Upvote a template (toggle)."""
    template = await db.templates.find_one({"template_id": template_id, "is_active": True})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check existing upvote
    existing = await db.template_upvotes.find_one({
        "template_id": template_id,
        "user_id": current_user["user_id"]
    })
    
    if existing:
        # Remove upvote
        await db.template_upvotes.delete_one({"_id": existing["_id"]})
        await db.templates.update_one(
            {"template_id": template_id},
            {"$inc": {"upvotes": -1}}
        )
        return {"success": True, "action": "removed", "upvoted": False}
    else:
        # Add upvote
        await db.template_upvotes.insert_one({
            "upvote_id": str(uuid.uuid4()),
            "template_id": template_id,
            "user_id": current_user["user_id"],
            "created_at": datetime.now(timezone.utc)
        })
        await db.templates.update_one(
            {"template_id": template_id},
            {"$inc": {"upvotes": 1}}
        )
        return {"success": True, "action": "added", "upvoted": True}


# ============ DELETE TEMPLATE ============

@router.delete("/{template_id}")
async def delete_template(template_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a template (author only)."""
    template = await db.templates.find_one({"template_id": template_id})
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if template["author_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the author can delete this template")
    
    # Soft delete
    await db.templates.update_one(
        {"template_id": template_id},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc)}}
    )
    
    return {"success": True, "message": "Template deleted"}
