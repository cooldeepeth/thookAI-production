"""Anti-Repetition Engine for ThookAI.

Prevents content staleness by:
- Tracking recent topics, hooks, and structures used
- Providing avoidance patterns to Commander agent
- Scoring repetition risk in QC agent
"""
import logging
from typing import Dict, Any, List, Tuple
from services.vector_store import get_recent_patterns, check_repetition_risk, query_similar_content

logger = logging.getLogger(__name__)


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
