"""Agent Accuracy Tracking Service for ThookAI.

Implements a learning flywheel that tracks per-agent prediction accuracy so the
system improves over time.  After content is published and engagement data
arrives, we compare each agent's predictions against actual outcomes:

- QC predicted ``personaMatch: 8.5`` -- was the post well-received?
- Viral predictor said ``engagement_score: 72`` -- what was actual engagement?
- Writer was chosen over an alternative hook -- did the winner perform better?

Over time, agents with low accuracy face more scrutiny (extra debate rounds,
lower trust weight).  Agents that predict well earn more autonomy.

Database collection: ``agent_accuracy``

Integration points (call sites -- do NOT modify these files from here):
    - orchestrator.py  finalize_node should call ``record_prediction()``
      for QC scores (personaMatch, aiRisk, platformFit).
    - content_tasks.py  poll_post_metrics should call ``resolve_prediction()``
      when engagement data arrives from social platform APIs.
    - orchestrator.py  hook_debate should check ``should_escalate_debate()``
      to decide how many debate rounds to run.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from database import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Known agents that participate in the prediction flywheel.
TRACKED_AGENTS = {"qc", "viral_predictor", "writer", "thinker"}

# Maximum reasonable value per metric, used for accuracy normalization.
# Metrics not listed here default to 100.
METRIC_MAX_VALUES: Dict[str, float] = {
    "persona_match": 10.0,
    "ai_risk": 100.0,
    "platform_fit": 10.0,
    "engagement_score": 100.0,
    "hook_selection": 1.0,     # binary: 1 = correct pick, 0 = wrong pick
    "virality_score": 100.0,
}

# Trust thresholds
ESCALATION_ACCURACY_THRESHOLD = 0.6   # below this -> escalate
HIGH_TRUST_THRESHOLD = 0.8            # above this -> high autonomy
DEFAULT_TRUST_SCORE = 0.7             # assumed for agents with no history

# Minimum resolved predictions required before trust scores are considered
# meaningful.  Below this count, the default trust score is returned.
MIN_PREDICTIONS_FOR_TRUST = 5

# Weight recent predictions more heavily when computing trust.
# Predictions in the most recent ``RECENT_WINDOW_DAYS`` are weighted 2x.
RECENT_WINDOW_DAYS = 14


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def record_prediction(
    agent: str,
    metric: str,
    predicted_value: float,
    job_id: str,
    user_id: str,
) -> str:
    """Record a prediction for later accuracy measurement.

    Called at generation time when an agent produces a score or selection that
    can later be validated against real-world performance data.

    Args:
        agent: Agent identifier (e.g. ``"qc"``, ``"viral_predictor"``).
        metric: Metric name (e.g. ``"persona_match"``, ``"engagement_score"``).
        predicted_value: The value the agent predicted.
        job_id: Content job this prediction relates to.
        user_id: Owner of the content job.

    Returns:
        The ``prediction_id`` of the newly created record.
    """
    if agent not in TRACKED_AGENTS:
        logger.warning(
            "record_prediction called for untracked agent '%s' -- recording anyway",
            agent,
        )

    prediction_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    document = {
        "prediction_id": prediction_id,
        "agent": agent,
        "metric": metric,
        "predicted_value": float(predicted_value),
        "actual_value": None,
        "accuracy": None,
        "job_id": job_id,
        "user_id": user_id,
        "created_at": now,
        "resolved_at": None,
    }

    try:
        await db.agent_accuracy.insert_one(document)
        logger.info(
            "Recorded prediction %s: agent=%s metric=%s predicted=%.2f job=%s",
            prediction_id, agent, metric, predicted_value, job_id,
        )
    except Exception:
        logger.exception(
            "Failed to record prediction for agent=%s metric=%s job=%s",
            agent, metric, job_id,
        )
        raise

    return prediction_id


async def resolve_prediction(
    job_id: str,
    metric: str,
    actual_value: float,
) -> None:
    """Fill in the actual value after performance data arrives.

    Looks up all unresolved predictions for the given ``job_id`` and
    ``metric``, computes accuracy for each, and persists the result.

    Accuracy formula::

        accuracy = 1 - abs(predicted - actual) / max_value

    The result is clamped to [0, 1].

    Args:
        job_id: Content job whose performance data just arrived.
        metric: Which metric was measured (must match the value used in
            ``record_prediction``).
        actual_value: The real-world measurement.
    """
    max_value = METRIC_MAX_VALUES.get(metric, 100.0)
    if max_value <= 0:
        max_value = 100.0

    now = datetime.now(timezone.utc)

    # Find all unresolved predictions for this job + metric.
    cursor = db.agent_accuracy.find({
        "job_id": job_id,
        "metric": metric,
        "actual_value": None,
    })

    resolved_count = 0
    async for record in cursor:
        predicted = record.get("predicted_value", 0.0)
        accuracy = max(0.0, 1.0 - abs(predicted - actual_value) / max_value)

        try:
            await db.agent_accuracy.update_one(
                {"prediction_id": record["prediction_id"]},
                {"$set": {
                    "actual_value": float(actual_value),
                    "accuracy": round(accuracy, 4),
                    "resolved_at": now,
                }},
            )
            resolved_count += 1
            logger.info(
                "Resolved prediction %s: agent=%s metric=%s "
                "predicted=%.2f actual=%.2f accuracy=%.4f",
                record["prediction_id"], record["agent"], metric,
                predicted, actual_value, accuracy,
            )
        except Exception:
            logger.exception(
                "Failed to resolve prediction %s", record["prediction_id"],
            )

    if resolved_count == 0:
        logger.debug(
            "No unresolved predictions found for job=%s metric=%s",
            job_id, metric,
        )


async def get_agent_accuracy(
    agent: str,
    user_id: Optional[str] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """Get accuracy statistics for an agent over the last N days.

    Args:
        agent: Agent identifier.
        user_id: If provided, scope stats to this user only.
            When ``None``, aggregate across all users (platform-wide).
        days: Look-back window in days.

    Returns:
        A dictionary with shape::

            {
                "agent": str,
                "total_predictions": int,
                "resolved_predictions": int,
                "average_accuracy": float,   # 0.0 - 1.0
                "trend": "improving" | "stable" | "declining",
                "by_metric": {
                    "<metric_name>": {
                        "count": int,
                        "avg_accuracy": float,
                    }
                }
            }
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    base_filter: Dict[str, Any] = {
        "agent": agent,
        "created_at": {"$gte": cutoff},
    }
    if user_id is not None:
        base_filter["user_id"] = user_id

    # Fetch all predictions in the window.
    cursor = db.agent_accuracy.find(base_filter).sort("created_at", 1)

    total = 0
    resolved = 0
    accuracy_sum = 0.0
    by_metric: Dict[str, Dict[str, Any]] = {}

    # For trend analysis, split into two halves.
    first_half_acc: List[float] = []
    second_half_acc: List[float] = []
    midpoint = cutoff + timedelta(days=days / 2)

    async for record in cursor:
        total += 1
        acc = record.get("accuracy")
        metric_name = record.get("metric", "unknown")
        created_at = record.get("created_at")

        if acc is not None:
            resolved += 1
            accuracy_sum += acc

            # Per-metric aggregation
            if metric_name not in by_metric:
                by_metric[metric_name] = {"count": 0, "accuracy_sum": 0.0}
            by_metric[metric_name]["count"] += 1
            by_metric[metric_name]["accuracy_sum"] += acc

            # Trend buckets
            if created_at and created_at < midpoint:
                first_half_acc.append(acc)
            else:
                second_half_acc.append(acc)

    average_accuracy = (accuracy_sum / resolved) if resolved > 0 else 0.0

    # Trend calculation
    trend = _compute_trend(first_half_acc, second_half_acc)

    # Finalize by_metric
    by_metric_final: Dict[str, Dict[str, Any]] = {}
    for m, data in by_metric.items():
        count = data["count"]
        by_metric_final[m] = {
            "count": count,
            "avg_accuracy": round(data["accuracy_sum"] / count, 4) if count else 0.0,
        }

    return {
        "agent": agent,
        "total_predictions": total,
        "resolved_predictions": resolved,
        "average_accuracy": round(average_accuracy, 4),
        "trend": trend,
        "by_metric": by_metric_final,
    }


async def get_agent_trust_scores(
    user_id: Optional[str] = None,
) -> Dict[str, float]:
    """Get trust scores for all tracked agents.

    Trust scores inform the orchestrator:
    - High trust (>= 0.8): agent output can be auto-accepted, fewer debate
      rounds.
    - Medium trust (0.6 - 0.8): normal processing.
    - Low trust (< 0.6): extra scrutiny, more debate rounds, require
      additional review.

    Recent predictions (last ``RECENT_WINDOW_DAYS`` days) are weighted 2x
    compared to older predictions within the 90-day window.

    Args:
        user_id: Scope to a single user, or ``None`` for platform-wide.

    Returns:
        Mapping of agent name to trust score (0.0 - 1.0).  Agents without
        enough data receive ``DEFAULT_TRUST_SCORE``.
    """
    trust_scores: Dict[str, float] = {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS)

    for agent in TRACKED_AGENTS:
        base_filter: Dict[str, Any] = {
            "agent": agent,
            "created_at": {"$gte": cutoff},
            "accuracy": {"$ne": None},
        }
        if user_id is not None:
            base_filter["user_id"] = user_id

        cursor = db.agent_accuracy.find(base_filter)

        weighted_sum = 0.0
        weight_total = 0.0
        count = 0

        async for record in cursor:
            count += 1
            acc = record["accuracy"]
            created_at = record.get("created_at")

            # Weight recent predictions more heavily.
            if created_at and created_at >= recent_cutoff:
                weight = 2.0
            else:
                weight = 1.0

            weighted_sum += acc * weight
            weight_total += weight

        if count < MIN_PREDICTIONS_FOR_TRUST:
            trust_scores[agent] = DEFAULT_TRUST_SCORE
        else:
            trust_scores[agent] = round(weighted_sum / weight_total, 4)

    return trust_scores


async def should_escalate_debate(
    agent: str,
    user_id: Optional[str] = None,
) -> bool:
    """Determine whether an agent should face additional scrutiny.

    Returns ``True`` if the agent's recent accuracy is below the escalation
    threshold (``< 0.6``), meaning the orchestrator should run more debate
    rounds, require extra review, or lower the agent's weight in final
    decisions.

    An agent with insufficient prediction history is never escalated (benefit
    of the doubt).

    Args:
        agent: Agent identifier.
        user_id: Optional user scope.

    Returns:
        ``True`` if the agent should be escalated, ``False`` otherwise.
    """
    stats = await get_agent_accuracy(agent, user_id=user_id, days=30)

    resolved = stats.get("resolved_predictions", 0)
    if resolved < MIN_PREDICTIONS_FOR_TRUST:
        # Not enough data to judge -- do not escalate.
        return False

    avg_accuracy = stats.get("average_accuracy", DEFAULT_TRUST_SCORE)
    should_flag = avg_accuracy < ESCALATION_ACCURACY_THRESHOLD

    if should_flag:
        logger.info(
            "Escalation triggered for agent=%s (accuracy=%.4f < %.2f, "
            "resolved=%d predictions in last 30d, user=%s)",
            agent, avg_accuracy, ESCALATION_ACCURACY_THRESHOLD,
            resolved, user_id or "all",
        )

    return should_flag


# ---------------------------------------------------------------------------
# Helpers for pipeline integration
# ---------------------------------------------------------------------------

async def record_qc_predictions(
    job_id: str,
    user_id: str,
    qc_output: Dict[str, Any],
) -> List[str]:
    """Convenience: record all standard QC predictions in one call.

    Extracts ``personaMatch``, ``aiRisk``, and ``platformFit`` from the QC
    output and records each as a separate prediction.

    Args:
        job_id: Content job ID.
        user_id: User ID.
        qc_output: The QC agent's output dict.

    Returns:
        List of prediction IDs created.
    """
    prediction_ids: List[str] = []

    qc_metrics = [
        ("persona_match", "personaMatch"),
        ("ai_risk", "aiRisk"),
        ("platform_fit", "platformFit"),
    ]

    for metric_name, qc_key in qc_metrics:
        value = qc_output.get(qc_key)
        if value is not None:
            try:
                pid = await record_prediction(
                    agent="qc",
                    metric=metric_name,
                    predicted_value=float(value),
                    job_id=job_id,
                    user_id=user_id,
                )
                prediction_ids.append(pid)
            except Exception:
                logger.exception(
                    "Failed to record QC prediction for metric=%s job=%s",
                    metric_name, job_id,
                )

    return prediction_ids


async def record_viral_prediction(
    job_id: str,
    user_id: str,
    engagement_score: float,
) -> str:
    """Convenience: record a viral predictor engagement score prediction.

    Args:
        job_id: Content job ID.
        user_id: User ID.
        engagement_score: Predicted engagement score (0-100).

    Returns:
        The prediction ID.
    """
    return await record_prediction(
        agent="viral_predictor",
        metric="engagement_score",
        predicted_value=engagement_score,
        job_id=job_id,
        user_id=user_id,
    )


async def record_hook_selection(
    job_id: str,
    user_id: str,
    agent: str = "writer",
) -> str:
    """Record a hook selection prediction (binary outcome).

    The predicted value is always 1.0 (we selected what we believe is the
    best hook).  When performance data arrives, ``actual_value`` will be 1.0
    if the hook outperformed alternatives, 0.0 otherwise.

    Args:
        job_id: Content job ID.
        user_id: User ID.
        agent: Which agent made the selection (defaults to ``"writer"``).

    Returns:
        The prediction ID.
    """
    return await record_prediction(
        agent=agent,
        metric="hook_selection",
        predicted_value=1.0,
        job_id=job_id,
        user_id=user_id,
    )


async def resolve_job_metrics(
    job_id: str,
    performance_data: Dict[str, Any],
) -> None:
    """Convenience: resolve multiple metrics for a job from performance data.

    Expected keys in ``performance_data``::

        {
            "engagement_rate": float,      # 0-100 scale
            "persona_reception": float,    # 0-10 scale (audience response)
            "hook_won": bool,              # did the selected hook outperform?
        }

    Args:
        job_id: Content job whose metrics arrived.
        performance_data: Dict of metric name -> actual value.
    """
    metric_mapping = {
        "engagement_rate": "engagement_score",
        "persona_reception": "persona_match",
        "hook_won": "hook_selection",
    }

    for data_key, metric_name in metric_mapping.items():
        value = performance_data.get(data_key)
        if value is not None:
            # Convert boolean hook_won to float
            if isinstance(value, bool):
                value = 1.0 if value else 0.0

            try:
                await resolve_prediction(
                    job_id=job_id,
                    metric=metric_name,
                    actual_value=float(value),
                )
            except Exception:
                logger.exception(
                    "Failed to resolve metric=%s for job=%s",
                    metric_name, job_id,
                )


# ---------------------------------------------------------------------------
# Analytics / reporting
# ---------------------------------------------------------------------------

async def get_accuracy_report(
    user_id: Optional[str] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """Generate a comprehensive accuracy report across all tracked agents.

    Useful for the admin dashboard or analytics endpoints.

    Args:
        user_id: Scope to a single user, or ``None`` for platform-wide.
        days: Look-back window.

    Returns:
        Report dict with per-agent stats and overall system health.
    """
    agents_data: Dict[str, Any] = {}
    total_resolved = 0
    total_accuracy_sum = 0.0

    for agent in sorted(TRACKED_AGENTS):
        stats = await get_agent_accuracy(agent, user_id=user_id, days=days)
        agents_data[agent] = stats
        resolved = stats["resolved_predictions"]
        total_resolved += resolved
        total_accuracy_sum += stats["average_accuracy"] * resolved

    trust_scores = await get_agent_trust_scores(user_id=user_id)

    overall_accuracy = (
        round(total_accuracy_sum / total_resolved, 4)
        if total_resolved > 0 else 0.0
    )

    # Count agents needing attention
    agents_needing_attention = [
        agent for agent, score in trust_scores.items()
        if score < ESCALATION_ACCURACY_THRESHOLD
    ]

    return {
        "period_days": days,
        "user_id": user_id,
        "overall_accuracy": overall_accuracy,
        "total_resolved_predictions": total_resolved,
        "agents": agents_data,
        "trust_scores": trust_scores,
        "agents_needing_attention": agents_needing_attention,
        "system_health": (
            "healthy" if not agents_needing_attention
            else "degraded" if len(agents_needing_attention) <= 1
            else "attention_required"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_trend(
    first_half: List[float],
    second_half: List[float],
) -> str:
    """Determine whether accuracy is improving, stable, or declining.

    Compares the average accuracy of the first half of the window against
    the second half.  A difference of more than 5 percentage points in
    either direction is considered a trend; otherwise it is ``"stable"``.

    Args:
        first_half: Accuracy values from the older half of the window.
        second_half: Accuracy values from the more recent half.

    Returns:
        One of ``"improving"``, ``"stable"``, or ``"declining"``.
    """
    if not first_half or not second_half:
        return "stable"

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    delta = avg_second - avg_first

    if delta > 0.05:
        return "improving"
    elif delta < -0.05:
        return "declining"
    return "stable"
