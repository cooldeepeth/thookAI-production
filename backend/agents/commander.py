import json
import asyncio
import logging
import uuid
from typing import Dict, List, Optional

from services.llm_client import LlmChat, UserMessage
from services.llm_keys import (
    chat_constructor_key,
    openai_available,
    anthropic_available,
    gemini_available,
    strip_valid_key,
)
from config import settings

logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


COMMANDER_SYSTEM = """You are the Commander Agent for ThookAI. You orchestrate content creation strategy.
Return ONLY valid JSON — no markdown, no explanations."""

COMMANDER_PROMPT = """Analyze this creator's input and build a precise content plan.

Creator Voice: {voice_descriptor}
Niche: {content_niche}
Audience: {audience_profile}
Hook Style: {hook_style}
Goal: {content_goal}
Avoid: Anything generic, AI-sounding, off-brand

Platform: {platform}
Content Type: {content_type}
Raw Input: {raw_input}

Return JSON:
{{
  "content_type": "{content_type}",
  "primary_angle": "The exact angle to take (be specific, not generic)",
  "hook_approach": "question|stat|bold_claim|story|contrast",
  "key_points": ["point1", "point2", "point3"],
  "research_needed": true,
  "research_query": "What to search for to support this content",
  "structure": "numbered_list|story|framework|tips|Q_and_A",
  "estimated_word_count": 200,
  "cta_approach": "question|share|follow|comment",
  "persona_notes": "2 specific notes on how to write this in their voice"
}}"""


async def run_commander(
    raw_input: str,
    platform: str,
    content_type: str,
    persona_card: dict,
    anti_rep_prompt: str = "",
    media_system_suffix: str = "",
    image_urls: Optional[List[str]] = None,
) -> dict:
    """Run Commander agent to generate content strategy.
    
    Args:
        raw_input: User's raw content idea
        platform: Target platform (linkedin, x, instagram)
        content_type: Type of content (post, thread, etc.)
        persona_card: User's persona information
        anti_rep_prompt: Optional anti-repetition instructions
    
    Returns:
        Content strategy dictionary
    """
    if not openai_available() and not anthropic_available():
        return _mock_commander(raw_input, platform, content_type)
    try:
        system_msg = COMMANDER_SYSTEM
        if media_system_suffix:
            system_msg = f"{COMMANDER_SYSTEM}\n\n{media_system_suffix}"

        provider = "openai" if openai_available() else "anthropic"
        model = "gpt-4o" if provider == "openai" else "claude-sonnet-4-20250514"
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"cmd-{uuid.uuid4().hex[:8]}",
            system_message=system_msg,
        ).with_model(provider, model)

        prompt = COMMANDER_PROMPT.format(
            voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional content creator"),
            content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
            audience_profile=persona_card.get("inferred_audience_profile", "Professionals"),
            hook_style=persona_card.get("hook_style", "Bold statement"),
            content_goal=persona_card.get("content_goal", "Build personal brand"),
            platform=platform, content_type=content_type, raw_input=raw_input
        )
        
        # Add anti-repetition instructions if provided
        if anti_rep_prompt:
            prompt += anti_rep_prompt
        
        imgs = image_urls if image_urls else None
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt, images=imgs)),
            timeout=20.0,
        )
        return json.loads(_clean_json(response))
    except Exception as e:
        logger.error("Commander agent failed, using mock: %s", e)
        return _mock_commander(raw_input, platform, content_type)


def _mock_commander(raw_input: str, platform: str, content_type: str) -> dict:
    return {
        "content_type": content_type,
        "primary_angle": f"A personal, data-backed perspective on: {raw_input[:60]}",
        "hook_approach": "bold_claim",
        "key_points": ["Key insight 1 from experience", "Data or statistic", "Actionable takeaway"],
        "research_needed": True,
        "research_query": f"{raw_input} statistics trends 2025",
        "structure": "numbered_list",
        "estimated_word_count": 220 if platform == "linkedin" else 100,
        "cta_approach": "question",
        "persona_notes": "Keep it conversational, use first-person. Start with a bold claim."
    }


# ---------------------------------------------------------------------------
# Model Auto-Routing (Underboss upgrade)
# ---------------------------------------------------------------------------

# Routing table: task_type -> quality_tier -> (provider, model)
_ROUTING_TABLE: Dict[str, Dict[str, tuple]] = {
    "strategy": {
        "budget":  ("openai", "gpt-4o-mini"),
        "standard": ("openai", "gpt-4o"),
        "premium": ("openai", "gpt-4o"),
    },
    "creative_writing": {
        "budget":  ("openai", "gpt-4o"),
        "standard": ("anthropic", "claude-sonnet-4-20250514"),
        "premium": ("anthropic", "claude-sonnet-4-20250514"),
    },
    "analysis": {
        "budget":  ("openai", "gpt-4o-mini"),
        "standard": ("openai", "gpt-4o-mini"),
        "premium": ("openai", "gpt-4o"),
    },
    "scoring": {
        "budget":  ("openai", "gpt-4o-mini"),
        "standard": ("openai", "gpt-4o-mini"),
        "premium": ("openai", "gpt-4o-mini"),
    },
    "research": {
        "budget":  ("perplexity", "sonar-pro"),
        "standard": ("perplexity", "sonar-pro"),
        "premium": ("perplexity", "sonar-pro"),
    },
    "vision": {
        "budget":  ("openai", "gpt-4o"),
        "standard": ("openai", "gpt-4o"),
        "premium": ("openai", "gpt-4o"),
    },
    "debate": {
        "budget":  ("openai", "gpt-4o-mini"),
        "standard": ("openai", "gpt-4o"),
        "premium": ("openai", "gpt-4o"),
    },
}

# Fallback chain: if preferred provider is unavailable, try these in order
_FALLBACK_CHAIN: Dict[str, List[tuple]] = {
    "openai":    [("anthropic", "claude-sonnet-4-20250514"), ("google", "gemini-pro")],
    "anthropic": [("openai", "gpt-4o"), ("google", "gemini-pro")],
    "google":    [("openai", "gpt-4o"), ("anthropic", "claude-sonnet-4-20250514")],
    "perplexity": [("openai", "gpt-4o"), ("anthropic", "claude-sonnet-4-20250514")],
}


def _is_provider_available(provider: str) -> bool:
    """Check if a given provider has valid API keys configured."""
    if provider == "openai":
        return openai_available()
    if provider == "anthropic":
        return anthropic_available()
    if provider == "google":
        return gemini_available()
    if provider == "perplexity":
        return strip_valid_key(settings.llm.perplexity_key)
    return False


def get_available_providers() -> Dict[str, List[str]]:
    """Returns dict of available providers and their supported models.

    Example return::

        {
            "openai": ["gpt-4o", "gpt-4o-mini"],
            "anthropic": ["claude-sonnet-4-20250514"],
        }
    """
    providers: Dict[str, List[str]] = {}

    if openai_available():
        providers["openai"] = ["gpt-4o", "gpt-4o-mini"]

    if anthropic_available():
        providers["anthropic"] = ["claude-sonnet-4-20250514"]

    if gemini_available():
        providers["google"] = ["gemini-pro"]

    if strip_valid_key(settings.llm.perplexity_key):
        providers["perplexity"] = ["sonar-pro"]

    return providers


async def select_optimal_model(
    task_type: str,
    quality_tier: str = "standard",
) -> dict:
    """Model Auto-Routing: Commander selects optimal LLM model per task.

    Args:
        task_type: One of ``"strategy"`` | ``"creative_writing"`` |
            ``"analysis"`` | ``"scoring"`` | ``"research"`` | ``"vision"`` |
            ``"debate"``.
        quality_tier: ``"budget"`` | ``"standard"`` | ``"premium"``.

    Returns:
        A dict with keys ``provider``, ``model``, and ``reasoning``::

            {
                "provider": "openai" | "anthropic" | "google" | "perplexity",
                "model": str,
                "reasoning": str,
            }

    Routing logic:
        - strategy (Commander): openai/gpt-4o (standard), gpt-4o-mini (budget)
        - creative_writing (Writer): anthropic/claude-sonnet-4-20250514
          (standard+premium), gpt-4o (budget)
        - analysis (Thinker): openai/gpt-4o-mini (budget+standard),
          gpt-4o (premium)
        - scoring (QC, Viral): openai/gpt-4o-mini (all tiers)
        - research (Scout): perplexity/sonar-pro (all tiers) -- special marker
        - vision (Visual): openai/gpt-4o (all tiers)
        - debate (Hook debate, Consigliere): openai/gpt-4o-mini (budget),
          gpt-4o (standard+premium)

    If the preferred provider is unavailable the function walks a fallback
    chain and returns the first available alternative.
    """
    # Normalise inputs
    task_type = task_type.lower().strip()
    quality_tier = quality_tier.lower().strip()

    if task_type not in _ROUTING_TABLE:
        logger.warning(
            "Unknown task_type '%s' for model routing, defaulting to 'strategy'",
            task_type,
        )
        task_type = "strategy"

    if quality_tier not in ("budget", "standard", "premium"):
        logger.warning(
            "Unknown quality_tier '%s', defaulting to 'standard'",
            quality_tier,
        )
        quality_tier = "standard"

    tier_map = _ROUTING_TABLE[task_type]
    preferred_provider, preferred_model = tier_map[quality_tier]

    # Check if the preferred provider is available
    if _is_provider_available(preferred_provider):
        return {
            "provider": preferred_provider,
            "model": preferred_model,
            "reasoning": (
                f"Primary route: {preferred_provider}/{preferred_model} "
                f"selected for {task_type} at {quality_tier} tier"
            ),
        }

    # Walk the fallback chain
    fallbacks = _FALLBACK_CHAIN.get(preferred_provider, [])
    for fb_provider, fb_model in fallbacks:
        if _is_provider_available(fb_provider):
            logger.info(
                "Model routing fallback: %s unavailable for %s, using %s/%s",
                preferred_provider,
                task_type,
                fb_provider,
                fb_model,
            )
            return {
                "provider": fb_provider,
                "model": fb_model,
                "reasoning": (
                    f"Fallback route: {preferred_provider} unavailable, "
                    f"using {fb_provider}/{fb_model} for {task_type} "
                    f"at {quality_tier} tier"
                ),
            }

    # Last resort: return the preferred selection anyway and let the caller
    # handle the missing-key error at call time.
    logger.error(
        "No LLM provider available for task_type=%s tier=%s. "
        "Returning preferred (%s/%s) — caller will likely fail.",
        task_type,
        quality_tier,
        preferred_provider,
        preferred_model,
    )
    return {
        "provider": preferred_provider,
        "model": preferred_model,
        "reasoning": (
            f"No provider available. Returning default {preferred_provider}/"
            f"{preferred_model} for {task_type} — caller should handle failure."
        ),
    }
