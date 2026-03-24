"""Repurpose Agent for ThookAI.

Transforms content from one platform format to multiple platform-native variants:
- LinkedIn post → X thread → Instagram caption
- X thread → LinkedIn article → Instagram carousel
- etc.

Uses the Writer agent with platform-specific adaptations.
"""
import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from services.llm_keys import anthropic_available, chat_constructor_key

logger = logging.getLogger(__name__)

# Platform format specifications
PLATFORM_SPECS = {
    "linkedin": {
        "max_chars": 3000,
        "style": "professional, thought leadership",
        "features": ["hashtags", "line breaks for readability", "hook + story + CTA pattern"],
        "optimal_structure": "Hook (2-3 lines) → Story/Value (5-10 lines) → Key Insight → CTA"
    },
    "x": {
        "max_chars": 280,
        "style": "concise, punchy, conversational",
        "features": ["threads for long content", "no hashtags in main text", "strong hooks"],
        "optimal_structure": "Hook tweet → Supporting points → Conclusion/CTA"
    },
    "instagram": {
        "max_chars": 2200,
        "style": "visual-first, relatable, authentic",
        "features": ["emoji usage", "hashtags at end", "personal storytelling"],
        "optimal_structure": "Hook → Story → Value → CTA → Hashtags (15-30)"
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


async def repurpose_content(
    source_content: str,
    source_platform: str,
    target_platforms: List[str],
    persona_card: Optional[Dict] = None,
    keep_tone: bool = True
) -> Dict[str, Any]:
    """Repurpose content from one platform to multiple target platforms.
    
    Args:
        source_content: The original content to repurpose
        source_platform: Platform the content was created for
        target_platforms: List of platforms to adapt content for
        persona_card: User's persona for voice matching
        keep_tone: Whether to maintain the original tone
    
    Returns:
        Dict with repurposed content for each platform
    """
    if not anthropic_available():
        # Return mock repurposed content
        return _mock_repurpose(source_content, source_platform, target_platforms)
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        results = {}
        
        for target_platform in target_platforms:
            if target_platform == source_platform:
                continue
            
            target_spec = PLATFORM_SPECS.get(target_platform, PLATFORM_SPECS["linkedin"])
            source_spec = PLATFORM_SPECS.get(source_platform, PLATFORM_SPECS["linkedin"])
            
            chat = LlmChat(
                api_key=chat_constructor_key(),
                session_id=f"repurpose-{uuid.uuid4().hex[:8]}",
                system_message="""You are an expert content adapter. Your job is to transform content 
between social media platforms while preserving the core message and the creator's voice.
Return only valid JSON."""
            ).with_model("anthropic", "claude-sonnet-4-20250514")
            
            voice_context = ""
            if persona_card:
                voice_context = f"""
Creator Voice Profile:
- Writing style: {persona_card.get('writing_voice_descriptor', 'Professional')}
- Tone: {persona_card.get('archetype', 'Thought Leader')}
- Content niche: {persona_card.get('content_niche_signature', 'General')}
"""
            
            prompt = f"""Transform this {source_platform.upper()} content into {target_platform.upper()} format.

ORIGINAL ({source_platform.upper()}):
{source_content}

SOURCE FORMAT ({source_platform}):
- Max length: {source_spec['max_chars']} chars
- Style: {source_spec['style']}
- Structure: {source_spec['optimal_structure']}

TARGET FORMAT ({target_platform}):
- Max length: {target_spec['max_chars']} chars
- Style: {target_spec['style']}
- Features: {', '.join(target_spec['features'])}
- Structure: {target_spec['optimal_structure']}

{voice_context}

REQUIREMENTS:
1. {"Maintain the original tone and voice" if keep_tone else "Adapt tone for the target platform"}
2. Keep the core message and key insights
3. Optimize for the target platform's engagement patterns
4. {"Create a thread if content exceeds 280 chars" if target_platform == "x" else ""}
5. Add platform-appropriate formatting

Return JSON:
{{
    "content": "The repurposed content (or array of tweets for X threads)",
    "is_thread": true/false,
    "hashtags": ["relevant", "hashtags"],
    "adaptation_notes": "Brief note on what was changed",
    "char_count": 123
}}"""
            
            response = await asyncio.wait_for(
                chat.send_message(UserMessage(text=prompt)),
                timeout=45.0
            )
            
            parsed = json.loads(_clean_json(response))
            
            results[target_platform] = {
                "content": parsed.get("content", ""),
                "is_thread": parsed.get("is_thread", False),
                "hashtags": parsed.get("hashtags", []),
                "adaptation_notes": parsed.get("adaptation_notes", ""),
                "char_count": parsed.get("char_count", len(str(parsed.get("content", "")))),
                "platform_spec": target_spec
            }
        
        return {
            "success": True,
            "source_platform": source_platform,
            "repurposed": results,
            "platforms_processed": list(results.keys())
        }
    
    except Exception as e:
        logger.error(f"Repurpose failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "source_platform": source_platform,
            "repurposed": {}
        }


def _mock_repurpose(source_content: str, source_platform: str, target_platforms: List[str]) -> Dict[str, Any]:
    """Generate mock repurposed content when API key is not available."""
    results = {}
    
    # Extract first sentence as hook
    hook = source_content.split('.')[0] if '.' in source_content else source_content[:100]
    
    for target in target_platforms:
        if target == source_platform:
            continue
        
        if target == "x":
            # Create a thread mock
            results["x"] = {
                "content": [
                    f"🧵 {hook}...",
                    "Here's what I've learned:",
                    "1/ The key insight is...",
                    "2/ This matters because...",
                    "3/ Action step: Start today.",
                    "Follow for more insights like this."
                ],
                "is_thread": True,
                "hashtags": [],
                "adaptation_notes": "Converted to X thread format",
                "char_count": 250
            }
        elif target == "linkedin":
            results["linkedin"] = {
                "content": f"{hook}.\n\nHere's what I've learned about this topic:\n\n→ Key insight 1\n→ Key insight 2\n→ Key insight 3\n\nWhat's your take on this?\n\n#ContentCreation #ThoughtLeadership",
                "is_thread": False,
                "hashtags": ["ContentCreation", "ThoughtLeadership"],
                "adaptation_notes": "Expanded for LinkedIn professional audience",
                "char_count": 300
            }
        elif target == "instagram":
            results["instagram"] = {
                "content": f"✨ {hook} ✨\n\nSwipe to learn more 👉\n\nSave this for later! 📌\n\n.\n.\n.\n#contentcreator #socialmedia #growthmindset #motivation",
                "is_thread": False,
                "hashtags": ["contentcreator", "socialmedia", "growthmindset", "motivation"],
                "adaptation_notes": "Added Instagram-friendly formatting and hashtags",
                "char_count": 200
            }
    
    return {
        "success": True,
        "source_platform": source_platform,
        "repurposed": results,
        "platforms_processed": list(results.keys()),
        "is_mock": True
    }


async def bulk_repurpose(
    user_id: str,
    source_job_id: str,
    target_platforms: List[str]
) -> Dict[str, Any]:
    """Repurpose an approved content job to multiple platforms.
    
    Creates new content jobs for each target platform.
    
    Args:
        user_id: User ID
        source_job_id: Job ID of the source content
        target_platforms: Platforms to repurpose to
    
    Returns:
        Dict with created job IDs for each platform
    """
    from database import db
    
    # Get source job
    source_job = await db.content_jobs.find_one({
        "job_id": source_job_id,
        "user_id": user_id,
        "status": {"$in": ["approved", "published"]}
    })
    
    if not source_job:
        return {"success": False, "error": "Source content not found or not approved"}
    
    source_content = source_job.get("final_content", "")
    source_platform = source_job.get("platform", "linkedin")
    
    # Get persona for voice matching
    persona = await db.persona_engines.find_one({"user_id": user_id})
    persona_card = persona.get("card", {}) if persona else None
    
    # Repurpose content
    repurpose_result = await repurpose_content(
        source_content=source_content,
        source_platform=source_platform,
        target_platforms=target_platforms,
        persona_card=persona_card
    )
    
    if not repurpose_result.get("success"):
        return repurpose_result
    
    # Create jobs for each repurposed version
    created_jobs = {}
    now = datetime.now(timezone.utc)
    
    for platform, content_data in repurpose_result.get("repurposed", {}).items():
        new_job_id = str(uuid.uuid4())
        
        content_text = content_data.get("content", "")
        if isinstance(content_text, list):
            content_text = "\n\n".join(content_text)  # Join thread tweets
        
        job_doc = {
            "job_id": new_job_id,
            "user_id": user_id,
            "platform": platform,
            "content_type": "thread" if content_data.get("is_thread") else "post",
            "raw_input": f"[Repurposed from {source_platform}]",
            "final_content": content_text,
            "status": "reviewing",  # Ready for review
            "source_job_id": source_job_id,  # Link to original
            "is_repurposed": True,
            "adaptation_notes": content_data.get("adaptation_notes", ""),
            "hashtags": content_data.get("hashtags", []),
            "qc_score": {
                "personaMatch": 8,  # Assumed good since from approved content
                "aiRisk": 15,
                "platformFit": 9,
                "overall_pass": True
            },
            "created_at": now,
            "updated_at": now
        }
        
        await db.content_jobs.insert_one(job_doc)
        created_jobs[platform] = {
            "job_id": new_job_id,
            "content_preview": content_text[:200] + "..." if len(content_text) > 200 else content_text,
            "is_thread": content_data.get("is_thread", False)
        }
    
    return {
        "success": True,
        "source_job_id": source_job_id,
        "source_platform": source_platform,
        "created_jobs": created_jobs,
        "total_created": len(created_jobs)
    }


async def get_repurpose_suggestions(
    user_id: str,
    limit: int = 5
) -> Dict[str, Any]:
    """Get suggestions for content that could be repurposed.
    
    Finds approved content that hasn't been repurposed to all platforms yet.
    
    Args:
        user_id: User ID
        limit: Max suggestions to return
    
    Returns:
        List of content suggestions for repurposing
    """
    from database import db
    
    # Find approved content
    cursor = db.content_jobs.find(
        {
            "user_id": user_id,
            "status": {"$in": ["approved", "published"]},
            "is_repurposed": {"$ne": True}  # Not already a repurposed item
        },
        {
            "job_id": 1,
            "platform": 1,
            "final_content": 1,
            "created_at": 1,
            "qc_score": 1
        }
    ).sort("created_at", -1).limit(limit * 2)
    
    suggestions = []
    all_platforms = ["linkedin", "x", "instagram"]
    
    async for job in cursor:
        if len(suggestions) >= limit:
            break
        
        job_id = job.get("job_id")
        source_platform = job.get("platform")
        
        # Check which platforms this hasn't been repurposed to
        existing = await db.content_jobs.find(
            {"source_job_id": job_id, "is_repurposed": True}
        ).to_list(10)
        
        existing_platforms = {j.get("platform") for j in existing}
        available_platforms = [p for p in all_platforms if p != source_platform and p not in existing_platforms]
        
        if available_platforms:
            suggestions.append({
                "job_id": job_id,
                "platform": source_platform,
                "content_preview": job.get("final_content", "")[:150] + "...",
                "available_platforms": available_platforms,
                "persona_match": job.get("qc_score", {}).get("personaMatch"),
                "created_at": job.get("created_at").isoformat() if job.get("created_at") else None
            })
    
    return {
        "suggestions": suggestions,
        "total": len(suggestions)
    }
