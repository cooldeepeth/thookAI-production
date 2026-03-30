"""Identity Capo for ThookAI.

Oversees: QC, Anti-Repetition, Fatigue Shield, Learning

Coordinates pre-generation identity checks (anti-repetition, fatigue shield),
post-generation quality control, and user learning signals.
Does NOT replace existing agent functions -- provides orchestration,
error handling, and decision-making on top of them.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from database import db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-generation identity checks
# ---------------------------------------------------------------------------

async def run_identity_check(
    user_id: str,
    platform: str,
    raw_input: str,
) -> dict:
    """Run pre-generation identity checks before content creation begins.

    Gathers three signals concurrently:
    1. **Fatigue shield** -- pattern staleness detection (2s timeout).
    2. **Anti-repetition context** -- recent topics/hooks/structures to avoid.
    3. Returns constraints that the Thinker and Writer should respect.

    All checks are non-fatal: if any fail, a safe default is returned so the
    pipeline is never blocked.

    Args:
        user_id: User ID.
        platform: Target platform.
        raw_input: The user's content prompt (used for context).

    Returns:
        Dict with keys:
            anti_rep_prompt (str): Prompt fragment for Commander/Thinker.
            fatigue_constraints (dict): Raw fatigue shield data.
            shield_status (str): "healthy" | "caution" | "warning" | "critical".
    """
    # Run fatigue shield and anti-repetition in parallel
    fatigue_task = asyncio.create_task(_safe_fatigue_shield(user_id))
    anti_rep_task = asyncio.create_task(_safe_anti_repetition(user_id))

    fatigue_data, anti_rep_data = await asyncio.gather(
        fatigue_task, anti_rep_task, return_exceptions=True
    )

    # Handle exceptions from gather
    if isinstance(fatigue_data, BaseException):
        logger.warning("Identity Capo: Fatigue shield raised %s", fatigue_data)
        fatigue_data = {}
    if isinstance(anti_rep_data, BaseException):
        logger.warning("Identity Capo: Anti-repetition raised %s", anti_rep_data)
        anti_rep_data = {"has_patterns": False}

    # Build the anti-repetition prompt fragment
    anti_rep_prompt = ""
    if anti_rep_data.get("has_patterns"):
        try:
            from agents.anti_repetition import build_anti_repetition_prompt
            anti_rep_prompt = build_anti_repetition_prompt(anti_rep_data)
        except Exception as exc:
            logger.warning("Identity Capo: build_anti_repetition_prompt failed: %s", exc)

    shield_status = fatigue_data.get("shield_status", "healthy") if fatigue_data else "healthy"

    return {
        "anti_rep_prompt": anti_rep_prompt,
        "anti_rep_context": anti_rep_data,
        "fatigue_constraints": fatigue_data,
        "shield_status": shield_status,
    }


# ---------------------------------------------------------------------------
# Quality control
# ---------------------------------------------------------------------------

async def run_quality_control(
    draft: str,
    persona_card: dict,
    platform: str,
    content_type: str,
    user_id: str = None,
) -> dict:
    """Run the QC agent and interpret results.

    Wraps the existing ``run_qc`` function with a timeout and fallback.

    Args:
        draft: The content draft to evaluate.
        persona_card: User persona card dict.
        platform: Target platform.
        content_type: Type of content.
        user_id: Optional user ID for repetition checking.

    Returns:
        QC output dict with overall_pass, scores, and feedback.
    """
    from agents.qc import run_qc

    try:
        qc_output = await asyncio.wait_for(
            run_qc(draft, persona_card, platform, content_type, user_id=user_id),
            timeout=25.0,
        )
        return qc_output
    except asyncio.TimeoutError:
        logger.error("Identity Capo: QC timed out after 25s")
        return _fallback_qc(draft)
    except Exception as exc:
        logger.error("Identity Capo: QC failed: %s", exc)
        return _fallback_qc(draft)


# ---------------------------------------------------------------------------
# Learning signals
# ---------------------------------------------------------------------------

async def record_learning_signal(
    user_id: str,
    job_id: str,
    signal_type: str,
    data: dict,
) -> None:
    """Record a learning signal from a user action.

    Delegates to the learning agent's ``capture_learning_signal`` function.
    Fires and does not raise -- failures are logged but never block the caller.

    Args:
        user_id: User ID.
        job_id: Content job ID.
        signal_type: One of "approved", "rejected", "edited".
        data: Dict with keys like original_content, final_content, etc.
    """
    from agents.learning import capture_learning_signal

    original_content = data.get("original_content", "")
    final_content = data.get("final_content", original_content)

    try:
        await asyncio.wait_for(
            capture_learning_signal(
                user_id=user_id,
                job_id=job_id,
                original_content=original_content,
                final_content=final_content,
                action=signal_type,
            ),
            timeout=15.0,
        )
        logger.info(
            "Identity Capo: Learning signal recorded for user=%s job=%s type=%s",
            user_id, job_id, signal_type,
        )
    except asyncio.TimeoutError:
        logger.warning("Identity Capo: Learning signal capture timed out for job %s", job_id)
    except Exception as exc:
        logger.error("Identity Capo: Learning signal capture failed: %s", exc)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _safe_fatigue_shield(user_id: str) -> dict:
    """Run the fatigue shield with a 2s timeout and safe fallback."""
    try:
        from services.persona_refinement import get_pattern_fatigue_shield

        return await asyncio.wait_for(
            get_pattern_fatigue_shield(user_id),
            timeout=2.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Identity Capo: Fatigue shield timed out (2s)")
        return {"shield_status": "healthy", "_timeout": True}
    except Exception as exc:
        logger.warning("Identity Capo: Fatigue shield error: %s", exc)
        return {"shield_status": "healthy", "_error": str(exc)}


async def _safe_anti_repetition(user_id: str) -> dict:
    """Run anti-repetition context gathering with a timeout and safe fallback."""
    try:
        from agents.anti_repetition import get_anti_repetition_context

        return await asyncio.wait_for(
            get_anti_repetition_context(user_id),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Identity Capo: Anti-repetition context timed out (5s)")
        return {"has_patterns": False, "_timeout": True}
    except Exception as exc:
        logger.warning("Identity Capo: Anti-repetition context error: %s", exc)
        return {"has_patterns": False, "_error": str(exc)}


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

def _fallback_qc(draft: str) -> dict:
    """Minimal QC output when the real agent is unavailable."""
    word_count = len(draft.split()) if draft else 0
    persona_match = min(9.0, 6.5 + (word_count / 100))
    return {
        "personaMatch": round(persona_match, 1),
        "aiRisk": 25,
        "platformFit": 8.0,
        "overall_pass": persona_match >= 7,
        "feedback": ["QC agent was unavailable; manual review recommended."],
        "suggestions": [],
        "strengths": [],
        "repetition_risk": 0,
        "repetition_level": "unknown",
        "_fallback": True,
    }
