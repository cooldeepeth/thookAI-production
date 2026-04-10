"""
ThookAI Webhook Management Routes

Endpoints for registering, listing, testing, and deleting
outbound webhook endpoints. Webhooks fire on platform events
to support Zapier, Make, n8n, and custom automation integrations.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import logging

from auth_utils import get_current_user
from services.webhook_service import (
    SUPPORTED_EVENTS,
    register_webhook,
    list_webhooks,
    delete_webhook,
    test_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    url: str  # Validated in service: must start with http:// or https://
    events: List[str]  # Max 10 events per webhook


@router.post("", status_code=201)
async def create_webhook(
    data: WebhookCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Register a new webhook endpoint.

    The response includes a `secret` field -- store it securely.
    ThookAI signs every delivery payload with HMAC-SHA256 using this secret
    so you can verify authenticity via the `X-ThookAI-Signature` header.
    """
    try:
        result = await register_webhook(
            user_id=current_user["user_id"],
            url=data.url,
            events=data.events,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def get_webhooks(
    current_user: dict = Depends(get_current_user),
):
    """List all webhook endpoints for the authenticated user."""
    endpoints = await list_webhooks(current_user["user_id"])
    return {"webhooks": endpoints}


@router.delete("/{webhook_id}")
async def remove_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a webhook endpoint."""
    deleted = await delete_webhook(current_user["user_id"], webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    return {"deleted": True, "webhook_id": webhook_id}


@router.post("/{webhook_id}/test")
async def send_test_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a test ping event to a webhook endpoint.

    Use this to verify that your endpoint is reachable and properly
    configured before relying on it for production events.
    """
    result = await test_webhook(current_user["user_id"], webhook_id)
    if not result.get("success") and result.get("error") == "Webhook endpoint not found":
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    return result


@router.get("/events")
async def get_supported_events():
    """
    List all supported webhook event types.

    Subscribe to these events when registering a webhook endpoint.
    """
    return {
        "events": [
            {
                "name": "job.completed",
                "description": "Content generation pipeline finished producing a draft",
            },
            {
                "name": "job.approved",
                "description": "User approved a content draft",
            },
            {
                "name": "post.published",
                "description": "Scheduled post was successfully published to a platform",
            },
            {
                "name": "post.failed",
                "description": "Scheduled post failed to publish",
            },
            {
                "name": "credits.low",
                "description": "User credits dropped below the low-credit threshold",
            },
            {
                "name": "subscription.changed",
                "description": "User subscription tier was changed (upgrade, downgrade, or cancel)",
            },
        ]
    }
