"""
User Operating Model (UOM) Service for ThookAI.

The UOM is the invisible adaptive layer that steers ALL agent behavior. It
observes how users interact with the platform -- approvals, edits, rejections,
session timing, feature usage, content preferences -- and translates those
behavioral signals into concrete directives that each agent receives before
doing its work.

Key design principles:
- Never blocks the generation pipeline. All inference is best-effort with
  sensible defaults when data is sparse.
- Confidence-weighted: early on (confidence < 0.5), defaults dominate.
  As more data arrives, the inferred values take over.
- Rule-based emotional state detection (no LLM call) for real-time speed.
- Agent directives are the primary consumer interface -- agents never read
  raw UOM fields directly; they receive translated instructions via
  ``get_agent_directives()``.

Database location: ``persona_engines.uom`` (embedded document)

Public API:
    get_uom(user_id)                 - Read full UOM with defaults filled in
    update_uom(user_id, partial)     - Validate and persist partial updates
    infer_uom_from_behavior(user_id) - Full behavioral inference (candidate)
    detect_emotional_state(text, ctx) - Real-time emotion detection (rule-based)
    get_agent_directives(user_id, a) - Translated directives per agent
    run_periodic_uom_update(user_id) - Infer + persist (cron / after N interactions)
    update_emotional_state(user_id, ..) - Detect + persist emotional state
    maybe_trigger_periodic_update(..)   - Conditionally trigger periodic update
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from database import db
from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema and Defaults
# ---------------------------------------------------------------------------

UOM_SCHEMA = {
    # Core behavioral dimensions
    "trust_in_thook": float,            # 0.0-1.0
    "strategy_maturity": int,           # 1-5
    "burnout_risk": str,                # "low" | "medium" | "high"
    "risk_tolerance": str,              # "conservative" | "balanced" | "bold"
    "cognitive_load_tolerance": str,    # "low" | "medium" | "high"
    "monetization_priority": str,       # "low" | "medium" | "high"
    "focus_preference": str,            # "single-platform" | "multi-platform"

    # Extended behavioral dimensions
    "content_velocity": str,            # "low" | "moderate" | "high"
    "creative_autonomy": str,           # "guided" | "collaborative" | "autonomous"
    "feedback_responsiveness": float,   # 0.0-1.0
    "preferred_content_depth": str,     # "snackable" | "standard" | "longform"
    "emotional_state": str,             # "energized" | "neutral" | "low_energy" | "rushed"
    "peak_activity_hours": list,        # e.g. [9, 10, 14, 15]
    "platform_affinity": dict,          # e.g. {"linkedin": 0.6, "x": 0.3, "instagram": 0.1}

    # Metadata
    "last_updated": datetime,
    "inference_version": int,
    "confidence": float,                # 0.0-1.0
}

UOM_DEFAULTS: Dict[str, Any] = {
    "trust_in_thook": 0.5,
    "strategy_maturity": 2,
    "burnout_risk": "medium",
    "risk_tolerance": "balanced",
    "cognitive_load_tolerance": "medium",
    "monetization_priority": "medium",
    "focus_preference": "multi-platform",
    "content_velocity": "moderate",
    "creative_autonomy": "collaborative",
    "feedback_responsiveness": 0.5,
    "preferred_content_depth": "standard",
    "emotional_state": "neutral",
    "peak_activity_hours": [],
    "platform_affinity": {},
    "confidence": 0.3,
    "inference_version": 1,
}

# Current inference engine version. Bump when inference logic changes
# materially so that stale UOM records can be identified and re-inferred.
CURRENT_INFERENCE_VERSION = 1

# Validation constraints used by update_uom()
_VALID_VALUES = {
    "burnout_risk": {"low", "medium", "high"},
    "risk_tolerance": {"conservative", "balanced", "bold"},
    "cognitive_load_tolerance": {"low", "medium", "high"},
    "monetization_priority": {"low", "medium", "high"},
    "focus_preference": {"single-platform", "multi-platform"},
    "content_velocity": {"low", "moderate", "high"},
    "creative_autonomy": {"guided", "collaborative", "autonomous"},
    "preferred_content_depth": {"snackable", "standard", "longform"},
    "emotional_state": {"energized", "neutral", "low_energy", "rushed"},
}

_FLOAT_RANGES = {
    "trust_in_thook": (0.0, 1.0),
    "feedback_responsiveness": (0.0, 1.0),
    "confidence": (0.0, 1.0),
}

_INT_RANGES = {
    "strategy_maturity": (1, 5),
    "inference_version": (1, 999),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def _blend(inferred: float, default: float, confidence: float) -> float:
    """Confidence-weighted blend between inferred and default values.

    At confidence 0.0 the result equals the default; at 1.0 the result equals
    the inferred value. The blending curve is linear.
    """
    return default + (inferred - default) * confidence


def _blend_categorical(
    inferred: str,
    default: str,
    confidence: float,
    threshold: float = 0.45,
) -> str:
    """For categorical values, use *inferred* only when confidence exceeds *threshold*."""
    return inferred if confidence >= threshold else default


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Safe division that returns *default* when *b* is zero."""
    return a / b if b else default


def _normalize_datetime(val: Any) -> Optional[datetime]:
    """Coerce a value to a timezone-aware UTC datetime, or None."""
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    elif isinstance(val, datetime):
        dt = val
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Core API: get_uom
# ---------------------------------------------------------------------------

async def get_uom(user_id: str) -> dict:
    """Get the current UOM for a user, with defaults filled in.

    Returns a complete UOM dict. Fields that are missing from the stored
    document are populated from ``UOM_DEFAULTS``. If no persona engine
    document exists at all, pure defaults are returned.

    This function never raises -- on any database error it returns defaults
    with confidence 0.3.
    """
    try:
        persona = await db.persona_engines.find_one(
            {"user_id": user_id},
            {"_id": 0, "uom": 1},
        )
        stored_uom = (persona or {}).get("uom", {})
    except Exception as exc:
        logger.error("Failed to fetch UOM for user %s: %s", user_id, exc)
        stored_uom = {}

    # Merge stored values over defaults
    result: Dict[str, Any] = {**UOM_DEFAULTS}
    for key, value in stored_uom.items():
        if key in UOM_DEFAULTS or key in ("last_updated",):
            result[key] = value

    # Ensure last_updated is always present
    if "last_updated" not in result or result["last_updated"] is None:
        result["last_updated"] = datetime.now(timezone.utc)

    return result


# ---------------------------------------------------------------------------
# Core API: update_uom
# ---------------------------------------------------------------------------

async def update_uom(user_id: str, partial_uom: dict) -> dict:
    """Validate and persist a partial UOM update.

    Only fields present in the schema are accepted. Values are validated
    against known constraints. Invalid fields/values are silently dropped
    with a warning log.

    Returns the full, merged UOM after the update.
    """
    now = datetime.now(timezone.utc)
    clean: Dict[str, Any] = {}

    for key, value in partial_uom.items():
        # Validate enum fields
        if key in _VALID_VALUES:
            if value in _VALID_VALUES[key]:
                clean[key] = value
            else:
                logger.warning(
                    "UOM update rejected for field '%s': invalid value '%s' (user %s)",
                    key, value, user_id,
                )

        # Validate float range fields
        elif key in _FLOAT_RANGES:
            try:
                fval = float(value)
                lo, hi = _FLOAT_RANGES[key]
                clean[key] = round(_clamp(fval, lo, hi), 4)
            except (TypeError, ValueError):
                logger.warning(
                    "UOM update rejected for field '%s': not a valid float (user %s)",
                    key, user_id,
                )

        # Validate int range fields
        elif key in _INT_RANGES:
            try:
                ival = int(value)
                lo, hi = _INT_RANGES[key]
                clean[key] = max(lo, min(hi, ival))
            except (TypeError, ValueError):
                logger.warning(
                    "UOM update rejected for field '%s': not a valid int (user %s)",
                    key, user_id,
                )

        # List fields (peak_activity_hours)
        elif key == "peak_activity_hours":
            if isinstance(value, list):
                clean[key] = [
                    int(h)
                    for h in value
                    if isinstance(h, (int, float)) and 0 <= h <= 23
                ]
            else:
                logger.warning(
                    "UOM update rejected for field '%s': not a list (user %s)",
                    key, user_id,
                )

        # Dict fields (platform_affinity)
        elif key == "platform_affinity":
            if isinstance(value, dict):
                clean[key] = {
                    str(k): round(_clamp(float(v), 0.0, 1.0), 4)
                    for k, v in value.items()
                    if isinstance(v, (int, float))
                }
            else:
                logger.warning(
                    "UOM update rejected for field '%s': not a dict (user %s)",
                    key, user_id,
                )

        # Skip read-only / metadata fields
        elif key in ("last_updated", "inference_version"):
            pass  # Managed internally

        else:
            logger.warning(
                "UOM update: unknown field '%s' ignored (user %s)", key, user_id,
            )

    if not clean:
        logger.info("UOM update for user %s: no valid fields to update", user_id)
        return await get_uom(user_id)

    clean["last_updated"] = now

    # Persist
    set_fields = {f"uom.{k}": v for k, v in clean.items()}
    try:
        await db.persona_engines.update_one(
            {"user_id": user_id},
            {"$set": set_fields},
            upsert=True,
        )
        logger.info(
            "UOM updated for user %s: fields=%s", user_id, list(clean.keys()),
        )
    except Exception as exc:
        logger.error("Failed to persist UOM update for user %s: %s", user_id, exc)

    return await get_uom(user_id)


# ---------------------------------------------------------------------------
# Behavioral Inference Engine
# ---------------------------------------------------------------------------

async def infer_uom_from_behavior(user_id: str) -> dict:
    """Analyze user behavior across multiple signals and produce an inferred UOM.

    This is the brain of the UOM system. It queries ``content_jobs`` and
    ``persona_engines`` for behavioral signals and maps them onto every UOM
    dimension. The returned dict is a *candidate* UOM -- the caller decides
    whether to persist it (see ``run_periodic_uom_update``).

    Signal sources and the dimensions they feed:

    1.  **trust_in_thook** -- approval rate, edit closeness, recency
    2.  **strategy_maturity** -- feature breadth (series, repurpose, templates)
    3.  **burnout_risk** -- session frequency, late-night sessions, rejection trend
    4.  **risk_tolerance** -- bold vs safe hook approvals, topic diversity
    5.  **cognitive_load_tolerance** -- feature depth, edit complexity, experience
    6.  **monetization_priority** -- business keyword density, CTA patterns
    7.  **focus_preference** -- platform distribution
    8.  **content_velocity** -- posts per week
    9.  **creative_autonomy** -- edit rate, regeneration rate
    10. **feedback_responsiveness** -- decision rate on generated content
    11. **preferred_content_depth** -- average word count of approved content
    12. **peak_activity_hours** -- hour histogram of content creation times
    13. **platform_affinity** -- proportional platform usage

    Inference is robust: every signal-gathering step is wrapped in try/except
    so that a missing collection or field never crashes the engine. When a
    signal is unavailable, the corresponding dimension falls back to defaults.
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # ------------------------------------------------------------------
    # Gather raw data
    # ------------------------------------------------------------------

    # 1. Persona engine document (learning signals, existing UOM)
    persona: Dict[str, Any] = {}
    try:
        persona = (
            await db.persona_engines.find_one({"user_id": user_id}, {"_id": 0})
        ) or {}
    except Exception as exc:
        logger.warning("UOM inference: failed to load persona for %s: %s", user_id, exc)

    learning = persona.get("learning_signals", {})
    existing_uom = persona.get("uom", {})

    approved_count = learning.get("approved_count", 0)
    rejected_count = learning.get("rejected_count", 0)
    total_decisions = approved_count + rejected_count

    # 2. Content jobs from last 30 days
    recent_jobs: List[Dict[str, Any]] = []
    try:
        cursor = db.content_jobs.find(
            {"user_id": user_id, "created_at": {"$gte": thirty_days_ago}},
            {
                "_id": 0,
                "job_id": 1,
                "status": 1,
                "platform": 1,
                "content_type": 1,
                "created_at": 1,
                "completed_at": 1,
                "updated_at": 1,
                "final_content": 1,
                "was_edited": 1,
                "agent_outputs.commander": 1,
                "agent_outputs.thinker": 1,
                "qc_score": 1,
            },
        )
        recent_jobs = await cursor.to_list(500)
    except Exception as exc:
        logger.warning("UOM inference: failed to load jobs for %s: %s", user_id, exc)

    # 3. All-time content job count (lightweight)
    all_time_job_count = 0
    try:
        all_time_job_count = await db.content_jobs.count_documents({"user_id": user_id})
    except Exception as exc:
        logger.warning("UOM inference: count_documents failed for %s: %s", user_id, exc)

    # 4. Missed scheduled posts
    missed_scheduled = 0
    try:
        missed_scheduled = await db.scheduled_posts.count_documents({
            "user_id": user_id,
            "status": "missed",
            "scheduled_at": {"$gte": thirty_days_ago},
        })
    except Exception:
        pass  # Collection may not exist yet

    # 5. Feature usage signals
    series_count = 0
    repurpose_count = 0
    template_uses = 0
    try:
        series_count = await db.content_jobs.count_documents({
            "user_id": user_id,
            "content_type": "series",
        })
    except Exception:
        pass
    try:
        repurpose_count = await db.content_jobs.count_documents({
            "user_id": user_id,
            "source_job_id": {"$exists": True},
        })
    except Exception:
        pass
    try:
        template_uses = await db.content_jobs.count_documents({
            "user_id": user_id,
            "template_id": {"$exists": True},
        })
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Classify recent jobs
    # ------------------------------------------------------------------
    approved_jobs = [j for j in recent_jobs if j.get("status") in ("approved", "published")]
    rejected_jobs = [j for j in recent_jobs if j.get("status") == "rejected"]
    edited_jobs = [j for j in recent_jobs if j.get("was_edited")]

    # ------------------------------------------------------------------
    # 1. TRUST IN THOOK
    # ------------------------------------------------------------------
    approval_rate = _safe_div(approved_count, total_decisions, 0.5)

    # Edit closeness: fraction of approved content that was NOT edited
    total_approved_recent = len(approved_jobs)
    edited_count = len(edited_jobs)
    edit_closeness = 1.0 - _safe_div(edited_count, max(total_approved_recent, 1), 0.5)

    # Recency: decay if user has been inactive for > 14 days
    most_recent_job = max(
        (j.get("created_at") for j in recent_jobs if j.get("created_at")),
        default=None,
    )
    if most_recent_job:
        most_recent_dt = _normalize_datetime(most_recent_job)
        if most_recent_dt:
            days_since = (now - most_recent_dt).days
            recency = max(0.0, 1.0 - (days_since / 30.0))
        else:
            recency = 0.5
    else:
        recency = 0.3

    trust_raw = (approval_rate * 0.4) + (edit_closeness * 0.3) + (recency * 0.3)
    trust_in_thook = round(_clamp(trust_raw, 0.0, 1.0), 3)

    # ------------------------------------------------------------------
    # 2. STRATEGY MATURITY (1-5)
    # ------------------------------------------------------------------
    feature_breadth = 0.0
    if series_count > 0:
        feature_breadth += 1.0
    if repurpose_count > 0:
        feature_breadth += 1.0
    if template_uses > 0:
        feature_breadth += 0.5
    if all_time_job_count > 20:
        feature_breadth += 0.5
    if all_time_job_count > 50:
        feature_breadth += 0.5
    # Advanced feature usage (analytics / viral predictor)
    perf_intel = persona.get("performance_intelligence")
    if perf_intel and perf_intel.get("total_posts_with_data", 0) > 0:
        feature_breadth += 0.5

    strategy_maturity = int(min(5, max(1, 1 + feature_breadth)))

    # ------------------------------------------------------------------
    # 3. BURNOUT RISK
    # ------------------------------------------------------------------
    recent_7d_jobs = [
        j for j in recent_jobs
        if j.get("created_at") and _normalize_datetime(j["created_at"])
        and _normalize_datetime(j["created_at"]) >= seven_days_ago  # type: ignore[operator]
    ]
    sessions_7d = len(recent_7d_jobs)

    late_night_count = 0
    for j in recent_7d_jobs:
        dt = _normalize_datetime(j.get("created_at"))
        if dt and (dt.hour >= 22 or dt.hour < 5):
            late_night_count += 1

    rejection_rate_recent = _safe_div(len(rejected_jobs), len(recent_jobs), 0.0)

    burnout_score = 0.0
    if sessions_7d > 20:
        burnout_score += 0.35
    elif sessions_7d > 10:
        burnout_score += 0.15
    if late_night_count > 3:
        burnout_score += 0.2
    if rejection_rate_recent > 0.4:
        burnout_score += 0.2
    if missed_scheduled > 2:
        burnout_score += 0.15

    # Detect decreasing activity (first 15 days vs last 15 days)
    if len(recent_jobs) >= 2:
        cutoff_mid = now - timedelta(days=15)
        first_half = [
            j for j in recent_jobs
            if j.get("created_at") and _normalize_datetime(j["created_at"])
            and _normalize_datetime(j["created_at"]) < cutoff_mid  # type: ignore[operator]
        ]
        second_half = [
            j for j in recent_jobs
            if j.get("created_at") and _normalize_datetime(j["created_at"])
            and _normalize_datetime(j["created_at"]) >= cutoff_mid  # type: ignore[operator]
        ]
        if len(first_half) > 0 and len(second_half) < len(first_half) * 0.5:
            burnout_score += 0.15  # Activity dropping off

    if burnout_score >= 0.5:
        burnout_risk = "high"
    elif burnout_score >= 0.25:
        burnout_risk = "medium"
    else:
        burnout_risk = "low"

    # ------------------------------------------------------------------
    # 4. RISK TOLERANCE
    # ------------------------------------------------------------------
    bold_hook_count = 0
    safe_hook_count = 0
    bold_hooks = {"bold_claim", "contrarian", "story_start", "curiosity_gap"}
    safe_hooks = {"question", "number_list", "direct_address"}

    for j in approved_jobs:
        cmd = j.get("agent_outputs", {}).get("commander", {})
        hook_approach = cmd.get("hook_approach", "")
        if hook_approach in bold_hooks:
            bold_hook_count += 1
        elif hook_approach in safe_hooks:
            safe_hook_count += 1

    total_hook_signals = bold_hook_count + safe_hook_count
    if total_hook_signals >= 3:
        bold_ratio = _safe_div(bold_hook_count, total_hook_signals, 0.5)
        if bold_ratio >= 0.6:
            risk_tolerance = "bold"
        elif bold_ratio <= 0.3:
            risk_tolerance = "conservative"
        else:
            risk_tolerance = "balanced"
    else:
        # Secondary signal: topic diversity
        topics: set = set()
        for j in recent_jobs:
            cmd = j.get("agent_outputs", {}).get("commander", {})
            angle = cmd.get("primary_angle", "")
            if angle:
                words = [w.lower() for w in angle.split() if len(w) > 3][:3]
                topics.update(words)

        if len(topics) > 10:
            risk_tolerance = "bold"
        elif len(topics) > 5:
            risk_tolerance = "balanced"
        else:
            risk_tolerance = "conservative"

    # ------------------------------------------------------------------
    # 5. COGNITIVE LOAD TOLERANCE
    # ------------------------------------------------------------------
    avg_edit_complexity = 0.0
    if edited_jobs:
        complexities: List[float] = []
        for j in edited_jobs:
            original = j.get("agent_outputs", {}).get("writer", {})
            original_wc = original.get("word_count", 200) if isinstance(original, dict) else 200
            final = j.get("final_content", "")
            final_wc = len(final.split()) if final else original_wc
            if original_wc > 0:
                complexities.append(abs(final_wc - original_wc) / original_wc)
        if complexities:
            avg_edit_complexity = sum(complexities) / len(complexities)

    cog_score = 0.0
    cog_score += min(1.0, feature_breadth / 3.0) * 0.4   # Feature depth
    cog_score += min(1.0, avg_edit_complexity) * 0.3       # Edit complexity
    cog_score += min(1.0, all_time_job_count / 50.0) * 0.3  # Experience

    if cog_score >= 0.6:
        cognitive_load_tolerance = "high"
    elif cog_score >= 0.3:
        cognitive_load_tolerance = "medium"
    else:
        cognitive_load_tolerance = "low"

    # ------------------------------------------------------------------
    # 6. MONETIZATION PRIORITY
    # ------------------------------------------------------------------
    monetization_signals = 0
    monetization_keywords = {
        "business", "sales", "revenue", "coaching", "consulting",
        "client", "offer", "price", "launch", "product", "service",
        "monetize", "income", "profit", "funnel", "convert",
    }
    for j in approved_jobs:
        content = (j.get("final_content") or "").lower()
        if any(kw in content for kw in monetization_keywords):
            monetization_signals += 1

    if total_approved_recent > 0:
        monetization_ratio = monetization_signals / total_approved_recent
        if monetization_ratio >= 0.5:
            monetization_priority = "high"
        elif monetization_ratio >= 0.2:
            monetization_priority = "medium"
        else:
            monetization_priority = "low"
    else:
        monetization_priority = existing_uom.get("monetization_priority", "medium")

    # ------------------------------------------------------------------
    # 7. FOCUS PREFERENCE
    # ------------------------------------------------------------------
    platform_counts: Counter = Counter()
    for j in recent_jobs:
        plat = j.get("platform", "")
        if plat:
            platform_counts[plat] += 1

    total_platform_jobs = sum(platform_counts.values())
    if total_platform_jobs >= 3 and platform_counts:
        dominant_count = platform_counts.most_common(1)[0][1]
        if dominant_count / total_platform_jobs >= 0.8:
            focus_preference = "single-platform"
        else:
            focus_preference = "multi-platform"
    else:
        focus_preference = existing_uom.get("focus_preference", "multi-platform")

    # ------------------------------------------------------------------
    # 8. CONTENT VELOCITY
    # ------------------------------------------------------------------
    weeks_in_range = max(1.0, (now - thirty_days_ago).days / 7.0)
    posts_per_week = len(recent_jobs) / weeks_in_range

    if posts_per_week >= 7:
        content_velocity = "high"
    elif posts_per_week >= 3:
        content_velocity = "moderate"
    else:
        content_velocity = "low"

    # ------------------------------------------------------------------
    # 9. CREATIVE AUTONOMY
    # ------------------------------------------------------------------
    edit_rate = _safe_div(edited_count, max(total_approved_recent, 1), 0.5)
    regen_rate = _safe_div(len(rejected_jobs), max(len(recent_jobs), 1), 0.0)

    if edit_rate < 0.2 and regen_rate < 0.1:
        creative_autonomy = "autonomous"
    elif edit_rate > 0.5 or regen_rate > 0.3:
        creative_autonomy = "guided"
    else:
        creative_autonomy = "collaborative"

    # ------------------------------------------------------------------
    # 10. FEEDBACK RESPONSIVENESS
    # ------------------------------------------------------------------
    completed_jobs = [
        j for j in recent_jobs if j.get("status") in ("approved", "rejected", "published")
    ]
    pending_jobs = [
        j for j in recent_jobs if j.get("status") in ("completed", "reviewing")
    ]
    total_actionable = len(completed_jobs) + len(pending_jobs)
    feedback_responsiveness = round(
        _clamp(_safe_div(len(completed_jobs), max(total_actionable, 1), 0.5), 0.0, 1.0),
        3,
    )

    # ------------------------------------------------------------------
    # 11. PREFERRED CONTENT DEPTH
    # ------------------------------------------------------------------
    word_counts: List[int] = []
    for j in approved_jobs:
        content = j.get("final_content", "")
        if content:
            word_counts.append(len(content.split()))

    if word_counts:
        avg_wc = sum(word_counts) / len(word_counts)
        if avg_wc >= 300:
            preferred_content_depth = "longform"
        elif avg_wc <= 120:
            preferred_content_depth = "snackable"
        else:
            preferred_content_depth = "standard"
    else:
        dominant_platform = platform_counts.most_common(1)[0][0] if platform_counts else ""
        if dominant_platform == "x":
            preferred_content_depth = "snackable"
        elif dominant_platform == "linkedin":
            preferred_content_depth = "standard"
        else:
            preferred_content_depth = "standard"

    # ------------------------------------------------------------------
    # 12. PEAK ACTIVITY HOURS
    # ------------------------------------------------------------------
    hour_histogram: Counter = Counter()
    for j in recent_jobs:
        dt = _normalize_datetime(j.get("created_at"))
        if dt:
            hour_histogram[dt.hour] += 1

    # Top hours with at least 2 occurrences, limited to 4
    peak_activity_hours = sorted(
        [h for h, c in hour_histogram.most_common(6) if c >= 2]
    )[:4]

    # ------------------------------------------------------------------
    # 13. PLATFORM AFFINITY
    # ------------------------------------------------------------------
    platform_affinity: Dict[str, float] = {}
    if total_platform_jobs > 0:
        for plat, count in platform_counts.items():
            platform_affinity[plat] = round(count / total_platform_jobs, 3)

    # ------------------------------------------------------------------
    # CONFIDENCE
    # ------------------------------------------------------------------
    # Confidence grows with the amount of behavioral data available.
    # Ranges: 0.3 (onboarding only) -> 0.5 (some usage) -> 0.8+ (power user)
    data_points = (
        min(total_decisions, 50) / 50.0 * 0.35
        + min(len(recent_jobs), 30) / 30.0 * 0.25
        + min(all_time_job_count, 100) / 100.0 * 0.2
        + (1.0 if platform_counts else 0.0) * 0.1
        + (1.0 if edited_jobs else 0.0) * 0.1
    )
    confidence = round(_clamp(0.3 + data_points * 0.6, 0.3, 0.95), 3)

    # ------------------------------------------------------------------
    # Assemble inferred UOM
    # ------------------------------------------------------------------
    inferred: Dict[str, Any] = {
        "trust_in_thook": trust_in_thook,
        "strategy_maturity": strategy_maturity,
        "burnout_risk": burnout_risk,
        "risk_tolerance": risk_tolerance,
        "cognitive_load_tolerance": cognitive_load_tolerance,
        "monetization_priority": monetization_priority,
        "focus_preference": focus_preference,
        "content_velocity": content_velocity,
        "creative_autonomy": creative_autonomy,
        "feedback_responsiveness": feedback_responsiveness,
        "preferred_content_depth": preferred_content_depth,
        # emotional_state is real-time only; preserve the existing value
        "emotional_state": existing_uom.get("emotional_state", "neutral"),
        "peak_activity_hours": peak_activity_hours,
        "platform_affinity": platform_affinity,
        "confidence": confidence,
        "inference_version": CURRENT_INFERENCE_VERSION,
        "last_updated": now,
    }

    logger.info(
        "UOM inferred for user %s: confidence=%.2f, trust=%.2f, maturity=%d, "
        "burnout=%s, risk=%s, velocity=%s, autonomy=%s",
        user_id,
        confidence,
        trust_in_thook,
        strategy_maturity,
        burnout_risk,
        risk_tolerance,
        content_velocity,
        creative_autonomy,
    )

    return inferred


# ---------------------------------------------------------------------------
# Real-time Emotional State Detection
# ---------------------------------------------------------------------------

# Keyword sets for emotion detection (no LLM call -- rule-based for speed)
_RUSHED_KEYWORDS = frozenset({
    "quick", "fast", "just", "asap", "hurry", "rush", "simple", "easy",
    "basic", "short", "brief", "straight", "done", "now",
})

_ENERGIZED_KEYWORDS = frozenset({
    "excited", "love", "great", "amazing", "awesome", "perfect", "fantastic",
    "brilliant", "incredible", "pumped", "thrilled", "inspired", "stoked",
    "fire", "ready",
})

_LOW_ENERGY_KEYWORDS = frozenset({
    "tired", "exhausted", "whatever", "idk", "meh", "sure", "fine",
    "ok", "okay", "anything", "eh",
})


async def detect_emotional_state(
    raw_input: str,
    session_context: Optional[dict] = None,
) -> str:
    """Real-time emotion detection from user input.

    This is rule-based for speed (no LLM call). It examines input length,
    punctuation patterns, keyword presence, time of day, and session depth
    to classify the user's current emotional state.

    Args:
        raw_input: The user's content generation prompt / raw input text.
        session_context: Optional dict with keys:
            - ``current_hour`` (int, 0-23): hour of day in user's local time
            - ``items_created_this_session`` (int): how many items already
              created in the current session
            - ``session_duration_minutes`` (int): how long the session has lasted

    Returns:
        One of: ``"energized"`` | ``"neutral"`` | ``"low_energy"`` | ``"rushed"``
    """
    if not raw_input:
        return "neutral"

    ctx = session_context or {}
    text = raw_input.strip()
    text_lower = text.lower()
    word_count = len(text.split())

    scores: Dict[str, float] = {
        "energized": 0.0,
        "neutral": 0.3,  # Slight prior bias toward neutral
        "low_energy": 0.0,
        "rushed": 0.0,
    }

    # --- Input length signals ---
    if word_count <= 5:
        scores["rushed"] += 0.3
    elif word_count <= 10:
        scores["rushed"] += 0.1
    elif word_count >= 50:
        scores["energized"] += 0.2
    elif word_count >= 30:
        scores["energized"] += 0.1

    # --- Punctuation signals ---
    exclamation_count = text.count("!")
    ellipsis_count = text.count("...")

    if exclamation_count >= 2:
        scores["energized"] += 0.25
    elif exclamation_count == 1:
        scores["energized"] += 0.1

    if ellipsis_count >= 2:
        scores["low_energy"] += 0.15
    elif ellipsis_count == 1:
        scores["low_energy"] += 0.05

    # All-caps words (>= 2 caps words = energized)
    caps_words = [w for w in text.split() if w.isupper() and len(w) > 1]
    if len(caps_words) >= 2:
        scores["energized"] += 0.15

    # --- Keyword signals ---
    words_set = set(re.findall(r'\b\w+\b', text_lower))

    rushed_matches = words_set & _RUSHED_KEYWORDS
    energized_matches = words_set & _ENERGIZED_KEYWORDS
    low_energy_matches = words_set & _LOW_ENERGY_KEYWORDS

    scores["rushed"] += len(rushed_matches) * 0.15
    scores["energized"] += len(energized_matches) * 0.2
    scores["low_energy"] += len(low_energy_matches) * 0.2

    # --- Time of day signal ---
    current_hour = ctx.get("current_hour")
    if current_hour is not None:
        try:
            hour = int(current_hour)
            if 0 <= hour < 6:
                scores["low_energy"] += 0.2
            elif 22 <= hour <= 23:
                scores["low_energy"] += 0.1
            elif 9 <= hour <= 11:
                scores["energized"] += 0.05  # Mild morning boost
        except (TypeError, ValueError):
            pass

    # --- Session depth signal ---
    items_created = ctx.get("items_created_this_session", 0)
    session_minutes = ctx.get("session_duration_minutes", 0)

    if items_created >= 5:
        scores["low_energy"] += 0.15
        scores["rushed"] += 0.1
    elif items_created >= 3:
        scores["rushed"] += 0.05

    if session_minutes > 90:
        scores["low_energy"] += 0.1

    # --- Pick the winner ---
    result = max(scores, key=lambda k: scores[k])
    return result


# ---------------------------------------------------------------------------
# Agent Directives -- the primary consumer interface
# ---------------------------------------------------------------------------

async def get_agent_directives(user_id: str, agent_name: str) -> dict:
    """Translate the UOM into specific directives for a named agent.

    This is **the key consumer-facing function**. Agents call this before
    starting their work to receive tailored parameters. The directives are
    derived from the full UOM and are confidence-weighted: when confidence is
    low, the directives stay close to safe defaults.

    Supported agent names:
        ``"thinker"`` | ``"writer"`` | ``"qc"`` | ``"commander"`` |
        ``"analyst"`` | ``"planner"`` | ``"consigliere"``

    Returns:
        Dict of agent-specific keys. Unknown agent names return an empty dict
        with a warning log.
    """
    uom = await get_uom(user_id)
    confidence = uom.get("confidence", 0.3)

    agent_name_clean = agent_name.lower().strip()

    builder = _AGENT_DIRECTIVE_BUILDERS.get(agent_name_clean)
    if builder is None:
        logger.warning("get_agent_directives: unknown agent '%s'", agent_name)
        return {}

    return builder(uom, confidence)


# ---------------------------------------------------------------------------
# Directive builder functions (one per agent)
# ---------------------------------------------------------------------------

def _directives_thinker(uom: dict, confidence: float) -> dict:
    """Thinker agent: angle selection, hook strategy, diversity."""
    risk = uom.get("risk_tolerance", "balanced")
    cog = uom.get("cognitive_load_tolerance", "medium")
    maturity = uom.get("strategy_maturity", 2)
    autonomy = uom.get("creative_autonomy", "collaborative")

    # risk_level
    risk_map = {"conservative": "safe", "balanced": "moderate", "bold": "bold"}
    risk_level = _blend_categorical(
        risk_map.get(risk, "moderate"), "moderate", confidence,
    )

    # hook_complexity: cognitive load + strategy maturity
    complexity_score = ({"low": 1, "medium": 2, "high": 3}.get(cog, 2) + maturity) / 2.0
    if complexity_score >= 3.5:
        hook_complexity = "complex"
    elif complexity_score >= 2.0:
        hook_complexity = "moderate"
    else:
        hook_complexity = "simple"
    hook_complexity = _blend_categorical(hook_complexity, "moderate", confidence)

    # angle_diversity
    autonomy_map = {
        "guided": "conservative",
        "collaborative": "balanced",
        "autonomous": "experimental",
    }
    angle_diversity = _blend_categorical(
        autonomy_map.get(autonomy, "balanced"), "balanced", confidence,
    )

    # max_options: fewer for low cognitive load
    if cog == "low":
        max_options = 2
    elif cog == "high" and maturity >= 4:
        max_options = 4
    else:
        max_options = 3

    return {
        "risk_level": risk_level,
        "hook_complexity": hook_complexity,
        "angle_diversity": angle_diversity,
        "max_options": max_options,
    }


def _directives_writer(uom: dict, confidence: float) -> dict:
    """Writer agent: tone, vocabulary, length, energy, CTA."""
    maturity = uom.get("strategy_maturity", 2)
    risk = uom.get("risk_tolerance", "balanced")
    cog = uom.get("cognitive_load_tolerance", "medium")
    depth = uom.get("preferred_content_depth", "standard")
    emotional = uom.get("emotional_state", "neutral")
    monetization = uom.get("monetization_priority", "medium")

    # tone_intensity
    intensity_score = maturity + {"conservative": 0, "balanced": 1, "bold": 2}.get(risk, 1)
    if intensity_score >= 6:
        tone_intensity = "assertive"
    elif intensity_score >= 3:
        tone_intensity = "moderate"
    else:
        tone_intensity = "gentle"
    tone_intensity = _blend_categorical(tone_intensity, "moderate", confidence)

    # vocabulary_depth
    vocab_score = ({"low": 1, "medium": 2, "high": 3}.get(cog, 2) + maturity) / 2.0
    if vocab_score >= 3.5:
        vocabulary_depth = "sophisticated"
    elif vocab_score >= 2.0:
        vocabulary_depth = "intermediate"
    else:
        vocabulary_depth = "accessible"
    vocabulary_depth = _blend_categorical(vocabulary_depth, "intermediate", confidence)

    # content_length
    depth_map = {"snackable": "concise", "standard": "standard", "longform": "detailed"}
    content_length = _blend_categorical(
        depth_map.get(depth, "standard"), "standard", confidence,
    )

    # emotional_energy (from real-time emotional state)
    energy_map = {
        "energized": "high_energy",
        "neutral": "neutral",
        "low_energy": "calm",
        "rushed": "neutral",  # Rushed != low energy; keep neutral but concise
    }
    emotional_energy = energy_map.get(emotional, "neutral")

    # cta_aggressiveness
    cta_map = {"low": "soft", "medium": "moderate", "high": "direct"}
    cta_aggressiveness = _blend_categorical(
        cta_map.get(monetization, "moderate"), "moderate", confidence,
    )

    return {
        "tone_intensity": tone_intensity,
        "vocabulary_depth": vocabulary_depth,
        "content_length": content_length,
        "emotional_energy": emotional_energy,
        "cta_aggressiveness": cta_aggressiveness,
    }


def _directives_qc(uom: dict, confidence: float) -> dict:
    """QC agent: scoring thresholds and tolerance."""
    maturity = uom.get("strategy_maturity", 2)
    trust = uom.get("trust_in_thook", 0.5)
    risk = uom.get("risk_tolerance", "balanced")

    # persona_match_threshold: lower for new users (6), higher for mature (8)
    base_threshold = 6.0 + (maturity - 1) * 0.5  # 6.0 - 8.0
    persona_match_threshold = round(_blend(base_threshold, 7.0, confidence), 1)

    # ai_risk_threshold: stricter for conservative, looser for bold
    risk_base = {"conservative": 20, "balanced": 30, "bold": 40}.get(risk, 30)
    ai_risk_threshold = round(_blend(float(risk_base), 30.0, confidence))

    # allow_experimental: only for bold users with decent confidence
    allow_experimental = (risk == "bold" and confidence >= 0.5)

    return {
        "persona_match_threshold": persona_match_threshold,
        "ai_risk_threshold": ai_risk_threshold,
        "allow_experimental": allow_experimental,
    }


def _directives_commander(uom: dict, confidence: float) -> dict:
    """Commander agent: quality tier and research depth."""
    maturity = uom.get("strategy_maturity", 2)
    trust = uom.get("trust_in_thook", 0.5)
    velocity = uom.get("content_velocity", "moderate")

    # quality_tier: maturity + trust
    quality_score = maturity + trust * 5  # ~1.5 - ~10
    if quality_score >= 7:
        quality_tier = "premium"
    elif quality_score >= 4:
        quality_tier = "standard"
    else:
        quality_tier = "budget"
    quality_tier = _blend_categorical(quality_tier, "standard", confidence)

    # research_depth: inverse of content velocity
    velocity_map = {"high": "quick", "moderate": "standard", "low": "deep"}
    research_depth = _blend_categorical(
        velocity_map.get(velocity, "standard"), "standard", confidence,
    )

    return {
        "quality_tier": quality_tier,
        "research_depth": research_depth,
    }


def _directives_analyst(uom: dict, confidence: float) -> dict:
    """Analyst agent: insight depth, suggestion count, focus area."""
    cog = uom.get("cognitive_load_tolerance", "medium")
    burnout = uom.get("burnout_risk", "medium")
    emotional = uom.get("emotional_state", "neutral")
    monetization = uom.get("monetization_priority", "medium")

    # insight_depth
    cog_map = {"low": "summary", "medium": "detailed", "high": "comprehensive"}
    insight_depth = _blend_categorical(
        cog_map.get(cog, "detailed"), "detailed", confidence,
    )

    # suggestion_count: fewer when burnt out or low energy
    base_suggestions = 3
    if burnout == "high" or emotional == "low_energy":
        base_suggestions = 1
    elif burnout == "medium":
        base_suggestions = 2
    elif emotional == "energized" and cog == "high":
        base_suggestions = 5
    suggestion_count = max(1, min(5, base_suggestions))

    # focus_area
    if monetization == "high":
        focus_area = "monetization"
    elif monetization == "low":
        focus_area = "engagement"
    else:
        focus_area = "growth"

    return {
        "insight_depth": insight_depth,
        "suggestion_count": suggestion_count,
        "focus_area": focus_area,
    }


def _directives_planner(uom: dict, confidence: float) -> dict:
    """Planner agent: scheduling, pacing, platform priority."""
    burnout = uom.get("burnout_risk", "medium")
    velocity = uom.get("content_velocity", "moderate")
    affinity = uom.get("platform_affinity", {})

    # posts_per_week_cap
    velocity_caps = {"low": 2, "moderate": 5, "high": 10}
    base_cap = velocity_caps.get(velocity, 5)
    if burnout == "high":
        base_cap = max(1, base_cap - 2)
    elif burnout == "medium":
        base_cap = max(1, base_cap - 1)
    posts_per_week_cap = base_cap

    # scheduling_aggressiveness
    if velocity == "high" and burnout != "high":
        scheduling_aggressiveness = "aggressive"
    elif velocity == "low" or burnout == "high":
        scheduling_aggressiveness = "conservative"
    else:
        scheduling_aggressiveness = "moderate"

    # platform_priority: ordered by affinity descending
    platform_priority = sorted(
        affinity.keys(),
        key=lambda p: affinity.get(p, 0),
        reverse=True,
    ) if affinity else ["linkedin"]

    return {
        "posts_per_week_cap": posts_per_week_cap,
        "scheduling_aggressiveness": scheduling_aggressiveness,
        "platform_priority": platform_priority,
    }


def _directives_consigliere(uom: dict, confidence: float) -> dict:
    """Consigliere (guardian) agent: risk thresholds and review gates."""
    risk = uom.get("risk_tolerance", "balanced")
    trust = uom.get("trust_in_thook", 0.5)

    # risk_threshold
    risk_map = {"conservative": "strict", "balanced": "moderate", "bold": "relaxed"}
    risk_threshold = _blend_categorical(
        risk_map.get(risk, "moderate"), "moderate", confidence,
    )

    # Force human review when trust is very low
    requires_human_review_override = trust < 0.3

    return {
        "risk_threshold": risk_threshold,
        "requires_human_review_override": requires_human_review_override,
    }


# Registry of all directive builders
_AGENT_DIRECTIVE_BUILDERS: Dict[str, Any] = {
    "thinker": _directives_thinker,
    "writer": _directives_writer,
    "qc": _directives_qc,
    "commander": _directives_commander,
    "analyst": _directives_analyst,
    "planner": _directives_planner,
    "consigliere": _directives_consigliere,
}


# ---------------------------------------------------------------------------
# Periodic Update
# ---------------------------------------------------------------------------

async def run_periodic_uom_update(user_id: str) -> dict:
    """Run the full inference engine and persist the result.

    Intended to be called:
    - After every 5 user interactions (via ``maybe_trigger_periodic_update``)
    - On a daily cron / Celery beat schedule for active users
    - On demand from an admin endpoint

    Returns the updated UOM.
    """
    try:
        inferred = await infer_uom_from_behavior(user_id)
    except Exception as exc:
        logger.error(
            "Periodic UOM update failed for user %s: %s", user_id, exc,
        )
        return await get_uom(user_id)

    # Persist
    try:
        await db.persona_engines.update_one(
            {"user_id": user_id},
            {"$set": {"uom": inferred}},
            upsert=True,
        )
        logger.info(
            "Periodic UOM update persisted for user %s (confidence=%.2f)",
            user_id, inferred.get("confidence", 0),
        )
    except Exception as exc:
        logger.error(
            "Failed to persist periodic UOM update for user %s: %s",
            user_id, exc,
        )

    return inferred


# ---------------------------------------------------------------------------
# Convenience: update emotional state inline (before generation)
# ---------------------------------------------------------------------------

async def update_emotional_state(
    user_id: str,
    raw_input: str,
    session_context: Optional[dict] = None,
) -> str:
    """Detect and persist the user's emotional state before a generation run.

    This is a lightweight helper that combines ``detect_emotional_state`` with
    a targeted UOM field update. It is safe to call on every generation request
    because the write is a single ``$set`` on one field.

    Returns the detected emotional state string.
    """
    state = await detect_emotional_state(raw_input, session_context)

    try:
        await db.persona_engines.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "uom.emotional_state": state,
                    "uom.last_updated": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
    except Exception as exc:
        logger.warning(
            "Failed to persist emotional state for user %s: %s", user_id, exc,
        )

    return state


# ---------------------------------------------------------------------------
# Interaction counter for triggering periodic updates
# ---------------------------------------------------------------------------

async def maybe_trigger_periodic_update(user_id: str) -> Optional[dict]:
    """Check if the user has accumulated enough interactions since the last
    UOM inference to warrant a periodic update. If so, run it.

    The threshold is every 5 interactions (approximated by approved_count +
    rejected_count modulo 5).

    Returns the updated UOM if an update was triggered, ``None`` otherwise.
    """
    try:
        persona = await db.persona_engines.find_one(
            {"user_id": user_id},
            {
                "_id": 0,
                "learning_signals.approved_count": 1,
                "learning_signals.rejected_count": 1,
            },
        )
        if not persona:
            return None

        learning = persona.get("learning_signals", {})
        total = learning.get("approved_count", 0) + learning.get("rejected_count", 0)

        if total > 0 and total % 5 == 0:
            logger.info(
                "Triggering periodic UOM update for user %s (interaction #%d)",
                user_id, total,
            )
            return await run_periodic_uom_update(user_id)

    except Exception as exc:
        logger.warning(
            "maybe_trigger_periodic_update failed for user %s: %s", user_id, exc,
        )

    return None


# ---------------------------------------------------------------------------
# Legacy compatibility shim
# ---------------------------------------------------------------------------
# The previous version exposed ``update_uom_interaction_count`` which is now
# superseded by ``maybe_trigger_periodic_update``. Keep a thin wrapper so
# existing callers (e.g. agents/learning.py) do not break.

async def update_uom_interaction_count(user_id: str) -> bool:
    """Legacy shim: increment interaction counter and maybe trigger UOM refresh.

    Prefer ``maybe_trigger_periodic_update`` for new code.
    """
    result = await maybe_trigger_periodic_update(user_id)
    return result is not None
