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

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
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
                    continue
                
                # Attempt to publish (placeholder - implement actual API calls)
                # In production, this would call platform-specific publishing APIs
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
                    
            except Exception as e:
                logger.error(f"Failed to process scheduled post {post.get('schedule_id')}: {e}")
                failed += 1
        
        logger.info(f"Processed scheduled posts: {published} published, {failed} failed")
        return {"published": published, "failed": failed}
    
    return run_async(_process())


async def _publish_to_platform(platform: str, content: str, token: dict) -> bool:
    """
    Publish content to a social platform.
    
    NOTE: This is a placeholder. Implement actual API calls for each platform.
    """
    # Check if token is valid/not expired
    if token.get("expires_at"):
        expires = token["expires_at"]
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
        if expires < datetime.now(timezone.utc):
            logger.warning(f"Token expired for platform {platform}")
            return False
    
    # Placeholder: In production, implement actual publishing
    # Example for LinkedIn:
    # if platform == "linkedin":
    #     return await publish_to_linkedin(content, token["access_token"])
    
    logger.info(f"[SIMULATED] Publishing to {platform}: {content[:50]}...")
    return True


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
        
        # Get all paying subscribers
        users = await db.users.find({
            "subscription_tier": {"$in": ["pro", "studio", "agency"]},
            "subscription_status": "active"
        }).to_list(length=1000)
        
        refreshed = 0
        for user in users:
            last_refresh = user.get("credits_refreshed_at")
            if last_refresh:
                if isinstance(last_refresh, str):
                    last_refresh = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
                if last_refresh > threshold:
                    continue  # Already refreshed recently
            
            tier = user.get("subscription_tier", "free")
            tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
            
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {
                    "credits": tier_config["credits"],
                    "credits_refreshed_at": datetime.now(timezone.utc)
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
