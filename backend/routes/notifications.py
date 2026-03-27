"""
ThookAI Notification Routes

Endpoints:
- GET  /api/notifications/stream   — SSE stream for real-time notifications
- GET  /api/notifications           — List notifications (with optional filters)
- POST /api/notifications/{id}/read — Mark a single notification as read
- POST /api/notifications/read-all  — Mark all notifications as read
- GET  /api/notifications/count     — Get unread notification count
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from auth_utils import get_current_user
from services.notification_service import (
    get_notifications,
    get_unread_count,
    mark_all_read,
    mark_read,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _sse_event_generator(user_id: str, request: Request):
    """
    Async generator that yields SSE events.

    Polls the database every 10 seconds for new unread notifications and
    sends them to the client. A heartbeat comment is sent on each tick to
    keep the connection alive through proxies/load balancers.
    """
    last_check = datetime.now(timezone.utc)

    while True:
        # Check if the client disconnected
        if await request.is_disconnected():
            logger.debug("SSE client disconnected for user %s", user_id)
            break

        try:
            # Fetch notifications created after our last check
            from database import db

            new_notifications = (
                await db.notifications.find(
                    {
                        "user_id": user_id,
                        "created_at": {"$gt": last_check},
                    },
                    {"_id": 0},
                )
                .sort("created_at", -1)
                .limit(10)
                .to_list(10)
            )

            if new_notifications:
                last_check = datetime.now(timezone.utc)
                # Serialize datetime objects for JSON
                for notif in new_notifications:
                    if isinstance(notif.get("created_at"), datetime):
                        notif["created_at"] = notif["created_at"].isoformat()

                unread = await get_unread_count(user_id)
                payload = json.dumps(
                    {"notifications": new_notifications, "unread_count": unread}
                )
                yield f"data: {payload}\n\n"
            else:
                # Send heartbeat comment to keep connection alive
                yield ": heartbeat\n\n"

        except Exception as e:
            logger.error("SSE generator error for user %s: %s", user_id, e)
            yield ": error\n\n"

        await asyncio.sleep(10)


@router.get("/stream")
async def notification_stream(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    SSE endpoint for real-time notification streaming.

    The client should connect with EventSource and will receive JSON
    payloads containing new notifications and the current unread count.
    """
    user_id = current_user["user_id"]
    logger.info("SSE stream opened for user %s", user_id)

    return StreamingResponse(
        _sse_event_generator(user_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("")
async def list_notifications(
    unread_only: bool = False,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """
    List notifications for the current user.

    Query params:
    - unread_only: Only return unread notifications (default False)
    - limit: Max results to return (default 20, max 100)
    """
    if limit > 100:
        limit = 100

    notifications = await get_notifications(
        user_id=current_user["user_id"],
        unread_only=unread_only,
        limit=limit,
    )

    # Serialize datetime for JSON response
    for notif in notifications:
        if isinstance(notif.get("created_at"), datetime):
            notif["created_at"] = notif["created_at"].isoformat()

    return {"notifications": notifications, "count": len(notifications)}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Mark a single notification as read."""
    updated = await mark_read(
        user_id=current_user["user_id"],
        notification_id=notification_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
):
    """Mark all notifications as read for the current user."""
    count = await mark_all_read(user_id=current_user["user_id"])
    return {"message": f"{count} notifications marked as read", "updated": count}


@router.get("/count")
async def unread_notification_count(
    current_user: dict = Depends(get_current_user),
):
    """Get the number of unread notifications for the current user."""
    count = await get_unread_count(user_id=current_user["user_id"])
    return {"unread_count": count}
