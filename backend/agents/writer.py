import os
import asyncio
import uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

PLATFORM_RULES = {
    "linkedin": "LinkedIn post (max 3000 chars). Use line breaks generously. No hashtag spam — max 3-5 relevant hashtags at the end.",
    "x": "X (Twitter) post or thread. Single tweet = max 280 chars. Thread: number each tweet '1/ 2/ 3/' etc. Be punchy and direct.",
    "instagram": "Instagram caption (max 2200 chars). Can use more hashtags (10-15). Emoji use is acceptable. End with call-to-action.",
}

WRITER_SYSTEM = """You are the Writer Agent for ThookAI. Your job is to write content that sounds EXACTLY like the creator — not like AI.

ABSOLUTE RULES:
- Write in FIRST PERSON as the creator
- NEVER use: "In conclusion", "In today's world", "It's no secret", "game-changer", "revolutionary", "synergy", "leverage"  
- NO corporate speak, NO AI-speak, NO generic phrases
- Sound like a real human with opinions and experience
- Return ONLY the content — no labels, no explanations, no meta-commentary"""

WRITER_PROMPT = """Write content for {creator_name}.

CREATOR VOICE — NON-NEGOTIABLE:
Voice Descriptor: {voice_descriptor}
Tone: {tone}
Hook Style: {hook_style}
English Style: {regional_english}
Style Notes:
{style_notes}

CONTENT STRATEGY (follow this precisely):
Angle: {angle}
Hook to Use: {hook}
Structure:
{structure}
Key Insight to Land: {key_insight}
CTA: {cta_approach}

SUPPORTING RESEARCH (use specific data points):
{research}

PLATFORM FORMAT: {platform_rules}
Target: ~{word_count} words

Write the content now. Only output the content itself."""


def _valid(key: str) -> bool:
    return bool(key) and not any(key.startswith(p) for p in ['placeholder', 'sk-placeholder', 'sk-ant-placeholder'])


async def run_writer(platform: str, content_type: str, commander_output: dict,
                     scout_output: dict, thinker_output: dict, persona_card: dict) -> dict:
    if not _valid(LLM_KEY):
        return _mock_writer(platform, content_type, persona_card)
    try:
        style_notes = "\n".join(f"- {n}" for n in (persona_card.get("writing_style_notes") or ["Write with authenticity and directness"]))
        structure_text = "\n".join(
            f"• {s['section']}: {s['guidance']}"
            for s in (thinker_output.get("content_structure") or [])
        )

        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"writer-{uuid.uuid4().hex[:8]}",
            system_message=WRITER_SYSTEM
        ).with_model("anthropic", "claude-4-sonnet-20250514")

        prompt = WRITER_PROMPT.format(
            creator_name=persona_card.get("creator_name", "the creator"),
            voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional thought leader"),
            tone=persona_card.get("tone", "Professional yet conversational"),
            hook_style=persona_card.get("hook_style", "Bold statement"),
            regional_english=persona_card.get("regional_english", "US"),
            style_notes=style_notes,
            angle=thinker_output.get("angle", commander_output.get("primary_angle", "")),
            hook=thinker_output.get("hook_options", [""])[0],
            structure=structure_text,
            key_insight=thinker_output.get("key_insight", ""),
            cta_approach=commander_output.get("cta_approach", "question"),
            research=scout_output.get("findings", "")[:800],
            platform_rules=PLATFORM_RULES.get(platform.lower(), PLATFORM_RULES["linkedin"]),
            word_count=commander_output.get("estimated_word_count", 200)
        )
        draft = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=30.0)
        word_count = len(draft.split())
        return {"draft": draft.strip(), "word_count": word_count, "character_count": len(draft), "platform": platform}
    except Exception:
        return _mock_writer(platform, content_type, persona_card)


def _mock_writer(platform: str, content_type: str, persona_card: dict) -> str:
    niche = persona_card.get("content_niche_signature", "professional growth")
    voice = persona_card.get("writing_voice_descriptor", "thought leader")
    if platform.lower() == "x":
        draft = (
            f"Most people think {niche} is about working harder.\n\n"
            f"It's not.\n\n"
            f"After years of experience, I've learned it's about working smarter:\n\n"
            f"1/ Know your leverage points\n"
            f"2/ Remove friction before adding features\n"
            f"3/ Measure what matters, not what's easy to measure\n\n"
            f"What's your biggest insight about {niche}?"
        )
    elif platform.lower() == "instagram":
        draft = (
            f"Here's what nobody tells you about {niche}...\n\n"
            f"The secret isn't in the tactics. It's in the fundamentals.\n\n"
            f"I've spent years studying what actually works vs what just sounds good.\n\n"
            f"The answer is always simpler than you think.\n\n"
            f"What's your experience been?\n\n"
            f"#thoughtleadership #growthmindset #professionaldevelopment"
        )
    else:
        draft = (
            f"Most people are thinking about {niche} completely backwards.\n\n"
            f"I used to think the same way. Then I noticed something:\n\n"
            f"The most effective professionals don't focus on doing more.\n"
            f"They focus on removing what doesn't matter.\n\n"
            f"Here's what changed my perspective:\n\n"
            f"1. Results come from clarity, not effort\n"
            f"2. The best work is often the work you decide not to do\n"
            f"3. Consistency beats intensity every single time\n\n"
            f"The counterintuitive truth: Less, but better.\n\n"
            f"What's the one thing you've stopped doing that made everything else easier?"
        )
    return {"draft": draft, "word_count": len(draft.split()), "character_count": len(draft), "platform": platform}
