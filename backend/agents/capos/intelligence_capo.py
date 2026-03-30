"""Intelligence Capo for ThookAI.

Oversees: Scout, Analyst, Planner (series_planner), Trend Predictor (viral_predictor)

Coordinates research, analytics aggregation, and scheduling intelligence.
Does NOT replace existing agent functions -- provides orchestration,
error handling, and decision-making on top of them.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

async def run_research(
    raw_input: str,
    platform: str,
    commander_output: dict,
) -> dict:
    """Coordinate the research phase of the pipeline.

    1. Determines whether research is needed (from commander_output).
    2. Runs the Scout agent with appropriate query and timeout.
    3. Returns the scout output dict.

    If the Scout fails or times out, returns a safe fallback so the pipeline
    can continue without external research.

    Args:
        raw_input: The user's original content prompt.
        platform: Target platform (linkedin, x, instagram).
        commander_output: Output from the Commander agent.

    Returns:
        Dict with keys: findings, citations, sources_found.
    """
    from agents.scout import run_scout

    research_needed = commander_output.get("research_needed", True)
    if not research_needed:
        return {
            "findings": "No external research required for this content.",
            "citations": [],
            "sources_found": 0,
        }

    research_query = commander_output.get("research_query", raw_input)

    try:
        scout_output = await asyncio.wait_for(
            run_scout(raw_input, research_query, platform),
            timeout=25.0,
        )
        return scout_output
    except asyncio.TimeoutError:
        logger.warning("Intelligence Capo: Scout timed out after 25s")
        return _fallback_research(raw_input, platform)
    except Exception as exc:
        logger.error("Intelligence Capo: Scout failed: %s", exc)
        return _fallback_research(raw_input, platform)


# ---------------------------------------------------------------------------
# Scheduling Intelligence
# ---------------------------------------------------------------------------

async def get_scheduling_intelligence(
    user_id: str,
    platform: str,
) -> dict:
    """Aggregate scheduling intelligence from Planner and Analyst data.

    Attempts to:
    1. Load pre-computed optimal_posting_times from the persona engine.
    2. If unavailable, runs calculate_optimal_posting_times (with timeout).
    3. Retrieves the latest performance trend to contextualise recommendations.

    Args:
        user_id: User ID.
        platform: Target platform to filter advice for.

    Returns:
        Dict with keys: optimal_times, rationale, platform, data_source.
    """
    from database import db

    optimal_times: list = []
    rationale = "Not enough data to recommend optimal posting times yet."
    data_source = "none"

    # ------------------------------------------------------------------
    # Step 1 -- Try pre-computed optimal times from persona engine
    # ------------------------------------------------------------------
    try:
        persona = await db.persona_engines.find_one(
            {"user_id": user_id},
            {"_id": 0, "optimal_posting_times": 1},
        )
        cached_times = (persona or {}).get("optimal_posting_times", {})
        platform_times = cached_times.get(platform)
        if platform_times and isinstance(platform_times, list) and len(platform_times) > 0:
            optimal_times = platform_times
            data_source = "cached"
    except Exception as exc:
        logger.warning("Intelligence Capo: Could not load cached optimal times: %s", exc)

    # ------------------------------------------------------------------
    # Step 2 -- If no cached data, attempt live calculation
    # ------------------------------------------------------------------
    if not optimal_times:
        try:
            from services.persona_refinement import calculate_optimal_posting_times

            result = await asyncio.wait_for(
                calculate_optimal_posting_times(user_id),
                timeout=10.0,
            )
            # result is either a dict with platform keys or a message dict
            if isinstance(result, dict) and platform in result:
                optimal_times = result[platform]
                data_source = "calculated"
            elif isinstance(result, dict) and "message" in result:
                rationale = result["message"]
        except asyncio.TimeoutError:
            logger.warning("Intelligence Capo: Optimal time calculation timed out")
        except Exception as exc:
            logger.warning("Intelligence Capo: Optimal time calculation failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 3 -- Fetch performance trend for richer rationale
    # ------------------------------------------------------------------
    trend = "unknown"
    try:
        from agents.analyst import get_performance_trends

        trend_data = await asyncio.wait_for(
            get_performance_trends(user_id, days=30),
            timeout=5.0,
        )
        trend = trend_data.get("trend", "unknown")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Build rationale
    # ------------------------------------------------------------------
    if optimal_times:
        top = optimal_times[0] if optimal_times else {}
        day = top.get("day_of_week", "")
        hour = top.get("hour_of_day", "")
        rate = top.get("avg_engagement_rate", 0)
        rationale = (
            f"Based on your past performance, {day} at {hour}:00 UTC "
            f"has the highest average engagement rate ({rate:.4%}) on {platform}."
        )
        if trend == "improving":
            rationale += " Your overall performance trend is improving -- keep posting at these times."
        elif trend == "declining":
            rationale += " Your performance trend is declining -- experimenting with new time slots may help."

    return {
        "optimal_times": optimal_times,
        "rationale": rationale,
        "platform": platform,
        "data_source": data_source,
        "performance_trend": trend,
    }


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

def _fallback_research(raw_input: str, platform: str) -> dict:
    """Safe fallback when Scout is unavailable."""
    return {
        "findings": (
            f"Research on '{raw_input[:50]}' for {platform}:\n"
            "External research was unavailable. Use your expertise and "
            "personal experience to support the content."
        ),
        "citations": [],
        "sources_found": 0,
        "_fallback": True,
    }
