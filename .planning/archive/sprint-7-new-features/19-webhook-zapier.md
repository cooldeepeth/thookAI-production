# Agent: Outbound Webhooks — Job Completion + Zapier Integration
Sprint: 7 | Branch: feat/outbound-webhooks | PR target: dev
Depends on: Sprint 6 fully merged, Sprint 2 merged (notifications framework helps)

## Context
There is no outbound webhook system. When a content job completes, a post is
published, or a credit limit is reached, nothing fires externally. This blocks
Zapier, Make.com, and any third-party automation a user might want. It is a
table-stakes feature for a B2B SaaS tool.

## Files You Will Touch
- backend/services/webhook_service.py    (CREATE)
- backend/routes/webhooks.py             (CREATE — CRUD for webhook endpoints)
- backend/server.py                      (MODIFY — register webhooks router)
- backend/tasks/content_tasks.py         (MODIFY — fire webhooks on publish)
- backend/routes/content.py              (MODIFY — fire webhook on job completion)

## Files You Must Read First (do not modify)
- backend/routes/content.py             (find job completion — where status → "reviewing")
- backend/tasks/content_tasks.py        (find publish completion)
- backend/database.py                   (db access pattern)

## Step 1: Create backend/services/webhook_service.py

Schema for db.webhook_endpoints:
```python
{
  webhook_id: str,
  user_id: str,
  url: str,                    # the HTTPS URL to POST to
  events: list[str],           # ["job.completed", "post.published", "credits.low"]
  secret: str,                 # HMAC secret for signature verification
  active: bool,
  created_at: datetime,
  last_triggered_at: datetime | None,
  last_status_code: int | None,
  failure_count: int           # pause after 5 consecutive failures
}
```

Implement these functions:
```python
async def fire_webhook(user_id: str, event: str, payload: dict) -> None:
    """
    Finds all active webhook endpoints for this user+event combo.
    For each endpoint:
    1. Signs the payload: HMAC-SHA256 of JSON body using endpoint.secret
    2. Sets header: X-ThookAI-Signature: sha256={hex_digest}
    3. Sets header: X-ThookAI-Event: {event}
    4. Sets header: X-ThookAI-Delivery: {uuid}
    5. POSTs to endpoint.url with 10s timeout using httpx
    6. Updates last_triggered_at, last_status_code, failure_count
    7. If failure_count >= 5, sets active=False and logs warning
    Never raise exceptions — webhook failures must never break the main flow.
    Run all webhook fires concurrently using asyncio.gather().
    """

async def register_webhook(user_id: str, url: str, events: list) -> dict:
    """Creates a new webhook endpoint. Generates a random secret."""

async def list_webhooks(user_id: str) -> list:
async def delete_webhook(user_id: str, webhook_id: str) -> bool:
async def test_webhook(user_id: str, webhook_id: str) -> dict:
    """Sends a test ping event to verify the endpoint is reachable."""
```

## Step 2: Create backend/routes/webhooks.py
```python
# POST /api/webhooks           — register new endpoint
# GET  /api/webhooks           — list user's webhooks
# DELETE /api/webhooks/{id}    — delete webhook
# POST /api/webhooks/{id}/test — send test event
# GET  /api/webhooks/events    — list all supported event types
```

Supported events list (return from GET /events):
- `job.completed` — content generation pipeline finished
- `job.approved` — user approved a content draft
- `post.published` — scheduled post was published to platform
- `post.failed` — publish attempt failed
- `credits.low` — user below 10% of monthly credits
- `subscription.changed` — tier upgraded or downgraded

## Step 3: Fire webhooks from content pipeline
In content.py, when a job reaches `reviewing` status (generation complete), add:
```python
from services.webhook_service import fire_webhook
asyncio.create_task(fire_webhook(
    user_id=user_id,
    event="job.completed",
    payload={
        "job_id": job_id,
        "platform": platform,
        "content_type": content_type,
        "content_preview": final_content[:200],
        "completed_at": datetime.utcnow().isoformat()
    }
))
```

In content_tasks.py, after a post is confirmed published, add:
```python
asyncio.run(fire_webhook(
    user_id=user_id,
    event="post.published",
    payload={
        "job_id": job_id,
        "platform": platform,
        "published_at": datetime.utcnow().isoformat(),
        "published_url": result.get("url", "")
    }
))
```

Register the webhooks router in server.py.

## Definition of Done
- Webhook CRUD endpoints work (create, list, delete, test)
- fire_webhook sends signed HMAC POST within the main request flow
- Webhook fires on job.completed and post.published events
- GET /api/webhooks/events lists all supported event types
- PR created to dev: "feat: outbound webhook system for Zapier and automation integrations"