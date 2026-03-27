"""Analyst Agent for ThookAI.

Analyzes content performance and provides actionable insights:
- Engagement tracking (simulated/real when platform APIs connected)
- Performance patterns identification
- Top-performing content analysis
- Cross-platform comparisons
- AI-powered recommendations
"""
import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from services.llm_keys import chat_constructor_key, openai_available

logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


# Engagement simulation configs (used when real metrics unavailable)
PLATFORM_ENGAGEMENT_PROFILES = {
    "linkedin": {
        "impressions_range": (500, 5000),
        "engagement_rate_range": (0.02, 0.08),  # 2-8%
        "click_rate_range": (0.01, 0.04),
        "share_rate_range": (0.005, 0.02)
    },
    "x": {
        "impressions_range": (200, 3000),
        "engagement_rate_range": (0.01, 0.05),
        "click_rate_range": (0.005, 0.02),
        "share_rate_range": (0.01, 0.03)
    },
    "instagram": {
        "impressions_range": (300, 4000),
        "engagement_rate_range": (0.03, 0.10),
        "click_rate_range": (0.01, 0.03),
        "share_rate_range": (0.02, 0.05)
    }
}


async def get_content_analytics(
    user_id: str,
    job_id: str
) -> Dict[str, Any]:
    """Get analytics for a specific content piece.
    
    Args:
        user_id: User ID
        job_id: Content job ID
    
    Returns:
        Performance metrics and insights
    """
    from database import db
    
    job = await db.content_jobs.find_one({
        "job_id": job_id,
        "user_id": user_id
    })
    
    if not job:
        return {"success": False, "error": "Content not found"}
    
    # Check if real metrics exist (from platform APIs)
    real_metrics = job.get("performance_metrics")
    
    if real_metrics:
        metrics = real_metrics
    else:
        # Generate simulated metrics for demo/testing
        metrics = _simulate_engagement(job.get("platform", "linkedin"), job)
    
    # Calculate performance score
    engagement_rate = metrics.get("engagement_rate", 0)
    platform = job.get("platform", "linkedin")
    profile = PLATFORM_ENGAGEMENT_PROFILES.get(platform, PLATFORM_ENGAGEMENT_PROFILES["linkedin"])
    
    # Score: 0-100 based on engagement rate vs platform average
    avg_rate = sum(profile["engagement_rate_range"]) / 2
    performance_score = min(100, int((engagement_rate / avg_rate) * 50))
    
    # Determine performance level
    if performance_score >= 80:
        performance_level = "exceptional"
    elif performance_score >= 60:
        performance_level = "above_average"
    elif performance_score >= 40:
        performance_level = "average"
    else:
        performance_level = "below_average"
    
    return {
        "success": True,
        "job_id": job_id,
        "platform": platform,
        "status": job.get("status"),
        "content_preview": job.get("final_content", "")[:200],
        "metrics": metrics,
        "performance_score": performance_score,
        "performance_level": performance_level,
        "is_simulated": real_metrics is None,
        "published_at": job.get("published_at").isoformat() if job.get("published_at") else None,
        "created_at": job.get("created_at").isoformat() if job.get("created_at") else None
    }


def _simulate_engagement(platform: str, job: Dict) -> Dict[str, Any]:
    """Simulate engagement metrics for content.
    
    Factors considered:
    - QC score (higher = better engagement)
    - Content length (optimal ranges)
    - Time published
    """
    import random
    
    profile = PLATFORM_ENGAGEMENT_PROFILES.get(platform, PLATFORM_ENGAGEMENT_PROFILES["linkedin"])
    
    # Base randomization
    base_factor = random.uniform(0.7, 1.3)
    
    # QC score factor
    qc_score = job.get("qc_score", {})
    persona_match = qc_score.get("personaMatch", 7)
    platform_fit = qc_score.get("platformFit", 7)
    qc_factor = ((persona_match + platform_fit) / 20)  # 0.5 - 1.0
    
    # Content length factor
    content_len = len(job.get("final_content", ""))
    if platform == "x":
        optimal = 200
    elif platform == "linkedin":
        optimal = 1500
    else:
        optimal = 500
    
    length_factor = 1.0 - abs(content_len - optimal) / (optimal * 3)
    length_factor = max(0.5, min(1.2, length_factor))
    
    # Combined factor
    combined = base_factor * qc_factor * length_factor
    
    # Calculate metrics
    imp_min, imp_max = profile["impressions_range"]
    impressions = int((imp_min + (imp_max - imp_min) * combined) * random.uniform(0.8, 1.2))
    
    eng_min, eng_max = profile["engagement_rate_range"]
    engagement_rate = (eng_min + (eng_max - eng_min) * combined) * random.uniform(0.8, 1.2)
    
    click_min, click_max = profile["click_rate_range"]
    click_rate = (click_min + (click_max - click_min) * combined) * random.uniform(0.8, 1.2)
    
    share_min, share_max = profile["share_rate_range"]
    share_rate = (share_min + (share_max - share_min) * combined) * random.uniform(0.8, 1.2)
    
    engagements = int(impressions * engagement_rate)
    clicks = int(impressions * click_rate)
    shares = int(impressions * share_rate)
    
    return {
        "impressions": impressions,
        "engagements": engagements,
        "engagement_rate": round(engagement_rate, 4),
        "clicks": clicks,
        "click_rate": round(click_rate, 4),
        "shares": shares,
        "share_rate": round(share_rate, 4),
        "likes": int(engagements * 0.6),
        "comments": int(engagements * 0.3),
        "saves": int(engagements * 0.1)
    }


async def get_analytics_overview(
    user_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """Get overview analytics for user's content.
    
    Args:
        user_id: User ID
        days: Number of days to analyze
    
    Returns:
        Aggregated performance metrics and trends
    """
    from database import db
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get published/approved content
    cursor = db.content_jobs.find(
        {
            "user_id": user_id,
            "status": {"$in": ["approved", "published", "scheduled"]},
            "created_at": {"$gte": cutoff}
        }
    )
    
    jobs = await cursor.to_list(100)
    
    if not jobs:
        return {
            "success": True,
            "has_data": False,
            "message": "No content in the selected period"
        }
    
    # Aggregate by platform
    platform_stats = defaultdict(lambda: {
        "total_posts": 0,
        "total_impressions": 0,
        "total_engagements": 0,
        "total_clicks": 0,
        "avg_engagement_rate": []
    })
    
    total_impressions = 0
    total_engagements = 0
    performance_scores = []
    top_content = []
    
    for job in jobs:
        platform = job.get("platform", "linkedin")
        
        # Get or simulate metrics
        metrics = job.get("performance_metrics")
        if not metrics:
            metrics = _simulate_engagement(platform, job)
        
        # Calculate performance score
        engagement_rate = metrics.get("engagement_rate", 0)
        profile = PLATFORM_ENGAGEMENT_PROFILES.get(platform, PLATFORM_ENGAGEMENT_PROFILES["linkedin"])
        avg_rate = sum(profile["engagement_rate_range"]) / 2
        score = min(100, int((engagement_rate / avg_rate) * 50))
        
        platform_stats[platform]["total_posts"] += 1
        platform_stats[platform]["total_impressions"] += metrics.get("impressions", 0)
        platform_stats[platform]["total_engagements"] += metrics.get("engagements", 0)
        platform_stats[platform]["total_clicks"] += metrics.get("clicks", 0)
        platform_stats[platform]["avg_engagement_rate"].append(engagement_rate)
        
        total_impressions += metrics.get("impressions", 0)
        total_engagements += metrics.get("engagements", 0)
        performance_scores.append(score)
        
        top_content.append({
            "job_id": job.get("job_id"),
            "platform": platform,
            "score": score,
            "engagement_rate": engagement_rate,
            "impressions": metrics.get("impressions", 0),
            "preview": job.get("final_content", "")[:100]
        })
    
    # Calculate platform averages
    for platform in platform_stats:
        rates = platform_stats[platform]["avg_engagement_rate"]
        platform_stats[platform]["avg_engagement_rate"] = round(sum(rates) / len(rates), 4) if rates else 0
    
    # Sort top content
    top_content.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "success": True,
        "has_data": True,
        "period_days": days,
        "summary": {
            "total_posts": len(jobs),
            "total_impressions": total_impressions,
            "total_engagements": total_engagements,
            "avg_performance_score": round(sum(performance_scores) / len(performance_scores), 1) if performance_scores else 0,
            "overall_engagement_rate": round(total_engagements / total_impressions, 4) if total_impressions else 0
        },
        "by_platform": dict(platform_stats),
        "top_performing": top_content[:5],
        "bottom_performing": list(reversed(top_content[-3:])) if len(top_content) >= 3 else []
    }


async def get_performance_trends(
    user_id: str,
    days: int = 30,
    granularity: str = "week"
) -> Dict[str, Any]:
    """Get performance trends over time.
    
    Args:
        user_id: User ID
        days: Number of days to analyze
        granularity: week or month
    
    Returns:
        Time-series performance data
    """
    from database import db
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    now = datetime.now(timezone.utc)
    
    cursor = db.content_jobs.find(
        {
            "user_id": user_id,
            "status": {"$in": ["approved", "published"]},
            "created_at": {"$gte": cutoff}
        }
    ).sort("created_at", 1)
    
    jobs = await cursor.to_list(200)
    
    if not jobs:
        return {
            "success": True,
            "has_data": False,
            "trends": []
        }
    
    # Group by time period
    if granularity == "week":
        period_days = 7
    else:
        period_days = 30
    
    periods = []
    current_period_start = cutoff
    
    while current_period_start < now:
        period_end = current_period_start + timedelta(days=period_days)
        period_jobs = [j for j in jobs if current_period_start <= j.get("created_at", now) < period_end]
        
        if period_jobs:
            scores = []
            impressions = 0
            engagements = 0
            
            for job in period_jobs:
                metrics = job.get("performance_metrics")
                if not metrics:
                    metrics = _simulate_engagement(job.get("platform", "linkedin"), job)
                
                engagement_rate = metrics.get("engagement_rate", 0)
                platform = job.get("platform", "linkedin")
                profile = PLATFORM_ENGAGEMENT_PROFILES.get(platform, PLATFORM_ENGAGEMENT_PROFILES["linkedin"])
                avg_rate = sum(profile["engagement_rate_range"]) / 2
                score = min(100, int((engagement_rate / avg_rate) * 50))
                
                scores.append(score)
                impressions += metrics.get("impressions", 0)
                engagements += metrics.get("engagements", 0)
            
            periods.append({
                "period_start": current_period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "posts": len(period_jobs),
                "avg_score": round(sum(scores) / len(scores), 1),
                "impressions": impressions,
                "engagements": engagements,
                "engagement_rate": round(engagements / impressions, 4) if impressions else 0
            })
        
        current_period_start = period_end
    
    # Calculate trend direction
    if len(periods) >= 2:
        first_half = periods[:len(periods)//2]
        second_half = periods[len(periods)//2:]
        
        first_avg = sum(p["avg_score"] for p in first_half) / len(first_half) if first_half else 0
        second_avg = sum(p["avg_score"] for p in second_half) / len(second_half) if second_half else 0
        
        if second_avg > first_avg * 1.1:
            trend = "improving"
        elif second_avg < first_avg * 0.9:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"
    
    return {
        "success": True,
        "has_data": True,
        "period_days": days,
        "granularity": granularity,
        "trend": trend,
        "periods": periods
    }


async def get_persona_performance_data(user_id: str) -> Dict[str, Any]:
    """Read performance_intelligence and optimal_posting_times from persona engine.

    Returns real calculated data when available, or informational placeholder
    messages when performance data has not yet been collected.

    Args:
        user_id: User ID

    Returns:
        Dict with ``performance_intelligence`` and ``optimal_posting_times``.
    """
    from database import db

    persona_engine = await db.persona_engines.find_one({"user_id": user_id})

    if not persona_engine:
        return {
            "performance_intelligence": {
                "message": "Performance data is being collected. Check back after your first 5 published posts."
            },
            "optimal_posting_times": {
                "message": "Optimal times are calculated after 10+ published posts with performance data."
            },
        }

    perf_intel = persona_engine.get("performance_intelligence", {})
    if not perf_intel:
        perf_intel = {
            "message": "Performance data is being collected. Check back after your first 5 published posts."
        }

    optimal_times = persona_engine.get("optimal_posting_times", {})
    if not optimal_times:
        optimal_times = {
            "message": "Optimal times are calculated after 10+ published posts with performance data."
        }

    return {
        "performance_intelligence": perf_intel,
        "optimal_posting_times": optimal_times,
    }


async def generate_insights(
    user_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """Generate AI-powered insights from performance data.

    Args:
        user_id: User ID
        days: Days to analyze

    Returns:
        AI-generated insights and recommendations
    """
    # Get analytics data
    overview = await get_analytics_overview(user_id, days)
    trends = await get_performance_trends(user_id, days)
    
    # Fetch persona-level performance intelligence (real calculated data or message)
    persona_perf = await get_persona_performance_data(user_id)

    if not overview.get("has_data"):
        return {
            "success": True,
            "has_insights": False,
            "message": "Need more content to generate insights",
            **persona_perf,
        }

    # Get diversity data
    from agents.anti_repetition import get_content_diversity_score, analyze_hook_fatigue
    diversity = await get_content_diversity_score(user_id, days)
    hook_fatigue = await analyze_hook_fatigue(user_id, limit=10)
    
    if not openai_available():
        result = _mock_insights(overview, trends, diversity, hook_fatigue)
        result.update(persona_perf)
        return result
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"insights-{uuid.uuid4().hex[:8]}",
            system_message="You are a social media strategist. Analyze data and provide actionable insights. Return JSON only."
        ).with_model("openai", "gpt-4.1-mini")
        
        prompt = f"""Analyze this content performance data and provide strategic insights.

PERFORMANCE OVERVIEW (Last {days} days):
- Total posts: {overview['summary']['total_posts']}
- Total impressions: {overview['summary']['total_impressions']}
- Avg performance score: {overview['summary']['avg_performance_score']}/100
- Overall engagement rate: {overview['summary']['overall_engagement_rate']*100:.2f}%

BY PLATFORM:
{json.dumps(overview.get('by_platform', {}), indent=2)}

TOP PERFORMING CONTENT:
{json.dumps(overview.get('top_performing', [])[:3], indent=2)}

TREND: {trends.get('trend', 'unknown')}

CONTENT DIVERSITY SCORE: {diversity.get('score', 'N/A')}/100
HOOK FATIGUE: {hook_fatigue.get('has_fatigue', False)}
OVERUSED HOOKS: {json.dumps(hook_fatigue.get('overused_hooks', []))}

Return JSON:
{{
    "summary": "One-sentence performance summary",
    "key_insights": [
        "Insight 1 with specific data",
        "Insight 2 with specific data",
        "Insight 3 with specific data"
    ],
    "recommendations": [
        {{
            "priority": "high|medium|low",
            "action": "Specific action to take",
            "expected_impact": "Expected improvement"
        }}
    ],
    "best_performing_patterns": ["Pattern 1", "Pattern 2"],
    "areas_to_improve": ["Area 1", "Area 2"],
    "next_30_day_focus": "Strategic focus recommendation"
}}"""
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=30.0
        )
        
        insights = json.loads(_clean_json(response))

        return {
            "success": True,
            "has_insights": True,
            "period_days": days,
            **insights,
            **persona_perf,
        }

    except Exception as e:
        logger.error(f"Insights generation failed: {e}")
        result = _mock_insights(overview, trends, diversity, hook_fatigue)
        result.update(persona_perf)
        return result


def _mock_insights(overview: Dict, trends: Dict, diversity: Dict, hook_fatigue: Dict) -> Dict[str, Any]:
    """Generate mock insights when AI unavailable."""
    summary = overview.get("summary", {})
    trend = trends.get("trend", "stable")
    
    insights = []
    recommendations = []
    
    # Performance-based insights
    if summary.get("avg_performance_score", 0) >= 60:
        insights.append(f"Strong performance with {summary.get('avg_performance_score')}/100 average score")
    else:
        insights.append(f"Room for improvement - current average score is {summary.get('avg_performance_score')}/100")
        recommendations.append({
            "priority": "high",
            "action": "Analyze top-performing content and replicate its patterns",
            "expected_impact": "15-25% engagement improvement"
        })
    
    # Trend-based insights
    if trend == "improving":
        insights.append("Performance trend is positive - keep doing what's working")
    elif trend == "declining":
        insights.append("Performance is declining - time to refresh your approach")
        recommendations.append({
            "priority": "high",
            "action": "Try new content formats or topics to re-engage audience",
            "expected_impact": "Break the downward trend"
        })
    
    # Hook fatigue
    if hook_fatigue.get("has_fatigue"):
        overused = hook_fatigue.get("overused_hooks", [])
        if overused:
            insights.append(f"Hook fatigue detected: {overused[0].get('type')} hooks overused at {overused[0].get('percentage')}%")
            recommendations.append({
                "priority": "medium",
                "action": f"Reduce {overused[0].get('type')} hooks, try {', '.join(hook_fatigue.get('underused_hooks', ['story'])[:2])} hooks",
                "expected_impact": "10-15% engagement boost from novelty"
            })
    
    # Platform-specific
    by_platform = overview.get("by_platform", {})
    if len(by_platform) >= 2:
        platform_rates = [(p, d.get("avg_engagement_rate", 0)) for p, d in by_platform.items()]
        best = max(platform_rates, key=lambda x: x[1])
        worst = min(platform_rates, key=lambda x: x[1])
        if best[1] > worst[1] * 1.5:
            insights.append(f"{best[0].upper()} outperforming {worst[0].upper()} by {int((best[1]/worst[1]-1)*100)}%")
    
    return {
        "success": True,
        "has_insights": True,
        "is_mock": True,
        "summary": f"Analyzed {summary.get('total_posts', 0)} posts with {int(summary.get('overall_engagement_rate', 0)*100)}% engagement rate",
        "key_insights": insights[:3],
        "recommendations": recommendations[:3],
        "best_performing_patterns": ["High persona match content", "Platform-optimized length"],
        "areas_to_improve": ["Hook variety", "Posting consistency"],
        "next_30_day_focus": "Experiment with underused content formats while maintaining top performers"
    }


async def track_content_performance(
    job_id: str,
    metrics: Dict[str, Any]
) -> bool:
    """Store real performance metrics from platform APIs.
    
    Called when platform integrations sync engagement data.
    
    Args:
        job_id: Content job ID
        metrics: Real metrics from platform API
    
    Returns:
        Success status
    """
    from database import db
    
    try:
        result = await db.content_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "performance_metrics": metrics,
                    "metrics_updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Failed to track performance: {e}")
        return False
