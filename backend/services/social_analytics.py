"""Social Analytics Service for ThookAI.

Fetches real post performance metrics from social platform APIs:
- LinkedIn: Social actions API (likes, comments, shares, impressions)
- X/Twitter: Tweet metrics API v2
- Instagram: Media Insights API (via Meta Graph API)

Each function handles errors gracefully and never raises — returns
an error dict instead, so Celery tasks can log and move on.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any
from urllib.parse import quote

import httpx

from database import db

logger = logging.getLogger(__name__)


# ============ LINKEDIN METRICS ============

async def fetch_linkedin_post_metrics(
    post_urn: str,
    access_token: str,
) -> Dict[str, Any]:
    """Fetch engagement metrics for a LinkedIn post.

    Uses the LinkedIn Social Actions API to retrieve likes, comments,
    and shares.  Impression data requires the LinkedIn Marketing API
    (r_organization_social scope for company pages) which most creator
    accounts don't have, so we derive an estimate from engagements when
    the organizationalEntityShareStatistics endpoint is unavailable.

    Args:
        post_urn: The LinkedIn post URN (e.g. "urn:li:share:123456")
        access_token: Decrypted OAuth access token

    Returns:
        Dict with metric values, or {"error": "..."} on failure.
    """
    encoded_urn = quote(post_urn, safe="")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Fetch social actions (likes, comments, shares counts)
            response = await client.get(
                f"https://api.linkedin.com/v2/socialActions/{encoded_urn}",
                headers=headers,
            )

            if response.status_code == 401:
                return {"error": "token_expired"}
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                return {"error": "rate_limited", "retry_after": retry_after}
            if response.status_code != 200:
                logger.error(
                    "LinkedIn socialActions returned %s: %s",
                    response.status_code,
                    response.text[:300],
                )
                return {"error": "api_unavailable"}

            data = response.json()
            likes = data.get("likesSummary", {}).get("totalLikes", 0)
            comments = data.get("commentsSummary", {}).get("totalFirstLevelComments", 0)
            shares = data.get("sharesSummary", {}).get("totalShares", 0) if "sharesSummary" in data else 0

            # Try to get impression / click data from share statistics
            impressions = 0
            clicks = 0

            stats_response = await client.get(
                f"https://api.linkedin.com/v2/organizationalEntityShareStatistics"
                f"?q=organizationalEntity&shares[0]={encoded_urn}",
                headers=headers,
            )
            if stats_response.status_code == 200:
                elements = stats_response.json().get("elements", [])
                if elements:
                    stats = elements[0].get("totalShareStatistics", {})
                    impressions = stats.get("impressionCount", 0)
                    clicks = stats.get("clickCount", 0)

            # If impressions endpoint failed or returned 0, estimate from
            # engagement (rough heuristic: LinkedIn avg engagement rate ~3-5%)
            if impressions == 0:
                total_engagements = likes + comments + shares
                # Estimate: assume ~4% engagement rate
                impressions = max(total_engagements * 25, total_engagements) if total_engagements else 0

            total_engagements = likes + comments + shares
            engagement_rate = round(total_engagements / impressions, 4) if impressions else 0.0

            return {
                "impressions": impressions,
                "clicks": clicks,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "engagement_rate": engagement_rate,
                "platform": "linkedin",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    except httpx.TimeoutException:
        logger.warning("LinkedIn metrics request timed out for %s", post_urn)
        return {"error": "api_unavailable"}
    except Exception as exc:
        logger.error("LinkedIn metrics fetch error: %s", exc, exc_info=True)
        return {"error": "api_unavailable"}


# ============ X / TWITTER METRICS ============

async def fetch_x_post_metrics(
    tweet_id: str,
    access_token: str,
) -> Dict[str, Any]:
    """Fetch engagement metrics for a tweet / X post.

    Uses the X API v2 tweets endpoint with public_metrics and
    non_public_metrics (impression_count requires OAuth 2.0 User
    Context with tweet.read scope).

    Args:
        tweet_id: The tweet/post ID string
        access_token: Decrypted OAuth access token

    Returns:
        Dict with metric values, or {"error": "..."} on failure.
    """
    url = (
        f"https://api.twitter.com/2/tweets/{tweet_id}"
        f"?tweet.fields=public_metrics,non_public_metrics,organic_metrics"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 401:
                return {"error": "token_expired"}
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                return {"error": "rate_limited", "retry_after": retry_after}
            if response.status_code != 200:
                logger.error(
                    "X tweets endpoint returned %s: %s",
                    response.status_code,
                    response.text[:300],
                )
                return {"error": "api_unavailable"}

            data = response.json().get("data", {})
            public = data.get("public_metrics", {})
            non_public = data.get("non_public_metrics", {})

            likes = public.get("like_count", 0)
            retweets = public.get("retweet_count", 0)
            replies = public.get("reply_count", 0)
            bookmarks = public.get("bookmark_count", 0)
            quote_tweets = public.get("quote_count", 0)
            impressions = non_public.get("impression_count", 0)

            # If non_public_metrics unavailable, estimate impressions
            if impressions == 0:
                total_engagements = likes + retweets + replies + bookmarks + quote_tweets
                impressions = max(total_engagements * 30, total_engagements) if total_engagements else 0

            total_engagements = likes + retweets + replies + bookmarks + quote_tweets
            engagement_rate = round(total_engagements / impressions, 4) if impressions else 0.0

            return {
                "impressions": impressions,
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "bookmarks": bookmarks,
                "quote_tweets": quote_tweets,
                "engagement_rate": engagement_rate,
                "platform": "x",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    except httpx.TimeoutException:
        logger.warning("X metrics request timed out for tweet %s", tweet_id)
        return {"error": "api_unavailable"}
    except Exception as exc:
        logger.error("X metrics fetch error: %s", exc, exc_info=True)
        return {"error": "api_unavailable"}


# ============ INSTAGRAM METRICS ============

async def fetch_instagram_post_metrics(
    media_id: str,
    access_token: str,
) -> Dict[str, Any]:
    """Fetch engagement metrics for an Instagram media post.

    Uses the Instagram Graph API (via Meta) media insights endpoint.
    Requires instagram_basic scope and a business/creator account.

    Args:
        media_id: The Instagram media ID
        access_token: Decrypted OAuth access token

    Returns:
        Dict with metric values, or {"error": "..."} on failure.
    """
    metrics_param = "impressions,reach,likes,comments,shares,saved"
    url = (
        f"https://graph.instagram.com/{media_id}/insights"
        f"?metric={metrics_param}&access_token={access_token}"
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)

            if response.status_code == 401 or (
                response.status_code == 400
                and "OAuthException" in response.text
            ):
                return {"error": "token_expired"}
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                return {"error": "rate_limited", "retry_after": retry_after}
            if response.status_code != 200:
                logger.error(
                    "Instagram insights returned %s: %s",
                    response.status_code,
                    response.text[:300],
                )
                return {"error": "api_unavailable"}

            insights_data = response.json().get("data", [])
            metrics_map = {}
            for item in insights_data:
                name = item.get("name", "")
                values = item.get("values", [{}])
                metrics_map[name] = values[0].get("value", 0) if values else 0

            impressions = metrics_map.get("impressions", 0)
            reach = metrics_map.get("reach", 0)
            likes = metrics_map.get("likes", 0)
            comments = metrics_map.get("comments", 0)
            shares = metrics_map.get("shares", 0)
            saved = metrics_map.get("saved", 0)

            total_engagements = likes + comments + shares + saved
            engagement_rate = round(total_engagements / impressions, 4) if impressions else 0.0

            return {
                "impressions": impressions,
                "reach": reach,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saved": saved,
                "engagement_rate": engagement_rate,
                "platform": "instagram",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    except httpx.TimeoutException:
        logger.warning("Instagram insights request timed out for media %s", media_id)
        return {"error": "api_unavailable"}
    except Exception as exc:
        logger.error("Instagram metrics fetch error: %s", exc, exc_info=True)
        return {"error": "api_unavailable"}


# ============ UNIFIED UPDATE FUNCTION ============

async def update_post_performance(
    job_id: str,
    user_id: str,
    platform: str,
) -> bool:
    """Fetch real metrics for a published post and persist them.

    Reads the post_id / tweet_ids from the content_job document,
    gets the decrypted access token, calls the appropriate platform
    fetcher, then writes results to:
      - db.content_jobs[job_id].performance_data   (per-post metrics)
      - db.persona_engines[user_id].performance_intelligence  (aggregated)

    Args:
        job_id: Content job ID
        user_id: User ID
        platform: "linkedin" | "x" | "instagram"

    Returns:
        True on success, False otherwise (never raises).
    """
    try:
        # ---- Load the content job ----
        job = await db.content_jobs.find_one({"job_id": job_id, "user_id": user_id})
        if not job:
            logger.warning("update_post_performance: job %s not found", job_id)
            return False

        publish_result = job.get("publish_result", {})
        if not publish_result:
            logger.warning("update_post_performance: no publish_result on job %s", job_id)
            return False

        # ---- Get the decrypted access token ----
        from routes.platforms import get_platform_token
        access_token = await get_platform_token(user_id, platform)
        if not access_token:
            logger.warning(
                "update_post_performance: no valid token for user=%s platform=%s",
                user_id,
                platform,
            )
            return False

        # ---- Fetch metrics from the right platform ----
        metrics: Dict[str, Any] = {}

        if platform == "linkedin":
            post_id = publish_result.get("post_id", "")
            if not post_id:
                logger.warning("No LinkedIn post_id in publish_result for job %s", job_id)
                return False
            metrics = await fetch_linkedin_post_metrics(post_id, access_token)

        elif platform == "x":
            tweet_ids = publish_result.get("tweet_ids", [])
            tweet_id = tweet_ids[0] if tweet_ids else publish_result.get("post_id", "")
            if not tweet_id:
                logger.warning("No tweet_id in publish_result for job %s", job_id)
                return False
            metrics = await fetch_x_post_metrics(tweet_id, access_token)

        elif platform == "instagram":
            post_id = publish_result.get("post_id", "")
            if not post_id:
                logger.warning("No Instagram post_id in publish_result for job %s", job_id)
                return False
            metrics = await fetch_instagram_post_metrics(post_id, access_token)

        else:
            logger.warning("Unknown platform %s for job %s", platform, job_id)
            return False

        # ---- Check for fetch errors ----
        if "error" in metrics:
            logger.warning(
                "Metrics fetch returned error for job=%s platform=%s: %s",
                job_id,
                platform,
                metrics,
            )
            # Still store the error so we can see it, but mark as failed
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "performance_data.last_error": metrics,
                        "performance_data.last_attempt": datetime.now(timezone.utc),
                    }
                },
            )
            return False

        # ---- Persist per-job metrics ----
        now = datetime.now(timezone.utc)
        existing_perf = job.get("performance_data", {})
        history = existing_perf.get("history", [])
        history.append({**metrics, "collected_at": now.isoformat()})

        await db.content_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "performance_data": {
                        "latest": metrics,
                        "history": history,
                        "updated_at": now,
                    },
                    "performance_metrics": metrics,  # backward compat with analyst.py
                    "metrics_updated_at": now,
                }
            },
        )

        # ---- Aggregate into persona_engines.performance_intelligence ----
        await _aggregate_performance_intelligence(user_id, platform, metrics)

        logger.info(
            "Updated performance data for job=%s platform=%s engagement_rate=%.4f",
            job_id,
            platform,
            metrics.get("engagement_rate", 0),
        )
        return True

    except Exception as exc:
        logger.error(
            "update_post_performance failed for job=%s: %s",
            job_id,
            exc,
            exc_info=True,
        )
        return False


async def _aggregate_performance_intelligence(
    user_id: str,
    platform: str,
    metrics: Dict[str, Any],
) -> None:
    """Aggregate a single metric snapshot into the user's
    persona_engines.performance_intelligence document.

    Maintains running averages and best/worst tracking per platform.
    """
    try:
        persona = await db.persona_engines.find_one({"user_id": user_id})
        if not persona:
            return

        perf_intel = persona.get("performance_intelligence", {})
        platform_data = perf_intel.get(platform, {
            "posts_tracked": 0,
            "total_impressions": 0,
            "total_engagements": 0,
            "avg_engagement_rate": 0.0,
            "best_engagement_rate": 0.0,
            "worst_engagement_rate": 1.0,
        })

        posts_tracked = platform_data.get("posts_tracked", 0) + 1
        total_impressions = platform_data.get("total_impressions", 0) + metrics.get("impressions", 0)

        engagement_count = metrics.get("likes", 0) + metrics.get("comments", 0) + metrics.get("shares", 0) + metrics.get("retweets", 0) + metrics.get("saved", 0) + metrics.get("bookmarks", 0)
        total_engagements = platform_data.get("total_engagements", 0) + engagement_count

        current_rate = metrics.get("engagement_rate", 0.0)
        # Running average
        old_avg = platform_data.get("avg_engagement_rate", 0.0)
        new_avg = round(old_avg + (current_rate - old_avg) / posts_tracked, 4)

        best_rate = max(platform_data.get("best_engagement_rate", 0.0), current_rate)
        worst_rate = min(platform_data.get("worst_engagement_rate", 1.0), current_rate)

        platform_data.update({
            "posts_tracked": posts_tracked,
            "total_impressions": total_impressions,
            "total_engagements": total_engagements,
            "avg_engagement_rate": new_avg,
            "best_engagement_rate": best_rate,
            "worst_engagement_rate": worst_rate,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        })

        perf_intel[platform] = platform_data
        perf_intel["last_updated"] = datetime.now(timezone.utc).isoformat()

        await db.persona_engines.update_one(
            {"user_id": user_id},
            {"$set": {"performance_intelligence": perf_intel}},
        )

    except Exception as exc:
        logger.error(
            "Failed to aggregate performance intelligence for user=%s: %s",
            user_id,
            exc,
            exc_info=True,
        )
