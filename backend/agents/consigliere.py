"""Consigliere (Risk Layer) for ThookAI.

The Consigliere is a content-risk advisory layer that evaluates drafts for
topic sensitivity, brand-damage potential, UOM alignment, and platform-specific
risks. It does NOT block content -- it annotates the draft with risk metadata
that the human reviewer can act on.

Uses gpt-4o for deeper reasoning (falls back to gpt-4o-mini if unavailable).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from config import settings
from services.llm_client import LlmChat, UserMessage
from services.llm_keys import chat_constructor_key, openai_available

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RISK_SYSTEM = (
    "You are a content risk advisor for a social media creator platform. "
    "Evaluate content for sensitivity, brand risk, and platform compliance. "
    "Be pragmatic -- flag real risks, not theoretical ones. "
    "Return ONLY valid JSON, no markdown."
)

RISK_PROMPT = """Evaluate the risk profile of this content draft.

PLATFORM: {platform}
CONTENT TYPE: {content_type}

CREATOR PERSONA:
Voice: {voice_descriptor}
Niche: {content_niche}
Tone: {tone}

UOM (User Operating Model):
Risk Tolerance: {risk_tolerance}
Trust in AI: {trust_score}
Strategy Maturity: {strategy_maturity}

CONTENT DRAFT:
{draft}

QC ASSESSMENT:
Persona Match: {persona_match}/10
AI Risk: {ai_risk}/100
Platform Fit: {platform_fit}/10
QC Feedback: {qc_feedback}

Evaluate:
1. Topic sensitivity (political, religious, controversial, health claims, financial advice)
2. Brand damage potential (could this hurt the creator's professional reputation?)
3. UOM alignment (does this match the user's stated risk tolerance?)
4. Platform-specific risks (LinkedIn professional standards, X content policy, IG community guidelines)

Return JSON:
{{
  "risk_level": "low|medium|high|critical",
  "flags": ["list of specific concerns, if any"],
  "recommendations": ["suggestions for safer alternatives, if any"],
  "requires_human_review": true/false,
  "approved": true/false,
  "reasoning": "Brief explanation of the assessment",
  "sensitivity_areas": {{
    "political": false,
    "religious": false,
    "health_claims": false,
    "financial_advice": false,
    "controversial_opinion": false,
    "profanity": false
  }}
}}

RULES:
- "low" = no concerns, safe to publish
- "medium" = minor concerns, human should glance at it
- "high" = significant concerns, human MUST review before publishing
- "critical" = potential legal/reputation risk, block auto-publish
- approved = true if risk is within the creator's stated risk_tolerance
- Be specific in flags -- "mentions a politician" not "political content"
- Empty flags list for low-risk content is fine
- If the content is standard professional/educational content, mark as "low" risk"""


# ---------------------------------------------------------------------------
# Platform risk profiles
# ---------------------------------------------------------------------------

PLATFORM_RISK_CONTEXT = {
    "linkedin": (
        "LinkedIn has strict professional standards. Avoid: profanity, "
        "aggressive sales language, unverified claims, political rants, "
        "anything that could be seen as unprofessional."
    ),
    "x": (
        "X (Twitter) is more permissive but still penalises: hate speech, "
        "misleading health/financial claims, direct harassment. "
        "Controversial takes are tolerated but can go viral negatively."
    ),
    "instagram": (
        "Instagram community guidelines prohibit: hate speech, nudity, "
        "violence, misinformation. Engagement bait is deprioritised. "
        "Captions should be authentic, not clickbait."
    ),
}


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------

async def evaluate_content_risk(
    draft: str,
    persona_card: dict,
    platform: str,
    qc_output: dict,
    uom: Optional[dict] = None,
) -> dict:
    """Evaluate the risk/sensitivity profile of a content draft.

    This is an advisory layer -- it adds metadata for the human reviewer but
    does NOT block content from being saved or shown.

    Args:
        draft: The content draft text.
        persona_card: User persona card dict.
        platform: Target platform (linkedin, x, instagram).
        qc_output: Output from the QC agent.
        uom: User Operating Model dict (optional; from persona_engines.uom).

    Returns:
        Dict with risk_level, flags, recommendations, requires_human_review,
        approved, reasoning, and sensitivity_areas.
    """
    if not draft or not draft.strip():
        return _safe_result("low", approved=True, reasoning="Empty draft -- nothing to evaluate.")

    # Attempt quick heuristic pre-screen; if obviously safe, skip the LLM call
    heuristic = _heuristic_prescreen(draft, platform)
    if heuristic.get("obviously_safe"):
        return _safe_result(
            "low",
            approved=True,
            reasoning="Content passed heuristic pre-screen with no flags.",
        )

    # Use LLM for deeper evaluation
    if not openai_available():
        logger.info("Consigliere: LLM unavailable, using heuristic-only evaluation")
        return _heuristic_evaluation(draft, platform, persona_card, qc_output, uom)

    uom = uom or {}
    risk_tolerance = uom.get("risk_tolerance", "balanced")
    trust_score = uom.get("trust_in_thook", 0.5)
    strategy_maturity = uom.get("strategy_maturity", 1)

    prompt = RISK_PROMPT.format(
        platform=platform,
        content_type="post",
        voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional"),
        content_niche=persona_card.get("content_niche_signature", "General"),
        tone=persona_card.get("tone", "Professional"),
        risk_tolerance=risk_tolerance,
        trust_score=trust_score,
        strategy_maturity=strategy_maturity,
        draft=draft[:3000],
        persona_match=qc_output.get("personaMatch", 0),
        ai_risk=qc_output.get("aiRisk", 0),
        platform_fit=qc_output.get("platformFit", 0),
        qc_feedback="; ".join(qc_output.get("feedback", [])),
    )

    try:
        # Prefer gpt-4o for reasoning depth; fall back to gpt-4o-mini
        model = "gpt-4o"
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"consigliere-{uuid.uuid4().hex[:8]}",
            system_message=RISK_SYSTEM,
        ).with_model("openai", model)

        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=20.0,
        )
        result = json.loads(_clean_json(response))

        # Normalise and validate the result
        result = _normalise_result(result, risk_tolerance)
        return result

    except asyncio.TimeoutError:
        logger.warning("Consigliere: LLM evaluation timed out after 20s, using heuristic")
        return _heuristic_evaluation(draft, platform, persona_card, qc_output, uom)
    except json.JSONDecodeError as exc:
        logger.warning("Consigliere: LLM returned invalid JSON: %s", exc)
        return _heuristic_evaluation(draft, platform, persona_card, qc_output, uom)
    except Exception as exc:
        logger.error("Consigliere: LLM evaluation failed: %s", exc)
        return _heuristic_evaluation(draft, platform, persona_card, qc_output, uom)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_json(raw: str) -> str:
    """Strip markdown code fences from an LLM response."""
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


def _normalise_result(result: dict, risk_tolerance: str) -> dict:
    """Ensure all expected keys are present and values are valid."""
    valid_levels = {"low", "medium", "high", "critical"}
    risk_level = result.get("risk_level", "low")
    if risk_level not in valid_levels:
        risk_level = "medium"

    flags = result.get("flags", [])
    if not isinstance(flags, list):
        flags = [str(flags)]

    recommendations = result.get("recommendations", [])
    if not isinstance(recommendations, list):
        recommendations = [str(recommendations)]

    requires_human_review = result.get("requires_human_review", risk_level in {"high", "critical"})
    approved = result.get("approved", True)

    # Override approved based on risk tolerance
    if risk_tolerance == "conservative" and risk_level in {"medium", "high", "critical"}:
        approved = False
        requires_human_review = True
    elif risk_tolerance == "aggressive" and risk_level in {"low", "medium"}:
        approved = True

    sensitivity_areas = result.get("sensitivity_areas", {})
    for key in ["political", "religious", "health_claims", "financial_advice", "controversial_opinion", "profanity"]:
        if key not in sensitivity_areas:
            sensitivity_areas[key] = False

    return {
        "risk_level": risk_level,
        "flags": flags,
        "recommendations": recommendations,
        "requires_human_review": requires_human_review,
        "approved": approved,
        "reasoning": result.get("reasoning", ""),
        "sensitivity_areas": sensitivity_areas,
    }


def _safe_result(
    risk_level: str = "low",
    approved: bool = True,
    reasoning: str = "",
) -> dict:
    """Return a minimal safe result dict."""
    return {
        "risk_level": risk_level,
        "flags": [],
        "recommendations": [],
        "requires_human_review": risk_level in {"high", "critical"},
        "approved": approved,
        "reasoning": reasoning,
        "sensitivity_areas": {
            "political": False,
            "religious": False,
            "health_claims": False,
            "financial_advice": False,
            "controversial_opinion": False,
            "profanity": False,
        },
    }


# ---------------------------------------------------------------------------
# Heuristic pre-screen (no LLM)
# ---------------------------------------------------------------------------

# Keywords that trigger deeper review
_SENSITIVE_KEYWORDS = {
    "political": [
        "democrat", "republican", "trump", "biden", "election", "vote",
        "liberal", "conservative", "left-wing", "right-wing", "government",
        "legislation", "congress", "parliament",
    ],
    "religious": [
        "god", "allah", "jesus", "bible", "quran", "church", "mosque",
        "synagogue", "prayer", "religion", "faith-based",
    ],
    "health_claims": [
        "cure", "miracle", "heal", "treatment", "diagnosis", "medical advice",
        "weight loss guaranteed", "detox", "anti-aging",
    ],
    "financial_advice": [
        "guaranteed returns", "get rich", "investment advice",
        "financial freedom guaranteed", "crypto guaranteed", "passive income guaranteed",
    ],
    "profanity": [
        "fuck", "shit", "damn", "ass", "hell", "bitch", "bastard",
    ],
}


def _heuristic_prescreen(draft: str, platform: str) -> dict:
    """Fast keyword-based pre-screen. Returns obviously_safe flag."""
    lower = draft.lower()
    for category, keywords in _SENSITIVE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower:
                return {"obviously_safe": False, "trigger_category": category, "trigger_keyword": keyword}
    return {"obviously_safe": True}


def _heuristic_evaluation(
    draft: str,
    platform: str,
    persona_card: dict,
    qc_output: dict,
    uom: Optional[dict],
) -> dict:
    """Full heuristic evaluation when LLM is unavailable."""
    lower = draft.lower()
    flags: List[str] = []
    sensitivity_areas = {
        "political": False,
        "religious": False,
        "health_claims": False,
        "financial_advice": False,
        "controversial_opinion": False,
        "profanity": False,
    }

    for category, keywords in _SENSITIVE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower:
                sensitivity_areas[category] = True
                flags.append(f"Contains potentially sensitive keyword: '{keyword}' (category: {category})")
                break  # One flag per category is enough

    # Platform-specific checks
    if platform == "linkedin":
        if sensitivity_areas.get("profanity"):
            flags.append("Profanity detected -- may violate LinkedIn professional standards")
    if platform == "instagram":
        if sensitivity_areas.get("health_claims"):
            flags.append("Health claims detected -- may violate Instagram misinformation policies")

    # QC-based risk amplification
    ai_risk = qc_output.get("aiRisk", 0)
    if ai_risk > 50:
        flags.append(f"High AI detection risk ({ai_risk}/100) -- may trigger platform AI content policies")

    # Determine risk level
    sensitive_count = sum(1 for v in sensitivity_areas.values() if v)
    if sensitive_count >= 3 or sensitivity_areas.get("health_claims") or sensitivity_areas.get("financial_advice"):
        risk_level = "high"
    elif sensitive_count >= 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    # UOM-based approval
    uom = uom or {}
    risk_tolerance = uom.get("risk_tolerance", "balanced")
    if risk_tolerance == "conservative":
        approved = risk_level == "low"
    elif risk_tolerance == "aggressive":
        approved = risk_level != "critical"
    else:  # balanced
        approved = risk_level in {"low", "medium"}

    recommendations = []
    if sensitivity_areas.get("health_claims"):
        recommendations.append("Add a disclaimer or soften health-related claims to 'in my experience'")
    if sensitivity_areas.get("financial_advice"):
        recommendations.append("Add 'not financial advice' disclaimer or reframe as personal experience")
    if sensitivity_areas.get("political"):
        recommendations.append("Consider whether political references serve the content's purpose")
    if sensitivity_areas.get("profanity") and platform == "linkedin":
        recommendations.append("Replace profanity with milder language for LinkedIn's professional audience")

    return {
        "risk_level": risk_level,
        "flags": flags,
        "recommendations": recommendations,
        "requires_human_review": risk_level in {"high", "critical"},
        "approved": approved,
        "reasoning": f"Heuristic evaluation (LLM unavailable): {sensitive_count} sensitivity area(s) detected.",
        "sensitivity_areas": sensitivity_areas,
        "_heuristic": True,
    }
