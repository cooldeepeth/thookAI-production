"""Media Orchestrator Service for ThookAI.

Decomposes a MediaBrief into per-asset tasks, routes to providers,
stages all assets to R2, then calls the Remotion render service.
Pipeline credit ledger tracks per-stage costs for partial-failure accounting.

Every provider call is preceded by a pending ledger entry — no provider is
called without a ledger record. On provider failure, remaining pipeline
stages are marked 'skipped' in the ledger — no silent credit drain.
"""

import asyncio
import base64
import logging
import mimetypes
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from config import settings
from database import db

logger = logging.getLogger(__name__)


# ============================================================
# MEDIA BRIEF DATACLASS
# ============================================================

@dataclass
class MediaBrief:
    """Defines a media generation request for the orchestrator.

    All media generation flows through this dataclass — it is the
    single source of truth for what gets generated and how.
    """
    job_id: str
    user_id: str
    # One of: static_image | quote_card | meme | carousel | infographic
    #         talking_head | short_form_video | text_on_video
    media_type: str
    platform: str  # "linkedin" | "instagram" | "x"
    content_text: str
    persona_card: Dict[str, Any]  # from db.persona_engines
    style: str = "minimal"
    slides: Optional[List[Dict[str, Any]]] = None     # for carousel
    data_points: Optional[List[Dict[str, Any]]] = None  # for infographic
    avatar_id: Optional[str] = None    # HeyGen avatar ID
    voice_id: Optional[str] = None     # ElevenLabs voice ID
    video_url: Optional[str] = None    # for text_on_video (user-uploaded)
    music_url: Optional[str] = None    # background music URL
    brand_color: str = "#2563EB"       # from persona visual_aesthetic


# ============================================================
# COST CONFIGURATION
# ============================================================

# Max credits per job (cost cap) — pipeline aborts if this is exceeded
MEDIA_TYPE_COST_CAPS: Dict[str, int] = {
    "static_image": 15,
    "quote_card": 10,
    "meme": 12,
    "carousel": 40,
    "infographic": 15,
    "talking_head": 80,
    "short_form_video": 100,
    "text_on_video": 60,
}

# Per-stage credit costs (deducted when a stage is consumed)
STAGE_COSTS: Dict[str, int] = {
    "image_generation": 8,
    "voice_generation": 12,
    "avatar_generation": 50,
    "broll_generation": 20,
    "remotion_render": 5,
}


# ============================================================
# LAZY AGENT IMPORTS (avoid circular dependencies)
# ============================================================

def _get_designer():
    """Lazy import for designer agent."""
    from agents.designer import generate_image
    return generate_image


def _get_voice_generator():
    """Lazy import for voice agent."""
    from agents.voice import generate_voice_narration
    return generate_voice_narration


def _get_video_generator():
    """Lazy import for video agent."""
    from agents.video import generate_video
    return generate_video


def _get_avatar_generator():
    """Lazy import for avatar video agent."""
    from agents.video import generate_avatar_video
    return generate_avatar_video


# ============================================================
# PIPELINE CREDIT LEDGER
# ============================================================

async def _ledger_stage(
    job_id: str,
    user_id: str,
    stage: str,
    provider: str,
    credits: int,
) -> str:
    """Insert a pending ledger entry before calling a provider.

    Returns the ledger_id (str) for subsequent status updates.

    This is the critical guarantee: every provider call is preceded by
    a pending record — no provider is called without a ledger entry.
    """
    ledger_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.media_pipeline_ledger.insert_one({
        "ledger_id": ledger_id,
        "job_id": job_id,
        "user_id": user_id,
        "stage": stage,
        "provider": provider,
        "credits_consumed": credits,
        "status": "pending",
        "failure_reason": None,
        "created_at": now,
        "completed_at": None,
    })
    logger.debug("Ledger pending: job=%s stage=%s provider=%s credits=%d", job_id, stage, provider, credits)
    return ledger_id


async def _ledger_update(
    ledger_id: str,
    status: str,
    reason: Optional[str] = None,
) -> None:
    """Update a ledger entry status to 'consumed', 'failed', or 'skipped'.

    Args:
        ledger_id: ID returned by _ledger_stage.
        status: One of 'consumed' | 'failed' | 'skipped'.
        reason: Human-readable reason (required for 'failed', optional otherwise).
    """
    now = datetime.now(timezone.utc)
    update: Dict[str, Any] = {
        "status": status,
        "completed_at": now,
    }
    if reason is not None:
        update["failure_reason"] = reason
    await db.media_pipeline_ledger.update_one(
        {"ledger_id": ledger_id},
        {"$set": update},
    )


async def _ledger_check_cap(job_id: str, cost_cap: int) -> bool:
    """Check whether cumulative consumed credits for job_id are under cost_cap.

    Returns True if under cap (pipeline may continue), False if at/over cap.

    Uses MongoDB aggregation to sum all 'consumed' credits for the job.
    """
    pipeline = [
        {"$match": {"job_id": job_id, "status": "consumed"}},
        {"$group": {"_id": None, "total": {"$sum": "$credits_consumed"}}},
    ]
    cursor = db.media_pipeline_ledger.aggregate(pipeline)
    total = 0
    async for doc in cursor:
        total = doc.get("total", 0)
    return total < cost_cap


async def _ledger_skip_remaining(job_id: str, reason: str) -> None:
    """Mark all pending ledger entries for job_id as 'skipped'.

    Called when a pipeline stage fails to prevent silent credit drain
    on stages that were queued but never executed.
    """
    now = datetime.now(timezone.utc)
    await db.media_pipeline_ledger.update_many(
        {"job_id": job_id, "status": "pending"},
        {"$set": {
            "status": "skipped",
            "failure_reason": reason,
            "completed_at": now,
        }},
    )
    logger.info("Ledger: marked remaining pending stages as skipped for job=%s reason=%s", job_id, reason)


# ============================================================
# R2 PRE-STAGING
# ============================================================

async def _stage_asset_to_r2(asset_url: str, job_id: str, asset_key: str) -> str:
    """Download or decode an asset and upload it to R2 for Remotion.

    Remotion requires stable, long-lived URLs — we never pass external CDN
    or ephemeral provider URLs directly. This function:
    - Decodes base64 data: URLs into raw bytes
    - Downloads HTTP(S) URLs via httpx
    - Uploads bytes to R2 under a deterministic key
    - Returns the R2 public URL

    Falls back to /tmp in development if R2 is not configured (logged as warning).

    Args:
        asset_url: Either a data: URL (base64) or http(s):// URL.
        job_id: Used for R2 key namespacing.
        asset_key: Logical name for the asset (e.g. "background_image", "voice_track").

    Returns:
        Public URL of the staged asset.
    """
    from services.media_storage import get_r2_client

    file_bytes: bytes
    content_type: str
    ext: str

    if asset_url.startswith("data:"):
        # Parse data: URL — format: data:<mime>;base64,<data>
        header, encoded = asset_url.split(",", 1)
        content_type = header.split(";")[0][len("data:"):]
        file_bytes = base64.b64decode(encoded)
        ext = mimetypes.guess_extension(content_type) or ".bin"
        # Normalize common extensions
        ext = {"jpeg": ".jpg", "jpe": ".jpg"}.get(ext.lstrip("."), ext)
    elif asset_url.startswith("http://") or asset_url.startswith("https://"):
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.get(asset_url)
            response.raise_for_status()
            file_bytes = response.content
            content_type = response.headers.get("content-type", "application/octet-stream").split(";")[0]
            # Try to get extension from URL path, fallback to mime type
            path = asset_url.split("?")[0]
            guessed_ext = "." + path.rsplit(".", 1)[-1] if "." in path.split("/")[-1] else None
            ext = guessed_ext or mimetypes.guess_extension(content_type) or ".bin"
    else:
        raise ValueError(f"Unsupported asset URL scheme for staging: {asset_url[:50]}")

    r2_key = f"media/orchestrated/{job_id}/{asset_key}{ext}"

    r2_client = get_r2_client()
    if r2_client is None:
        # Development fallback: save to /tmp
        import os
        tmp_dir = f"/tmp/thookai_orchestrated/{job_id}"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = f"{tmp_dir}/{asset_key}{ext}"
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)
        logger.warning(
            "R2 not configured — staged asset to /tmp (ephemeral!): %s. "
            "Set R2_ACCESS_KEY_ID etc. for production.", tmp_path
        )
        return tmp_path

    # Upload to R2
    bucket_name = settings.r2.r2_bucket_name
    r2_client.put_object(
        Bucket=bucket_name,
        Key=r2_key,
        Body=file_bytes,
        ContentType=content_type,
    )
    public_url = f"{settings.r2.r2_public_url.rstrip('/')}/{r2_key}"
    logger.debug("Staged asset to R2: key=%s url=%s", r2_key, public_url)
    return public_url


async def _stage_assets_to_r2(assets: Dict[str, str], job_id: str) -> Dict[str, str]:
    """Stage multiple assets to R2 in parallel.

    Args:
        assets: Dict mapping asset_key -> asset_url.
        job_id: Used for R2 key namespacing.

    Returns:
        Dict mapping asset_key -> r2_url.
    """
    if not assets:
        return {}

    async def _stage_one(key: str, url: str) -> tuple:
        staged_url = await _stage_asset_to_r2(url, job_id, key)
        return key, staged_url

    results = await asyncio.gather(
        *[_stage_one(k, v) for k, v in assets.items()],
        return_exceptions=False,
    )
    return dict(results)


# ============================================================
# REMOTION SERVICE CLIENT
# ============================================================

async def _call_remotion(
    composition_id: str,
    input_props: Dict[str, Any],
    render_type: str = "still",
) -> Dict[str, Any]:
    """Call the Remotion render sidecar service and poll for completion.

    Remotion sidecar API:
    - POST /render: Start render, returns {"render_id": "..."}
    - GET /render/{render_id}/status: Poll status
      - {"status": "queued" | "rendering" | "done", "url": "..."}
      - {"status": "failed", "error": "..."}

    Args:
        composition_id: Remotion composition name (e.g. "StaticImage", "Carousel").
        input_props: Props passed to the composition.
        render_type: "still" (image) or "video".

    Returns:
        {"url": <result_url>, "render_id": <id>}

    Raises:
        RuntimeError: If render fails or times out.
    """
    base_url = settings.remotion.remotion_service_url.rstrip("/")
    render_id: Optional[str] = None

    async def _do_render() -> Dict[str, Any]:
        nonlocal render_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/render",
                json={
                    "composition": composition_id,
                    "inputProps": input_props,
                    "renderType": render_type,
                },
            )
            response.raise_for_status()
            data = response.json()
            render_id = data["render_id"]
            logger.info("Remotion render started: composition=%s render_id=%s", composition_id, render_id)

        # Poll until done
        poll_url = f"{base_url}/render/{render_id}/status"
        while True:
            await asyncio.sleep(5)
            async with httpx.AsyncClient(timeout=15.0) as client:
                status_resp = await client.get(poll_url)
                status_resp.raise_for_status()
                status_data = status_resp.json()

            status = status_data.get("status")
            logger.debug("Remotion poll: render_id=%s status=%s", render_id, status)

            if status == "done":
                result_url = status_data["url"]
                logger.info("Remotion render done: render_id=%s url=%s", render_id, result_url)
                return {"url": result_url, "render_id": render_id}

            if status == "failed":
                error_msg = status_data.get("error", "Unknown Remotion render error")
                raise RuntimeError(f"Remotion render failed (render_id={render_id}): {error_msg}")

            # Still queued or rendering — continue polling

    try:
        result = await asyncio.wait_for(_do_render(), timeout=300.0)
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"Remotion render timed out after 300s (render_id={render_id}, composition={composition_id})"
        )

    return result


# ============================================================
# MEDIA-TYPE HANDLERS (dispatch table)
# Plans 03-04 will register handlers into this dict.
# ============================================================

# Handler signature: async def handler(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]
# Returns: {"url": str, "render_id": str, "credits_consumed": int, ...}
_MEDIA_TYPE_HANDLERS: Dict[str, Any] = {}


def register_media_handler(media_type: str):
    """Decorator to register a media-type handler.

    Usage (in plans 03-04):
        @register_media_handler("static_image")
        async def handle_static_image(brief: MediaBrief, cost_cap: int) -> Dict:
            ...
    """
    def decorator(func):
        _MEDIA_TYPE_HANDLERS[media_type] = func
        return func
    return decorator


# ============================================================
# MAIN ORCHESTRATE FUNCTION
# ============================================================

async def orchestrate(brief: MediaBrief) -> Dict[str, Any]:
    """Orchestrate multi-stage media generation for a MediaBrief.

    This is the single entry point for all media generation. It:
    1. Validates media_type
    2. Looks up cost_cap
    3. Dispatches to the registered media-type handler
    4. Returns result dict with url, render_id, media_type, job_id, credits_consumed

    Media-type handlers (static_image, carousel, talking_head, etc.) are registered
    via @register_media_handler and added in Plans 03-04.

    Args:
        brief: Fully populated MediaBrief.

    Returns:
        {"url": str, "render_id": str, "media_type": str, "job_id": str, "credits_consumed": int}

    Raises:
        ValueError: If media_type is invalid or has no registered handler.
        RuntimeError: If orchestration fails (propagated from handler or Remotion).
    """
    if brief.media_type not in MEDIA_TYPE_COST_CAPS:
        valid_types = ", ".join(sorted(MEDIA_TYPE_COST_CAPS.keys()))
        raise ValueError(
            f"Unknown media_type '{brief.media_type}'. Valid types: {valid_types}"
        )

    cost_cap = MEDIA_TYPE_COST_CAPS[brief.media_type]

    handler = _MEDIA_TYPE_HANDLERS.get(brief.media_type)
    if handler is None:
        raise NotImplementedError(
            f"No handler registered for media_type '{brief.media_type}'. "
            f"Registered handlers: {list(_MEDIA_TYPE_HANDLERS.keys())}. "
            f"This type will be implemented in Plans 03-04."
        )

    result = await handler(brief, cost_cap)

    return {
        "url": result.get("url"),
        "render_id": result.get("render_id"),
        "media_type": brief.media_type,
        "job_id": brief.job_id,
        "credits_consumed": result.get("credits_consumed", 0),
    }
