# Agent: Notification System — SSE + In-App Notifications
Sprint: 7 | Branch: feat/notification-system | PR target: dev
Depends on: Sprint 2 fully merged (email service must exist for email notifications)

## Context
Users have no feedback when long-running tasks complete. Content generation takes
15-30 seconds — the user has no idea if it worked. Scheduled posts publish silently.
Billing events happen with no confirmation. There is no notification system at all.

## Files You Will Touch
- backend/routes/notifications.py        (CREATE)
- backend/services/notification_service.py (CREATE)
- backend/server.py                      (MODIFY — register new router)
- backend/tasks/content_tasks.py         (MODIFY — fire notifications on completion)
- frontend/src/hooks/useNotifications.js (CREATE)
- frontend/src/components/NotificationBell.jsx (CREATE)

## Files You Must Read First (do not modify)
- backend/routes/content.py             (understand job completion flow)
- backend/tasks/content_tasks.py        (understand where publish completes)
- backend/services/email_service.py     (use send_content_published_email)

## Step 1: Create notification_service.py
```python
# Manages in-app notifications stored in db.notifications
# Schema: {notification_id, user_id, type, title, body, read: False, 
#          created_at, metadata: {job_id, platform, etc.}}

async def create_notification(user_id: str, type: str, title: str, body: str, metadata: dict = None)
async def get_notifications(user_id: str, unread_only: bool = False, limit: int = 20) -> list
async def mark_read(user_id: str, notification_id: str)
async def mark_all_read(user_id: str)
async def get_unread_count(user_id: str) -> int
```

## Step 2: Create notifications.py route with SSE
```python
# GET /api/notifications/stream — Server-Sent Events stream
# GET /api/notifications — list notifications
# POST /api/notifications/{id}/read — mark one read
# POST /api/notifications/read-all — mark all read
# GET /api/notifications/count — unread count

# SSE endpoint using async generator:
@router.get("/notifications/stream")
async def notification_stream(current_user = Depends(get_current_user)):
    async def event_generator():
        user_id = current_user["user_id"]
        last_check = datetime.utcnow()
        while True:
            await asyncio.sleep(10)  # poll every 10 seconds
            new_notifications = await get_notifications(
                user_id, since=last_check, unread_only=True
            )
            if new_notifications:
                last_check = datetime.utcnow()
                yield f"data: {json.dumps(new_notifications)}\n\n"
            else:
                yield f": heartbeat\n\n"  # keep connection alive
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## Step 3: Fire notifications from content_tasks.py
After `process_scheduled_posts` confirms a post is published, add:
```python
from services.notification_service import create_notification
from services.email_service import send_content_published_email

asyncio.run(create_notification(
    user_id=user_id,
    type="post_published",
    title=f"Your {platform} post was published",
    body=content[:100] + "...",
    metadata={"job_id": job_id, "platform": platform}
))
# Also send email notification
send_content_published_email(user_email, platform, content[:200])
```

## Step 4: Frontend — useNotifications hook
Create a React hook that:
1. Opens an SSE connection to /api/notifications/stream
2. Listens for new notification events
3. Maintains a local state of notifications and unread count
4. Exposes: `{ notifications, unreadCount, markRead, markAllRead }`

## Step 5: Frontend — NotificationBell component
A bell icon in the app header that:
1. Shows unread count badge
2. On click, shows a dropdown with the latest 10 notifications
3. Each notification is clickable and marks as read
4. "Mark all read" button at the bottom

Register the new notifications router in server.py.

## Definition of Done
- GET /api/notifications/stream returns SSE events
- New notification is created when a scheduled post publishes
- Frontend NotificationBell shows unread count
- PR created to dev with title: "feat: SSE notification system for job and publish events"