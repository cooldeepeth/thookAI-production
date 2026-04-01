"""Strategist Agent for ThookAI.

Nightly synthesis engine that reads each user's content history, LightRAG
knowledge graph, and performance signals to produce ranked recommendation
cards stored in db.strategy_recommendations.

This agent is WRITE-ONLY for recommendations — it never triggers content
generation directly. Phase 14's Strategy Dashboard displays the cards and
calls handle_dismissal / handle_approval which carry the generate_payload
for one-click generation.

STRAT requirements addressed:
- STRAT-01: run_strategist_for_all_users / run_strategist_for_user exported
- STRAT-02: All cards written with status="pending_approval"
- STRAT-03: Every card includes a non-empty why_now rationale
- STRAT-04: Atomic cap guard — max 3 cards per user per day
- STRAT-05: Topics dismissed within suppression_days are filtered
- STRAT-06: 5 consecutive dismissals sets halved_rate=True
- STRAT-07: generate_payload matches ContentCreateRequest schema exactly
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from database import db
from config import settings
from services.llm_keys import anthropic_available, chat_constructor_key

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — read from StrategistConfig at module initialisation time
# ---------------------------------------------------------------------------
MAX_CARDS_PER_DAY: int = settings.strategist.max_cards_per_day
SUPPRESSION_DAYS: int = settings.strategist.suppression_days
CONSECUTIVE_DISMISSAL_THRESHOLD: int = settings.strategist.consecutive_dismissal_threshold
MIN_APPROVED_CONTENT: int = settings.strategist.min_approved_content

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

STRATEGIST_SYSTEM_PROMPT = """You are the Strategist Agent for ThookAI — a proactive content intelligence engine.

Your job is to analyse a creator's content history, performance signals, and knowledge graph gaps to surface 1–3 high-value content recommendation cards that the creator has NOT yet explored.

RULES:
1. Return ONLY valid JSON — no markdown code fences, no preamble, no explanation.
2. Output must be a JSON array of recommendation objects.
3. Return between 1 and 3 recommendations.
4. Each recommendation MUST include a clear "why_now" rationale starting with "Why now:".
5. Never recommend a topic that appears in the suppressed_topics list.
6. Focus on unexplored angles, not repetitions of recent content.
7. Match the creator's platform and voice fingerprint.

Each recommendation object MUST have ALL of these keys:
{
  "topic": "concise topic label (5-10 words)",
  "hook_options": ["hook 1", "hook 2", "hook 3"],
  "platform": "linkedin|x|instagram",
  "why_now": "Why now: <clear rationale linking signal to timing>",
  "signal_source": "persona|performance|knowledge_graph|trending",
  "generate_payload": {
    "content_type": "post|carousel|thread|story|reel",
    "raw_input": "Full content brief — topic, angle, hook direction, persona notes"
  }
}

Guidance on why_now:
- Reference performance data when available: "Why now: Your last 3 posts on [topic] averaged 2x your usual engagement"
- Reference knowledge gaps: "Why now: Your knowledge graph shows [entity] is frequently referenced but never directly covered"
- Reference timing/context: "Why now: This topic aligns with your persona pillar [pillar] and you haven't posted on it in 14+ days"
- Be specific, not generic.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_json(raw: str) -> str:
    """Strip markdown code fences from LLM JSON output."""
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def _get_eligible_users() -> List[str]:
    """Return user_ids that have completed onboarding and meet the min approved threshold.

    A user is eligible if:
    - onboarding_completed is True in db.users
    - learning_signals.approved_count >= MIN_APPROVED_CONTENT in db.persona_engines
    """
    eligible: List[str] = []
    try:
        cursor = db.users.find({"onboarding_completed": True}, {"_id": 0, "user_id": 1})
        async for user_doc in cursor:
            user_id = user_doc.get("user_id")
            if not user_id:
                continue
            persona = await db.persona_engines.find_one(
                {"user_id": user_id},
                {"_id": 0, "learning_signals.approved_count": 1},
            )
            if persona is None:
                continue
            approved_count = (
                persona.get("learning_signals", {}).get("approved_count", 0)
            )
            if approved_count >= MIN_APPROVED_CONTENT:
                eligible.append(user_id)
    except Exception as e:
        logger.error("Failed to fetch eligible users: %s", e)
    return eligible


async def _get_cadence_state(user_id: str) -> dict:
    """Return the strategist_state document for this user, or empty dict."""
    try:
        doc = await db.strategist_state.find_one({"user_id": user_id})
        return doc or {}
    except Exception as e:
        logger.warning("Could not fetch cadence state for %s: %s", user_id, e)
        return {}


async def _atomic_claim_card_slot(user_id: str) -> bool:
    """Atomically claim one card slot for today. Returns False if cap reached.

    Uses find_one_and_update to prevent race conditions (STRAT-04).
    Two-phase upsert:
    1. Try to increment today's counter (only succeeds if count < max).
    2. If that fails, try to reset for a new day (only succeeds if date changed).
    If both fail, the daily cap has been reached.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Phase 1: Increment within today's window if below cap
    result = await db.strategist_state.find_one_and_update(
        {
            "user_id": user_id,
            "cards_today_date": today_str,
            "cards_today_count": {"$lt": settings.strategist.max_cards_per_day},
        },
        {"$inc": {"cards_today_count": 1}},
        return_document=True,
    )
    if result is not None:
        return True

    # Phase 2: New day — try to reset date and set count to 1
    result = await db.strategist_state.find_one_and_update(
        {"user_id": user_id, "cards_today_date": {"$ne": today_str}},
        {
            "$set": {"cards_today_date": today_str, "cards_today_count": 1},
            "$setOnInsert": {
                "consecutive_dismissals": 0,
                "halved_rate": False,
                "needs_calibration_prompt": False,
                "suppressed_topics": [],
            },
        },
        upsert=True,
        return_document=True,
    )
    if result is not None:
        return True

    # Both phases failed — cap already reached today
    return False


async def _is_topic_suppressed(user_id: str, topic: str) -> bool:
    """Return True if this topic was dismissed within the suppression window (STRAT-05)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=SUPPRESSION_DAYS)
    normalised = topic.lower()
    try:
        doc = await db.strategy_recommendations.find_one(
            {
                "user_id": user_id,
                "status": "dismissed",
                "dismissed_at": {"$gte": cutoff},
                # Case-insensitive match via $regex
                "topic": {"$regex": f"^{normalised}$", "$options": "i"},
            }
        )
        return doc is not None
    except Exception as e:
        logger.warning(
            "Topic suppression check failed for user %s topic '%s' (non-fatal): %s",
            user_id, topic, e,
        )
        return False


async def _query_content_gaps(user_id: str) -> str:
    """Query LightRAG for unexplored topic domains. Returns empty string on any failure."""
    try:
        from services.lightrag_service import query_knowledge_graph  # lazy import
        return await query_knowledge_graph(
            user_id=user_id,
            topic="content strategy gaps and unexplored topic domains",
            mode="hybrid",
        )
    except Exception as e:
        logger.warning("LightRAG gap query failed for %s (non-fatal): %s", user_id, e)
        return ""


async def _gather_user_context(user_id: str) -> dict:
    """Gather all signals needed for synthesis: persona, recent content, performance, LightRAG."""
    persona = await db.persona_engines.find_one({"user_id": user_id})

    recent_jobs_cursor = db.content_jobs.find(
        {"user_id": user_id, "status": {"$in": ["approved", "published"]}},
        {"_id": 0, "platform": 1, "content_type": 1, "draft": 1, "final_content": 1, "performance_data": 1, "created_at": 1},
    ).sort("created_at", -1)
    recent_jobs = await recent_jobs_cursor.to_list(length=10)

    performance_signals = [
        j.get("performance_data")
        for j in recent_jobs
        if j.get("performance_data")
    ]

    knowledge_gaps = await _query_content_gaps(user_id)

    return {
        "persona": persona,
        "recent_content": recent_jobs,
        "performance_signals": performance_signals,
        "knowledge_gaps": knowledge_gaps,
    }


async def _build_synthesis_prompt(context: dict, suppressed_topics: List[str]) -> str:
    """Build the user-turn prompt for the LLM synthesis call."""
    persona = context.get("persona") or {}
    card = persona.get("card", {})
    voice = persona.get("voice_fingerprint", {})
    identity = persona.get("content_identity", {})

    # Persona summary
    persona_summary = (
        f"Archetype: {card.get('archetype', 'N/A')}\n"
        f"Content pillars: {', '.join(identity.get('content_pillars', []))}\n"
        f"Voice traits: {', '.join(voice.get('traits', []))}\n"
        f"Primary platform: {card.get('primary_platform', 'linkedin')}"
    )

    # Recent content topics
    recent_lines = []
    for job in context.get("recent_content", []):
        platform = job.get("platform", "unknown")
        snippet = (job.get("final_content") or job.get("draft") or "")[:120]
        recent_lines.append(f"- [{platform}] {snippet}")
    recent_summary = "\n".join(recent_lines) if recent_lines else "No recent approved content."

    # Performance signals
    perf_signals = context.get("performance_signals", [])
    if perf_signals:
        perf_summary = json.dumps(perf_signals[:5], default=str)
    else:
        perf_summary = "No performance data available yet — focus on content gaps and persona strengths."

    # Knowledge graph gaps
    knowledge_gaps = context.get("knowledge_gaps", "")
    if not knowledge_gaps:
        kg_section = "No knowledge graph data available — focus on persona and recent content history."
    else:
        kg_section = knowledge_gaps[:800]  # cap to avoid bloating LLM context

    # Suppressed topics
    if suppressed_topics:
        suppressed_section = "SUPPRESSED TOPICS (do NOT recommend these):\n" + "\n".join(
            f"- {t}" for t in suppressed_topics
        )
    else:
        suppressed_section = "No topics currently suppressed."

    return f"""CREATOR PROFILE:
{persona_summary}

RECENT APPROVED CONTENT (last 10 posts):
{recent_summary}

PERFORMANCE SIGNALS:
{perf_summary}

KNOWLEDGE GRAPH GAPS:
{kg_section}

{suppressed_section}

Generate 1–3 high-value recommendation cards for this creator. Follow the JSON schema exactly.
"""


async def _synthesize_recommendations(user_id: str, context: dict, suppressed_topics: List[str]) -> List[dict]:
    """Call LLM to synthesise recommendation cards. Returns empty list on any failure."""
    if not anthropic_available():
        logger.info("Anthropic unavailable — skipping synthesis for %s", user_id)
        return []

    try:
        from services.llm_client import LlmChat, UserMessage  # lazy import consistent with codebase

        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"strategist-{uuid.uuid4().hex[:8]}",
            system_message=STRATEGIST_SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-20250514")

        prompt = await _build_synthesis_prompt(context, suppressed_topics)

        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=settings.strategist.synthesis_timeout,
        )

        raw_list = json.loads(_clean_json(response))
        if not isinstance(raw_list, list):
            logger.warning("Strategist LLM returned non-list for %s — discarding", user_id)
            return []

        validated: List[dict] = []
        required_keys = {"topic", "hook_options", "platform", "why_now", "signal_source", "generate_payload"}
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            missing = required_keys - item.keys()
            if missing:
                logger.warning(
                    "Strategist rec missing keys %s for user %s — skipping item", missing, user_id
                )
                continue
            validated.append(item)

        return validated

    except asyncio.TimeoutError:
        logger.warning("Strategist LLM synthesis timed out for user %s", user_id)
        return []
    except Exception as e:
        logger.error("Strategist synthesis failed for user %s: %s", user_id, e)
        return []


def _build_generate_payload(rec: dict) -> dict:
    """Extract a generate_payload dict matching ContentCreateRequest schema.

    Keys: platform, content_type, raw_input (required by /api/content/generate).
    Prevents 422 errors when Phase 14 POSTs the payload (STRAT-07, Pitfall 4).
    """
    inner = rec.get("generate_payload") or {}
    return {
        "platform": rec.get("platform", "linkedin"),
        "content_type": inner.get("content_type", "post"),
        "raw_input": inner.get("raw_input", rec.get("topic", "")),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_strategist_for_user(user_id: str) -> dict:
    """Run nightly strategist for a single user. Writes cards to db.strategy_recommendations.

    Returns summary dict: {user_id, cards_written, skipped_suppressed, errors}.
    """
    cadence = await _get_cadence_state(user_id)
    halved = cadence.get("halved_rate", False)
    max_cards = max(1, MAX_CARDS_PER_DAY // 2) if halved else MAX_CARDS_PER_DAY

    # Gather suppressed topics for context injection into LLM prompt
    cutoff = datetime.now(timezone.utc) - timedelta(days=SUPPRESSION_DAYS)
    suppressed_cursor = db.strategy_recommendations.find(
        {"user_id": user_id, "status": "dismissed", "dismissed_at": {"$gte": cutoff}},
        {"_id": 0, "topic": 1},
    )
    suppressed_topics: List[str] = []
    async for doc in suppressed_cursor:
        if doc.get("topic"):
            suppressed_topics.append(doc["topic"].lower())

    context = await _gather_user_context(user_id)
    recommendations = await _synthesize_recommendations(user_id, context, suppressed_topics)

    cards_written = 0
    skipped_suppressed = 0

    for rec in recommendations[:max_cards]:
        topic = rec.get("topic", "").lower()

        # Runtime suppression check (double-check against DB — LLM may still try)
        if await _is_topic_suppressed(user_id, topic):
            skipped_suppressed += 1
            logger.debug("Suppressed topic skipped for %s: '%s'", user_id, topic)
            continue

        # Atomic cap guard — stop writing if daily limit reached
        slot_claimed = await _atomic_claim_card_slot(user_id)
        if not slot_claimed:
            logger.info("Daily card cap reached for user %s", user_id)
            break

        why_now = rec.get("why_now", "")
        if not why_now:
            why_now = f"Why now: Based on your content history and persona profile, this topic represents an unexplored angle."

        card_doc = {
            "recommendation_id": f"strat_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "status": "pending_approval",  # STRAT-02: always pending_approval on creation
            "topic": topic,
            "hook_options": rec.get("hook_options", []),
            "platform": rec.get("platform", "linkedin"),
            "why_now": why_now,  # STRAT-03: non-empty rationale
            "signal_source": rec.get("signal_source", "persona"),
            "generate_payload": _build_generate_payload(rec),  # STRAT-07
            "created_at": datetime.now(timezone.utc),
            "expires_at": None,
            "dismissed_at": None,
            "dismissed_reason": None,
        }

        try:
            await db.strategy_recommendations.insert_one(card_doc)
            cards_written += 1
            logger.info(
                "Card written for user %s: topic='%s' recommendation_id='%s'",
                user_id, topic, card_doc["recommendation_id"],
            )
        except Exception as e:
            logger.error("Failed to insert card for user %s: %s", user_id, e)

    # Update last_run_at in strategist_state
    try:
        await db.strategist_state.update_one(
            {"user_id": user_id},
            {"$set": {"last_run_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception as e:
        logger.warning("Could not update last_run_at for %s: %s", user_id, e)

    return {
        "user_id": user_id,
        "cards_written": cards_written,
        "skipped_suppressed": skipped_suppressed,
    }


async def run_strategist_for_all_users() -> dict:
    """Nightly entry point — runs strategist for all eligible users sequentially.

    Sequential (not parallel) to avoid LLM provider rate limits.
    Each user failure is caught and logged; other users continue.
    """
    users = await _get_eligible_users()
    processed = 0
    total_cards = 0
    error_count = 0
    affected_user_ids: List[str] = []

    for user_id in users:
        try:
            result = await run_strategist_for_user(user_id)
            processed += 1
            total_cards += result.get("cards_written", 0)
            if result.get("cards_written", 0) > 0:
                affected_user_ids.append(user_id)
        except Exception as e:
            error_count += 1
            logger.error("Strategist failed for user %s (continuing): %s", user_id, e)

    logger.info(
        "Nightly strategist complete: users=%d processed=%d cards=%d errors=%d",
        len(users), processed, total_cards, error_count,
    )

    return {
        "total_users": len(users),
        "processed": processed,
        "total_cards": total_cards,
        "errors": error_count,
        "affected_user_ids": affected_user_ids,
    }


async def handle_dismissal(
    user_id: str,
    recommendation_id: str,
    reason: Optional[str] = None,
) -> dict:
    """Mark a recommendation card as dismissed and update cadence state.

    Increments consecutive_dismissals. If threshold reached, halves delivery rate.
    The dismissed topic is suppressed for SUPPRESSION_DAYS via the DB record's
    status + dismissed_at fields (queried by _is_topic_suppressed).
    """
    now = datetime.now(timezone.utc)

    rec = await db.strategy_recommendations.find_one_and_update(
        {
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "status": "pending_approval",
        },
        {
            "$set": {
                "status": "dismissed",
                "dismissed_at": now,
                "dismissed_reason": reason,
            }
        },
        return_document=True,
    )

    if rec is None:
        return {"error": "not_found"}

    # Increment consecutive_dismissals
    state = await db.strategist_state.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"consecutive_dismissals": 1}},
        upsert=True,
        return_document=True,
    )

    needs_calibration = False
    consecutive = (state or {}).get("consecutive_dismissals", 0)
    # After increment the value in `state` is the pre-increment value; add 1
    consecutive += 1

    if (
        consecutive >= CONSECUTIVE_DISMISSAL_THRESHOLD
        and not (state or {}).get("halved_rate", False)
    ):
        # STRAT-06: halve delivery rate and flag for calibration prompt
        await db.strategist_state.update_one(
            {"user_id": user_id},
            {"$set": {"halved_rate": True, "needs_calibration_prompt": True}},
        )
        needs_calibration = True
        logger.info(
            "User %s hit %d consecutive dismissals — delivery rate halved",
            user_id, consecutive,
        )

    suppressed_until = (now + timedelta(days=SUPPRESSION_DAYS)).isoformat()
    return {
        "dismissed": True,
        "topic_suppressed_until": suppressed_until,
        "needs_calibration_prompt": needs_calibration,
    }


async def handle_approval(user_id: str, recommendation_id: str) -> dict:
    """Mark a recommendation card as approved and reset dismissal cadence.

    Returns generate_payload so Phase 14 can immediately POST to
    /api/content/generate for one-click generation (STRAT-07).
    """
    now = datetime.now(timezone.utc)

    rec = await db.strategy_recommendations.find_one_and_update(
        {
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "status": "pending_approval",
        },
        {"$set": {"status": "approved", "approved_at": now}},
        return_document=True,
    )

    if rec is None:
        return {"error": "not_found"}

    # Reset consecutive dismissals — approval resets the cadence back to normal
    await db.strategist_state.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "consecutive_dismissals": 0,
                "halved_rate": False,
                "needs_calibration_prompt": False,
            }
        },
    )

    return {
        "approved": True,
        "generate_payload": rec.get("generate_payload", {}),  # STRAT-07
    }
