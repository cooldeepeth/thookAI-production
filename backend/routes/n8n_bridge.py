"""
ThookAI n8n Webhook Bridge

HTTP contract layer between FastAPI and n8n workflow orchestration.

Endpoints:
  POST /api/n8n/callback                         — Receive HMAC-SHA256-signed callbacks from n8n
  POST /api/n8n/trigger/{workflow_name}          — Trigger an n8n workflow (auth-protected)
  POST /api/n8n/execute/cleanup-stale-jobs       — Mark stale running jobs as errored
  POST /api/n8n/execute/cleanup-old-jobs         — Delete old failed jobs and sessions
  POST /api/n8n/execute/cleanup-expired-shares   — Deactivate expired persona share links
  POST /api/n8n/execute/reset-daily-limits       — Reset daily content creation counters
  POST /api/n8n/execute/refresh-monthly-credits  — Refresh monthly credits for users
  POST /api/n8n/execute/aggregate-daily-analytics — Aggregate daily analytics stats
  POST /api/n8n/execute/process-scheduled-posts  — Publish due scheduled posts via real publisher
  POST /api/n8n/execute/run-nightly-strategist   — Run Strategist agent for all eligible users

Security:
  - Callback endpoint verifies X-ThookAI-Signature header using HMAC-SHA256
  - Execute endpoints verify X-ThookAI-Signature via _verify_n8n_request dependency
  - Uses hmac.compare_digest for constant-time comparison (timing-safe)
  - Trigger endpoint requires authenticated user via get_current_user dependency
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from agents.publisher import publish_to_platform as real_publish_to_platform
from auth_utils import get_current_user
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/n8n", tags=["n8n"])

# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def _verify_n8n_signature(body_bytes: bytes, signature_header: str) -> bool:
    """
    Verify HMAC-SHA256 signature from n8n callback.

    Uses constant-time comparison via hmac.compare_digest to prevent
    timing attacks. Returns False immediately if webhook_secret is empty.
    """
    secret = settings.n8n.webhook_secret
    if not secret:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


# ---------------------------------------------------------------------------
# Workflow name → n8n workflow ID mapping
# ---------------------------------------------------------------------------


def _get_workflow_map() -> Dict[str, Optional[str]]:
    """Return mapping of workflow name to n8n workflow ID from settings."""
    return {
        "process-scheduled-posts": settings.n8n.workflow_scheduled_posts,
        "reset-daily-limits": settings.n8n.workflow_reset_daily_limits,
        "refresh-monthly-credits": settings.n8n.workflow_refresh_monthly_credits,
        "cleanup-old-jobs": settings.n8n.workflow_cleanup_old_jobs,
        "cleanup-expired-shares": settings.n8n.workflow_cleanup_expired_shares,
        "aggregate-daily-analytics": settings.n8n.workflow_aggregate_daily_analytics,
        "cleanup-stale-jobs": settings.n8n.workflow_cleanup_stale_jobs,
        "nightly-strategist": settings.n8n.workflow_nightly_strategist,
    }


# ---------------------------------------------------------------------------
# Workflow status notification dispatch
# ---------------------------------------------------------------------------

# Map workflow types to user-facing notification titles and body templates.
# Cleanup tasks (cleanup-stale-jobs, cleanup-old-jobs, cleanup-expired-shares)
# are intentionally excluded — they don't require user-visible notifications.
WORKFLOW_NOTIFICATION_MAP = {
    "process-scheduled-posts": {
        "title": "Scheduled posts processed",
        "body_template": "Published {published} post(s), {failed} failed",
    },
    "reset-daily-limits": {
        "title": "Daily limits reset",
        "body_template": "Daily content creation limits have been reset",
    },
    "refresh-monthly-credits": {
        "title": "Monthly credits refreshed",
        "body_template": "Your monthly credits have been refreshed",
    },
    "aggregate-daily-analytics": {
        "title": "Daily analytics aggregated",
        "body_template": "Analytics for yesterday have been processed",
    },
    "nightly-strategist": {
        "title": "Your daily content strategy is ready",
        "body_template": "New content recommendations are waiting for your review",
    },
}


async def _dispatch_workflow_notification(payload: dict) -> None:
    """
    Create workflow_status notifications for affected users.

    Reads the callback payload and creates a notification for each user in
    affected_user_ids. Cleanup tasks (not in WORKFLOW_NOTIFICATION_MAP) are
    silently skipped. Never raises — failures are logged as warnings.
    """
    workflow_type = payload.get("workflow_type", "")
    status = payload.get("status", "unknown")
    result = payload.get("result", {})
    affected_user_ids = payload.get("affected_user_ids", [])

    config = WORKFLOW_NOTIFICATION_MAP.get(workflow_type)
    if not config or not affected_user_ids:
        # Cleanup tasks or workflows with no user context — skip silently
        return

    from services.notification_service import create_notification

    title = config["title"]
    if status == "failed":
        title = f"[Failed] {title}"

    try:
        body = config["body_template"].format(**result) if result else config["body_template"]
    except (KeyError, ValueError):
        body = config["body_template"]

    for user_id in affected_user_ids:
        try:
            await create_notification(
                user_id=user_id,
                type="workflow_status",
                title=title,
                body=body,
                metadata={
                    "workflow_type": workflow_type,
                    "status": status,
                    "result": result,
                    "executed_at": payload.get("executed_at"),
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to create workflow_status notification for user %s: %s",
                user_id,
                e,
            )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/callback")
async def n8n_callback(request: Request) -> Dict[str, Any]:
    """
    Receive a signed callback from n8n.

    n8n must include the HMAC-SHA256 signature in the X-ThookAI-Signature header.
    The signature is computed over the raw request body bytes.
    Returns 401 for missing, invalid, or empty-secret signatures.
    """
    body_bytes = await request.body()

    signature_header = request.headers.get("X-ThookAI-Signature", "")
    if not signature_header:
        logger.warning("n8n callback received without X-ThookAI-Signature header")
        raise HTTPException(status_code=401, detail="Missing X-ThookAI-Signature header")

    if not _verify_n8n_signature(body_bytes, signature_header):
        logger.warning("n8n callback received with invalid signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        payload = {}

    workflow_type = payload.get("workflow_type", "unknown")
    logger.info(f"n8n callback accepted: workflow_type={workflow_type}")

    # Dispatch workflow status notifications (fire-and-forget — don't block response)
    try:
        await _dispatch_workflow_notification(payload)
    except Exception as e:
        logger.warning("Workflow notification dispatch failed: %s", e)

    return {"status": "accepted", "workflow_type": workflow_type}


@router.post("/trigger/{workflow_name}")
async def trigger_workflow(
    workflow_name: str,
    payload: Dict[str, Any] = {},
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger an n8n workflow by name.

    Authenticated endpoint — requires valid JWT via get_current_user.
    Maps the workflow_name to a configured n8n workflow ID, then fires
    a POST to the n8n webhook URL.

    Returns 404 if workflow_name is unknown or not configured.
    Returns 502 if the n8n request fails.
    """
    workflow_map = _get_workflow_map()

    if workflow_name not in workflow_map:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown workflow: {workflow_name}. Known workflows: {list(workflow_map.keys())}",
        )

    workflow_id = workflow_map[workflow_name]
    if not workflow_id:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' is not configured (missing workflow ID)",
        )

    n8n_url = f"{settings.n8n.n8n_url}/webhook/{workflow_id}"
    logger.info(f"Triggering n8n workflow '{workflow_name}' at {n8n_url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(n8n_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(f"n8n webhook returned error for '{workflow_name}': {exc.response.status_code}")
        raise HTTPException(status_code=502, detail=f"n8n returned error: {exc.response.status_code}")
    except httpx.RequestError as exc:
        logger.error(f"n8n request failed for '{workflow_name}': {exc}")
        raise HTTPException(status_code=502, detail=f"Failed to reach n8n: {exc}")

    return {"status": "triggered", "workflow": workflow_name}


# ---------------------------------------------------------------------------
# Execute endpoint shared dependency
# ---------------------------------------------------------------------------


async def _verify_n8n_request(request: Request) -> dict:
    """
    Dependency that verifies n8n HMAC-SHA256 signature and parses the body.

    Used by all /execute/* endpoints to ensure only n8n can call them.
    Returns the parsed JSON body dict (or empty dict if no body).
    Raises HTTP 401 if the signature is missing or invalid.
    """
    body_bytes = await request.body()
    signature = request.headers.get("X-ThookAI-Signature", "")
    if not signature:
        logger.warning("n8n execute endpoint called without X-ThookAI-Signature header")
        raise HTTPException(status_code=401, detail="Missing X-ThookAI-Signature header")
    if not _verify_n8n_signature(body_bytes, signature):
        logger.warning("n8n execute endpoint called with invalid signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    if body_bytes:
        try:
            return json.loads(body_bytes)
        except json.JSONDecodeError:
            return {}
    return {}


# ---------------------------------------------------------------------------
# Execute endpoints — n8n calls these to run migrated Celery beat tasks
# ---------------------------------------------------------------------------


@router.post("/execute/cleanup-stale-jobs")
async def execute_cleanup_stale_jobs(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Mark stale running jobs as errored.

    A content_job is considered stale if its status is "running" and its
    updated_at timestamp is more than 10 minutes in the past.
    Called by n8n every 10 minutes (replaces Celery beat cleanup-stale-jobs).
    """
    logger.info("Executing cleanup-stale-jobs via n8n")

    from database import db

    threshold = datetime.now(timezone.utc) - timedelta(minutes=10)

    result = await db.content_jobs.update_many(
        {
            "status": "running",
            "updated_at": {"$lt": threshold},
        },
        {
            "$set": {
                "status": "error",
                "current_agent": "error",
                "error": "Job timed out (stale running job detected by n8n cleanup task).",
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    stale_cleaned = result.modified_count
    if stale_cleaned:
        logger.warning("Marked %d stale running jobs as errored", stale_cleaned)
    else:
        logger.info("No stale running jobs found")

    return {
        "status": "completed",
        "result": {"stale_jobs_cleaned": stale_cleaned},
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/execute/cleanup-old-jobs")
async def execute_cleanup_old_jobs(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Delete old failed/errored content jobs, expired sessions, and OAuth states.

    - Failed/errored jobs older than 30 days are deleted.
    - Onboarding sessions older than 30 days are deleted.
    - OAuth states older than 1 hour are deleted (they are short-lived by design).

    Called by n8n daily at 02:00 UTC (replaces Celery beat cleanup-old-jobs).
    """
    logger.info("Executing cleanup-old-jobs via n8n")

    from database import db

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    one_hour_ago = now - timedelta(hours=1)

    # Delete old failed/errored content jobs (keep completed ones for history)
    jobs_result = await db.content_jobs.delete_many(
        {
            "status": {"$in": ["error", "failed"]},
            "created_at": {"$lt": thirty_days_ago},
        }
    )
    failed_jobs_deleted = jobs_result.deleted_count

    # Delete old onboarding sessions
    sessions_result = await db.onboarding_sessions.delete_many(
        {"created_at": {"$lt": thirty_days_ago}}
    )
    sessions_deleted = sessions_result.deleted_count

    # Delete old OAuth states (short-lived by design — purge after 1 hour)
    oauth_result = await db.oauth_states.delete_many(
        {"created_at": {"$lt": one_hour_ago}}
    )
    oauth_deleted = oauth_result.deleted_count

    logger.info(
        "cleanup-old-jobs: deleted %d failed jobs, %d sessions, %d oauth states",
        failed_jobs_deleted,
        sessions_deleted,
        oauth_deleted,
    )

    return {
        "status": "completed",
        "result": {
            "failed_jobs_deleted": failed_jobs_deleted,
            "sessions_deleted": sessions_deleted,
            "oauth_states_deleted": oauth_deleted,
        },
        "executed_at": now.isoformat(),
    }


@router.post("/execute/cleanup-expired-shares")
async def execute_cleanup_expired_shares(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Deactivate expired persona share links.

    Sets is_active=False for persona_shares whose expires_at < now.
    Called by n8n daily at 02:30 UTC (replaces Celery beat cleanup-expired-shares).
    """
    logger.info("Executing cleanup-expired-shares via n8n")

    from database import db

    now = datetime.now(timezone.utc)

    result = await db.persona_shares.update_many(
        {
            "is_active": True,
            "expires_at": {"$lt": now},
        },
        {"$set": {"is_active": False, "expired_at": now}},
    )

    deactivated = result.modified_count
    logger.info("Deactivated %d expired persona share links", deactivated)

    return {
        "status": "completed",
        "result": {"deactivated": deactivated},
        "executed_at": now.isoformat(),
    }


@router.post("/execute/reset-daily-limits")
async def execute_reset_daily_limits(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Reset daily content creation counters for all users.

    Sets daily_content_count=0 for all users who have a non-zero count.
    Called by n8n at midnight UTC (replaces Celery beat reset-daily-limits).
    """
    logger.info("Executing reset-daily-limits via n8n")

    from database import db

    result = await db.users.update_many(
        {"daily_content_count": {"$gt": 0}},
        {
            "$set": {
                "daily_content_count": 0,
                "daily_reset_at": datetime.now(timezone.utc),
            }
        },
    )

    reset_count = result.modified_count
    logger.info("Reset daily limits for %d users", reset_count)

    return {
        "status": "completed",
        "result": {"reset_count": reset_count},
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/execute/refresh-monthly-credits")
async def execute_refresh_monthly_credits(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Refresh monthly credits for subscribed users.

    Refreshes credits for starter/free users and active custom plan users
    who haven't had credits refreshed in the last 30 days.
    Called by n8n on the 1st of each month at 00:05 UTC
    (replaces Celery beat refresh-monthly-credits).
    """
    logger.info("Executing refresh-monthly-credits via n8n")

    from database import db
    from services.credits import TIER_CONFIGS

    threshold = datetime.now(timezone.utc) - timedelta(days=30)

    users = await db.users.find(
        {
            "$or": [
                {"subscription_tier": {"$in": ["starter", "free"]}},
                {
                    "subscription_tier": "custom",
                    "subscription_status": "active",
                },
            ]
        }
    ).to_list(length=1000)

    refreshed = 0
    for user in users:
        last_refresh = user.get("credits_refreshed_at")
        if last_refresh:
            if isinstance(last_refresh, str):
                last_refresh = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
            if last_refresh > threshold:
                continue  # Already refreshed recently

        tier = user.get("subscription_tier", "starter")
        if tier == "custom":
            plan_config = user.get("plan_config", {})
            monthly_credits = plan_config.get("monthly_credits", 0)
        else:
            tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["starter"])
            monthly_credits = tier_config["monthly_credits"]

        now = datetime.now(timezone.utc)
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {
                "$set": {
                    "credits": monthly_credits,
                    "credits_refreshed_at": now,
                    "credits_last_refresh": now,
                }
            },
        )
        refreshed += 1

    logger.info("Refreshed credits for %d users", refreshed)

    return {
        "status": "completed",
        "result": {"refreshed_count": refreshed},
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/execute/aggregate-daily-analytics")
async def execute_aggregate_daily_analytics(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Aggregate daily analytics for the previous calendar day.

    Counts content jobs created, new users, and active users yesterday,
    then upserts the result into db.daily_stats.
    Called by n8n daily at 01:00 UTC (replaces Celery beat aggregate-daily-analytics).
    """
    logger.info("Executing aggregate-daily-analytics via n8n")

    from database import db

    now = datetime.now(timezone.utc)
    yesterday = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=1)
    today_start = yesterday + timedelta(days=1)

    # Count completed content jobs created yesterday
    content_count = await db.content_jobs.count_documents(
        {
            "created_at": {"$gte": yesterday, "$lt": today_start},
            "status": "completed",
        }
    )

    # Count new users registered yesterday
    new_users = await db.users.count_documents(
        {"created_at": {"$gte": yesterday, "$lt": today_start}}
    )

    # Count distinct active users (any content creation yesterday)
    active_user_ids = await db.content_jobs.distinct(
        "user_id",
        {"created_at": {"$gte": yesterday, "$lt": today_start}},
    )
    active_users = len(active_user_ids)

    date_str = yesterday.strftime("%Y-%m-%d")
    stats = {
        "date": date_str,
        "content_created": content_count,
        "new_users": new_users,
        "active_users": active_users,
        "aggregated_at": now,
    }

    await db.daily_stats.update_one(
        {"date": date_str},
        {"$set": stats},
        upsert=True,
    )

    logger.info(
        "Daily analytics aggregated for %s: %d content, %d new users, %d active",
        date_str,
        content_count,
        new_users,
        active_users,
    )

    return {
        "status": "completed",
        "result": {
            "date": date_str,
            "content_created": content_count,
            "new_users": new_users,
            "active_users": active_users,
        },
        "executed_at": now.isoformat(),
    }


@router.post("/execute/process-scheduled-posts")
async def execute_process_scheduled_posts(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Publish all scheduled posts that are due.

    Uses agents.publisher.publish_to_platform directly (per D-09) for real
    publishing to LinkedIn/X/Instagram.

    Idempotency guard (per D-05):
      1. Atomic claim via find_one_and_update — only the first caller can
         set status "processing" on a given post in a given run.
      2. A post with published_at within the last 2 minutes is skipped — this
         guards against duplicate delivery during overlapping n8n executions.
      3. A claim older than 5 minutes is considered stale and can be reclaimed
         (handles worker crash mid-publish).

    Called by n8n every 5 minutes (replaces Celery beat process-scheduled-posts).
    """
    logger.info("Executing process-scheduled-posts via n8n")

    from database import db

    now = datetime.now(timezone.utc)
    published = 0
    failed = 0
    skipped = 0
    published_user_ids: List[str] = []

    # Fetch all posts that are due for publishing
    cursor = db.scheduled_posts.find(
        {
            "status": "scheduled",
            "scheduled_at": {"$lte": now},
        }
    )
    due_posts = await cursor.to_list(length=100)

    for post in due_posts:
        schedule_id = post.get("schedule_id", str(post.get("_id", "")))

        # -----------------------------------------------------------------
        # IDEMPOTENCY GUARD (per D-05)
        # Atomic claim: only one worker instance can transition this post
        # from "scheduled" → "processing".  A second concurrent call will
        # find no matching document and receive None.
        # -----------------------------------------------------------------
        claim = await db.scheduled_posts.find_one_and_update(
            {
                "schedule_id": schedule_id,
                "status": "scheduled",
                "$or": [
                    {"processing_started_at": {"$exists": False}},
                    {
                        "processing_started_at": {
                            "$lt": now - timedelta(minutes=5)
                        }
                    },
                ],
            },
            {"$set": {"status": "processing", "processing_started_at": now}},
            return_document=True,
        )
        if not claim:
            logger.info(
                "Post %s already claimed — skipping (idempotency guard)",
                schedule_id,
            )
            skipped += 1
            continue

        # 2-minute recently-published check (second layer of idempotency)
        published_at = post.get("published_at")
        if published_at:
            if isinstance(published_at, str):
                published_at = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
            if (now - published_at) < timedelta(minutes=2):
                logger.info(
                    "Post %s published within last 2 min — skipping (idempotency)",
                    schedule_id,
                )
                # Revert status to scheduled so it won't be stuck in processing
                await db.scheduled_posts.update_one(
                    {"schedule_id": schedule_id},
                    {"$set": {"status": "scheduled"}},
                )
                skipped += 1
                continue
        # -----------------------------------------------------------------
        # END IDEMPOTENCY GUARD
        # -----------------------------------------------------------------

        platform = post.get("platform", "")
        user_id = post.get("user_id", "")
        content = post.get("content", "")
        media_assets = post.get("media_assets")

        # Fetch OAuth token for the platform
        token = await db.platform_tokens.find_one(
            {
                "user_id": user_id,
                "platform": platform,
            }
        )
        if not token:
            logger.warning(
                "No OAuth token for user %s platform %s", user_id, platform
            )
            await db.scheduled_posts.update_one(
                {"schedule_id": schedule_id},
                {"$set": {"status": "failed", "error": "No OAuth token"}},
            )
            failed += 1
            continue

        access_token = token.get("access_token", "")

        # Call the REAL publisher (per D-09) — NOT content_tasks._publish_to_platform
        try:
            result = await real_publish_to_platform(
                platform=platform,
                content=content,
                access_token=access_token,
                user_id=user_id,
                media_assets=media_assets,
            )
            success = (
                result.get("success", False)
                if isinstance(result, dict)
                else bool(result)
            )
        except Exception as pub_exc:
            logger.error(
                "publish_to_platform failed for %s: %s",
                platform,
                pub_exc,
                exc_info=True,
            )
            success = False
            result = {}

        if success:
            await db.scheduled_posts.update_one(
                {"schedule_id": schedule_id},
                {"$set": {"status": "published", "published_at": now}},
            )
            published += 1
            if user_id not in published_user_ids:
                published_user_ids.append(user_id)
        else:
            error_msg = (
                str(result.get("error", "Unknown"))
                if isinstance(result, dict)
                else "Publishing failed"
            )
            await db.scheduled_posts.update_one(
                {"schedule_id": schedule_id},
                {"$set": {"status": "failed", "error": error_msg}},
            )
            failed += 1

    logger.info(
        "process-scheduled-posts complete: %d published, %d failed, %d skipped",
        published,
        failed,
        skipped,
    )

    # Notify users whose posts were processed
    for user_id in published_user_ids:
        try:
            from services.notification_service import create_notification
            await create_notification(
                user_id=user_id,
                type="workflow_status",
                title="Scheduled posts processed",
                body="Your scheduled posts have been published",
                metadata={"workflow_type": "process-scheduled-posts"},
            )
        except Exception as e:
            logger.warning(
                "Failed to create workflow notification for user %s: %s", user_id, e
            )

    return {
        "status": "completed",
        "result": {
            "published": published,
            "failed": failed,
            "skipped": skipped,
            "published_user_ids": published_user_ids,
        },
        "executed_at": now.isoformat(),
    }


@router.post("/execute/run-nightly-strategist")
async def execute_run_nightly_strategist(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Run the nightly Strategist agent for all eligible users.
    Called by n8n at 03:00 UTC daily.

    Synthesizes LightRAG + analytics + persona signals into ranked
    recommendation cards written to db.strategy_recommendations.
    Never triggers content generation directly.
    """
    from agents.strategist import run_strategist_for_all_users

    result = await run_strategist_for_all_users()
    return {
        "status": "completed",
        "result": result,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
