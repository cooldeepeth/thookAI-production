"""Viral Persona Card — Public endpoint for ThookAI growth funnel.

Anyone (no signup required) can paste their posts and receive a beautiful,
shareable persona card.  Cards are stored in ``db.viral_cards`` with a 30-day
TTL so they auto-expire.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import db
import json
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viral-card", tags=["viral-card"])


# ─── Request / Response Models ────────────────────────────

ALLOWED_PLATFORMS = {"linkedin", "x", "instagram", "general"}


class ViralCardRequest(BaseModel):
    posts_text: str  # User's posts (separated by blank lines)
    platform: str = "general"  # linkedin, x, instagram, general
    name: Optional[str] = None  # Optional display name


# ─── Endpoints ────────────────────────────────────────────

@router.post("/analyze")
async def generate_viral_card(data: ViralCardRequest):
    """
    PUBLIC endpoint (no auth).  Analyzes pasted posts and generates
    a shareable persona card.  This is the viral growth funnel.

    TODO (Phase 2): Add IP-based rate limiting to protect against abuse of
    the downstream LLM call.  This endpoint currently has no rate limit.
    Implement via Redis-backed middleware in backend/middleware/security.py
    (e.g., 5 requests/IP/hour).  Tracked in infra backlog.
    """
    if data.platform not in ALLOWED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform '{data.platform}'. Must be one of: {sorted(ALLOWED_PLATFORMS)}",
        )

    posts = data.posts_text.strip()
    if len(posts) < 100:
        raise HTTPException(
            status_code=400,
            detail="Please paste at least 100 characters of your content",
        )
    if len(posts) > 10000:
        posts = posts[:10000]  # Cap at 10K chars

    # ── LLM analysis ──────────────────────────────────────
    from services.llm_client import LlmChat, UserMessage
    from services.llm_keys import chat_constructor_key, anthropic_available

    card = None
    if anthropic_available():
        try:
            chat = LlmChat(
                api_key=chat_constructor_key(),
                session_id=f"viral-{uuid.uuid4().hex[:8]}",
                system_message=(
                    "You are a content strategist. Analyze writing samples "
                    "and create a persona profile. Return ONLY valid JSON."
                ),
            ).with_model("anthropic", "claude-sonnet-4-20250514")

            prompt = f"""Analyze these content samples and create a creator persona card.

CONTENT SAMPLES:
{posts[:5000]}

PLATFORM: {data.platform}

Return JSON:
{{
    "writing_voice_descriptor": "2-3 word voice style (e.g., 'Bold Strategist', 'Warm Storyteller')",
    "content_niche_signature": "Their content niche in one phrase",
    "personality_archetype": "Educator | Storyteller | Provocateur | Builder | Entertainer",
    "tone": "The overall tone (e.g., 'Professional yet conversational')",
    "hook_style": "Their preferred hook approach",
    "top_content_format": "Their best format (e.g., 'Thought leadership posts')",
    "content_pillars": ["pillar1", "pillar2", "pillar3"],
    "strengths": ["strength1", "strength2", "strength3"],
    "voice_metrics": {{
        "sentence_rhythm": 65,
        "vocabulary_depth": 70,
        "emoji_usage": 20,
        "hook_strength": 75,
        "cta_clarity": 60
    }},
    "audience_vibe": "Who their content resonates with"
}}"""

            import asyncio

            response = await asyncio.wait_for(
                chat.send_message(UserMessage(text=prompt)),
                timeout=30.0,
            )

            # Clean markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                cleaned = cleaned.rsplit("```", 1)[0]
            card = json.loads(cleaned)
        except Exception as e:
            logger.exception("Viral card LLM analysis failed, falling back to heuristic")

    # ── Smart fallback — basic heuristic analysis ─────────
    if not card:
        word_count = len(posts.split())
        avg_word_len = (
            sum(len(w) for w in posts.split()) / max(word_count, 1)
        )
        has_questions = posts.count("?") > 1
        has_lists = any(c in posts for c in ["1.", "2.", "-", "•"])

        archetype = "Builder"
        if has_questions and has_lists:
            archetype = "Educator"
        elif posts.count("I ") > 5 or posts.count("my ") > 3:
            archetype = "Storyteller"
        elif posts.count("!") > 3:
            archetype = "Provocateur"

        card = {
            "writing_voice_descriptor": "Authentic Creator",
            "content_niche_signature": f"{data.platform.title()} Content Creator",
            "personality_archetype": archetype,
            "tone": "Conversational",
            "hook_style": "Direct statement",
            "top_content_format": "Short-form posts",
            "content_pillars": [
                "Personal insights",
                "Industry knowledge",
                "Storytelling",
            ],
            "strengths": [
                "Authentic voice",
                "Consistent output",
                "Engaging style",
            ],
            "voice_metrics": {
                "sentence_rhythm": min(80, 40 + word_count // 20),
                "vocabulary_depth": min(85, int(avg_word_len * 10)),
                "emoji_usage": min(60, posts.count(":") * 5 + 15),
                "hook_strength": 65 if has_questions else 55,
                "cta_clarity": 50,
            },
            "audience_vibe": "Professionals and fellow creators",
        }

    # ── Persist card ──────────────────────────────────────
    card_id = f"vc_{uuid.uuid4().hex[:12]}"

    await db.viral_cards.insert_one(
        {
            "card_id": card_id,
            "card": card,
            "name": data.name or "Creator",
            "platform": data.platform,
            "posts_preview": posts[:200],
            "created_at": datetime.now(timezone.utc),
        }
    )

    return {
        "success": True,
        "card_id": card_id,
        "card": card,
        "share_url": f"/discover/{card_id}",
        "name": data.name or "Creator",
    }


@router.get("/{card_id}")
async def get_viral_card(card_id: str):
    """Public endpoint to retrieve a previously generated viral card."""
    doc = await db.viral_cards.find_one({"card_id": card_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Card not found or expired")
    return {"success": True, **doc}
