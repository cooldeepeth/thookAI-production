import os, json, asyncio, uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')


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


async def run_thinker(raw_input: str, commander_output: dict, scout_output: dict, persona_card: dict) -> dict:
    if not _valid(LLM_KEY):
        return _mock_thinker(raw_input, commander_output)
    try:
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"thinker-{uuid.uuid4().hex[:8]}",
            system_message="You are the Thinker Agent for ThookAI. Return only valid JSON, no markdown."
        ).with_model("openai", "o4-mini")

        prompt = THINKER_PROMPT.format(
            raw_input=raw_input,
            commander_summary=commander_output.get("primary_angle", ""),
            research_summary=scout_output.get("findings", "")[:500],
            content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
            platform=commander_output.get("content_type", "post")
        )
        response = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=25.0)
        return json.loads(_clean_json(response))
    except Exception:
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
