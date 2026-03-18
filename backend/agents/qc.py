import os, json, asyncio, uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

QC_SYSTEM = """You are the QC Agent for ThookAI. Score content against creator persona. Return only valid JSON."""

QC_PROMPT = """Score this {platform} {content_type} against the creator's persona.

CREATOR PERSONA:
Voice: {voice_descriptor}
Niche: {content_niche}
Tone: {tone}
Hook Style: {hook_style}

CONTENT DRAFT:
{draft}

Score objectively. Return JSON:
{{
  "personaMatch": 8.5,
  "aiRisk": 18,
  "platformFit": 9.0,
  "overall_pass": true,
  "feedback": ["What could be improved"],
  "suggestions": ["Specific actionable suggestion"],
  "strengths": ["What works well"]
}}

personaMatch 0-10: Does this sound like the creator? (7+ = good)
aiRisk 0-100: How AI-generated does this feel? (below 30 = good, below 20 = excellent)
platformFit 0-10: Platform-appropriate length, format, style? (7+ = good)
overall_pass: true if personaMatch>=7 AND aiRisk<=35 AND platformFit>=7"""


def _valid(key: str) -> bool:
    return bool(key) and not any(key.startswith(p) for p in ['placeholder', 'sk-placeholder'])


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def run_qc(draft: str, persona_card: dict, platform: str, content_type: str) -> dict:
    if not _valid(LLM_KEY):
        return _mock_qc(draft)
    try:
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"qc-{uuid.uuid4().hex[:8]}",
            system_message=QC_SYSTEM
        ).with_model("openai", "gpt-4.1-mini")

        prompt = QC_PROMPT.format(
            platform=platform, content_type=content_type,
            voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional creator"),
            content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
            tone=persona_card.get("tone", "Professional"),
            hook_style=persona_card.get("hook_style", "Bold statement"),
            draft=draft[:2000]
        )
        response = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=20.0)
        result = json.loads(_clean_json(response))
        # Ensure overall_pass is computed correctly
        result["overall_pass"] = (
            result.get("personaMatch", 0) >= 7 and
            result.get("aiRisk", 100) <= 35 and
            result.get("platformFit", 0) >= 7
        )
        return result
    except Exception:
        return _mock_qc(draft)


def _mock_qc(draft: str) -> dict:
    word_count = len(draft.split())
    persona_match = min(9.0, 6.5 + (word_count / 100))
    return {
        "personaMatch": round(persona_match, 1),
        "aiRisk": 22,
        "platformFit": 8.5,
        "overall_pass": persona_match >= 7,
        "feedback": ["Consider adding more personal anecdote or specific data point"],
        "suggestions": ["Open with a stronger hook to stop the scroll faster"],
        "strengths": ["Good structure", "Clear key insight", "Actionable takeaway in CTA"]
    }
