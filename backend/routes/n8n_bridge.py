"""
ThookAI n8n Webhook Bridge

HTTP contract layer between FastAPI and n8n workflow orchestration.

Endpoints:
  POST /api/n8n/callback     — Receive HMAC-SHA256-signed callbacks from n8n
  POST /api/n8n/trigger/{workflow_name} — Trigger an n8n workflow (auth-protected)

Security:
  - Callback endpoint verifies X-ThookAI-Signature header using HMAC-SHA256
  - Uses hmac.compare_digest for constant-time comparison (timing-safe)
  - Trigger endpoint requires authenticated user via get_current_user dependency
"""

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

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
    }


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

    return {"status": "accepted"}


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
