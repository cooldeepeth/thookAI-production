import asyncio
import uuid
import logging
from services.llm_client import LlmChat, UserMessage
from services.llm_keys import anthropic_available, chat_constructor_key

logger = logging.getLogger(__name__)

PLATFORM_RULES = {
    "linkedin": "LinkedIn post (max 3000 chars). Use line breaks generously. No hashtag spam — max 3-5 relevant hashtags at the end.",
    "x": "X (Twitter) post or thread. Single tweet = max 280 chars. Thread: number each tweet '1/ 2/ 3/' etc. Be punchy and direct.",
    "instagram": "Instagram caption (max 2200 chars). Can use more hashtags (10-15). Emoji use is acceptable. End with call-to-action.",
}

# Regional English configuration for Writer agent
REGIONAL_ENGLISH_RULES = {
    "US": {
        "name": "American English",
        "rules": """REGIONAL ENGLISH: American English (US)
- Use American spellings: optimize, analyze, color, favor, theater, center
- Date format: Month Day, Year (e.g., March 15, 2025)
- Numbers: 1,000,000 with commas as thousand separators
- Standard American expressions and idioms
- Write in a direct, conversational American style""",
    },
    "UK": {
        "name": "British English",
        "rules": """REGIONAL ENGLISH: British English (UK)
- Use British spellings: optimise, analyse, colour, favour, theatre, centre
- Date format: Day Month Year (e.g., 15 March 2025)
- Numbers: 1,000,000 with commas as thousand separators
- Use British expressions: whilst, amongst, towards, learnt, dreamt
- Write in a polished British style, slightly more formal than American""",
    },
    "AU": {
        "name": "Australian English",
        "rules": """REGIONAL ENGLISH: Australian English (AU)
- Use Australian spellings (similar to British): optimise, analyse, colour
- Date format: Day Month Year (e.g., 15 March 2025)
- Numbers: 1,000,000 with commas as thousand separators
- Include occasional Australian colloquialisms where appropriate: arvo (afternoon), brekkie (breakfast), reckon
- Write in a friendly, approachable Australian style - casual but professional""",
    },
    "IN": {
        "name": "Indian English",
        "rules": """REGIONAL ENGLISH: Indian English (IN)
- Use British spellings: optimise, analyse, colour, favour
- Date format: Day Month Year (e.g., 15 March 2025)
- For large numbers, use Indian numbering: lakh (1,00,000 = 100,000), crore (1,00,00,000 = 10,000,000)
- Write in a formal register - avoid very casual contractions (use "do not" instead of "don't" where appropriate)
- Use formal but accessible language suitable for professional Indian audience""",
    },
}

WRITER_SYSTEM = """You are the Writer Agent for ThookAI. Your job is to write content that sounds EXACTLY like the creator — not like AI.

ABSOLUTE RULES:
- Write in FIRST PERSON as the creator
- NEVER use: "In conclusion", "In today's world", "It's no secret", "game-changer", "revolutionary", "synergy", "leverage"  
- NO corporate speak, NO AI-speak, NO generic phrases
- Sound like a real human with opinions and experience
- Return ONLY the content — no labels, no explanations, no meta-commentary
- STRICTLY FOLLOW the regional English rules provided — spellings, date formats, and expressions must match"""

WRITER_PROMPT = """Write content for {creator_name}.

CREATOR VOICE — NON-NEGOTIABLE:
Voice Descriptor: {voice_descriptor}
Tone: {tone}
Hook Style: {hook_style}
Style Notes:
{style_notes}

{regional_english_rules}
{style_examples_section}
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


def _get_regional_rules(regional_english: str) -> str:
    """Get the regional English rules for the writer prompt."""
    config = REGIONAL_ENGLISH_RULES.get(regional_english, REGIONAL_ENGLISH_RULES["US"])
    return config["rules"]


async def _fetch_style_examples(user_id: str, raw_input: str, platform: str) -> str:
    """Retrieve similar past approved content from the vector store to use as style reference.

    Returns a formatted string block ready to inject into the writer prompt.
    If the vector store is unavailable or no results are found, returns an empty string.
    """
    if not user_id:
        return ""

    try:
        from services.vector_store import query_similar_content

        results = await query_similar_content(
            user_id=user_id,
            query_text=raw_input,
            top_k=3,
            similarity_threshold=0.65,
        )

        if not results:
            return ""

        # Filter to same platform when possible, but keep cross-platform as fallback
        platform_matches = [r for r in results if r.get("metadata", {}).get("platform") == platform]
        chosen = platform_matches or results

        example_lines = []
        for i, item in enumerate(chosen[:3], 1):
            preview = item.get("metadata", {}).get("content_preview", "")
            if preview:
                example_lines.append(f"Example {i}:\n{preview}")

        if not example_lines:
            return ""

        return (
            "PREVIOUSLY APPROVED CONTENT IN THIS VOICE (match this style closely):\n"
            + "\n---\n".join(example_lines)
            + "\n"
        )
    except Exception as e:
        logger.warning(f"Vector store retrieval failed (non-fatal): {e}")
        return ""


async def run_writer(
    platform: str,
    content_type: str,
    commander_output: dict,
    scout_output: dict,
    thinker_output: dict,
    persona_card: dict,
    media_system_suffix: str = "",
    user_id: str = "",
) -> dict:
    # Fetch UOM directives for the Writer agent (non-fatal)
    uom_directives = {}
    if user_id:
        try:
            from services.uom_service import get_agent_directives
            uom_directives = await get_agent_directives(user_id, "writer")
        except Exception:
            pass

    if not anthropic_available():
        return _mock_writer(platform, content_type, persona_card)
    try:
        style_notes = "\n".join(f"- {n}" for n in (persona_card.get("writing_style_notes") or ["Write with authenticity and directness"]))
        structure_text = "\n".join(
            f"• {s['section']}: {s['guidance']}"
            for s in (thinker_output.get("content_structure") or [])
        )

        # Get regional English setting from persona card
        regional_english = persona_card.get("regional_english", "US")
        regional_rules = _get_regional_rules(regional_english)

        # Retrieve similar past approved content from vector store for style reference
        raw_input = commander_output.get("raw_input", commander_output.get("primary_angle", ""))
        style_examples_section = await _fetch_style_examples(user_id, raw_input, platform)

        system_msg = WRITER_SYSTEM
        if media_system_suffix:
            system_msg = f"{WRITER_SYSTEM}\n\n{media_system_suffix}"

        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"writer-{uuid.uuid4().hex[:8]}",
            system_message=system_msg,
        ).with_model("anthropic", "claude-sonnet-4-20250514")  # FIXED: correct model name

        prompt = WRITER_PROMPT.format(
            creator_name=persona_card.get("creator_name", "the creator"),
            voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional thought leader"),
            tone=persona_card.get("tone", "Professional yet conversational"),
            hook_style=persona_card.get("hook_style", "Bold statement"),
            regional_english_rules=regional_rules,
            style_examples_section=style_examples_section,
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

        # Inject UOM adaptive style directives when available
        if uom_directives:
            uom_section = (
                "\n\nADAPTIVE STYLE DIRECTIVES:"
                f"\n- Tone intensity: {uom_directives.get('tone_intensity', 'confident')}"
                f"\n- Vocabulary depth: {uom_directives.get('vocabulary_depth', 'intermediate')}"
                f"\n- Content length preference: {uom_directives.get('content_length', 'standard')}"
                f"\n- Emotional energy: {uom_directives.get('emotional_energy', 'moderate')}"
                f"\n- CTA style: {uom_directives.get('cta_aggressiveness', 'moderate')}"
            )
            prompt = prompt + uom_section
            logger.info("UOM adaptive style directives injected into Writer prompt")

        draft = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=30.0)
        word_count = len(draft.split())
        return {"draft": draft.strip(), "word_count": word_count, "character_count": len(draft), "platform": platform, "regional_english": regional_english}
    except Exception as e:
        logger.error("Writer agent failed, using mock: %s", e)
        return _mock_writer(platform, content_type, persona_card)


def _mock_writer(platform: str, content_type: str, persona_card: dict) -> str:
    niche = persona_card.get("content_niche_signature", "professional growth")
    regional_english = persona_card.get("regional_english", "US")
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
    return {"draft": draft, "word_count": len(draft.split()), "character_count": len(draft), "platform": platform, "regional_english": regional_english}
