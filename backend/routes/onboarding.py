from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import os
import uuid
from database import db
from auth_utils import get_current_user
from emergentintegrations.llm.chat import LlmChat, UserMessage

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

INTERVIEW_QUESTIONS = [
    {
        "id": 0, "type": "text",
        "question": "Let's start — who are you and what do you create? Tell me in 2-3 sentences.",
        "placeholder": "e.g. I'm a B2B SaaS founder sharing lessons on growing from 0 to $1M ARR...",
        "hint": "Be specific — 'content creator' is too broad. What's your unique angle?"
    },
    {
        "id": 1, "type": "multi_choice",
        "question": "Which platforms are most important to your content strategy right now?",
        "options": ["LinkedIn", "X (Twitter)", "Instagram", "LinkedIn + X", "All three"],
        "hint": "Focus beats presence. Pick where your audience actually lives."
    },
    {
        "id": 2, "type": "text",
        "question": "Describe your content style in exactly 3 words. No more, no less.",
        "placeholder": "e.g. Bold, Strategic, Human",
        "hint": "These 3 words shape your entire voice fingerprint."
    },
    {
        "id": 3, "type": "text",
        "question": "Name 1–2 creators you admire for their content style (not just their success). Why them specifically?",
        "placeholder": "e.g. Lenny Rachitsky — depth + accessibility. Paul Graham for razor-sharp clarity.",
        "hint": "Style admiration is a signal — we extract voice patterns from your choices."
    },
    {
        "id": 4, "type": "text",
        "question": "What topics do you want to NEVER write about — even if they're trending?",
        "placeholder": "e.g. Crypto speculation, hustle culture, politics, corporate jargon...",
        "hint": "Your 'never list' defines your brand as much as your content pillars."
    },
    {
        "id": 5, "type": "multi_choice",
        "question": "What's your primary goal with content creation?",
        "options": ["Grow my audience", "Generate leads/clients", "Build personal brand", "Monetize directly", "All of the above"],
        "hint": "Every agent will optimize outputs for this goal."
    },
    {
        "id": 6, "type": "multi_choice",
        "question": "How much time can you realistically give to content each week?",
        "options": ["Under 1 hour", "1–3 hours", "3–5 hours", "5+ hours"],
        "hint": "Be honest — Thook adjusts your output volume to match your capacity."
    }
]

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

PERSONA_PROMPT = """You are the Persona Agent for ThookAI. Analyze a content creator's interview answers and generate their precise Persona Card.

Creator Interview Answers:
{answers_text}

{posts_context}

Return ONLY valid JSON — no markdown, no explanation, no code blocks. Use this exact structure:
{{
  "writing_voice_descriptor": "5-8 word unique voice (e.g. 'Systems-thinker who narrates the founder journey')",
  "content_niche_signature": "Specific niche (e.g. 'B2B SaaS growth for technical founders')",
  "inferred_audience_profile": "Who reads them (e.g. 'Series A founders, VPs of Engineering, operators')",
  "top_content_format": "Best format for their niche (e.g. 'Long-form LinkedIn posts with numbered frameworks')",
  "personality_archetype": "Educator OR Storyteller OR Provocateur OR Builder",
  "tone": "Primary tone (e.g. 'Professional yet conversational')",
  "regional_english": "US OR UK OR AU OR IN",
  "hook_style": "Signature opening style (e.g. 'Bold statements that challenge common assumptions')",
  "focus_platforms": ["LinkedIn"],
  "content_pillars": ["pillar1", "pillar2", "pillar3"],
  "content_goal": "Their primary content objective in 8 words or less",
  "burnout_risk": "low OR medium OR high",
  "risk_tolerance": "conservative OR balanced OR bold",
  "strategy_maturity": 2,
  "writing_style_notes": ["Specific note about their writing style", "Note about their voice patterns", "Note about their content structure"]
}}

Be specific and authentic based on their actual answers. No generic templates."""


class AnalyzePostsRequest(BaseModel):
    posts_text: str
    platform: Optional[str] = "general"


class GeneratePersonaRequest(BaseModel):
    answers: List[Dict[str, Any]]
    posts_analysis: Optional[str] = None


def _is_placeholder_key(key: str) -> bool:
    return not key or key.startswith('placeholder') or key.startswith('sk-ant-placeholder') or key.startswith('sk-placeholder')


@router.get("/questions")
async def get_questions():
    return {"questions": INTERVIEW_QUESTIONS, "total": len(INTERVIEW_QUESTIONS)}


@router.post("/analyze-posts")
async def analyze_posts(data: AnalyzePostsRequest, current_user: dict = Depends(get_current_user)):
    if _is_placeholder_key(LLM_KEY):
        return {
            "analysis": "We analyzed your posts and detected a clear pattern: data-driven narratives, professional tone, and an insights-heavy format that resonates well with professional audiences.",
            "detected_patterns": ["Strong analytical voice", "Long-form preference", "Education-focused approach"],
            "demo_mode": True
        }
    try:
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"analyze-{current_user['user_id']}-{uuid.uuid4().hex[:8]}",
            system_message="You are an expert content analyst. Analyze writing samples and extract key voice patterns."
        ).with_model("anthropic", "claude-4-sonnet-20250514")

        prompt = f"""Analyze these {data.platform} posts and extract writing patterns:

{data.posts_text[:3000]}

Return a 2-3 sentence analysis covering:
1. Writing voice and tone
2. Content patterns and strengths
3. Distinctive style elements

Be specific and actionable."""
        import asyncio
        response = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=25.0)
        return {"analysis": response, "demo_mode": False}
    except Exception:
        return {
            "analysis": "We analyzed your posts. Your writing has a distinctive analytical voice with a preference for structured insights.",
            "demo_mode": True
        }


@router.post("/generate-persona")
async def generate_persona(data: GeneratePersonaRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]

    answers_text = ""
    for a in data.answers:
        q_id = a.get("question_id", 0)
        question = INTERVIEW_QUESTIONS[q_id]["question"] if q_id < len(INTERVIEW_QUESTIONS) else "Question"
        answers_text += f"Q: {question}\nA: {a.get('answer', '')}\n\n"

    posts_context = f"Additional context from post analysis:\n{data.posts_analysis}" if data.posts_analysis else ""

    persona_card = None

    if not _is_placeholder_key(LLM_KEY):
        try:
            chat = LlmChat(
                api_key=LLM_KEY,
                session_id=f"persona-{user_id}-{uuid.uuid4().hex[:8]}",
                system_message="You are the Persona Agent for ThookAI. Return only valid JSON with no additional text."
            ).with_model("anthropic", "claude-4-sonnet-20250514")

            import asyncio
            prompt = PERSONA_PROMPT.format(answers_text=answers_text, posts_context=posts_context)
            response = await asyncio.wait_for(
                chat.send_message(UserMessage(text=prompt)),
                timeout=30.0
            )

            # Clean up any markdown wrapping
            clean = response.strip()
            if "```" in clean:
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else clean
                if clean.startswith("json"):
                    clean = clean[4:]
            persona_card = json.loads(clean.strip())
        except Exception:
            persona_card = None

    if not persona_card:
        persona_card = _generate_smart_persona(data.answers)

    now = datetime.now(timezone.utc)
    platforms = persona_card.get("focus_platforms", ["LinkedIn"])
    persona_doc = {
        "user_id": user_id,
        "card": persona_card,
        "voice_fingerprint": {
            "sentence_length_distribution": {"short": 0.35, "medium": 0.50, "long": 0.15},
            "vocabulary_complexity": 0.65,
            "emoji_frequency": 0.05,
            "hook_style_preferences": [persona_card.get("hook_style", "")],
            "cta_patterns": ["Follow for more", "What's your experience?", "Drop a comment below"],
        },
        "content_identity": {
            "topic_clusters": persona_card.get("content_pillars", []),
            "tone": persona_card.get("tone", "Professional"),
            "regional_english": persona_card.get("regional_english", "US"),
            "personality_archetype": persona_card.get("personality_archetype", "Educator"),
        },
        "performance_intelligence": {
            "best_performing_formats": {persona_card.get("top_content_format", ""): 1},
            "optimal_posting_times": {},
            "content_pillar_balance": {},
        },
        "learning_signals": {"edit_deltas": [], "approved_embeddings": [], "rejected_patterns": []},
        "uom": {
            "burnout_risk": persona_card.get("burnout_risk", "medium"),
            "focus_preference": "single-platform" if len(platforms) == 1 else "multi-platform",
            "risk_tolerance": persona_card.get("risk_tolerance", "balanced"),
            "cognitive_load_tolerance": "high" if persona_card.get("strategy_maturity", 1) >= 3 else "low",
            "monetization_priority": "high" if "monetize" in persona_card.get("content_goal", "").lower() else "medium",
            "strategy_maturity": persona_card.get("strategy_maturity", 2),
            "trust_in_thook": 0.5,
        },
        "onboarding_answers": data.answers,
        "created_at": now,
        "updated_at": now,
    }

    await db.persona_engines.update_one({"user_id": user_id}, {"$set": persona_doc}, upsert=True)
    await db.users.update_one({"user_id": user_id}, {"$set": {"onboarding_completed": True}})
    return {"persona_card": persona_card, "message": "Persona Engine activated"}


def _generate_smart_persona(answers: list) -> dict:
    """Smart fallback persona generation from interview answers without AI."""
    get_ans = lambda qid: next((a.get("answer", "") for a in answers if a.get("question_id") == qid), "")

    about = get_ans(0)
    platform = get_ans(1)
    style_words = get_ans(2) or "Bold, Clear, Strategic"
    goal = get_ans(5) or "Build personal brand"
    time_avail = get_ans(6) or "1–3 hours"

    archetype = "Educator"
    if any(w in about.lower() for w in ["story", "journey", "experience", "life"]):
        archetype = "Storyteller"
    elif any(w in style_words.lower() for w in ["bold", "provocative", "challenge", "disrupt"]):
        archetype = "Provocateur"
    elif any(w in about.lower() for w in ["build", "founder", "create", "launch", "startup"]):
        archetype = "Builder"

    burnout_risk = "low"
    if "Under 1" in time_avail:
        burnout_risk = "high"
    elif "1–3" in time_avail or "1-3" in time_avail:
        burnout_risk = "medium"

    if "All three" in platform:
        platforms = ["LinkedIn", "X (Twitter)", "Instagram"]
    elif "+" in platform:
        platforms = [p.strip() for p in platform.split("+")]
    else:
        platforms = [platform] if platform else ["LinkedIn"]

    return {
        "writing_voice_descriptor": f"{style_words.replace(',', '–')} content creator",
        "content_niche_signature": "Thought leadership with actionable professional frameworks",
        "inferred_audience_profile": "Professionals and decision-makers seeking practical insights",
        "top_content_format": "Long-form posts with numbered frameworks and personal stories",
        "personality_archetype": archetype,
        "tone": "Professional yet conversational",
        "regional_english": "US",
        "hook_style": "Bold opening statements that challenge conventional thinking",
        "focus_platforms": platforms,
        "content_pillars": ["Industry insights", "Personal lessons", "How-to frameworks", "Behind-the-scenes"],
        "content_goal": goal,
        "burnout_risk": burnout_risk,
        "risk_tolerance": "balanced",
        "strategy_maturity": 2,
        "writing_style_notes": [
            f"Signature style: {style_words}",
            "Values authenticity and depth over surface-level takes",
            "Strong personal POV woven into every piece of content"
        ]
    }
