import json
import asyncio
import logging
import uuid
from typing import Optional
from services.llm_client import LlmChat, UserMessage
from services.llm_keys import chat_constructor_key, openai_available, anthropic_available

logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


THINKER_PROMPT = """You are the Thinker Agent — you turn content briefs into sharp content strategies.

Topic: {raw_input}
Commander's Plan: {commander_summary}
Research Available: {research_summary}
Creator Niche: {content_niche}
Platform: {platform}

Build the optimal content strategy. Return JSON only:
{{
  "angle": "The precise, differentiated angle to take",
  "hook_options": [
    "Hook option 1 (bold claim style)",
    "Hook option 2 (question or stat style)"
  ],
  "content_structure": [
    {{"section": "Hook", "guidance": "What to say and how"}},
    {{"section": "Body", "guidance": "Main content direction"}},
    {{"section": "Insight", "guidance": "The key takeaway to land"}},
    {{"section": "CTA", "guidance": "How to close"}}
  ],
  "key_insight": "The single most important idea to communicate",
  "differentiation": "What makes this specific take unique and non-generic"
}}"""


def _build_fatigue_prompt_section(fatigue_context: Optional[dict]) -> str:
    """Build a prompt section from fatigue shield data to inject into the Thinker prompt.

    Returns an empty string when there is nothing to constrain.
    """
    if not fatigue_context:
        return ""

    # The fatigue shield uses "shield_status" to indicate severity.
    # Only inject constraints when there is a real signal.
    status = fatigue_context.get("shield_status", "healthy")
    if status == "healthy":
        return ""

    risk_factors = fatigue_context.get("risk_factors", [])
    recommendations = fatigue_context.get("recommendations", [])

    overused_patterns = []
    for factor in risk_factors:
        detail = factor.get("detail", "")
        if detail:
            overused_patterns.append(detail)

    if not overused_patterns and not recommendations:
        return ""

    lines = [
        "\nCONTENT DIVERSITY CONSTRAINTS (do not ignore these):",
        "The following patterns have been overused recently and MUST be avoided:",
    ]
    for pattern in overused_patterns:
        lines.append(f"- {pattern}")

    if recommendations:
        lines.append("\nPrioritise fresh angles and underused formats instead:")
        for rec in recommendations:
            lines.append(f"- {rec}")

    return "\n".join(lines)


async def run_thinker(
    raw_input: str,
    commander_output: dict,
    scout_output: dict,
    persona_card: dict,
    fatigue_context: Optional[dict] = None,
    user_id: str = "",
) -> dict:
    # Fetch UOM directives for the Thinker agent (non-fatal)
    uom_directives = {}
    if user_id:
        try:
            from services.uom_service import get_agent_directives
            uom_directives = await get_agent_directives(user_id, "thinker")
        except Exception:
            pass

    # Fetch knowledge graph context for topic gap analysis (non-fatal)
    # NOTE: query_knowledge_graph enforces per-user isolation via storage-level
    # doc_filter_func — only documents tagged with CREATOR:{user_id} are retrieved
    knowledge_context = ""
    if user_id:
        try:
            from services.lightrag_service import query_knowledge_graph
            knowledge_context = await query_knowledge_graph(
                user_id=user_id,
                topic=raw_input,
                mode="hybrid",
            )
        except Exception:
            pass  # Non-fatal — proceed without graph context

    if not openai_available() and not anthropic_available():
        return _mock_thinker(raw_input, commander_output)
    try:
        provider = "openai" if openai_available() else "anthropic"
        model = "gpt-4o-mini" if provider == "openai" else "claude-sonnet-4-20250514"
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"thinker-{uuid.uuid4().hex[:8]}",
            system_message="You are the Thinker Agent for ThookAI. Return only valid JSON, no markdown."
        ).with_model(provider, model)

        prompt = THINKER_PROMPT.format(
            raw_input=raw_input,
            commander_summary=commander_output.get("primary_angle", ""),
            research_summary=scout_output.get("findings", "")[:500],
            content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
            platform=commander_output.get("platform", commander_output.get("content_type", "post"))
        )

        # Inject UOM constraints when directives are available
        if uom_directives:
            uom_section = (
                "\n\nUOM CONSTRAINTS:"
                f"\n- Risk level: {uom_directives.get('risk_level', 'medium')}"
                f"\n- Hook complexity: {uom_directives.get('hook_complexity', 'advanced')}"
                f"\n- Maximum hook options: {uom_directives.get('max_options', 3)}"
            )
            prompt = prompt + uom_section
            logger.info("UOM constraints injected into Thinker prompt")

        # Inject fatigue shield constraints when fatigue is detected
        fatigue_section = _build_fatigue_prompt_section(fatigue_context)
        if fatigue_section:
            prompt = prompt + "\n" + fatigue_section
            logger.info("Fatigue shield constraints injected into Thinker prompt")

        # Inject knowledge graph context for angle gap analysis
        if knowledge_context:
            kg_section = (
                "\n\nKNOWLEDGE GRAPH - TOPICS AND ANGLES ALREADY USED:"
                f"\n{knowledge_context[:800]}"
                "\n\nPrioritise angles, hook archetypes, and emotional tones NOT listed above."
            )
            prompt = prompt + kg_section
            logger.info("Knowledge graph context injected into Thinker prompt")

        response = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=25.0)
        return json.loads(_clean_json(response))
    except Exception as e:
        logger.error("Thinker agent failed, using mock: %s", e)
        return _mock_thinker(raw_input, commander_output)


def _mock_thinker(raw_input: str, commander_output: dict) -> dict:
    angle = commander_output.get("primary_angle", f"A fresh perspective on {raw_input[:40]}")
    return {
        "angle": angle,
        "hook_options": [
            f"Most people get {raw_input[:30]} wrong. Here's what actually works.",
            f"After [X] years, I finally figured out the truth about {raw_input[:30]}."
        ],
        "content_structure": [
            {"section": "Hook", "guidance": "Start with a bold, counter-intuitive claim that stops the scroll"},
            {"section": "Body", "guidance": "3 concrete points backed by the research data"},
            {"section": "Insight", "guidance": "The one sentence that captures the whole lesson"},
            {"section": "CTA", "guidance": "End with a thought-provoking question to drive comments"}
        ],
        "key_insight": f"The most important truth about {raw_input[:40]} that professionals miss",
        "differentiation": "First-person experience combined with data — personal but credible"
    }
