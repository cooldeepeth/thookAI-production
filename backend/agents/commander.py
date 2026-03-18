import os, json, asyncio, uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')


def _valid(key: str) -> bool:
    return bool(key) and not any(key.startswith(p) for p in ['placeholder', 'sk-placeholder', 'sk-ant-placeholder'])


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


async def run_commander(raw_input: str, platform: str, content_type: str, persona_card: dict) -> dict:
    if not _valid(LLM_KEY):
        return _mock_commander(raw_input, platform, content_type)
    try:
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"cmd-{uuid.uuid4().hex[:8]}",
            system_message=COMMANDER_SYSTEM
        ).with_model("openai", "gpt-4o")

        prompt = COMMANDER_PROMPT.format(
            voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional content creator"),
            content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
            audience_profile=persona_card.get("inferred_audience_profile", "Professionals"),
            hook_style=persona_card.get("hook_style", "Bold statement"),
            content_goal=persona_card.get("content_goal", "Build personal brand"),
            platform=platform, content_type=content_type, raw_input=raw_input
        )
        response = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=20.0)
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
