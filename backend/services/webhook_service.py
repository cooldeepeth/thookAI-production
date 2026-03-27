"""
ThookAI Outbound Webhook Service

Fires signed webhooks to user-registered endpoints when platform events occur.
Supports Zapier, Make, n8n, and custom automation integrations.

Events:
- job.completed    — content generation pipeline finished
- job.approved     — user approved a content draft
- post.published   — scheduled post published to a platform
- post.failed      — scheduled post failed to publish
- credits.low      — user credits dropped below threshold
- subscription.changed — user subscription tier changed
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from database import db

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = [
    "job.completed",
    "job.approved",
    "post.published",
    "post.failed",
    "credits.low",
    "subscription.changed",
]

# Disable an endpoint after this many consecutive failures
MAX_FAILURE_COUNT = 5

# Timeout for outbound webhook HTTP calls
WEBHOOK_TIMEOUT_SECONDS = 10.0


def _generate_webhook_secret() -> str:
    """Generate a cryptographically secure webhook signing secret."""
    return secrets.token_hex(32)


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


async def fire_webhook(user_id: str, event: str, payload: dict) -> None:
    """
    Fire webhooks for a user event.

    Finds all active endpoints registered by the user for the given event,
    signs the payload with each endpoint's secret, and POSTs concurrently.
    Failures are recorded but NEVER raised — this must not break callers.
    """
    try:
        endpoints = await db.webhook_endpoints.find({
            "user_id": user_id,
            "active": True,
            "events": event,
        }).to_list(length=50)

        if not endpoints:
            return

        tasks = [
            _deliver_webhook(endpoint, event, payload)
            for endpoint in endpoints
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception:
        logger.exception(
            "Unexpected error in fire_webhook for user=%s event=%s", user_id, event
        )


async def _deliver_webhook(
    endpoint: dict, event: str, payload: dict
) -> None:
    """Deliver a single webhook to one endpoint. Never raises."""
    delivery_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    body = {
        "event": event,
        "delivered_at": now.isoformat(),
        "delivery_id": delivery_id,
        "data": payload,
    }

    body_bytes = json.dumps(body, default=str).encode("utf-8")
    signature = _sign_payload(body_bytes, endpoint["secret"])

    headers = {
        "Content-Type": "application/json",
        "X-ThookAI-Signature": signature,
        "X-ThookAI-Event": event,
        "X-ThookAI-Delivery": delivery_id,
        "User-Agent": "ThookAI-Webhooks/1.0",
    }

    status_code = 0
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                endpoint["url"],
                content=body_bytes,
                headers=headers,
            )
            status_code = resp.status_code

        if 200 <= status_code < 300:
            # Success — reset failure counter
            await db.webhook_endpoints.update_one(
                {"webhook_id": endpoint["webhook_id"]},
                {"$set": {
                    "last_triggered_at": now,
                    "last_status_code": status_code,
                    "failure_count": 0,
                }},
            )
            logger.info(
                "Webhook delivered: endpoint=%s event=%s status=%s",
                endpoint["webhook_id"], event, status_code,
            )
        else:
            await _record_failure(endpoint, status_code, now)

    except httpx.TimeoutException:
        logger.warning(
            "Webhook timed out: endpoint=%s url=%s",
            endpoint["webhook_id"], endpoint["url"],
        )
        await _record_failure(endpoint, 0, now)

    except Exception:
        logger.exception(
            "Webhook delivery error: endpoint=%s url=%s",
            endpoint["webhook_id"], endpoint["url"],
        )
        await _record_failure(endpoint, 0, now)


async def _record_failure(endpoint: dict, status_code: int, now: datetime) -> None:
    """Increment failure count and disable endpoint if threshold exceeded."""
    new_failure_count = endpoint.get("failure_count", 0) + 1
    update: Dict[str, Any] = {
        "last_triggered_at": now,
        "last_status_code": status_code,
        "failure_count": new_failure_count,
    }

    if new_failure_count >= MAX_FAILURE_COUNT:
        update["active"] = False
        logger.warning(
            "Webhook endpoint disabled after %d failures: endpoint=%s url=%s",
            new_failure_count, endpoint["webhook_id"], endpoint["url"],
        )

    await db.webhook_endpoints.update_one(
        {"webhook_id": endpoint["webhook_id"]},
        {"$set": update},
    )


# ============ CRUD ============


async def register_webhook(
    user_id: str,
    url: str,
    events: List[str],
) -> dict:
    """Register a new webhook endpoint for a user."""
    # Validate events
    invalid = [e for e in events if e not in SUPPORTED_EVENTS]
    if invalid:
        raise ValueError(f"Unsupported events: {invalid}")

    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("Webhook URL must start with http:// or https://")

    webhook_id = f"wh_{uuid.uuid4().hex[:12]}"
    secret = _generate_webhook_secret()
    now = datetime.now(timezone.utc)

    doc = {
        "webhook_id": webhook_id,
        "user_id": user_id,
        "url": url,
        "events": events,
        "secret": secret,
        "active": True,
        "created_at": now,
        "last_triggered_at": None,
        "last_status_code": None,
        "failure_count": 0,
    }

    await db.webhook_endpoints.insert_one(doc)

    # Return without _id
    doc.pop("_id", None)
    return doc


async def list_webhooks(user_id: str) -> list:
    """List all webhook endpoints for a user."""
    endpoints = await db.webhook_endpoints.find(
        {"user_id": user_id},
        {"_id": 0},
    ).sort("created_at", -1).to_list(length=100)
    return endpoints


async def delete_webhook(user_id: str, webhook_id: str) -> bool:
    """Delete a webhook endpoint. Returns True if found and deleted."""
    result = await db.webhook_endpoints.delete_one({
        "webhook_id": webhook_id,
        "user_id": user_id,
    })
    return result.deleted_count > 0


async def test_webhook(user_id: str, webhook_id: str) -> dict:
    """
    Send a test ping event to a webhook endpoint.
    Returns delivery result with status code.
    """
    endpoint = await db.webhook_endpoints.find_one({
        "webhook_id": webhook_id,
        "user_id": user_id,
    })

    if not endpoint:
        return {"success": False, "error": "Webhook endpoint not found"}

    test_payload = {
        "message": "This is a test webhook from ThookAI",
        "webhook_id": webhook_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    delivery_id = uuid.uuid4().hex
    body = {
        "event": "test.ping",
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "delivery_id": delivery_id,
        "data": test_payload,
    }

    body_bytes = json.dumps(body, default=str).encode("utf-8")
    signature = _sign_payload(body_bytes, endpoint["secret"])

    headers = {
        "Content-Type": "application/json",
        "X-ThookAI-Signature": signature,
        "X-ThookAI-Event": "test.ping",
        "X-ThookAI-Delivery": delivery_id,
        "User-Agent": "ThookAI-Webhooks/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                endpoint["url"],
                content=body_bytes,
                headers=headers,
            )

        return {
            "success": 200 <= resp.status_code < 300,
            "status_code": resp.status_code,
            "delivery_id": delivery_id,
        }

    except httpx.TimeoutException:
        return {"success": False, "error": "Request timed out", "delivery_id": delivery_id}

    except Exception as e:
        return {"success": False, "error": str(e), "delivery_id": delivery_id}
