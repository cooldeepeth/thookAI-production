# NOTE: Pattern fatigue detection has been consolidated into
# services/persona_refinement.py (get_pattern_fatigue_shield).
# This module now handles only exact-content deduplication.
# Pattern diversity is handled in the pipeline via the fatigue shield.
#
# Functions like analyze_hook_fatigue, get_content_diversity_score, and
# detect_hook_type are retained here because they are consumed by
# services/persona_refinement.py, routes/repurpose.py, and agents/analyst.py.
# Do NOT delete this file — other code imports from it.
"""Anti-Repetition Engine V2 for ThookAI.

Retained capabilities (exact-content deduplication):
- score_repetition_risk: TF-IDF / cosine similarity for near-duplicate detection
- calculate_phrase_overlap: n-gram overlap between two texts
- get_anti_repetition_context / build_anti_repetition_prompt: Commander-level dedup hints

Hook fatigue & diversity scoring functions are still exported from this module
for backward compatibility but the authoritative pattern-fatigue analysis now
lives in services/persona_refinement.get_pattern_fatigue_shield(), which is
called in the generation pipeline (pipeline.py) before the Thinker step.
"""
import os
import json
import asyncio
import logging
import re
from typing import Dict, Any, List, Tuple
from collections import Counter
from services.vector_store import get_recent_patterns, check_repetition_risk, query_similar_content
from services.llm_keys import chat_constructor_key, openai_available

logger = logging.getLogger(__name__)

# Hook pattern categories
HOOK_PATTERNS = {
    "question": r"^(what|why|how|when|where|who|do you|have you|are you|is it|can you)\b",
    "number_list": r"^(\d+)\s+(things?|ways?|tips?|reasons?|steps?|secrets?|lessons?)",
    "story_start": r"^(i |my |when i |last |yesterday |today |this morning)",
    "bold_claim": r"^(stop|forget|never|always|the truth|unpopular|controversial)",
    "direct_address": r"^(you |your |if you|most people)",
    "curiosity_gap": r"^(here's|this is|the |there's|something)"
}

# Structure patterns
STRUCTURE_PATTERNS = {
    "listicle": ["numbered points", "bullet points", "multiple sections"],
    "story": ["narrative", "personal experience", "timeline"],
    "educational": ["how-to", "tutorial", "explanation"],
    "opinion": ["hot take", "controversial", "perspective"],
    "cta_heavy": ["call to action", "engage", "follow"]
}


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def get_anti_repetition_context(user_id: str) -> Dict[str, Any]:
    """Get context for Commander to avoid repetition.
    
    Returns patterns to avoid in new content generation.
    
    Args:
        user_id: User ID
    
    Returns:
        Dict with patterns to avoid
    """
    try:
        patterns = await get_recent_patterns(user_id, limit=5)
        
        # Only return meaningful context if we have enough data
        if patterns.get("count", 0) < 2:
            return {
                "has_patterns": False,
                "message": "Not enough content history for anti-repetition"
            }
        
        return {
            "has_patterns": True,
            "avoid_topics": patterns.get("recent_topics", []),
            "avoid_hooks": patterns.get("recent_hooks", []),
            "avoid_structures": patterns.get("recent_structures", []),
            "pattern_count": patterns.get("count", 0)
        }
    
    except Exception as e:
        logger.error(f"Failed to get anti-repetition context: {e}")
        return {"has_patterns": False, "error": str(e)}


def build_anti_repetition_prompt(patterns: Dict[str, Any]) -> str:
    """Build prompt addition for Commander to avoid repetition.
    
    Args:
        patterns: Output from get_anti_repetition_context
    
    Returns:
        Prompt string to append to Commander prompt
    """
    if not patterns.get("has_patterns", False):
        return ""
    
    prompt_parts = ["\n\nANTI-REPETITION REQUIREMENTS:"]
    
    avoid_topics = patterns.get("avoid_topics", [])
    if avoid_topics:
        topics_str = "; ".join(avoid_topics[:3])
        prompt_parts.append(f"- DO NOT repeat these recent topic angles: {topics_str}")
    
    avoid_hooks = patterns.get("avoid_hooks", [])
    if avoid_hooks:
        hooks_str = "; ".join([h[:50] for h in avoid_hooks[:3]])
        prompt_parts.append(f"- DO NOT use similar hooks to: {hooks_str}")
    
    avoid_structures = patterns.get("avoid_structures", [])
    if avoid_structures:
        structures_str = ", ".join(avoid_structures[:3])
        prompt_parts.append(f"- Consider a DIFFERENT structure than recent: {structures_str}")
    
    prompt_parts.append("- Find a FRESH angle that hasn't been covered recently")
    prompt_parts.append("- Prioritize originality over familiarity")
    
    return "\n".join(prompt_parts)


async def score_repetition_risk(
    user_id: str,
    draft_content: str
) -> Dict[str, Any]:
    """Score how repetitive the draft is compared to recent content.
    
    Args:
        user_id: User ID
        draft_content: The content draft to evaluate
    
    Returns:
        Repetition risk assessment
    """
    try:
        risk_score, similar_previews = await check_repetition_risk(
            user_id=user_id,
            draft_text=draft_content,
            threshold=0.70
        )
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = "high"
            feedback = "This content is very similar to recent posts. Consider a completely different angle."
        elif risk_score >= 60:
            risk_level = "medium"
            feedback = "Some overlap with recent content detected. Try varying the hook or structure."
        elif risk_score >= 40:
            risk_level = "low"
            feedback = "Minor similarities to past content. Generally fresh approach."
        else:
            risk_level = "none"
            feedback = "Content appears fresh and original."
        
        return {
            "repetition_risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "feedback": feedback,
            "similar_content": similar_previews[:2]  # Show max 2 examples
        }
    
    except Exception as e:
        logger.error(f"Failed to score repetition risk: {e}")
        return {
            "repetition_risk_score": 0,
            "risk_level": "unknown",
            "feedback": "Could not evaluate repetition risk",
            "similar_content": []
        }


def calculate_phrase_overlap(text1: str, text2: str, phrase_length: int = 5) -> float:
    """Calculate percentage of phrase overlap between two texts.
    
    Args:
        text1: First text
        text2: Second text
        phrase_length: Number of words per phrase
    
    Returns:
        Overlap percentage (0-100)
    """
    def get_phrases(text: str, n: int) -> set:
        words = text.lower().split()
        phrases = set()
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i+n])
            phrases.add(phrase)
        return phrases
    
    phrases1 = get_phrases(text1, phrase_length)
    phrases2 = get_phrases(text2, phrase_length)
    
    if not phrases1 or not phrases2:
        return 0.0
    
    overlap = len(phrases1 & phrases2)
    total = min(len(phrases1), len(phrases2))
    
    return (overlap / total * 100) if total > 0 else 0.0


# ============ V2 ENHANCEMENTS ============

def detect_hook_type(content: str) -> Dict[str, Any]:
    """Detect the type of hook used in content.
    
    Args:
        content: The content text
    
    Returns:
        Hook type and confidence
    """
    first_line = content.split('\n')[0].strip().lower()
    
    detected_types = []
    for hook_type, pattern in HOOK_PATTERNS.items():
        if re.search(pattern, first_line, re.IGNORECASE):
            detected_types.append(hook_type)
    
    if not detected_types:
        detected_types = ["other"]
    
    return {
        "hook_text": content.split('\n')[0][:100],
        "types": detected_types,
        "primary_type": detected_types[0] if detected_types else "other"
    }


async def analyze_hook_fatigue(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """Analyze hook usage patterns to detect fatigue.
    
    Args:
        user_id: User ID
        limit: Number of recent posts to analyze
    
    Returns:
        Hook fatigue analysis
    """
    from database import db
    
    # Get recent approved/published content
    cursor = db.content_jobs.find(
        {
            "user_id": user_id,
            "status": {"$in": ["approved", "published"]}
        },
        {"final_content": 1, "created_at": 1}
    ).sort("created_at", -1).limit(limit)
    
    hook_types = []
    async for job in cursor:
        content = job.get("final_content", "")
        if content:
            hook_info = detect_hook_type(content)
            hook_types.extend(hook_info["types"])
    
    if not hook_types:
        return {
            "has_fatigue": False,
            "message": "Not enough content to analyze hook patterns"
        }
    
    # Count hook type frequency
    type_counts = Counter(hook_types)
    total = len(hook_types)
    
    # Identify overused hooks (>40% usage)
    overused = []
    for hook_type, count in type_counts.items():
        percentage = (count / total) * 100
        if percentage > 40:
            overused.append({
                "type": hook_type,
                "percentage": round(percentage, 1),
                "count": count
            })
    
    # Identify underused hooks
    used_types = set(type_counts.keys())
    all_types = set(HOOK_PATTERNS.keys())
    underused = list(all_types - used_types)
    
    return {
        "has_fatigue": len(overused) > 0,
        "overused_hooks": overused,
        "underused_hooks": underused[:3],
        "distribution": {k: round((v/total)*100, 1) for k, v in type_counts.items()},
        "recommendation": _get_hook_recommendation(overused, underused),
        "total_analyzed": total
    }


def _get_hook_recommendation(overused: List[Dict], underused: List[str]) -> str:
    """Generate recommendation based on hook analysis."""
    if not overused:
        return "Good variety in hooks! Keep mixing it up."
    
    overused_types = [h["type"] for h in overused]
    
    rec_parts = []
    
    if "question" in overused_types:
        rec_parts.append("Try fewer question hooks - use bold statements instead")
    if "number_list" in overused_types:
        rec_parts.append("Reduce listicle-style hooks - try storytelling")
    if "story_start" in overused_types:
        rec_parts.append("Balance personal stories with data or observations")
    if "bold_claim" in overused_types:
        rec_parts.append("Mix bold claims with educational content")
    
    if underused:
        rec_parts.append(f"Try more: {', '.join(underused[:2])} hooks")
    
    return " | ".join(rec_parts) if rec_parts else "Consider varying your hook styles more"


async def get_content_diversity_score(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Calculate content diversity score based on recent posts.
    
    Analyzes:
    - Topic diversity
    - Hook variety
    - Structure variation
    - Platform distribution
    
    Args:
        user_id: User ID
        days: Number of days to analyze
    
    Returns:
        Diversity score and breakdown
    """
    from database import db
    from datetime import datetime, timezone, timedelta
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    cursor = db.content_jobs.find(
        {
            "user_id": user_id,
            "status": {"$in": ["approved", "published"]},
            "created_at": {"$gte": cutoff}
        },
        {
            "final_content": 1,
            "platform": 1,
            "content_type": 1,
            "agent_outputs": 1
        }
    )
    
    contents = []
    platforms = []
    content_types = []
    topics = []
    
    async for job in cursor:
        contents.append(job.get("final_content", ""))
        platforms.append(job.get("platform", "unknown"))
        content_types.append(job.get("content_type", "post"))
        
        # Extract topic from commander output if available
        commander = job.get("agent_outputs", {}).get("commander", {})
        if commander.get("primary_angle"):
            topics.append(commander.get("primary_angle"))
    
    if len(contents) < 3:
        return {
            "score": None,
            "message": "Need at least 3 posts for diversity analysis"
        }
    
    # Calculate sub-scores
    hook_analysis = await analyze_hook_fatigue(user_id, limit=len(contents))
    hook_diversity = 100 - (hook_analysis.get("overused_hooks", [{}])[0].get("percentage", 0) if hook_analysis.get("overused_hooks") else 0)
    
    platform_diversity = len(set(platforms)) / 3 * 100  # 3 platforms max
    type_diversity = len(set(content_types)) / 4 * 100  # Assuming ~4 content types
    
    # Topic diversity (unique topics / total)
    topic_diversity = (len(set(topics)) / len(topics) * 100) if topics else 50
    
    # Overall score (weighted average)
    overall = (
        hook_diversity * 0.3 +
        topic_diversity * 0.35 +
        platform_diversity * 0.2 +
        type_diversity * 0.15
    )
    
    return {
        "score": round(overall, 1),
        "breakdown": {
            "hook_diversity": round(hook_diversity, 1),
            "topic_diversity": round(topic_diversity, 1),
            "platform_diversity": round(platform_diversity, 1),
            "content_type_diversity": round(type_diversity, 1)
        },
        "total_posts_analyzed": len(contents),
        "period_days": days,
        "rating": _get_diversity_rating(overall),
        "hook_fatigue": hook_analysis
    }


def _get_diversity_rating(score: float) -> str:
    """Get rating label for diversity score."""
    if score >= 80:
        return "excellent"
    elif score >= 60:
        return "good"
    elif score >= 40:
        return "fair"
    else:
        return "needs_improvement"


async def get_variation_suggestions(
    user_id: str,
    draft_content: str,
    platform: str
) -> Dict[str, Any]:
    """Get AI-powered suggestions to make content more unique.
    
    Args:
        user_id: User ID
        draft_content: The draft to analyze
        platform: Target platform
    
    Returns:
        Specific suggestions for variation
    """
    if not openai_available():
        return _mock_variation_suggestions(draft_content)
    
    try:
        from services.llm_client import LlmChat, UserMessage
        import uuid
        
        # Get recent patterns
        patterns = await get_anti_repetition_context(user_id)
        hook_fatigue = await analyze_hook_fatigue(user_id, limit=5)
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"variation-{uuid.uuid4().hex[:8]}",
            system_message="You are a content optimization expert. Provide specific, actionable suggestions. Return JSON only."
        ).with_model("openai", "gpt-4o-mini")
        
        context = f"""
Recent patterns to avoid: {json.dumps(patterns.get('avoid_topics', [])[:3])}
Overused hook types: {json.dumps([h['type'] for h in hook_fatigue.get('overused_hooks', [])])}
Underused hook types: {json.dumps(hook_fatigue.get('underused_hooks', [])[:2])}
"""
        
        prompt = f"""Analyze this {platform} draft and suggest 3 specific ways to make it more unique and engaging.

DRAFT:
{draft_content[:500]}

CONTEXT:
{context}

Return JSON:
{{
    "suggestions": [
        {{
            "type": "hook|structure|angle|tone",
            "current": "What's currently being done",
            "suggested": "Specific alternative",
            "example": "Quick example of the change"
        }}
    ],
    "uniqueness_score": 70,
    "top_priority": "The most impactful change to make"
}}"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=20.0
        )
        
        return {
            "success": True,
            **json.loads(_clean_json(response))
        }
    
    except Exception as e:
        logger.error(f"Variation suggestions failed: {e}")
        return _mock_variation_suggestions(draft_content)


def _mock_variation_suggestions(draft_content: str) -> Dict[str, Any]:
    """Mock variation suggestions."""
    hook_info = detect_hook_type(draft_content)
    
    suggestions = [
        {
            "type": "hook",
            "current": f"Using {hook_info['primary_type']} hook",
            "suggested": "Try a contrarian or bold statement hook",
            "example": "What if everything you know about [topic] is wrong?"
        },
        {
            "type": "structure",
            "current": "Standard format",
            "suggested": "Add a surprising twist or callback",
            "example": "End by contradicting your opening (then resolving it)"
        },
        {
            "type": "angle",
            "current": "Direct approach",
            "suggested": "Use an unexpected metaphor or analogy",
            "example": "Compare your topic to something unrelated but insightful"
        }
    ]
    
    return {
        "success": True,
        "suggestions": suggestions,
        "uniqueness_score": 65,
        "top_priority": "Vary your hook style to stand out",
        "is_mock": True
    }

