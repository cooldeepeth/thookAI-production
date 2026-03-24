import json
import asyncio
import uuid
from typing import List, Optional

from services.llm_client import LlmChat, UserMessage
from services.llm_keys import chat_constructor_key, openai_available


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
    if not openai_available():
        return _mock_commander(raw_input, platform, content_type)
    try:
        system_msg = COMMANDER_SYSTEM
        if media_system_suffix:
            system_msg = f"{COMMANDER_SYSTEM}\n\n{media_system_suffix}"

        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"cmd-{uuid.uuid4().hex[:8]}",
            system_message=system_msg,
        ).with_model("openai", "gpt-4o")

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
    except Exception:
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
