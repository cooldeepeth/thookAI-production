"""
ThookAI Notification Service

Manages notifications for users including:
- Content generation completion
- Scheduled post publishing
- Billing events
- System announcements

All notifications are stored in db.notifications and can be
streamed to the frontend via SSE.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from database import db

logger = logging.getLogger(__name__)


async def create_notification(
    user_id: str,
    type: str,
    title: str,
    body: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Create a new notification for a user.

    Args:
        user_id: The target user's ID.
        type: Notification type (e.g. "post_published", "job_completed",
              "billing_event", "system").
        title: Short notification title.
        body: Notification body text.
        metadata: Optional dict of extra data (platform, job_id, etc.).

    Returns:
        The inserted notification document.
    """
    notification = {
        "notification_id": f"notif_{uuid4().hex[:12]}",
        "user_id": user_id,
        "type": type,
        "title": title,
        "body": body,
        "read": False,
        "created_at": datetime.now(timezone.utc),
        "metadata": metadata or {},
    }

    try:
        await db.notifications.insert_one(notification)
        logger.info(
            "Notification created: id=%s user=%s type=%s",
            notification["notification_id"],
            user_id,
            type,
        )
    except Exception as e:
        logger.error("Failed to create notification for user %s: %s", user_id, e)

    return notification


async def get_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 20,
) -> list:
    """
    Fetch notifications for a user, most recent first.

    Args:
        user_id: The user to query.
        unread_only: If True, only return unread notifications.
        limit: Maximum number of results (default 20).

    Returns:
        List of notification dicts (without MongoDB _id).
    """
    query = {"user_id": user_id}
    if unread_only:
        query["read"] = False

    notifications = (
        await db.notifications.find(query, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    return notifications


async def mark_read(user_id: str, notification_id: str) -> bool:
    """
    Mark a single notification as read.

    Returns True if the notification was found and updated.
    """
    result = await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": user_id},
        {"$set": {"read": True}},
    )
    return result.modified_count > 0


async def mark_all_read(user_id: str) -> int:
    """
    Mark all unread notifications for a user as read.

    Returns the number of notifications updated.
    """
    result = await db.notifications.update_many(
        {"user_id": user_id, "read": False},
        {"$set": {"read": True}},
    )
    return result.modified_count


async def get_unread_count(user_id: str) -> int:
    """Return the number of unread notifications for a user."""
    return await db.notifications.count_documents(
        {"user_id": user_id, "read": False}
    )
