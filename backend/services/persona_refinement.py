"""Persona Refinement Service for ThookAI.

Evolves user persona based on:
- Content performance patterns
- Learning signals from approvals/rejections
- Style drift analysis
- AI-powered voice evolution recommendations
"""
import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from services.llm_keys import (
    anthropic_available,
    chat_constructor_key,
    openai_available,
)

logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def analyze_voice_evolution(user_id: str) -> Dict[str, Any]:
    """Analyze how user's content voice has evolved over time.
    
    Compares early approved content with recent approved content
    to identify voice drift and evolution patterns.
    
    Args:
        user_id: User ID
    
    Returns:
        Voice evolution analysis
    """
    from database import db
    
    # Get approved content, earliest and latest
    cursor = db.content_jobs.find(
        {
            "user_id": user_id,
            "status": {"$in": ["approved", "published"]}
        },
        {"final_content": 1, "created_at": 1, "platform": 1, "qc_score": 1}
    ).sort("created_at", 1)
    
    all_content = await cursor.to_list(100)
    
    if len(all_content) < 5:
        return {
            "has_data": False,
            "message": "Need at least 5 approved posts to analyze voice evolution"
        }
    
    # Split into early and recent
    split_point = len(all_content) // 2
    early_content = all_content[:split_point]
    recent_content = all_content[split_point:]
    
    # Extract samples
    early_samples = [c.get("final_content", "")[:500] for c in early_content[:3]]
    recent_samples = [c.get("final_content", "")[:500] for c in recent_content[-3:]]
    
    if not anthropic_available():
        return _mock_evolution_analysis(early_samples, recent_samples, len(all_content))
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"evolution-{uuid.uuid4().hex[:8]}",
            system_message="You are a writing style analyst. Compare content samples to identify voice evolution. Return JSON only."
        ).with_model("anthropic", "claude-sonnet-4-20250514")
        
        prompt = f"""Analyze voice evolution between early and recent content samples.

EARLY CONTENT (from beginning):
{chr(10).join([f"Sample {i+1}: {s}" for i, s in enumerate(early_samples)])}

RECENT CONTENT (latest):
{chr(10).join([f"Sample {i+1}: {s}" for i, s in enumerate(recent_samples)])}

Return JSON:
{{
    "evolution_detected": true/false,
    "evolution_summary": "One sentence describing how voice has changed",
    "changes": [
        {{
            "aspect": "tone|structure|vocabulary|formality|personality",
            "from": "How it was",
            "to": "How it is now",
            "strength": "subtle|moderate|significant"
        }}
    ],
    "consistency_score": 0-100,
    "maturity_direction": "growing|stable|uncertain",
    "recommendations": ["Suggestion 1", "Suggestion 2"]
}}"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=30.0
        )
        
        analysis = json.loads(_clean_json(response))
        
        return {
            "has_data": True,
            "total_posts_analyzed": len(all_content),
            "period_start": all_content[0].get("created_at").isoformat() if all_content[0].get("created_at") else None,
            "period_end": all_content[-1].get("created_at").isoformat() if all_content[-1].get("created_at") else None,
            **analysis
        }
    
    except Exception as e:
        logger.error(f"Evolution analysis failed: {e}")
        return _mock_evolution_analysis(early_samples, recent_samples, len(all_content))


def _mock_evolution_analysis(early: List[str], recent: List[str], total: int) -> Dict[str, Any]:
    """Mock voice evolution analysis."""
    # Simple heuristics
    early_avg_len = sum(len(s) for s in early) / len(early) if early else 0
    recent_avg_len = sum(len(s) for s in recent) / len(recent) if recent else 0
    
    changes = []
    if recent_avg_len > early_avg_len * 1.2:
        changes.append({
            "aspect": "structure",
            "from": "Concise posts",
            "to": "More detailed content",
            "strength": "moderate"
        })
    elif recent_avg_len < early_avg_len * 0.8:
        changes.append({
            "aspect": "structure",
            "from": "Detailed content",
            "to": "More concise posts",
            "strength": "moderate"
        })
    
    changes.append({
        "aspect": "tone",
        "from": "Finding voice",
        "to": "More confident expression",
        "strength": "subtle"
    })
    
    return {
        "has_data": True,
        "total_posts_analyzed": total,
        "evolution_detected": len(changes) > 0,
        "evolution_summary": "Your voice has become more refined and confident over time",
        "changes": changes,
        "consistency_score": 72,
        "maturity_direction": "growing",
        "recommendations": [
            "Continue developing your unique perspective",
            "Experiment with formats while maintaining core voice"
        ],
        "is_mock": True
    }


async def suggest_persona_updates(user_id: str) -> Dict[str, Any]:
    """Suggest updates to persona card based on performance and learning.
    
    Args:
        user_id: User ID
    
    Returns:
        Suggested persona card updates
    """
    from database import db
    from agents.learning import get_learning_insights
    from agents.analyst import get_analytics_overview
    
    # Get current persona
    persona = await db.persona_engines.find_one({"user_id": user_id})
    if not persona:
        return {
            "success": False,
            "error": "No persona found. Complete onboarding first."
        }
    
    current_card = persona.get("card", {})
    
    # Get learning insights
    learning = await get_learning_insights(user_id)
    
    # Get performance data
    analytics = await get_analytics_overview(user_id, days=30)
    
    # Get voice evolution
    evolution = await analyze_voice_evolution(user_id)
    
    if not openai_available():
        return _mock_persona_suggestions(current_card, learning, analytics, evolution)
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"refine-{uuid.uuid4().hex[:8]}",
            system_message="You are a personal branding expert. Suggest persona refinements based on data. Return JSON only."
        ).with_model("openai", "gpt-4.1-mini")
        
        prompt = f"""Suggest persona card updates based on this data.

CURRENT PERSONA CARD:
{json.dumps(current_card, indent=2, default=str)}

LEARNING INSIGHTS:
- Approved count: {learning.get('approved_count', 0)}
- Rejected count: {learning.get('rejected_count', 0)}
- Patterns to adopt: {learning.get('patterns_to_adopt', [])}
- Patterns to avoid: {learning.get('patterns_to_avoid', [])}
- Style learnings: {learning.get('style_learnings', [])}

PERFORMANCE:
- Avg score: {analytics.get('summary', {}).get('avg_performance_score', 'N/A')}/100
- Top platform: {max(analytics.get('by_platform', {'unknown': {'avg_engagement_rate': 0}}).items(), key=lambda x: x[1].get('avg_engagement_rate', 0))[0] if analytics.get('by_platform') else 'unknown'}

VOICE EVOLUTION:
{json.dumps(evolution, indent=2, default=str)}

Return JSON:
{{
    "should_update": true/false,
    "confidence": 0-100,
    "suggested_updates": [
        {{
            "field": "field_name",
            "current_value": "What it is now",
            "suggested_value": "What it should be",
            "reason": "Why this change"
        }}
    ],
    "new_strengths_identified": ["strength1", "strength2"],
    "refinement_summary": "Overall recommendation"
}}"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=30.0
        )
        
        suggestions = json.loads(_clean_json(response))
        
        return {
            "success": True,
            **suggestions
        }
    
    except Exception as e:
        logger.error(f"Persona suggestions failed: {e}")
        return _mock_persona_suggestions(current_card, learning, analytics, evolution)


def _mock_persona_suggestions(card: Dict, learning: Dict, analytics: Dict, evolution: Dict) -> Dict[str, Any]:
    """Mock persona suggestions."""
    suggestions = []
    
    # Check if patterns suggest updates
    patterns = learning.get("patterns_to_adopt", [])
    if patterns:
        suggestions.append({
            "field": "content_niche_signature",
            "current_value": card.get("content_niche_signature", "Not set"),
            "suggested_value": f"{card.get('content_niche_signature', 'Your niche')} with focus on {patterns[0] if patterns else 'engagement'}",
            "reason": "Based on your successful content patterns"
        })
    
    # Check voice evolution
    if evolution.get("evolution_detected"):
        changes = evolution.get("changes", [])
        if changes:
            suggestions.append({
                "field": "writing_voice_descriptor",
                "current_value": card.get("writing_voice_descriptor", "Not set"),
                "suggested_value": f"Evolved to more {changes[0].get('to', 'refined')} style",
                "reason": f"Your voice has shifted: {evolution.get('evolution_summary', 'natural evolution')}"
            })
    
    return {
        "success": True,
        "should_update": len(suggestions) > 0,
        "confidence": 65,
        "suggested_updates": suggestions,
        "new_strengths_identified": ["Consistent posting", "Audience engagement"],
        "refinement_summary": "Your persona is evolving naturally. Consider updating your card to reflect your growth.",
        "is_mock": True
    }


async def apply_persona_refinements(
    user_id: str,
    updates: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Apply suggested refinements to persona card.
    
    Args:
        user_id: User ID
        updates: List of {field, value} updates
    
    Returns:
        Updated persona summary
    """
    from database import db
    
    now = datetime.now(timezone.utc)
    
    # Get current persona
    persona = await db.persona_engines.find_one({"user_id": user_id})
    if not persona:
        return {"success": False, "error": "Persona not found"}
    
    current_card = persona.get("card", {})
    
    # Build update operations
    update_fields = {}
    history_entry = {
        "timestamp": now,
        "updates": [],
        "source": "refinement"
    }
    
    for update in updates:
        field = update.get("field")
        value = update.get("value")
        
        if field and value:
            old_value = current_card.get(field)
            update_fields[f"card.{field}"] = value
            history_entry["updates"].append({
                "field": field,
                "old_value": old_value,
                "new_value": value
            })
    
    if not update_fields:
        return {"success": False, "error": "No valid updates provided"}
    
    # Apply updates
    update_fields["card.last_refined"] = now
    
    result = await db.persona_engines.update_one(
        {"user_id": user_id},
        {
            "$set": update_fields,
            "$push": {
                "evolution_history": {
                    "$each": [history_entry],
                    "$slice": -20  # Keep last 20 refinements
                }
            }
        }
    )
    
    if result.modified_count == 0:
        return {"success": False, "error": "Failed to apply updates"}
    
    return {
        "success": True,
        "updates_applied": len(updates),
        "fields_updated": list(update_fields.keys()),
        "timestamp": now.isoformat()
    }


async def get_persona_evolution_timeline(user_id: str) -> Dict[str, Any]:
    """Get the timeline of persona changes over time.
    
    Args:
        user_id: User ID
    
    Returns:
        Evolution timeline with all changes
    """
    from database import db
    
    persona = await db.persona_engines.find_one({"user_id": user_id})
    
    if not persona:
        return {"success": False, "error": "Persona not found"}
    
    history = persona.get("evolution_history", [])
    card = persona.get("card", {})
    
    # Build timeline
    timeline = []
    
    # Initial creation
    created_at = persona.get("created_at")
    if created_at:
        timeline.append({
            "timestamp": created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
            "event": "persona_created",
            "description": "Initial persona card created from onboarding"
        })
    
    # Add refinement events
    for entry in history:
        timestamp = entry.get("timestamp")
        updates = entry.get("updates", [])
        
        if updates:
            timeline.append({
                "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                "event": "refinement",
                "description": f"Updated {len(updates)} field(s)",
                "changes": updates
            })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "success": True,
        "current_card_summary": {
            "archetype": card.get("archetype"),
            "voice": card.get("writing_voice_descriptor"),
            "niche": card.get("content_niche_signature"),
            "last_refined": card.get("last_refined").isoformat() if card.get("last_refined") else None
        },
        "timeline": timeline[:10],  # Last 10 events
        "total_refinements": len(history)
    }


async def get_pattern_fatigue_shield(user_id: str) -> Dict[str, Any]:
    """Pattern Fatigue Shield - Advanced protection against content staleness.
    
    Combines:
    - Anti-repetition data
    - Performance trends
    - Hook fatigue
    - Audience engagement patterns
    
    Args:
        user_id: User ID
    
    Returns:
        Fatigue shield status and recommendations
    """
    from agents.anti_repetition import get_content_diversity_score, analyze_hook_fatigue, get_anti_repetition_context
    from agents.analyst import get_performance_trends
    
    # Gather all fatigue signals
    diversity = await get_content_diversity_score(user_id, days=30)
    hook_fatigue = await analyze_hook_fatigue(user_id, limit=15)
    repetition = await get_anti_repetition_context(user_id)
    trends = await get_performance_trends(user_id, days=30)
    
    # Calculate fatigue risk score
    risk_factors = []
    risk_score = 0
    
    # Diversity factor
    diversity_score = diversity.get("score")
    if diversity_score is not None:
        if diversity_score < 40:
            risk_score += 30
            risk_factors.append({
                "factor": "low_diversity",
                "severity": "high",
                "detail": f"Content diversity at {diversity_score}% - needs more variety"
            })
        elif diversity_score < 60:
            risk_score += 15
            risk_factors.append({
                "factor": "moderate_diversity",
                "severity": "medium",
                "detail": f"Content diversity at {diversity_score}% - some variety needed"
            })
    
    # Hook fatigue factor
    if hook_fatigue.get("has_fatigue"):
        overused = hook_fatigue.get("overused_hooks", [])
        if overused:
            risk_score += 25
            risk_factors.append({
                "factor": "hook_fatigue",
                "severity": "high",
                "detail": f"Hook type '{overused[0].get('type')}' overused at {overused[0].get('percentage')}%"
            })
    
    # Trend factor
    trend = trends.get("trend")
    if trend == "declining":
        risk_score += 30
        risk_factors.append({
            "factor": "declining_performance",
            "severity": "high",
            "detail": "Performance trending downward - audience may be fatigued"
        })
    
    # Repetition factor
    if repetition.get("has_patterns"):
        recent_topics = repetition.get("avoid_topics", [])
        if len(recent_topics) >= 3:
            risk_score += 10
            risk_factors.append({
                "factor": "topic_concentration",
                "severity": "low",
                "detail": f"Recent content concentrated on: {', '.join(recent_topics[:2])}"
            })
    
    # Determine shield status
    if risk_score >= 60:
        shield_status = "critical"
        shield_message = "High fatigue risk detected. Take immediate action to refresh content."
    elif risk_score >= 40:
        shield_status = "warning"
        shield_message = "Moderate fatigue risk. Consider varying your approach."
    elif risk_score >= 20:
        shield_status = "caution"
        shield_message = "Some fatigue signals detected. Monitor closely."
    else:
        shield_status = "healthy"
        shield_message = "Content is fresh and varied. Keep up the good work!"
    
    # Generate refresh recommendations
    recommendations = []
    
    if diversity_score is not None and diversity_score < 60:
        underused_hooks = hook_fatigue.get("underused_hooks", [])
        if underused_hooks:
            recommendations.append(f"Try {underused_hooks[0]} hooks in your next 3 posts")
    
    if trend == "declining":
        recommendations.append("Experiment with a new content format (carousel, thread, story)")
    
    if hook_fatigue.get("has_fatigue"):
        recommendations.append(f"Put a 7-day cooldown on {hook_fatigue.get('overused_hooks', [{}])[0].get('type', 'overused')} hooks")
    
    recommendations.append("Review your top-performing content and identify what made it unique")
    
    return {
        "success": True,
        "shield_status": shield_status,
        "shield_message": shield_message,
        "fatigue_risk_score": min(100, risk_score),
        "risk_factors": risk_factors,
        "recommendations": recommendations[:4],
        "diversity_score": diversity_score,
        "hook_fatigue_detected": hook_fatigue.get("has_fatigue", False),
        "performance_trend": trend
    }
