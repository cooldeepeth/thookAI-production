"""Content Series Planner for ThookAI.

Plans and manages content series - sequences of related posts that build on a theme:
- "7 Days of Productivity Tips"
- "My Journey to 10K Followers" (5-part series)
- "Behind the Scenes Week"

Features:
- Series template generation
- Progress tracking
- Optimal posting sequence
- Theme consistency enforcement
"""
import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from services.llm_keys import chat_constructor_key, openai_available

logger = logging.getLogger(__name__)

# Popular series templates
SERIES_TEMPLATES = {
    "numbered_tips": {
        "name": "Numbered Tips Series",
        "description": "Daily tips on a specific topic (e.g., '7 Days of X')",
        "suggested_length": 5,
        "structure": "Tip #{number}: [Hook] → [Explanation] → [Action]",
        "example": "Day 1 of 7: The ONE morning habit that changed everything..."
    },
    "journey": {
        "name": "Journey/Story Series",
        "description": "Chronicle of a personal or professional journey",
        "suggested_length": 5,
        "structure": "Part {number}: [Timeline] → [Challenge] → [Learning]",
        "example": "Part 1: How I went from 0 to 10K followers (the ugly beginning)..."
    },
    "myth_busting": {
        "name": "Myth Busting Series",
        "description": "Debunk common misconceptions in your niche",
        "suggested_length": 5,
        "structure": "Myth #{number}: [Common belief] → [Reality] → [Why it matters]",
        "example": "Myth #1: You need to post every day to grow..."
    },
    "case_study": {
        "name": "Case Study Series",
        "description": "Deep dive into real examples",
        "suggested_length": 3,
        "structure": "Case Study {number}: [Subject] → [Analysis] → [Takeaways]",
        "example": "Case Study: How Company X grew 300% in 6 months..."
    },
    "behind_scenes": {
        "name": "Behind the Scenes",
        "description": "Peek into your process, workspace, or routine",
        "suggested_length": 5,
        "structure": "BTS #{number}: [Topic] → [Reveal] → [Why this way]",
        "example": "BTS: My actual content creation process (raw and unfiltered)..."
    },
    "contrarian": {
        "name": "Contrarian Takes",
        "description": "Challenge conventional wisdom",
        "suggested_length": 5,
        "structure": "Unpopular Opinion #{number}: [Hot take] → [Evidence] → [Conclusion]",
        "example": "Unpopular Opinion: Hustle culture is killing creativity..."
    }
}


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def create_series_plan(
    topic: str,
    template_type: str,
    num_posts: int,
    platform: str,
    persona_card: Optional[Dict] = None,
    custom_angle: Optional[str] = None
) -> Dict[str, Any]:
    """Create a content series plan.
    
    Args:
        topic: Main topic/theme for the series
        template_type: Type of series (from SERIES_TEMPLATES)
        num_posts: Number of posts in the series
        platform: Target platform
        persona_card: User's persona for voice matching
        custom_angle: Optional custom angle or hook
    
    Returns:
        Series plan with individual post outlines
    """
    template = SERIES_TEMPLATES.get(template_type, SERIES_TEMPLATES["numbered_tips"])
    
    if not openai_available():
        return _mock_series_plan(topic, template, num_posts, platform)
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"series-{uuid.uuid4().hex[:8]}",
            system_message="You are a content strategist specializing in content series that build audience engagement. Return only valid JSON."
        ).with_model("openai", "gpt-4o")
        
        voice_context = ""
        if persona_card:
            voice_context = f"""
Creator Profile:
- Voice: {persona_card.get('writing_voice_descriptor', 'Professional')}
- Niche: {persona_card.get('content_niche_signature', 'General')}
- Style: {persona_card.get('archetype', 'Thought Leader')}
"""
        
        prompt = f"""Create a {num_posts}-post content series plan.

SERIES DETAILS:
- Topic: {topic}
- Template: {template['name']}
- Structure: {template['structure']}
- Platform: {platform.upper()}
{f"- Custom Angle: {custom_angle}" if custom_angle else ""}

{voice_context}

REQUIREMENTS:
1. Each post should build on the previous while standing alone
2. Include a compelling hook for each post
3. Vary the approach slightly to maintain interest
4. End with a strong conclusion/CTA in the final post
5. Consider {platform}'s best practices

Return JSON:
{{
    "series_title": "Catchy series title",
    "series_description": "Brief description of what the series covers",
    "hashtag": "#SeriesHashtag",
    "posts": [
        {{
            "number": 1,
            "title": "Post title/hook",
            "outline": "Brief outline of content",
            "key_points": ["point1", "point2"],
            "cta": "Call to action for this post",
            "teaser_for_next": "Tease for next post (null for last)"
        }}
    ],
    "optimal_schedule": {{
        "frequency": "daily|every_other_day|weekly",
        "best_days": ["Monday", "Wednesday"],
        "reasoning": "Why this schedule"
    }},
    "series_hooks": ["Alternative hooks/angles for promotion"]
}}"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=60.0
        )
        
        plan = json.loads(_clean_json(response))
        
        return {
            "success": True,
            "topic": topic,
            "template": template_type,
            "platform": platform,
            "plan": plan
        }
    
    except Exception as e:
        logger.error(f"Series plan creation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "topic": topic
        }


def _mock_series_plan(topic: str, template: Dict, num_posts: int, platform: str) -> Dict[str, Any]:
    """Generate mock series plan."""
    posts = []
    for i in range(1, num_posts + 1):
        posts.append({
            "number": i,
            "title": f"{template['name'].split()[0]} #{i}: {topic} insight",
            "outline": f"Cover aspect {i} of {topic}",
            "key_points": [f"Key point {i}a", f"Key point {i}b"],
            "cta": "Share your thoughts in the comments" if i < num_posts else "Follow for more!",
            "teaser_for_next": f"Tomorrow: Even more about {topic}..." if i < num_posts else None
        })
    
    return {
        "success": True,
        "topic": topic,
        "template": template.get("name"),
        "platform": platform,
        "plan": {
            "series_title": f"{num_posts} Days of {topic.title()}",
            "series_description": f"A {num_posts}-part series exploring {topic}",
            "hashtag": f"#{topic.replace(' ', '')}Series",
            "posts": posts,
            "optimal_schedule": {
                "frequency": "daily",
                "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "reasoning": "Daily posts maintain momentum and keep audience engaged"
            },
            "series_hooks": [
                f"I'm starting a {num_posts}-day challenge...",
                f"What I learned about {topic} in {num_posts} posts..."
            ]
        },
        "is_mock": True
    }


async def save_series(
    user_id: str,
    plan: Dict[str, Any],
    start_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Save a series plan to the database.
    
    Args:
        user_id: User ID
        plan: Series plan from create_series_plan
        start_date: Optional start date for scheduling
    
    Returns:
        Saved series with ID
    """
    from database import db
    
    series_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    series_data = plan.get("plan", {})
    posts = series_data.get("posts", [])
    
    # Calculate schedule
    schedule = []
    if start_date:
        frequency = series_data.get("optimal_schedule", {}).get("frequency", "daily")
        day_gap = 1 if frequency == "daily" else 2 if frequency == "every_other_day" else 7
        
        for i, post in enumerate(posts):
            post_date = start_date + timedelta(days=i * day_gap)
            schedule.append({
                "post_number": post.get("number"),
                "scheduled_date": post_date.isoformat(),
                "status": "planned"
            })
    
    series_doc = {
        "series_id": series_id,
        "user_id": user_id,
        "title": series_data.get("series_title", "Untitled Series"),
        "description": series_data.get("series_description", ""),
        "hashtag": series_data.get("hashtag", ""),
        "topic": plan.get("topic", ""),
        "template": plan.get("template", ""),
        "platform": plan.get("platform", "linkedin"),
        "total_posts": len(posts),
        "completed_posts": 0,
        "posts": posts,
        "schedule": schedule,
        "optimal_schedule": series_data.get("optimal_schedule", {}),
        "series_hooks": series_data.get("series_hooks", []),
        "status": "active",
        "created_at": now,
        "updated_at": now
    }
    
    await db.content_series.insert_one(series_doc)
    
    return {
        "success": True,
        "series_id": series_id,
        "title": series_doc["title"],
        "total_posts": len(posts),
        "schedule": schedule
    }


async def get_user_series(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """Get user's content series.
    
    Args:
        user_id: User ID
        status: Filter by status (active, completed, paused)
        limit: Max series to return
    
    Returns:
        List of series
    """
    from database import db
    
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    
    cursor = db.content_series.find(
        query,
        {
            "series_id": 1,
            "title": 1,
            "description": 1,
            "platform": 1,
            "total_posts": 1,
            "completed_posts": 1,
            "status": 1,
            "created_at": 1
        }
    ).sort("created_at", -1).limit(limit)
    
    series_list = []
    async for series in cursor:
        # Safe division handling
        completed = series.get("completed_posts", 0)
        total = series.get("total_posts", 0)
        progress = (completed / max(total, 1)) * 100 if total > 0 else 0
        
        # Safe datetime handling
        created_at = series.get("created_at")
        created_at_iso = None
        if created_at:
            try:
                if hasattr(created_at, 'isoformat'):
                    created_at_iso = created_at.isoformat()
                else:
                    created_at_iso = str(created_at)
            except Exception as e:
                logger.error(f"Error converting created_at to ISO format: {e}")
                created_at_iso = None
        
        series_list.append({
            "series_id": series.get("series_id"),
            "title": series.get("title"),
            "description": series.get("description"),
            "platform": series.get("platform"),
            "total_posts": total,
            "completed_posts": completed,
            "progress": round(progress, 1),
            "status": series.get("status"),
            "created_at": created_at_iso
        })
    
    return {
        "series": series_list,
        "total": len(series_list)
    }


async def get_series_detail(user_id: str, series_id: str) -> Dict[str, Any]:
    """Get detailed series information.
    
    Args:
        user_id: User ID
        series_id: Series ID
    
    Returns:
        Full series details
    """
    from database import db
    
    series = await db.content_series.find_one({
        "series_id": series_id,
        "user_id": user_id
    })
    
    if not series:
        return {"success": False, "error": "Series not found"}
    
    # Get any created content jobs for this series
    jobs_cursor = db.content_jobs.find(
        {"series_id": series_id, "user_id": user_id},
        {"job_id": 1, "status": 1, "created_at": 1, "series_post_number": 1}
    )
    
    created_jobs = {}
    async for job in jobs_cursor:
        post_num = job.get("series_post_number")
        if post_num:
            created_jobs[post_num] = {
                "job_id": job.get("job_id"),
                "status": job.get("status")
            }
    
    posts = series.get("posts", [])
    for post in posts:
        post_num = post.get("number")
        if post_num in created_jobs:
            post["job"] = created_jobs[post_num]
    
    return {
        "success": True,
        "series_id": series.get("series_id"),
        "title": series.get("title"),
        "description": series.get("description"),
        "hashtag": series.get("hashtag"),
        "platform": series.get("platform"),
        "template": series.get("template"),
        "total_posts": series.get("total_posts"),
        "completed_posts": series.get("completed_posts", 0),
        "posts": posts,
        "schedule": series.get("schedule", []),
        "optimal_schedule": series.get("optimal_schedule", {}),
        "series_hooks": series.get("series_hooks", []),
        "status": series.get("status"),
        "created_at": series.get("created_at").isoformat() if series.get("created_at") else None
    }


async def create_series_post(
    user_id: str,
    series_id: str,
    post_number: int
) -> Dict[str, Any]:
    """Create a content job for a specific series post.
    
    Args:
        user_id: User ID
        series_id: Series ID
        post_number: Post number in the series
    
    Returns:
        Created job info
    """
    from database import db
    from pipelines.content_pipeline import run_content_pipeline
    
    # Get series
    series = await db.content_series.find_one({
        "series_id": series_id,
        "user_id": user_id
    })
    
    if not series:
        return {"success": False, "error": "Series not found"}
    
    posts = series.get("posts", [])
    post_data = next((p for p in posts if p.get("number") == post_number), None)
    
    if not post_data:
        return {"success": False, "error": f"Post {post_number} not found in series"}
    
    # Build raw input from post outline
    series_context = f"""
[SERIES: {series.get('title')} - Part {post_number}/{series.get('total_posts')}]
{series.get('hashtag', '')}

Topic: {post_data.get('title')}
Outline: {post_data.get('outline')}
Key Points: {', '.join(post_data.get('key_points', []))}
CTA: {post_data.get('cta', '')}
{"Next post teaser: " + post_data.get('teaser_for_next') if post_data.get('teaser_for_next') else ""}
"""
    
    # Create content job via pipeline
    job_id = str(uuid.uuid4())
    platform = series.get("platform", "linkedin")
    
    # Start the pipeline
    await run_content_pipeline(
        user_id=user_id,
        raw_input=series_context,
        platform=platform,
        content_type="post",
        hints=f"This is part {post_number} of a {series.get('total_posts')}-part series. Maintain consistency with series theme.",
        job_id=job_id
    )
    
    # Link job to series
    await db.content_jobs.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "series_id": series_id,
                "series_post_number": post_number
            }
        }
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "series_id": series_id,
        "post_number": post_number,
        "status": "processing"
    }


async def update_series_progress(user_id: str, series_id: str, post_number: int) -> Dict[str, Any]:
    """Mark a series post as completed.
    
    Args:
        user_id: User ID
        series_id: Series ID
        post_number: Completed post number
    
    Returns:
        Updated series progress
    """
    from database import db
    
    result = await db.content_series.update_one(
        {"series_id": series_id, "user_id": user_id},
        {
            "$inc": {"completed_posts": 1},
            "$set": {
                f"posts.{post_number - 1}.completed": True,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    if result.modified_count == 0:
        return {"success": False, "error": "Series not found or already updated"}
    
    # Check if series is complete
    series = await db.content_series.find_one({"series_id": series_id})
    if series and series.get("completed_posts", 0) >= series.get("total_posts", 1):
        await db.content_series.update_one(
            {"series_id": series_id},
            {"$set": {"status": "completed"}}
        )
    
    return {
        "success": True,
        "series_id": series_id,
        "completed_posts": series.get("completed_posts", 0) if series else 0,
        "total_posts": series.get("total_posts", 0) if series else 0
    }


def get_series_templates() -> Dict[str, Any]:
    """Get available series templates."""
    templates = []
    for key, template in SERIES_TEMPLATES.items():
        templates.append({
            "id": key,
            "name": template["name"],
            "description": template["description"],
            "suggested_length": template["suggested_length"],
            "example": template["example"]
        })
    
    return {"templates": templates, "total": len(templates)}
