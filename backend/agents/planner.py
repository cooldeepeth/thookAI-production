"""Planner Agent for ThookAI.

Suggests optimal posting times based on:
- Platform-specific peak engagement hours
- Day of the week
- User's UOM (burnout risk)
- Content type
"""
import os
import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Platform-specific peak times (hours in user's timezone, simplified to UTC)
PLATFORM_PEAKS = {
    "linkedin": {
        "weekday": [8, 9, 10, 12, 17, 18],  # 8-10am, noon, 5-6pm
        "weekend": [10, 11, 12],  # 10am-noon
        "best_days": ["Tuesday", "Wednesday", "Thursday"]
    },
    "x": {
        "weekday": [9, 12, 17, 21],  # 9am, noon, 5pm, 9pm
        "weekend": [10, 12, 20, 21],  # 10am, noon, 8-9pm
        "best_days": ["Monday", "Wednesday", "Friday"]
    },
    "instagram": {
        "weekday": [9, 12, 15, 21],  # 9am, noon, 3pm, 9pm
        "weekend": [10, 11, 19, 20, 21],  # 10-11am, 7-9pm
        "best_days": ["Wednesday", "Friday", "Saturday"]
    }
}


def _valid_key(key: str) -> bool:
    if not key:
        return False
    placeholders = ['placeholder', 'sk-placeholder']
    return not any(key.lower().startswith(p) for p in placeholders)


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def get_optimal_posting_times(
    user_id: str,
    platform: str,
    content_type: Optional[str] = None,
    num_suggestions: int = 3
) -> Dict[str, Any]:
    """Get optimal posting times for a platform.
    
    Args:
        user_id: User ID
        platform: Target platform (linkedin, x, instagram)
        content_type: Type of content (post, thread, etc.)
        num_suggestions: Number of time slots to suggest
    
    Returns:
        {best_times: [{datetime, reason}], reasoning, platform}
    """
    from database import db
    
    now = datetime.now(timezone.utc)
    
    # Get user's UOM for burnout check
    persona = await db.persona_engines.find_one({"user_id": user_id})
    uom = persona.get("uom", {}) if persona else {}
    burnout_risk = uom.get("burnout_risk", "low")
    
    # Adjust suggestions based on burnout
    if burnout_risk == "high":
        num_suggestions = min(num_suggestions, 1)
    elif burnout_risk == "medium":
        num_suggestions = min(num_suggestions, 2)
    
    # Get platform peak times
    peaks = PLATFORM_PEAKS.get(platform, PLATFORM_PEAKS["linkedin"])
    
    # Generate time suggestions for next 7 days
    suggestions = []
    
    for day_offset in range(7):
        check_date = now + timedelta(days=day_offset)
        day_name = check_date.strftime("%A")
        is_weekend = day_name in ["Saturday", "Sunday"]
        
        # Get peak hours for this day type
        peak_hours = peaks["weekend"] if is_weekend else peaks["weekday"]
        is_best_day = day_name in peaks["best_days"]
        
        for hour in peak_hours:
            slot_time = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Skip past times
            if slot_time <= now:
                continue
            
            # Calculate score
            score = 50  # Base score
            if is_best_day:
                score += 30
            if hour in [9, 12, 17]:  # Prime hours
                score += 20
            if is_weekend and platform == "instagram":
                score += 10  # Instagram does well on weekends
            
            suggestions.append({
                "datetime": slot_time.isoformat(),
                "display_time": slot_time.strftime("%A, %b %d at %I:%M %p UTC"),
                "score": score,
                "is_best_day": is_best_day,
                "reason": _generate_reason(platform, day_name, hour, is_best_day)
            })
    
    # Sort by score and take top suggestions
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    best_times = suggestions[:num_suggestions]
    
    # Use AI to provide more nuanced reasoning if key available
    ai_reasoning = await _get_ai_reasoning(platform, best_times, content_type, burnout_risk)
    
    return {
        "best_times": best_times,
        "reasoning": ai_reasoning,
        "platform": platform,
        "burnout_adjusted": burnout_risk != "low",
        "burnout_risk": burnout_risk
    }


def _generate_reason(platform: str, day_name: str, hour: int, is_best_day: bool) -> str:
    """Generate a reason for the time slot."""
    time_desc = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    
    reasons = {
        "linkedin": f"{day_name} {time_desc} is peak engagement time for professionals",
        "x": f"{day_name} {time_desc} sees high activity and conversations",
        "instagram": f"{day_name} {time_desc} has strong visual content engagement"
    }
    
    reason = reasons.get(platform, f"Good engagement window for {platform}")
    
    if is_best_day:
        reason += " (optimal day)"
    
    return reason


async def _get_ai_reasoning(
    platform: str,
    best_times: List[Dict],
    content_type: Optional[str],
    burnout_risk: str
) -> str:
    """Get AI-generated reasoning for the suggestions."""
    if not _valid_key(LLM_KEY):
        return f"Based on {platform} engagement patterns, these times typically see higher audience activity."
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"planner-{uuid.uuid4().hex[:8]}",
            system_message="You are a social media strategist. Give brief, actionable posting advice."
        ).with_model("openai", "gpt-4.1-mini")
        
        times_str = ", ".join([t["display_time"] for t in best_times[:3]])
        
        prompt = f"""Briefly explain (1-2 sentences) why these times are good for {platform}:
{times_str}

Content type: {content_type or 'general post'}
Creator burnout level: {burnout_risk}

Keep it practical and encouraging."""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=10.0
        )
        
        return response.strip()
    
    except Exception as e:
        logger.error(f"AI reasoning failed: {e}")
        return f"These times align with peak {platform} engagement patterns for your audience."


async def get_weekly_schedule(
    user_id: str,
    platforms: List[str],
    posts_per_week: int = 5
) -> Dict[str, Any]:
    """Generate a weekly posting schedule across platforms.
    
    Args:
        user_id: User ID
        platforms: List of platforms to schedule for
        posts_per_week: Target number of posts per week
    
    Returns:
        Weekly schedule with suggested times for each platform
    """
    from database import db
    
    now = datetime.now(timezone.utc)
    
    # Get UOM
    persona = await db.persona_engines.find_one({"user_id": user_id})
    uom = persona.get("uom", {}) if persona else {}
    burnout_risk = uom.get("burnout_risk", "low")
    
    # Adjust posts based on burnout
    if burnout_risk == "high":
        posts_per_week = min(posts_per_week, 2)
    elif burnout_risk == "medium":
        posts_per_week = min(posts_per_week, 4)
    
    schedule = []
    posts_per_platform = max(1, posts_per_week // len(platforms))
    
    for platform in platforms:
        times = await get_optimal_posting_times(user_id, platform, num_suggestions=posts_per_platform)
        for time_slot in times["best_times"]:
            schedule.append({
                "platform": platform,
                "suggested_time": time_slot["datetime"],
                "display_time": time_slot["display_time"],
                "reason": time_slot["reason"]
            })
    
    # Sort by datetime
    schedule.sort(key=lambda x: x["suggested_time"])
    
    return {
        "schedule": schedule,
        "total_posts": len(schedule),
        "platforms": platforms,
        "burnout_adjusted": burnout_risk != "low",
        "recommendation": _get_schedule_recommendation(len(schedule), burnout_risk)
    }


def _get_schedule_recommendation(post_count: int, burnout_risk: str) -> str:
    """Get a recommendation based on schedule and burnout."""
    if burnout_risk == "high":
        return "Taking it easy this week. Quality over quantity - focus on one great post."
    elif burnout_risk == "medium":
        return f"Balanced schedule with {post_count} posts. Remember to take breaks between content sessions."
    else:
        return f"You're in a good rhythm! {post_count} posts scheduled for maximum reach."


async def schedule_content(
    user_id: str,
    job_id: str,
    scheduled_at: datetime,
    platforms: List[str]
) -> Dict[str, Any]:
    """Schedule content for future publishing.
    
    Args:
        user_id: User ID
        job_id: Content job ID
        scheduled_at: When to publish
        platforms: Target platforms
    
    Returns:
        {scheduled: true, scheduled_at, platforms}
    """
    from database import db
    
    # Validate scheduled time is in the future
    if scheduled_at <= datetime.now(timezone.utc):
        return {"scheduled": False, "error": "Scheduled time must be in the future"}
    
    # Update job with schedule
    result = await db.content_jobs.update_one(
        {"job_id": job_id, "user_id": user_id},
        {
            "$set": {
                "status": "scheduled",
                "scheduled_at": scheduled_at,
                "scheduled_platforms": platforms,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    if result.modified_count == 0:
        return {"scheduled": False, "error": "Job not found"}
    
    return {
        "scheduled": True,
        "job_id": job_id,
        "scheduled_at": scheduled_at.isoformat(),
        "platforms": platforms,
        "message": f"Content scheduled for {scheduled_at.strftime('%A, %b %d at %I:%M %p UTC')}"
    }
