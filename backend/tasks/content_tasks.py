"""
Content Processing Tasks for ThookAI

Async Celery tasks for:
- Content pipeline processing
- Scheduled post publishing
- Daily limit resets
- Cleanup operations
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============ CONTENT PIPELINE ============

@shared_task(bind=True, max_retries=2, default_retry_delay=30,
             soft_time_limit=240, time_limit=300)
def run_content_pipeline(
    self,
    job_id: str,
    user_id: str,
    platform: str,
    content_type: str,
    raw_input: str,
    upload_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run the full content generation pipeline asynchronously.

    Pipeline: Commander → Scout → Thinker → Writer → QC

    Time limits:
    - soft_time_limit=240s — raises SoftTimeLimitExceeded, allowing graceful cleanup
    - time_limit=300s — hard kill by the Celery worker if soft limit is not honoured
    """
    logger.info(f"Starting content pipeline task for job {job_id}")

    async def _run_pipeline():
        from agents.pipeline import run_agent_pipeline

        try:
            await run_agent_pipeline(
                job_id=job_id,
                user_id=user_id,
                platform=platform,
                content_type=content_type,
                raw_input=raw_input,
                upload_ids=upload_ids or [],
            )
            return {"success": True, "job_id": job_id}
        except Exception as e:
            logger.error(f"Content pipeline failed for job {job_id}: {e}")
            raise

    try:
        return run_async(_run_pipeline())
    except SoftTimeLimitExceeded:
        logger.error(f"Content pipeline soft time limit exceeded for job {job_id}")
        # Mark job as timed out in the DB (synchronous fallback since the
        # event loop used by run_async has been torn down at this point).
        async def _mark_timeout():
            from database import db
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "error",
                    "current_agent": "error",
                    "error": "Content generation timed out. Please try again.",
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
        try:
            run_async(_mark_timeout())
        except Exception:
            logger.exception("Failed to mark timed-out job %s as error", job_id)
        return {"success": False, "job_id": job_id, "error": "timeout"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


# ============ SCHEDULED POSTS ============

@shared_task
def process_scheduled_posts() -> Dict[str, Any]:
    """
    Process posts scheduled for publishing.
    
    Runs every 5 minutes via Celery Beat.
    """
    logger.info("Processing scheduled posts...")
    
    async def _process():
        from database import db
        
        now = datetime.now(timezone.utc)
        
        # Find posts due for publishing
        due_posts = await db.scheduled_posts.find({
            "status": "scheduled",
            "scheduled_at": {"$lte": now}
        }).to_list(length=100)
        
        published = 0
        failed = 0
        
        for post in due_posts:
            try:
                # Get user's platform tokens
                user_id = post["user_id"]
                platform = post["platform"]
                
                token = await db.platform_tokens.find_one({
                    "user_id": user_id,
                    "platform": platform
                })
                
                if not token:
                    # Mark as failed - no platform connection
                    await db.scheduled_posts.update_one(
                        {"schedule_id": post["schedule_id"]},
                        {"$set": {
                            "status": "failed",
                            "error": "Platform not connected",
                            "processed_at": now
                        }}
                    )
                    failed += 1
                    # Fire outbound webhook for post.failed (no token)
                    try:
                        from services.webhook_service import fire_webhook
                        await fire_webhook(user_id, "post.failed", {
                            "schedule_id": post.get("schedule_id"),
                            "job_id": post.get("job_id"),
                            "platform": platform,
                            "error": "Platform not connected",
                        })
                    except Exception as wh_err:
                        logger.warning(
                            "Failed to fire post.failed webhook for schedule %s: %s",
                            post.get("schedule_id"), wh_err,
                        )
                    continue
                
                # Publish via real platform APIs (production) or simulation (dev)
                success = await _publish_to_platform(
                    platform=platform,
                    content=post.get("content"),
                    token=token
                )
                
                if success:
                    await db.scheduled_posts.update_one(
                        {"schedule_id": post["schedule_id"]},
                        {"$set": {
                            "status": "published",
                            "published_at": now,
                            "processed_at": now
                        }}
                    )
                    published += 1

                    # Fire notification to user — never crash the publishing flow
                    try:
                        from services.notification_service import create_notification

                        content_preview = (post.get("content") or "")[:100]
                        if len(post.get("content") or "") > 100:
                            content_preview += "..."
                        await create_notification(
                            user_id=user_id,
                            type="post_published",
                            title=f"Your {platform} post was published",
                            body=content_preview,
                            metadata={
                                "platform": platform,
                                "schedule_id": post.get("schedule_id"),
                                "job_id": post.get("job_id"),
                            },
                        )
                    except Exception as notif_err:
                        logger.warning(
                            "Failed to create publish notification for schedule %s: %s",
                            post.get("schedule_id"),
                            notif_err,
                        )

                    # Schedule follow-up analytics polling
                    job_id = post.get("job_id", post.get("schedule_id"))
                    if job_id:
                        try:
                            poll_post_metrics_24h.apply_async(
                                args=[job_id, user_id, platform],
                                countdown=86400,  # 24 hours
                            )
                            poll_post_metrics_7d.apply_async(
                                args=[job_id, user_id, platform],
                                countdown=604800,  # 7 days
                            )
                        except Exception as poll_err:
                            logger.warning(
                                "Failed to schedule metrics polling for job %s: %s",
                                job_id,
                                poll_err,
                            )

                    # Fire outbound webhook for post.published
                    try:
                        from services.webhook_service import fire_webhook
                        await fire_webhook(user_id, "post.published", {
                            "schedule_id": post.get("schedule_id"),
                            "job_id": post.get("job_id"),
                            "platform": platform,
                            "published_at": now.isoformat(),
                        })
                    except Exception as wh_err:
                        logger.warning(
                            "Failed to fire post.published webhook for schedule %s: %s",
                            post.get("schedule_id"), wh_err,
                        )
                else:
                    await db.scheduled_posts.update_one(
                        {"schedule_id": post["schedule_id"]},
                        {"$set": {
                            "status": "failed",
                            "error": "Publishing failed",
                            "processed_at": now
                        }}
                    )
                    failed += 1

                    # Fire outbound webhook for post.failed
                    try:
                        from services.webhook_service import fire_webhook
                        await fire_webhook(user_id, "post.failed", {
                            "schedule_id": post.get("schedule_id"),
                            "job_id": post.get("job_id"),
                            "platform": platform,
                            "error": "Publishing failed",
                        })
                    except Exception as wh_err:
                        logger.warning(
                            "Failed to fire post.failed webhook for schedule %s: %s",
                            post.get("schedule_id"), wh_err,
                        )
                    
            except Exception as e:
                logger.error(f"Failed to process scheduled post {post.get('schedule_id')}: {e}")
                failed += 1
        
        logger.info(f"Processed scheduled posts: {published} published, {failed} failed")
        return {"published": published, "failed": failed}
    
    return run_async(_process())


async def _publish_to_platform(platform: str, content: str, token: dict) -> bool:
    """
    Publish content to a social platform.

    In production: delegates to the real publisher agent.  Never simulates.
    In dev/test: falls back to simulation if the publisher module is missing.
    Returns False on any error (never raises).
    """
    from config import settings

    try:
        # Check if token is valid/not expired
        if token.get("expires_at"):
            expires = token["expires_at"]
            if isinstance(expires, str):
                expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if expires < datetime.now(timezone.utc):
                logger.warning("Token expired for platform %s", platform)
                return False

        access_token = token.get("access_token", "")
        user_id = token.get("user_id", "")

        # --- Production: always call the real publisher, no simulation ---
        if settings.app.is_production:
            from agents.publisher import publish_to_platform

            try:
                result = await publish_to_platform(
                    platform=platform,
                    content=content,
                    access_token=access_token,
                    user_id=user_id,
                )
            except Exception as pub_exc:
                logger.error(
                    "Production publish_to_platform failed for %s: %s",
                    platform,
                    pub_exc,
                    exc_info=True,
                )
                return False

            if isinstance(result, dict):
                if not result.get("success"):
                    logger.error(
                        "Publishing to %s failed: %s",
                        platform,
                        result.get("error", "unknown error"),
                    )
                return result.get("success", False)
            return bool(result)

        # --- Dev / test: try real publisher, fall back to simulation ---
        try:
            from agents.publisher import publish_to_platform

            result = await publish_to_platform(
                platform=platform,
                content=content,
                access_token=access_token,
                user_id=user_id,
            )
            if isinstance(result, dict):
                if not result.get("success"):
                    logger.warning(
                        "[DEV] Publishing to %s failed: %s",
                        platform,
                        result.get("error", "unknown error"),
                    )
                return result.get("success", False)
            return bool(result)
        except ImportError:
            logger.warning(
                "[SIMULATED] Publishing to %s (publisher agent not available, dev mode): %s...",
                platform,
                (content or "")[:50],
            )
            return True
        except Exception as pub_exc:
            logger.warning("[DEV] publish_to_platform raised for %s: %s", platform, pub_exc)
            return False  # Don't hide real errors

    except Exception as exc:
        logger.error("_publish_to_platform failed for %s: %s", platform, exc, exc_info=True)
        return False


# ============ DAILY LIMITS ============

@shared_task
def reset_daily_limits() -> Dict[str, Any]:
    """
    Reset daily content creation counters for all users.
    
    Runs at midnight UTC via Celery Beat.
    """
    logger.info("Resetting daily content limits...")
    
    async def _reset():
        from database import db
        
        result = await db.users.update_many(
            {"daily_content_count": {"$gt": 0}},
            {"$set": {"daily_content_count": 0, "daily_reset_at": datetime.now(timezone.utc)}}
        )
        
        logger.info(f"Reset daily limits for {result.modified_count} users")
        return {"reset_count": result.modified_count}
    
    return run_async(_reset())


# ============ CREDIT REFRESH ============

@shared_task
def refresh_monthly_credits() -> Dict[str, Any]:
    """
    Refresh monthly credits for subscribed users.
    
    Called by Stripe webhook when subscription renews, but this can also
    be run as a failsafe via Celery Beat on the 1st of each month.
    """
    logger.info("Refreshing monthly credits for subscribed users...")
    
    async def _refresh():
        from database import db
        from services.credits import TIER_CONFIGS
        
        # Find users whose subscription renewed more than 30 days ago
        # and haven't had credits refreshed
        threshold = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Get all subscribers including free tier
        # Only refresh credits for free users and paid users with active subscriptions
        users = await db.users.find({
            "$or": [
                {"subscription_tier": {"$in": ["starter", "free"]}},
                {
                    "subscription_tier": "custom",
                    "subscription_status": "active"
                }
            ]
        }).to_list(length=1000)
        
        refreshed = 0
        for user in users:
            last_refresh = user.get("credits_refreshed_at")
            if last_refresh:
                if isinstance(last_refresh, str):
                    last_refresh = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
                if last_refresh > threshold:
                    continue  # Already refreshed recently
            
            tier = user.get("subscription_tier", "starter")
            # For custom plan users, use their plan_config for credit allowance
            if tier == "custom":
                plan_config = user.get("plan_config", {})
                monthly_credits = plan_config.get("monthly_credits", 0)
            else:
                tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["starter"])
                monthly_credits = tier_config["monthly_credits"]
            
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {
                    "credits": monthly_credits,
                    "credits_refreshed_at": datetime.now(timezone.utc),
                    "credits_last_refresh": datetime.now(timezone.utc),
                }}
            )
            refreshed += 1
        
        logger.info(f"Refreshed credits for {refreshed} users")
        return {"refreshed_count": refreshed}
    
    return run_async(_refresh())


# ============ CLEANUP TASKS ============

@shared_task
def cleanup_old_jobs() -> Dict[str, Any]:
    """
    Clean up old content jobs and temporary data.
    
    Runs daily via Celery Beat.
    """
    logger.info("Cleaning up old content jobs...")
    
    async def _cleanup():
        from database import db
        
        # Jobs older than 30 days
        threshold = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Delete old failed jobs (keep completed ones for history)
        result = await db.content_jobs.delete_many({
            "status": {"$in": ["error", "failed"]},
            "created_at": {"$lt": threshold}
        })
        failed_deleted = result.deleted_count
        
        # Delete old onboarding sessions
        result = await db.onboarding_sessions.delete_many({
            "created_at": {"$lt": threshold}
        })
        sessions_deleted = result.deleted_count
        
        # Delete old OAuth states (should auto-expire, but clean up anyway)
        result = await db.oauth_states.delete_many({
            "created_at": {"$lt": datetime.now(timezone.utc) - timedelta(hours=1)}
        })
        oauth_deleted = result.deleted_count
        
        logger.info(f"Cleanup complete: {failed_deleted} failed jobs, {sessions_deleted} sessions, {oauth_deleted} OAuth states")
        return {
            "failed_jobs_deleted": failed_deleted,
            "sessions_deleted": sessions_deleted,
            "oauth_states_deleted": oauth_deleted
        }
    
    return run_async(_cleanup())


@shared_task
def cleanup_expired_shares() -> Dict[str, Any]:
    """
    Deactivate expired persona share links.
    """
    logger.info("Cleaning up expired persona shares...")
    
    async def _cleanup():
        from database import db
        
        now = datetime.now(timezone.utc)
        
        result = await db.persona_shares.update_many(
            {
                "is_active": True,
                "expires_at": {"$lt": now}
            },
            {"$set": {"is_active": False, "expired_at": now}}
        )
        
        logger.info(f"Deactivated {result.modified_count} expired share links")
        return {"deactivated": result.modified_count}
    
    return run_async(_cleanup())


# ============ PERFORMANCE INTELLIGENCE ============

@shared_task
def update_performance_intelligence(user_id: str) -> Dict[str, Any]:
    """Recalculate performance intelligence after new metrics arrive.

    Runs both performance intelligence aggregation and optimal posting
    time calculation for a single user.  Intended to be called after
    social analytics data is ingested for the user's published posts.
    """

    async def _update():
        from services.persona_refinement import (
            calculate_optimal_posting_times,
            calculate_performance_intelligence,
        )

        perf = await calculate_performance_intelligence(user_id)
        times = await calculate_optimal_posting_times(user_id)
        logger.info(f"Performance intelligence updated for user {user_id}")
        return {
            "user_id": user_id,
            "performance_intelligence": perf,
            "optimal_posting_times": times,
        }

    return run_async(_update())


# ============ ANALYTICS AGGREGATION ============

@shared_task
def aggregate_daily_analytics() -> Dict[str, Any]:
    """
    Aggregate daily analytics for reporting.
    
    Runs daily at 1 AM UTC via Celery Beat.
    """
    logger.info("Aggregating daily analytics...")
    
    async def _aggregate():
        from database import db
        
        yesterday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        today = yesterday + timedelta(days=1)
        
        # Count content created
        content_count = await db.content_jobs.count_documents({
            "created_at": {"$gte": yesterday, "$lt": today},
            "status": "completed"
        })
        
        # Count new users
        new_users = await db.users.count_documents({
            "created_at": {"$gte": yesterday, "$lt": today}
        })
        
        # Count active users (any content creation)
        active_users = len(await db.content_jobs.distinct("user_id", {
            "created_at": {"$gte": yesterday, "$lt": today}
        }))
        
        # Store daily stats
        await db.daily_stats.update_one(
            {"date": yesterday.strftime("%Y-%m-%d")},
            {"$set": {
                "date": yesterday.strftime("%Y-%m-%d"),
                "content_created": content_count,
                "new_users": new_users,
                "active_users": active_users,
                "aggregated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        logger.info(f"Daily analytics aggregated: {content_count} content, {new_users} new users, {active_users} active")
        return {
            "date": yesterday.strftime("%Y-%m-%d"),
            "content_created": content_count,
            "new_users": new_users,
            "active_users": active_users
        }
    
    return run_async(_aggregate())


# ============ SOCIAL ANALYTICS POLLING ============

@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def poll_post_metrics_24h(self, job_id: str, user_id: str, platform: str) -> Dict[str, Any]:
    """Poll post metrics 24 hours after publishing.

    Fetches real engagement data from the platform API and persists it
    to the content_job document and the user's performance_intelligence.

    Retries up to 2 times with 5-minute delays on transient failures.
    """
    logger.info("Polling 24h metrics for job=%s platform=%s", job_id, platform)

    async def _poll():
        from services.social_analytics import update_post_performance

        success = await update_post_performance(job_id, user_id, platform)
        if not success:
            logger.warning("24h metrics poll returned False for job=%s", job_id)
        return {"success": success, "job_id": job_id, "interval": "24h"}

    try:
        return run_async(_poll())
    except Exception as exc:
        logger.error("poll_post_metrics_24h failed for job=%s: %s", job_id, exc)
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def poll_post_metrics_7d(self, job_id: str, user_id: str, platform: str) -> Dict[str, Any]:
    """Poll post metrics 7 days after publishing.

    Captures longer-term engagement data (evergreen reach, late shares)
    and updates the stored performance data accordingly.

    Retries up to 2 times with 5-minute delays on transient failures.
    """
    logger.info("Polling 7d metrics for job=%s platform=%s", job_id, platform)

    async def _poll():
        from services.social_analytics import update_post_performance

        success = await update_post_performance(job_id, user_id, platform)
        if not success:
            logger.warning("7d metrics poll returned False for job=%s", job_id)
        return {"success": success, "job_id": job_id, "interval": "7d"}

    try:
        return run_async(_poll())
    except Exception as exc:
        logger.error("poll_post_metrics_7d failed for job=%s: %s", job_id, exc)
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


# ============ STALE JOB CLEANUP ============

@shared_task(name='tasks.content_tasks.cleanup_stale_running_jobs')
def cleanup_stale_running_jobs() -> Dict[str, Any]:
    """Find and mark stale running jobs as errored.

    A job is considered stale if its status is ``running`` and its
    ``updated_at`` timestamp is more than 10 minutes in the past.
    This guards against jobs that slip through both the in-pipeline
    ``asyncio.wait_for`` timeout and the Celery soft/hard time limits
    (e.g. worker crash, OOM kill).

    Runs every 10 minutes via Celery Beat.
    """
    logger.info("Scanning for stale running jobs...")

    async def _cleanup():
        from database import db

        threshold = datetime.now(timezone.utc) - timedelta(minutes=10)

        result = await db.content_jobs.update_many(
            {
                "status": "running",
                "updated_at": {"$lt": threshold},
            },
            {"$set": {
                "status": "error",
                "current_agent": "error",
                "error": "Job timed out (stale running job detected by cleanup task).",
                "updated_at": datetime.now(timezone.utc),
            }},
        )

        count = result.modified_count
        if count:
            logger.warning("Marked %d stale running jobs as errored", count)
        else:
            logger.info("No stale running jobs found")
        return {"stale_jobs_cleaned": count}

    return run_async(_cleanup())
