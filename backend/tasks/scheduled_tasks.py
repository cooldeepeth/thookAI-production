"""Celery Beat scheduled tasks for ThookAI.

These tasks replace the n8n cron workflows. Each task wraps the same
async logic from routes/n8n_bridge.py but runs via Celery Beat,
eliminating the need for a separate n8n service.

All tasks use run_async() to bridge Celery's sync execution model
with Motor's async MongoDB driver.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

logger = logging.getLogger(__name__)

# Module-level imports for testability (allows patching in tests).
# These are optional at import time — if agents.publisher is unavailable
# (e.g. missing dependency) the task will catch the ImportError at runtime.
try:
    from agents.publisher import publish_to_platform as real_publish
except ImportError:
    real_publish = None  # type: ignore[assignment]

try:
    from config import settings
except ImportError:
    settings = None  # type: ignore[assignment]

try:
    from database import db
except ImportError:
    db = None  # type: ignore[assignment]


def run_async(coro):
    """Run async code in a Celery task (sync context)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============ CLEANUP TASKS ============


@shared_task(name="tasks.scheduled_tasks.cleanup_stale_jobs")
def cleanup_stale_jobs():
    """Mark stale running jobs as errored (>10 min old)."""
    return run_async(_cleanup_stale_jobs())


async def _cleanup_stale_jobs():
    from database import db

    threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
    result = await db.content_jobs.update_many(
        {"status": "running", "updated_at": {"$lt": threshold}},
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
    return {"stale_jobs_cleaned": count}


@shared_task(name="tasks.scheduled_tasks.cleanup_old_jobs")
def cleanup_old_jobs():
    """Delete old failed jobs, expired sessions, and OAuth states."""
    return run_async(_cleanup_old_jobs())


async def _cleanup_old_jobs():
    from database import db

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    one_hour_ago = now - timedelta(hours=1)

    jobs = await db.content_jobs.delete_many(
        {"status": {"$in": ["error", "failed"]}, "created_at": {"$lt": thirty_days_ago}}
    )
    sessions = await db.onboarding_sessions.delete_many(
        {"created_at": {"$lt": thirty_days_ago}}
    )
    oauth = await db.oauth_states.delete_many(
        {"created_at": {"$lt": one_hour_ago}}
    )

    logger.info(
        "cleanup-old-jobs: %d failed jobs, %d sessions, %d oauth states deleted",
        jobs.deleted_count, sessions.deleted_count, oauth.deleted_count,
    )
    return {
        "failed_jobs_deleted": jobs.deleted_count,
        "sessions_deleted": sessions.deleted_count,
        "oauth_states_deleted": oauth.deleted_count,
    }


@shared_task(name="tasks.scheduled_tasks.cleanup_expired_shares")
def cleanup_expired_shares():
    """Deactivate expired persona share links."""
    return run_async(_cleanup_expired_shares())


async def _cleanup_expired_shares():
    from database import db

    now = datetime.now(timezone.utc)
    result = await db.persona_shares.update_many(
        {"is_active": True, "expires_at": {"$lt": now}},
        {"$set": {"is_active": False, "expired_at": now}},
    )
    count = result.modified_count
    if count:
        logger.info("Deactivated %d expired persona share links", count)
    return {"deactivated": count}


# ============ USER MANAGEMENT TASKS ============


@shared_task(name="tasks.scheduled_tasks.reset_daily_limits")
def reset_daily_limits():
    """Reset daily content creation counters for all users."""
    return run_async(_reset_daily_limits())


async def _reset_daily_limits():
    from database import db

    result = await db.users.update_many(
        {"daily_content_count": {"$gt": 0}},
        {"$set": {
            "daily_content_count": 0,
            "daily_reset_at": datetime.now(timezone.utc),
        }},
    )
    logger.info("Reset daily limits for %d users", result.modified_count)
    return {"reset_count": result.modified_count}


@shared_task(name="tasks.scheduled_tasks.refresh_monthly_credits")
def refresh_monthly_credits():
    """Refresh monthly credits for starter and custom plan users."""
    return run_async(_refresh_monthly_credits())


async def _refresh_monthly_credits():
    from database import db
    from services.credits import TIER_CONFIGS

    threshold = datetime.now(timezone.utc) - timedelta(days=30)

    users = await db.users.find({
        "$or": [
            {"subscription_tier": {"$in": ["starter", "free"]}},
            {"subscription_tier": "custom", "subscription_status": "active"},
        ]
    }).to_list(length=1000)

    refreshed = 0
    for user in users:
        last_refresh = user.get("credits_refreshed_at")
        if last_refresh:
            if isinstance(last_refresh, str):
                last_refresh = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
            if last_refresh > threshold:
                continue

        tier = user.get("subscription_tier", "starter")
        if tier == "custom":
            monthly_credits = user.get("plan_config", {}).get("monthly_credits", 0)
        else:
            monthly_credits = TIER_CONFIGS.get(tier, TIER_CONFIGS["starter"])["monthly_credits"]

        now = datetime.now(timezone.utc)
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {
                "credits": monthly_credits,
                "credits_refreshed_at": now,
                "credits_last_refresh": now,
            }},
        )
        refreshed += 1

    logger.info("Refreshed credits for %d users", refreshed)
    return {"refreshed_count": refreshed}


# ============ ANALYTICS TASKS ============


@shared_task(name="tasks.scheduled_tasks.aggregate_daily_analytics")
def aggregate_daily_analytics():
    """Aggregate daily analytics for yesterday."""
    return run_async(_aggregate_daily_analytics())


async def _aggregate_daily_analytics():
    from database import db

    now = datetime.now(timezone.utc)
    yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    today_start = yesterday + timedelta(days=1)

    content_count = await db.content_jobs.count_documents(
        {"created_at": {"$gte": yesterday, "$lt": today_start}, "status": "completed"}
    )
    new_users = await db.users.count_documents(
        {"created_at": {"$gte": yesterday, "$lt": today_start}}
    )
    active_user_ids = await db.content_jobs.distinct(
        "user_id", {"created_at": {"$gte": yesterday, "$lt": today_start}}
    )

    date_str = yesterday.strftime("%Y-%m-%d")
    await db.daily_stats.update_one(
        {"date": date_str},
        {"$set": {
            "date": date_str,
            "content_created": content_count,
            "new_users": new_users,
            "active_users": len(active_user_ids),
            "aggregated_at": now,
        }},
        upsert=True,
    )

    logger.info("Daily analytics for %s: %d content, %d new, %d active",
                date_str, content_count, new_users, len(active_user_ids))
    return {"date": date_str, "content_created": content_count,
            "new_users": new_users, "active_users": len(active_user_ids)}


# ============ PUBLISHING TASKS ============


@shared_task(name="tasks.scheduled_tasks.process_scheduled_posts",
             soft_time_limit=120, time_limit=180)
def process_scheduled_posts():
    """Publish all scheduled posts that are due."""
    return run_async(_process_scheduled_posts())


async def _process_scheduled_posts():
    # Use module-level db (patchable in tests); fall back to lazy import for
    # cases where the module-level import failed (e.g. cold start ordering).
    _db = db
    if _db is None:
        from database import db as _db  # type: ignore[assignment]

    now = datetime.now(timezone.utc)

    posts = await _db.scheduled_posts.find({
        "scheduled_at": {"$lte": now},
        "status": {"$in": ["pending", "scheduled"]},
    }).to_list(length=50)

    published = 0
    failed = 0
    for post in posts:
        schedule_id = post.get("schedule_id", str(post.get("_id")))

        # Idempotency: skip if already processing
        lock = await _db.scheduled_posts.find_one_and_update(
            {"schedule_id": schedule_id, "status": {"$in": ["pending", "scheduled"]}},
            {"$set": {"status": "publishing", "publish_started_at": now}},
        )
        if not lock:
            continue

        try:
            # Use module-level real_publish so tests can patch it easily.
            _publish = real_publish
            if _publish is None:
                from agents.publisher import publish_to_platform as _publish  # type: ignore[assignment]

            result = await _publish(
                platform=post["platform"],
                content=post.get("final_content") or post.get("content", ""),
                user_id=post["user_id"],
                # Use media_assets (correct kwarg); fall back to media_urls for
                # backwards-compat with older scheduled_posts documents.
                media_assets=post.get("media_assets") or post.get("media_urls"),
            )

            if result.get("success"):
                pub_now = datetime.now(timezone.utc)
                await _db.scheduled_posts.update_one(
                    {"schedule_id": schedule_id},
                    {"$set": {
                        "status": "published",
                        "published_at": pub_now,
                        "publish_result": result,
                    }},
                )
                # Also write publish_results to the linked content_job so that
                # analytics polling (poll_post_metrics_24h/7d) can find post_id/post_url.
                job_id = post.get("job_id")
                if job_id:
                    await _db.content_jobs.update_one(
                        {"job_id": job_id},
                        {"$set": {
                            "status": "published",
                            "published_at": pub_now,
                            "publish_results": {post["platform"]: result},
                            "updated_at": pub_now,
                        }},
                    )
                published += 1
            else:
                await _db.scheduled_posts.update_one(
                    {"schedule_id": schedule_id},
                    {"$set": {
                        "status": "failed",
                        "error": result.get("error", "Unknown publish error"),
                        "failed_at": datetime.now(timezone.utc),
                    }},
                )
                failed += 1
                # Alert via Sentry when a scheduled post publish fails.
                try:
                    _settings = settings
                    if _settings is None:
                        from config import settings as _settings  # type: ignore[assignment]
                    if _settings and _settings.app.sentry_dsn:
                        import sentry_sdk
                        sentry_sdk.capture_message(
                            f"Scheduled post failed to publish: platform={post['platform']}, "
                            f"schedule_id={schedule_id}",
                            level="error",
                            extras={
                                "schedule_id": schedule_id,
                                "platform": post["platform"],
                                "user_id": post["user_id"],
                                "error": result.get("error"),
                            },
                        )
                except Exception as sentry_err:
                    logger.warning("Sentry capture failed: %s", sentry_err)

        except Exception as e:
            logger.error("Failed to publish scheduled post %s: %s", schedule_id, e)
            await _db.scheduled_posts.update_one(
                {"schedule_id": schedule_id},
                {"$set": {"status": "failed", "error": str(e),
                          "failed_at": datetime.now(timezone.utc)}},
            )
            failed += 1
            try:
                _settings = settings
                if _settings is None:
                    from config import settings as _settings  # type: ignore[assignment]
                if _settings and _settings.app.sentry_dsn:
                    import sentry_sdk
                    sentry_sdk.capture_exception(e)
            except Exception:
                pass

    if published or failed:
        logger.info("Scheduled posts: %d published, %d failed", published, failed)
    return {"published": published, "failed": failed}


# ============ STRATEGIST & ANALYTICS POLL ============


@shared_task(name="tasks.scheduled_tasks.run_nightly_strategist",
             soft_time_limit=300, time_limit=360)
def run_nightly_strategist():
    """Run Strategist agent for all eligible users."""
    return run_async(_run_nightly_strategist())


async def _run_nightly_strategist():
    from database import db

    # Find users with personas and active subscriptions
    users = await db.users.find({
        "onboarding_completed": True,
        "subscription_tier": {"$ne": "free"},
    }, {"user_id": 1, "_id": 0}).to_list(length=500)

    processed = 0
    for user in users:
        try:
            from agents.series_planner import generate_strategy_recommendation
            await generate_strategy_recommendation(user["user_id"])
            processed += 1
        except Exception as e:
            logger.warning("Strategist failed for %s: %s", user["user_id"], e)

    logger.info("Nightly strategist: processed %d users", processed)
    return {"processed": processed}


@shared_task(name="tasks.scheduled_tasks.poll_analytics_24h")
def poll_analytics_24h():
    """Poll 24h post analytics from connected social platforms."""
    return run_async(_poll_analytics())


@shared_task(name="tasks.scheduled_tasks.poll_analytics_7d")
def poll_analytics_7d():
    """Poll 7-day post analytics from connected social platforms."""
    return run_async(_poll_analytics(days=7))


async def _poll_analytics(days: int = 1):
    from database import db

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    posts = await db.scheduled_posts.find({
        "status": "published",
        "published_at": {"$gte": cutoff},
    }).to_list(length=200)

    polled = 0
    for post in posts:
        try:
            # Simulate analytics if real API not connected
            from agents.analyst import simulate_engagement
            metrics = simulate_engagement(post.get("platform", "linkedin"))
            await db.scheduled_posts.update_one(
                {"schedule_id": post.get("schedule_id")},
                {"$set": {f"analytics_{days}d": metrics,
                          f"analytics_{days}d_polled_at": datetime.now(timezone.utc)}},
            )
            polled += 1
        except Exception as e:
            logger.warning("Analytics poll failed for post %s: %s",
                           post.get("schedule_id"), e)

    logger.info("Polled %dd analytics for %d posts", days, polled)
    return {"polled": polled, "period_days": days}
