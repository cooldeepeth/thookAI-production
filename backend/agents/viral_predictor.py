"""Viral Hook Predictor Agent for ThookAI.

Predicts virality potential of hooks and provides improvement suggestions:
- Virality score (0-100)
- Pattern analysis against successful hooks
- Specific improvement suggestions
- A/B test suggestions
"""
import os
import json
import asyncio
import uuid
import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# High-performing hook patterns based on research
VIRAL_PATTERNS = {
    "curiosity_gap": {
        "patterns": [
            r"^(here's|this is|the) (one|single|only|secret|surprising|unexpected)",
            r"^(nobody|no one) (talks about|mentions|knows)",
            r"^(what|why) (most|everyone) (gets wrong|misses|ignores)"
        ],
        "weight": 1.2,
        "description": "Creates intrigue by hinting at exclusive knowledge"
    },
    "contrarian": {
        "patterns": [
            r"^(stop|forget|ignore|ditch|skip|quit)",
            r"^(unpopular opinion|hot take|controversial)",
            r"^(the truth|harsh truth|reality) (about|is|nobody)"
        ],
        "weight": 1.15,
        "description": "Challenges conventional wisdom"
    },
    "number_hook": {
        "patterns": [
            r"^(\d+) (things?|ways?|tips?|reasons?|mistakes?|secrets?|lessons?|rules?)",
            r"^(the )?\d+[-\s]?(step|minute|second|hour|day|week)",
            r"^\d+%"
        ],
        "weight": 1.1,
        "description": "Provides clear structure and expectations"
    },
    "story_hook": {
        "patterns": [
            r"^(i |my |we |our )(just|finally|almost|nearly|recently)",
            r"^(last|yesterday|today|this morning|2 years ago)",
            r"^(in \d{4}|when i was)"
        ],
        "weight": 1.05,
        "description": "Personal narrative creates connection"
    },
    "direct_address": {
        "patterns": [
            r"^(you |your |if you|most people|everyone)",
            r"^(want to|need to|trying to|struggling to)",
            r"^(tired of|sick of|frustrated with)"
        ],
        "weight": 1.0,
        "description": "Directly engages the reader"
    },
    "result_hook": {
        "patterns": [
            r"(made|earned|saved|lost|grew|gained) \$?\d+",
            r"(from \d+ to \d+|\d+x|doubled|tripled)",
            r"(in \d+ days?|in \d+ months?|overnight)"
        ],
        "weight": 1.25,
        "description": "Shows tangible outcomes"
    }
}

# Negative patterns that reduce virality
WEAK_PATTERNS = {
    "generic_opener": {
        "patterns": [
            r"^(hi|hello|hey) (everyone|all|there)",
            r"^(good morning|happy|excited to)",
            r"^(i wanted to share|just wanted to|thought i'd)"
        ],
        "penalty": 0.85,
        "reason": "Too generic, doesn't grab attention"
    },
    "weak_language": {
        "patterns": [
            r"\b(maybe|perhaps|might|could be|i think|i believe)\b",
            r"\b(just|only|simply|basically|literally)\b"
        ],
        "penalty": 0.95,
        "reason": "Undermines authority and confidence"
    },
    "clickbait_overload": {
        "patterns": [
            r"(!{2,}|\?{2,})",
            r"(🔥|💯|😱|🤯){2,}",
            r"(you won't believe|shocking|mind-blowing)"
        ],
        "penalty": 0.9,
        "reason": "Feels spammy and inauthentic"
    }
}


def _valid_key(key: str) -> bool:
    return bool(key) and not any(key.startswith(p) for p in ['placeholder', 'sk-placeholder'])


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


def _extract_hook(content: str) -> str:
    """Extract the hook (first line/sentence) from content."""
    # Get first line
    first_line = content.split('\n')[0].strip()
    
    # If very long, get first sentence
    if len(first_line) > 200:
        sentences = re.split(r'[.!?]', first_line)
        if sentences:
            first_line = sentences[0].strip()
    
    return first_line[:200]  # Cap at 200 chars


def analyze_hook_patterns(hook: str) -> Dict[str, Any]:
    """Analyze hook against known viral patterns.
    
    Args:
        hook: The hook text to analyze
    
    Returns:
        Pattern analysis results
    """
    hook_lower = hook.lower()
    
    detected_patterns = []
    base_score = 50  # Start at neutral
    
    # Check viral patterns
    for pattern_name, config in VIRAL_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, hook_lower, re.IGNORECASE):
                detected_patterns.append({
                    "type": pattern_name,
                    "impact": "positive",
                    "weight": config["weight"],
                    "description": config["description"]
                })
                base_score *= config["weight"]
                break  # Only count each pattern type once
    
    # Check weak patterns
    weak_detected = []
    for pattern_name, config in WEAK_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, hook_lower, re.IGNORECASE):
                weak_detected.append({
                    "type": pattern_name,
                    "impact": "negative",
                    "penalty": config["penalty"],
                    "reason": config["reason"]
                })
                base_score *= config["penalty"]
                break
    
    # Additional factors
    factors = []
    
    # Length factor
    hook_len = len(hook)
    if 50 <= hook_len <= 150:
        factors.append({"factor": "optimal_length", "impact": 1.05})
        base_score *= 1.05
    elif hook_len < 30:
        factors.append({"factor": "too_short", "impact": 0.95})
        base_score *= 0.95
    elif hook_len > 200:
        factors.append({"factor": "too_long", "impact": 0.9})
        base_score *= 0.9
    
    # Emoji factor (1-3 emojis can help)
    emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', hook))
    if 1 <= emoji_count <= 3:
        factors.append({"factor": "good_emoji_usage", "impact": 1.02})
        base_score *= 1.02
    elif emoji_count > 5:
        factors.append({"factor": "emoji_overload", "impact": 0.95})
        base_score *= 0.95
    
    # Cap score at 100
    final_score = min(100, max(0, int(base_score)))
    
    return {
        "hook": hook,
        "base_score": 50,
        "final_score": final_score,
        "viral_patterns": detected_patterns,
        "weak_patterns": weak_detected,
        "factors": factors
    }


async def predict_virality(
    content: str,
    platform: str = "linkedin"
) -> Dict[str, Any]:
    """Predict viral potential of content hook.
    
    Args:
        content: Content text (hook will be extracted)
        platform: Target platform
    
    Returns:
        Virality prediction with score and analysis
    """
    hook = _extract_hook(content)
    
    # Rule-based analysis
    pattern_analysis = analyze_hook_patterns(hook)
    rule_score = pattern_analysis["final_score"]
    
    # AI analysis for deeper insights
    if _valid_key(LLM_KEY):
        ai_analysis = await _ai_analyze_hook(hook, platform, pattern_analysis)
    else:
        ai_analysis = _mock_ai_analysis(hook, pattern_analysis)
    
    # Combine scores (60% AI, 40% rule-based if AI available)
    if ai_analysis.get("ai_score"):
        final_score = int(ai_analysis["ai_score"] * 0.6 + rule_score * 0.4)
    else:
        final_score = rule_score
    
    # Determine virality level
    if final_score >= 80:
        level = "high"
        level_description = "Strong viral potential"
    elif final_score >= 60:
        level = "moderate"
        level_description = "Good engagement expected"
    elif final_score >= 40:
        level = "low"
        level_description = "May need improvement"
    else:
        level = "poor"
        level_description = "Significant improvement needed"
    
    return {
        "success": True,
        "hook": hook,
        "platform": platform,
        "virality_score": final_score,
        "virality_level": level,
        "level_description": level_description,
        "rule_based_score": rule_score,
        "pattern_analysis": pattern_analysis,
        "ai_analysis": ai_analysis,
        "improvements": ai_analysis.get("improvements", []),
        "alternative_hooks": ai_analysis.get("alternatives", [])
    }


async def _ai_analyze_hook(hook: str, platform: str, pattern_analysis: Dict) -> Dict[str, Any]:
    """Get AI analysis of hook virality."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"viral-{uuid.uuid4().hex[:8]}",
            system_message="You are a viral content expert who analyzes hooks for social media. Return JSON only."
        ).with_model("openai", "gpt-4.1-mini")
        
        prompt = f"""Analyze this {platform.upper()} hook for viral potential.

HOOK: "{hook}"

PATTERN ANALYSIS:
- Rule-based score: {pattern_analysis['final_score']}/100
- Viral patterns found: {[p['type'] for p in pattern_analysis.get('viral_patterns', [])]}
- Weak patterns found: {[p['type'] for p in pattern_analysis.get('weak_patterns', [])]}

Evaluate the hook for:
1. Emotional trigger strength (curiosity, fear, excitement, etc.)
2. Clarity and specificity
3. Platform fit for {platform}
4. Scroll-stopping power

Return JSON:
{{
    "ai_score": 0-100,
    "emotional_triggers": ["trigger1", "trigger2"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1"],
    "improvements": [
        {{
            "issue": "What's wrong",
            "suggestion": "How to fix",
            "priority": "high|medium|low"
        }}
    ],
    "alternatives": [
        "Alternative hook 1",
        "Alternative hook 2"
    ],
    "platform_fit_score": 0-100,
    "scroll_stop_rating": "high|medium|low"
}}"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=20.0
        )
        
        return json.loads(_clean_json(response))
    
    except Exception as e:
        logger.error(f"AI hook analysis failed: {e}")
        return _mock_ai_analysis(hook, pattern_analysis)


def _mock_ai_analysis(hook: str, pattern_analysis: Dict) -> Dict[str, Any]:
    """Generate mock AI analysis."""
    rule_score = pattern_analysis["final_score"]
    
    improvements = []
    alternatives = []
    
    # Generate improvements based on pattern analysis
    if not pattern_analysis.get("viral_patterns"):
        improvements.append({
            "issue": "No strong hook pattern detected",
            "suggestion": "Start with a curiosity gap, number, or contrarian statement",
            "priority": "high"
        })
        alternatives.append(f"The ONE thing about {hook[:30]}... that nobody talks about")
    
    if pattern_analysis.get("weak_patterns"):
        for weak in pattern_analysis["weak_patterns"][:2]:
            improvements.append({
                "issue": weak["reason"],
                "suggestion": f"Remove or replace {weak['type'].replace('_', ' ')} elements",
                "priority": "medium"
            })
    
    if len(hook) > 150:
        improvements.append({
            "issue": "Hook is too long",
            "suggestion": "Trim to under 150 characters for better scroll-stopping",
            "priority": "medium"
        })
    
    # Generate alternative if score is low
    if rule_score < 60:
        alternatives.extend([
            f"Stop {hook.split()[1] if len(hook.split()) > 1 else 'doing this'}. Here's why:",
            f"I spent 100 hours learning about {hook[:20]}..."
        ])
    
    return {
        "ai_score": rule_score,  # Use rule score as AI score in mock
        "emotional_triggers": ["curiosity"] if rule_score > 50 else [],
        "strengths": ["Clear topic"] if len(hook) > 20 else [],
        "weaknesses": ["Could be more specific"] if rule_score < 70 else [],
        "improvements": improvements[:3],
        "alternatives": alternatives[:2],
        "platform_fit_score": rule_score,
        "scroll_stop_rating": "high" if rule_score >= 70 else "medium" if rule_score >= 50 else "low",
        "is_mock": True
    }


async def improve_hook(
    hook: str,
    platform: str = "linkedin",
    style: str = "curiosity"
) -> Dict[str, Any]:
    """Generate improved versions of a hook.
    
    Args:
        hook: Original hook text
        platform: Target platform
        style: Improvement style (curiosity, contrarian, story, number)
    
    Returns:
        Improved hook versions
    """
    if not _valid_key(LLM_KEY):
        return _mock_improve_hook(hook, style)
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"improve-{uuid.uuid4().hex[:8]}",
            system_message="You are a viral copywriter. Generate scroll-stopping hooks. Return JSON only."
        ).with_model("anthropic", "claude-sonnet-4-20250514")
        
        style_instructions = {
            "curiosity": "Create intrigue by hinting at exclusive knowledge or surprising revelations",
            "contrarian": "Challenge common beliefs or conventional wisdom",
            "story": "Start with a personal narrative that builds connection",
            "number": "Use specific numbers to set clear expectations"
        }
        
        prompt = f"""Improve this {platform.upper()} hook using the {style} style.

ORIGINAL HOOK: "{hook}"

STYLE INSTRUCTION: {style_instructions.get(style, style_instructions['curiosity'])}

Generate 3 improved versions that:
1. Stop the scroll
2. Create urgency to read more
3. Feel authentic (not clickbaity)
4. Fit {platform}'s audience expectations

Return JSON:
{{
    "improved_hooks": [
        {{
            "text": "Improved hook text",
            "predicted_score": 0-100,
            "key_change": "What makes this better"
        }}
    ],
    "style_applied": "{style}",
    "original_analysis": "Brief analysis of original"
}}"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=25.0
        )
        
        result = json.loads(_clean_json(response))
        
        return {
            "success": True,
            "original_hook": hook,
            "style": style,
            "platform": platform,
            **result
        }
    
    except Exception as e:
        logger.error(f"Hook improvement failed: {e}")
        return _mock_improve_hook(hook, style)


def _mock_improve_hook(hook: str, style: str) -> Dict[str, Any]:
    """Generate mock improved hooks."""
    topic = " ".join(hook.split()[:3]) if len(hook.split()) >= 3 else hook
    
    improved = []
    
    if style == "curiosity":
        improved = [
            {"text": f"Nobody talks about this {topic}... but it changed everything", "predicted_score": 72, "key_change": "Added curiosity gap"},
            {"text": f"The truth about {topic} that experts won't tell you", "predicted_score": 68, "key_change": "Added exclusivity"},
            {"text": f"I discovered something about {topic}. Here's what happened:", "predicted_score": 65, "key_change": "Personal discovery angle"}
        ]
    elif style == "contrarian":
        improved = [
            {"text": f"Stop focusing on {topic}. Here's what actually works:", "predicted_score": 75, "key_change": "Contrarian opener"},
            {"text": f"Unpopular opinion: {topic} is overrated", "predicted_score": 70, "key_change": "Hot take positioning"},
            {"text": f"Everyone's wrong about {topic}. Let me explain:", "predicted_score": 68, "key_change": "Challenge consensus"}
        ]
    elif style == "number":
        improved = [
            {"text": f"7 {topic} lessons I learned the hard way", "predicted_score": 70, "key_change": "Specific number + experience"},
            {"text": f"I spent 500 hours on {topic}. Here are 5 insights:", "predicted_score": 72, "key_change": "Credibility + list"},
            {"text": f"3 {topic} mistakes costing you results", "predicted_score": 68, "key_change": "Pain point + number"}
        ]
    else:  # story
        improved = [
            {"text": f"2 years ago, I knew nothing about {topic}. Today:", "predicted_score": 70, "key_change": "Transformation arc"},
            {"text": f"Last week, something happened that changed how I see {topic}", "predicted_score": 65, "key_change": "Recency + intrigue"},
            {"text": f"My biggest {topic} failure taught me this:", "predicted_score": 68, "key_change": "Vulnerability + lesson"}
        ]
    
    return {
        "success": True,
        "original_hook": hook,
        "style": style,
        "improved_hooks": improved,
        "style_applied": style,
        "original_analysis": "Hook could benefit from stronger emotional trigger",
        "is_mock": True
    }


async def batch_predict(hooks: List[str], platform: str = "linkedin") -> Dict[str, Any]:
    """Predict virality for multiple hooks (A/B testing).
    
    Args:
        hooks: List of hook variations
        platform: Target platform
    
    Returns:
        Ranked hooks with predictions
    """
    results = []
    
    for hook in hooks[:5]:  # Limit to 5
        prediction = await predict_virality(hook, platform)
        results.append({
            "hook": hook,
            "score": prediction.get("virality_score", 0),
            "level": prediction.get("virality_level", "unknown")
        })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "success": True,
        "platform": platform,
        "predictions": results,
        "recommended": results[0] if results else None,
        "total_analyzed": len(results)
    }
