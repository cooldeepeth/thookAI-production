"""Dashboard routes for ThookAI.

Provides aggregated stats and insights for the dashboard.
"""
import json
import asyncio
import uuid
import logging
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user
from services.llm_keys import chat_constructor_key, openai_available
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

PERPLEXITY_API_KEY = settings.llm.perplexity_key or ''
DAILY_BRIEF_CACHE_HOURS = 6


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get aggregated dashboard statistics for the current user.
    
    Returns:
    - posts_created: Total approved content count
    - credits: User's credit balance
    - platforms_count: Number of connected platforms
    - persona_score: Trust score from UOM (0-10 scale)
    - learning_signals_count: Number of learning signals captured
    - recent_jobs: Last 3 content jobs
    """
    user_id = current_user["user_id"]
    
    # Parallel queries for performance
    # Query 1: Count approved content
    posts_created = await db.content_jobs.count_documents({
        "user_id": user_id,
        "status": "approved"
    })
    
    # Query 2: Get user data (credits, platforms)
    user_data = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0, "credits": 1, "platforms_connected": 1}
    )
    credits = user_data.get("credits", 100) if user_data else 100
    platforms_connected = user_data.get("platforms_connected", []) if user_data else []
    
    # Query 3: Get persona data (UOM trust, learning signals)
    persona_data = await db.persona_engines.find_one(
        {"user_id": user_id},
        {"_id": 0, "uom": 1, "learning_signals": 1}
    )
    
    # Calculate persona score from UOM trust (0-1 -> 0-10)
    persona_score = None
    learning_signals_count = 0
    
    if persona_data:
        uom = persona_data.get("uom", {})
        trust = uom.get("trust_in_thook")
        if trust is not None:
            persona_score = round(trust * 10, 1)
        
        learning = persona_data.get("learning_signals", {})
        learning_signals_count = learning.get("approved_count", 0) + learning.get("rejected_count", 0)
    
    # Query 4: Get last 3 content jobs
    recent_jobs_cursor = db.content_jobs.find(
        {"user_id": user_id},
        {
            "_id": 0,
            "job_id": 1,
            "platform": 1,
            "content_type": 1,
            "status": 1,
            "final_content": 1,
            "created_at": 1,
            "qc_score": 1
        }
    ).sort("created_at", -1).limit(3)
    
    recent_jobs = []
    async for job in recent_jobs_cursor:
        recent_jobs.append({
            "job_id": job.get("job_id"),
            "platform": job.get("platform"),
            "content_type": job.get("content_type"),
            "status": job.get("status"),
            "preview": job.get("final_content", "")[:100] + "..." if job.get("final_content") else None,
            "created_at": job.get("created_at").isoformat() if job.get("created_at") else None,
            "persona_match": job.get("qc_score", {}).get("personaMatch") if job.get("qc_score") else None
        })
    
    return {
        "posts_created": posts_created,
        "credits": credits,
        "platforms_count": len(platforms_connected),
        "platforms_connected": platforms_connected,
        "persona_score": persona_score,
        "learning_signals_count": learning_signals_count,
        "recent_jobs": recent_jobs
    }


@router.get("/activity")
async def get_activity_feed(current_user: dict = Depends(get_current_user), limit: int = 10) -> Dict[str, Any]:
    """Get recent activity feed for the user.
    
    Includes:
    - Content creation events
    - Approval/rejection events
    - Learning signal events
    """
    user_id = current_user["user_id"]
    
    # Get recent content jobs with all statuses
    jobs_cursor = db.content_jobs.find(
        {"user_id": user_id},
        {
            "_id": 0,
            "job_id": 1,
            "platform": 1,
            "content_type": 1,
            "status": 1,
            "created_at": 1,
            "updated_at": 1
        }
    ).sort("updated_at", -1).limit(limit)
    
    activities = []
    async for job in jobs_cursor:
        activity_type = "created"
        if job.get("status") == "approved":
            activity_type = "approved"
        elif job.get("status") == "rejected":
            activity_type = "rejected"
        elif job.get("status") in ("reviewing", "completed"):
            activity_type = "ready_for_review"
        
        activities.append({
            "type": activity_type,
            "job_id": job.get("job_id"),
            "platform": job.get("platform"),
            "content_type": job.get("content_type"),
            "timestamp": job.get("updated_at", job.get("created_at")).isoformat() if job.get("updated_at") or job.get("created_at") else None
        })
    
    return {
        "activities": activities,
        "total": len(activities)
    }


@router.get("/learning-insights")
async def get_learning_insights(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get AI learning insights for the user.
    
    Shows what the AI has learned about the user's preferences.
    """
    from agents.learning import get_learning_insights
    return await get_learning_insights(current_user["user_id"])


def _valid_key(key: str) -> bool:
    return bool(key) and not any(key.startswith(p) for p in ['placeholder', 'sk-placeholder', 'pplx-placeholder'])


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def _get_trending_topics(niche: str) -> List[str]:
    """Use Scout (Perplexity) to get trending topics in creator's niche."""
    if not _valid_key(PERPLEXITY_API_KEY):
        # Return mock trending topics
        return [
            f"AI disruption in {niche}",
            "Creator economy growth",
            "Remote work trends 2025"
        ]
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a trend analyst. Return only a JSON array of 3 trending topics."
                        },
                        {
                            "role": "user",
                            "content": f"What are 3 trending topics in {niche} that a content creator should post about today? Return as JSON array: [\"topic1\", \"topic2\", \"topic3\"]"
                        }
                    ],
                    "max_tokens": 200
                },
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(_clean_json(content))
    except Exception as e:
        logger.error(f"Trending topics fetch failed: {e}")
        return [f"Industry insights in {niche}", "Personal growth stories", "Behind the scenes content"]


async def _generate_content_ideas(
    persona_card: dict,
    recent_topics: List[str],
    trending: List[str],
    burnout_risk: str
) -> List[Dict[str, str]]:
    """Use Commander (GPT-4o) to generate content ideas."""
    if not openai_available():
        # Return mock ideas
        return [
            {
                "title": "Share your biggest lesson this week",
                "hook": "I learned something that changed how I think about...",
                "platform": "linkedin"
            },
            {
                "title": "Industry trend hot take",
                "hook": "Everyone is talking about X, but nobody mentions...",
                "platform": "x"
            },
            {
                "title": "Behind the scenes moment",
                "hook": "Here's what my typical day actually looks like...",
                "platform": "instagram"
            }
        ]
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        # Adjust number of ideas based on burnout risk
        num_ideas = 1 if burnout_risk == "high" else 3
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"brief-{uuid.uuid4().hex[:8]}",
            system_message="You are a content strategist. Return only valid JSON."
        ).with_model("openai", "gpt-4o")
        
        avoid_topics = ", ".join(recent_topics[:3]) if recent_topics else "none"
        trending_str = ", ".join(trending[:3]) if trending else "general industry trends"
        
        prompt = f"""Generate {num_ideas} content ideas for a creator.

Creator Profile:
- Voice: {persona_card.get('writing_voice_descriptor', 'Professional')}
- Niche: {persona_card.get('content_niche_signature', 'Thought leadership')}
- Content Pillars: {', '.join(persona_card.get('content_pillars', ['Industry insights', 'Personal lessons']))}

Trending Topics: {trending_str}
AVOID (recently posted): {avoid_topics}

Return JSON array:
[
  {{"title": "Brief title", "hook": "Opening line hook", "platform": "linkedin|x|instagram"}}
]"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=20.0
        )
        return json.loads(_clean_json(response))[:num_ideas]
    
    except Exception as e:
        logger.error(f"Content ideas generation failed: {e}")
        return [{
            "title": "Share your perspective",
            "hook": "Here's what I've been thinking about lately...",
            "platform": "linkedin"
        }]


@router.get("/daily-brief")
async def get_daily_brief(
    current_user: dict = Depends(get_current_user),
    refresh: bool = Query(False, description="Force refresh the brief")
) -> Dict[str, Any]:
    """Get personalized daily content brief.
    
    Returns:
    - greeting: Personalized greeting
    - date_context: Current date and any relevant context
    - trending_topics: 3 trending topics in creator's niche
    - content_ideas: 3 content idea suggestions (clickable to pre-fill studio)
    - optimal_time: Best posting time suggestion
    - energy_check: UOM burnout status
    
    Results are cached for 6 hours unless refresh=true.
    """
    user_id = current_user["user_id"]
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    
    # Check for cached brief
    if not refresh:
        cached = await db.daily_briefs.find_one({
            "user_id": user_id,
            "date": today,
            "expires_at": {"$gt": now}
        })
        if cached:
            return {
                "greeting": cached.get("greeting"),
                "date_context": cached.get("date_context"),
                "trending_topics": cached.get("trending_topics", []),
                "content_ideas": cached.get("content_ideas", []),
                "optimal_time": cached.get("optimal_time"),
                "energy_check": cached.get("energy_check"),
                "cached": True
            }
    
    # Get persona and UOM data
    persona = await db.persona_engines.find_one({"user_id": user_id})
    persona_card = persona.get("card", {}) if persona else {}
    uom = persona.get("uom", {}) if persona else {}
    burnout_risk = uom.get("burnout_risk", "low")
    
    # Get user name
    user = await db.users.find_one({"user_id": user_id}, {"name": 1})
    user_name = user.get("name", "Creator").split()[0] if user else "Creator"
    
    # Get recent approved topics to avoid repetition
    recent_jobs = await db.content_jobs.find(
        {"user_id": user_id, "status": "approved"},
        {"agent_outputs.commander.primary_angle": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    recent_topics = [
        job.get("agent_outputs", {}).get("commander", {}).get("primary_angle", "")
        for job in recent_jobs if job.get("agent_outputs")
    ]
    
    # Generate brief content
    niche = persona_card.get("content_niche_signature", "professional content")
    
    # Fetch trending topics and generate ideas in parallel
    trending_task = _get_trending_topics(niche)
    trending = await trending_task
    
    ideas = await _generate_content_ideas(persona_card, recent_topics, trending, burnout_risk)
    
    # Build greeting
    hour = now.hour
    time_greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    greeting = f"{time_greeting}, {user_name}!"
    
    # Build date context
    weekday = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    date_context = f"{weekday}, {date_str}"
    
    # Optimal posting time (simplified)
    optimal_times = {
        "linkedin": "8-10 AM or 12-1 PM",
        "x": "9 AM or 5 PM",
        "instagram": "11 AM or 7 PM"
    }
    optimal_time = optimal_times.get("linkedin", "Morning hours")
    
    # Energy check based on UOM
    energy_messages = {
        "low": {"status": "energized", "message": "You're on a roll! Great time to create."},
        "medium": {"status": "balanced", "message": "Steady pace today. Quality over quantity."},
        "high": {"status": "rest", "message": "Take it easy today. One post is enough."}
    }
    energy_check = energy_messages.get(burnout_risk, energy_messages["low"])
    
    # Build response
    brief = {
        "greeting": greeting,
        "date_context": date_context,
        "trending_topics": trending[:3],
        "content_ideas": ideas[:3],
        "optimal_time": optimal_time,
        "energy_check": energy_check,
        "cached": False
    }
    
    # Cache the brief
    await db.daily_briefs.update_one(
        {"user_id": user_id, "date": today},
        {
            "$set": {
                **brief,
                "expires_at": now + timedelta(hours=DAILY_BRIEF_CACHE_HOURS),
                "updated_at": now
            }
        },
        upsert=True
    )
    
    return brief


@router.post("/daily-brief/dismiss")
async def dismiss_daily_brief(current_user: dict = Depends(get_current_user)) -> Dict[str, str]:
    """Dismiss the daily brief for today."""
    user_id = current_user["user_id"]
    today = datetime.now(timezone.utc).date().isoformat()
    
    await db.daily_brief_dismissals.update_one(
        {"user_id": user_id, "date": today},
        {"$set": {"dismissed_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    return {"message": "Brief dismissed for today"}


@router.get("/daily-brief/status")
async def get_brief_status(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Check if daily brief should be shown."""
    user_id = current_user["user_id"]
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Check if dismissed today
    dismissal = await db.daily_brief_dismissals.find_one({
        "user_id": user_id,
        "date": today
    })
    
    return {
        "show_brief": dismissal is None,
        "dismissed_today": dismissal is not None
    }




# ============ PYDANTIC MODELS ============

class ScheduleContentRequest(BaseModel):
    job_id: str
    scheduled_at: datetime
    platforms: List[str]


# ============ PLANNER ENDPOINTS ============

@router.get("/schedule/optimal-times")
async def get_optimal_times(
    platform: str = Query(..., description="Platform to get times for"),
    content_type: Optional[str] = Query(None, description="Type of content"),
    count: int = Query(3, description="Number of suggestions"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get optimal posting times for a platform."""
    from agents.planner import get_optimal_posting_times
    return await get_optimal_posting_times(
        user_id=current_user["user_id"],
        platform=platform,
        content_type=content_type,
        num_suggestions=count
    )


@router.get("/schedule/weekly")
async def get_weekly_schedule(
    platforms: str = Query("linkedin,x,instagram", description="Comma-separated platforms"),
    posts_per_week: int = Query(5, description="Target posts per week"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate a weekly posting schedule."""
    from agents.planner import get_weekly_schedule
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
    return await get_weekly_schedule(
        user_id=current_user["user_id"],
        platforms=platform_list,
        posts_per_week=posts_per_week
    )


@router.post("/schedule/content")
async def schedule_content(
    request: ScheduleContentRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Schedule content for future publishing."""
    from agents.planner import schedule_content
    return await schedule_content(
        user_id=current_user["user_id"],
        job_id=request.job_id,
        scheduled_at=request.scheduled_at,
        platforms=request.platforms
    )


@router.get("/schedule/upcoming")
async def get_upcoming_scheduled(
    limit: int = Query(10, description="Number of items to return"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get upcoming scheduled content."""
    user_id = current_user["user_id"]
    now = datetime.now(timezone.utc)
    
    scheduled_cursor = db.content_jobs.find(
        {
            "user_id": user_id,
            "status": "scheduled",
            "scheduled_at": {"$gt": now}
        },
        {
            "_id": 0,
            "job_id": 1,
            "platform": 1,
            "content_type": 1,
            "final_content": 1,
            "scheduled_at": 1,
            "scheduled_platforms": 1,
            "created_at": 1
        }
    ).sort("scheduled_at", 1).limit(limit)
    
    scheduled = []
    async for job in scheduled_cursor:
        scheduled.append({
            "job_id": job.get("job_id"),
            "platform": job.get("platform"),
            "content_type": job.get("content_type"),
            "preview": job.get("final_content", "")[:100] + "..." if job.get("final_content") else None,
            "scheduled_at": job.get("scheduled_at").isoformat() if job.get("scheduled_at") else None,
            "scheduled_platforms": job.get("scheduled_platforms", []),
            "created_at": job.get("created_at").isoformat() if job.get("created_at") else None
        })
    
    return {
        "scheduled": scheduled,
        "total": len(scheduled)
    }


# ============ PUBLISHER ENDPOINTS ============

@router.post("/publish/{job_id}")
async def publish_content_now(
    job_id: str,
    platforms: List[str] = Query(..., description="Platforms to publish to"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Publish approved content immediately to selected platforms."""
    from agents.publisher import publish_content
    
    user_id = current_user["user_id"]
    
    # Get the content job
    job = await db.content_jobs.find_one({
        "job_id": job_id,
        "user_id": user_id
    })
    
    if not job:
        return {"success": False, "error": "Content not found"}
    
    if job.get("status") not in ["approved", "scheduled"]:
        return {"success": False, "error": "Content must be approved before publishing"}
    
    content = job.get("final_content", "")
    media_assets = job.get("media_assets", [])
    is_thread = job.get("content_type") == "thread"
    
    # Publish to platforms
    result = await publish_content(
        user_id=user_id,
        content=content,
        platforms=platforms,
        media_assets=media_assets,
        is_thread=is_thread
    )
    
    # Update job status
    if result.get("all_success"):
        new_status = "published"
    elif result.get("partial_success"):
        new_status = "partially_published"
    else:
        new_status = job.get("status")  # Keep current status on failure
    
    await db.content_jobs.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "status": new_status,
                "published_at": datetime.now(timezone.utc),
                "publish_results": result.get("results"),
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {
        **result,
        "job_id": job_id,
        "status": new_status
    }


@router.delete("/schedule/{job_id}")
async def cancel_scheduled(
    job_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Cancel a scheduled post."""
    result = await db.content_jobs.update_one(
        {
            "job_id": job_id,
            "user_id": current_user["user_id"],
            "status": "scheduled"
        },
        {
            "$set": {
                "status": "approved",
                "scheduled_at": None,
                "scheduled_platforms": [],
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    if result.modified_count == 0:
        return {"message": "Scheduled post not found or already processed"}
    
    return {"message": "Scheduled post cancelled", "job_id": job_id}
