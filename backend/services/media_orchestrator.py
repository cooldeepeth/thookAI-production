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
from services.media_storage import get_r2_client

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
    """Lazy import for designer agent (single image)."""
    from agents.designer import generate_image
    return generate_image


def _get_carousel():
    """Lazy import for designer agent (carousel)."""
    from agents.designer import generate_image
    # Carousel handler calls generate_image once per slide in parallel
    return generate_image


def _get_voice():
    """Lazy import for voice narration agent."""
    from agents.voice import generate_voice_narration
    return generate_voice_narration


def _get_avatar_video():
    """Lazy import for HeyGen avatar video agent."""
    from agents.video import generate_avatar_video
    return generate_avatar_video


def _get_broll_video():
    """Lazy import for B-roll video generation agent."""
    from agents.video import generate_video
    return generate_video


# Legacy aliases kept for backward compatibility
def _get_voice_generator():
    """Lazy import for voice agent (legacy alias)."""
    return _get_voice()


def _get_video_generator():
    """Lazy import for video agent (legacy alias)."""
    return _get_broll_video()


def _get_avatar_generator():
    """Lazy import for avatar video agent (legacy alias)."""
    return _get_avatar_video()


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

    # get_r2_client is imported at module level for testability
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
                    "composition_id": composition_id,
                    "input_props": input_props,
                    "render_type": render_type,
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
# STATIC IMAGE HANDLERS (Plan 03)
# ============================================================

@register_media_handler("static_image")
async def _handle_static_image(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle static_image media type.

    Pipeline:
    1. Check cost cap
    2. Ledger image_generation stage (pending)
    3. Generate image via designer.py
    4. Update ledger (consumed or failed)
    5. Stage generated image to R2
    6. Check cost cap again
    7. Ledger remotion_render stage (pending)
    8. Call Remotion StaticImageCard composition with layout="standard"
    9. Update ledger (consumed)
    10. Return result dict
    """
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Stage 1: image_generation
    img_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "image_generation", "fal", STAGE_COSTS["image_generation"]
    )
    try:
        generate_image = _get_designer()
        img_result = await generate_image(
            prompt=brief.content_text,
            style=brief.style,
            platform=brief.platform,
            persona_card=brief.persona_card,
            job_id=brief.job_id,
        )
        await _ledger_update(img_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(img_ledger_id, "failed", str(e))
        await _ledger_skip_remaining(brief.job_id, f"image_generation failed: {e}")
        raise

    # Stage image to R2 (use image_url if available, else image_base64)
    asset_url = img_result.get("image_url") or img_result.get("image_base64", "")
    r2_url = await _stage_asset_to_r2(asset_url, brief.job_id, "background_image")

    # Check cap before remotion render
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Stage 2: remotion_render
    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )
    try:
        render_result = await _call_remotion(
            "StaticImageCard",
            {
                "imageUrl": r2_url,
                "text": brief.content_text,
                "brandColor": brief.brand_color,
                "fontFamily": "Inter",
                "platform": brief.platform,
                "layout": "standard",
            },
            render_type="still",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "static_image",
        "job_id": brief.job_id,
        "credits_consumed": STAGE_COSTS["image_generation"] + STAGE_COSTS["remotion_render"],
    }


@register_media_handler("quote_card")
async def _handle_quote_card(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle quote_card media type.

    Same pipeline as static_image but:
    - Image prompt is an abstract background (not content text directly)
    - Remotion layout is "quote" instead of "standard"
    """
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Stage 1: image_generation — abstract background for the quote
    img_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "image_generation", "fal", STAGE_COSTS["image_generation"]
    )
    try:
        generate_image = _get_designer()
        img_result = await generate_image(
            prompt=f"Abstract background for quote card. Style: {brief.style}. Colors: {brief.brand_color}",
            style=brief.style,
            platform=brief.platform,
            persona_card=brief.persona_card,
            job_id=brief.job_id,
        )
        await _ledger_update(img_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(img_ledger_id, "failed", str(e))
        await _ledger_skip_remaining(brief.job_id, f"image_generation failed: {e}")
        raise

    # Stage image to R2
    asset_url = img_result.get("image_url") or img_result.get("image_base64", "")
    r2_url = await _stage_asset_to_r2(asset_url, brief.job_id, "background_image")

    # Check cap before remotion render
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Stage 2: remotion_render with quote layout
    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )
    try:
        render_result = await _call_remotion(
            "StaticImageCard",
            {
                "imageUrl": r2_url,
                "text": brief.content_text,
                "brandColor": brief.brand_color,
                "fontFamily": "Inter",
                "platform": brief.platform,
                "layout": "quote",
            },
            render_type="still",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "quote_card",
        "job_id": brief.job_id,
        "credits_consumed": STAGE_COSTS["image_generation"] + STAGE_COSTS["remotion_render"],
    }


@register_media_handler("meme")
async def _handle_meme(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle meme media type.

    Same pipeline as static_image but:
    - Image prompt is meme-friendly background
    - content_text is split on first double-newline into topText + bottomText
    - Remotion layout is "meme"
    """
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Split content_text for meme top/bottom text
    if "\n\n" in brief.content_text:
        top_text, bottom_text = brief.content_text.split("\n\n", 1)
    else:
        top_text = brief.content_text
        bottom_text = ""

    # Stage 1: image_generation — meme background
    img_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "image_generation", "fal", STAGE_COSTS["image_generation"]
    )
    try:
        generate_image = _get_designer()
        img_result = await generate_image(
            prompt=f"Meme background image for: {brief.content_text[:100]}. Style: meme-friendly, clear subject",
            style=brief.style,
            platform=brief.platform,
            persona_card=brief.persona_card,
            job_id=brief.job_id,
        )
        await _ledger_update(img_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(img_ledger_id, "failed", str(e))
        await _ledger_skip_remaining(brief.job_id, f"image_generation failed: {e}")
        raise

    # Stage image to R2
    asset_url = img_result.get("image_url") or img_result.get("image_base64", "")
    r2_url = await _stage_asset_to_r2(asset_url, brief.job_id, "background_image")

    # Check cap before remotion render
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Stage 2: remotion_render with meme layout
    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )
    try:
        render_result = await _call_remotion(
            "StaticImageCard",
            {
                "imageUrl": r2_url,
                "topText": top_text,
                "bottomText": bottom_text,
                "brandColor": brief.brand_color,
                "fontFamily": "Impact",
                "platform": brief.platform,
                "layout": "meme",
            },
            render_type="still",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "meme",
        "job_id": brief.job_id,
        "credits_consumed": STAGE_COSTS["image_generation"] + STAGE_COSTS["remotion_render"],
    }


@register_media_handler("infographic")
async def _handle_infographic(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle infographic media type.

    No image generation — pure Remotion composition using data_points.
    Only one stage: remotion_render with the Infographic composition.
    """
    # Validate data_points before any ledger entries
    if not brief.data_points:
        raise ValueError(
            "infographic media type requires data_points to be a non-empty list. "
            f"Got: {brief.data_points!r}"
        )

    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Stage 1: remotion_render (no image generation for infographics)
    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )
    try:
        render_result = await _call_remotion(
            "Infographic",
            {
                "title": brief.content_text,
                "dataPoints": brief.data_points,
                "brandColor": brief.brand_color,
                "style": brief.style,
            },
            render_type="still",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "infographic",
        "job_id": brief.job_id,
        "credits_consumed": STAGE_COSTS["remotion_render"],
    }


# ============================================================
# COMPLEX MEDIA-TYPE HANDLERS (Plan 04)
# Carousel, talking_head, short_form_video, text_on_video
# ============================================================

async def _generate_voice_for_video(text: str, voice_id: Optional[str] = None) -> Dict[str, Any]:
    """Generate voice narration with pcm_48000 format intent for video sync.

    Wraps generate_voice_narration for use in the video pipeline.
    The ElevenLabs output_format='pcm_48000' is the target for video sync;
    the base function returns audio_base64 which is staged to R2.
    Full pcm_48000 support will be added to the voice agent in a future iteration.
    """
    return await _get_voice()(text=text, voice_id=voice_id)


@register_media_handler("carousel")
async def _handle_carousel(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle carousel media type.

    Pipeline:
    1. Validate slides (non-empty, <= 10)
    2. Ledger image_generation stage (credits = per-slide cost * slide count)
    3. Generate all slide images in parallel via asyncio.gather
    4. Handle partial failures — continue with successful slides
    5. Stage all slide images to R2
    6. Check cost cap
    7. Ledger remotion_render stage
    8. Call Remotion ImageCarousel composition
    9. Return result
    """
    if not brief.slides or len(brief.slides) < 1:
        raise ValueError(
            "carousel media type requires slides to be a non-empty list. "
            f"Got: {brief.slides!r}"
        )

    # Truncate to max 10 slides
    slides = brief.slides[:10]
    slide_count = len(slides)

    # Ledger: charge per slide
    img_ledger_id = await _ledger_stage(
        brief.job_id,
        brief.user_id,
        "image_generation",
        "fal",
        STAGE_COSTS["image_generation"] * slide_count,
    )

    # Generate all slide images in parallel
    generate_image = _get_carousel()
    slide_tasks = [
        generate_image(
            prompt=slide.get("text", brief.content_text),
            style=brief.style,
            platform=brief.platform,
            persona_card=brief.persona_card,
        )
        for slide in slides
    ]

    try:
        slide_results = await asyncio.gather(*slide_tasks, return_exceptions=True)
        await _ledger_update(img_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(img_ledger_id, "failed", str(e))
        await _ledger_skip_remaining(brief.job_id, f"image_generation failed: {e}")
        raise

    # Stage successful slides to R2; log and skip failed ones
    staged_slides = []
    for i, result in enumerate(slide_results):
        if isinstance(result, Exception):
            logger.warning(
                "Carousel slide %d/%d failed generation: %s — skipping slide",
                i + 1, slide_count, result,
            )
            continue
        asset_url = result.get("image_url") or result.get("image_base64", "")
        r2_url = await _stage_asset_to_r2(asset_url, brief.job_id, f"slide_{i}")
        staged_slides.append({
            "imageUrl": r2_url,
            "text": slides[i].get("text", ""),
            "slideNumber": i + 1,
        })

    # Check cap before remotion render
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Ledger: remotion_render
    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )
    try:
        render_result = await _call_remotion(
            "ImageCarousel",
            {
                "slides": staged_slides,
                "brandColor": brief.brand_color,
                "fontFamily": "Inter",
            },
            render_type="still",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "carousel",
        "job_id": brief.job_id,
        "credits_consumed": STAGE_COSTS["image_generation"] * slide_count + STAGE_COSTS["remotion_render"],
    }


@register_media_handler("talking_head")
async def _handle_talking_head(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle talking_head media type.

    Pipeline:
    1. Ledger avatar_generation stage
    2. Generate HeyGen avatar video
    3. Stage HeyGen video URL to R2 IMMEDIATELY (HeyGen URLs expire ~1h after polling)
    4. Update ledger
    5. Check cost cap
    6. Ledger remotion_render stage
    7. Call Remotion TalkingHeadOverlay composition with R2 URL
    8. Return result
    """
    # Stage 1: avatar_generation
    avatar_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "avatar_generation", "heygen", STAGE_COSTS["avatar_generation"]
    )
    try:
        avatar_result = await _get_avatar_video()(
            script=brief.content_text,
            avatar_id=brief.avatar_id or "default",
        )
        # Stage HeyGen video URL to R2 IMMEDIATELY — HeyGen CDN URLs expire
        avatar_r2_url = await _stage_asset_to_r2(
            avatar_result.get("video_url", ""),
            brief.job_id,
            "avatar_video",
        )
        await _ledger_update(avatar_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(avatar_ledger_id, "failed", str(e))
        await _ledger_skip_remaining(brief.job_id, f"avatar_generation failed: {e}")
        raise

    # Check cap before remotion render
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    # Calculate duration in frames (30fps)
    duration_frames = int(avatar_result.get("duration", 30) * 30)

    # Stage 2: remotion_render
    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )
    try:
        render_result = await _call_remotion(
            "TalkingHeadOverlay",
            {
                "videoUrl": avatar_r2_url,
                "overlayText": "",
                "lowerThirdName": brief.persona_card.get("name", ""),
                "lowerThirdTitle": brief.persona_card.get("title", ""),
                "brandColor": brief.brand_color,
                "durationInFrames": duration_frames,
            },
            render_type="video",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "talking_head",
        "job_id": brief.job_id,
        "credits_consumed": STAGE_COSTS["avatar_generation"] + STAGE_COSTS["remotion_render"],
    }


@register_media_handler("short_form_video")
async def _handle_short_form_video(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle short_form_video media type.

    Pipeline:
    1. Phase 1: Parallel asset generation (voice + optional avatar + B-roll)
       - Voice narration (always; uses pcm_48000 intent for video sync)
       - Avatar video (only if brief.avatar_id is set)
       - B-roll video (always)
    2. Stage all successful assets to R2
    3. Build Remotion segment list
    4. Check cost cap
    5. Ledger + call Remotion ShortFormVideo composition
    6. Return result
    """
    # Phase 1: Setup ledger entries and collect tasks
    task_list = []
    task_keys = []
    ledger_ids = {}

    # Voice narration — critical for video sync
    ledger_ids["voice"] = await _ledger_stage(
        brief.job_id, brief.user_id, "voice_generation", "elevenlabs", STAGE_COSTS["voice_generation"]
    )
    task_keys.append("voice")
    task_list.append(_generate_voice_for_video(text=brief.content_text, voice_id=brief.voice_id))

    # Avatar (A-roll) if avatar_id provided
    if brief.avatar_id:
        ledger_ids["avatar"] = await _ledger_stage(
            brief.job_id, brief.user_id, "avatar_generation", "heygen", STAGE_COSTS["avatar_generation"]
        )
        task_keys.append("avatar")
        task_list.append(_get_avatar_video()(script=brief.content_text, avatar_id=brief.avatar_id))

    # B-roll generation
    ledger_ids["broll"] = await _ledger_stage(
        brief.job_id, brief.user_id, "broll_generation", "luma", STAGE_COSTS["broll_generation"]
    )
    task_keys.append("broll")
    task_list.append(_get_broll_video()(
        prompt=f"B-roll footage for: {brief.content_text[:100]}",
        duration=5,
    ))

    # Execute all asset generation in parallel
    raw_results = await asyncio.gather(*task_list, return_exceptions=True)
    results: Dict[str, Any] = dict(zip(task_keys, raw_results))

    # Update ledger entries based on success/failure
    for key, result in results.items():
        if isinstance(result, Exception):
            logger.warning("Short-form video asset '%s' failed: %s", key, result)
            await _ledger_update(ledger_ids[key], "failed", str(result))
        else:
            await _ledger_update(ledger_ids[key], "consumed")

    # Phase 2: Stage all successful assets to R2
    staged: Dict[str, str] = {}
    for key, result in results.items():
        if isinstance(result, Exception):
            continue
        # Pick the correct URL field per asset type
        url = (
            result.get("video_url")
            or result.get("audio_url")
            or result.get("audio_base64", "")
        )
        if url:
            staged[key] = await _stage_asset_to_r2(url, brief.job_id, key)

    # Phase 3: Build Remotion segment list
    segments: List[Dict[str, Any]] = []
    if "avatar" in staged:
        segments.append({
            "type": "video",
            "url": staged["avatar"],
            "durationInFrames": 450,  # 15s at 30fps
            "text": "",
        })
    if "broll" in staged:
        segments.append({
            "type": "video",
            "url": staged["broll"],
            "durationInFrames": 150,  # 5s at 30fps
        })
    # Fallback: text-only segment if no video assets generated
    if not segments:
        segments.append({
            "type": "image",
            "url": "",
            "durationInFrames": 900,  # 30s at 30fps
            "text": brief.content_text,
        })

    total_frames = sum(seg["durationInFrames"] for seg in segments)

    # Phase 4: Check cap and call Remotion
    if not await _ledger_check_cap(brief.job_id, cost_cap):
        await _ledger_skip_remaining(brief.job_id, "cost cap exceeded")
        raise RuntimeError("Cost cap exceeded")

    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )
    try:
        render_result = await _call_remotion(
            "ShortFormVideo",
            {
                "segments": segments,
                "audioUrl": staged.get("voice", ""),
                "musicUrl": brief.music_url or "",
                "brandColor": brief.brand_color,
                "durationInFrames": total_frames,
            },
            render_type="video",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    # Calculate credits consumed (only successfully consumed stages)
    credits_consumed = sum(
        STAGE_COSTS[stage]
        for stage, key in [
            ("voice_generation", "voice"),
            ("avatar_generation", "avatar"),
            ("broll_generation", "broll"),
        ]
        if key in results and not isinstance(results[key], Exception)
    ) + STAGE_COSTS["remotion_render"]

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "short_form_video",
        "job_id": brief.job_id,
        "credits_consumed": credits_consumed,
    }


@register_media_handler("text_on_video")
async def _handle_text_on_video(brief: MediaBrief, cost_cap: int) -> Dict[str, Any]:
    """Handle text_on_video media type.

    Pipeline:
    1. Validate brief.video_url is present
    2. Ledger remotion_render stage
    3. Stage user-uploaded video to R2
    4. Build single segment with user video + content_text overlay
    5. Call Remotion ShortFormVideo composition
    6. Return result
    """
    if brief.video_url is None:
        raise ValueError("video_url required for text_on_video media type")

    # Stage 1: remotion_render (single stage — user provides the video)
    render_ledger_id = await _ledger_stage(
        brief.job_id, brief.user_id, "remotion_render", "remotion", STAGE_COSTS["remotion_render"]
    )

    # Stage user-uploaded video to R2 before Remotion call
    video_r2_url = await _stage_asset_to_r2(brief.video_url, brief.job_id, "input_video")

    segments = [
        {
            "type": "video",
            "url": video_r2_url,
            "durationInFrames": 900,  # 30s at 30fps default
            "text": brief.content_text,
        }
    ]

    try:
        render_result = await _call_remotion(
            "ShortFormVideo",
            {
                "segments": segments,
                "audioUrl": "",
                "musicUrl": brief.music_url or "",
                "brandColor": brief.brand_color,
                "durationInFrames": 900,
            },
            render_type="video",
        )
        await _ledger_update(render_ledger_id, "consumed")
    except Exception as e:
        await _ledger_update(render_ledger_id, "failed", str(e))
        raise

    return {
        "url": render_result["url"],
        "render_id": render_result["render_id"],
        "media_type": "text_on_video",
        "job_id": brief.job_id,
        "credits_consumed": STAGE_COSTS["remotion_render"],
    }


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

    # Run QC media validation (MEDIA-14) — non-fatal
    output_url = result.get("url")
    if output_url:
        try:
            from agents.qc import validate_media_output
            qc_result = await validate_media_output(
                media_url=output_url,
                media_type=brief.media_type,
                platform=brief.platform,
                persona_card=brief.persona_card,
            )
            if not qc_result.get("passed", True):
                logger.warning(
                    "QC media validation failed for job %s: %s",
                    brief.job_id,
                    [c for c in qc_result.get("checks", []) if not c.get("passed")],
                )
        except Exception as e:
            logger.warning("QC media validation error (non-fatal): %s", e)

    return {
        "url": output_url,
        "render_id": result.get("render_id"),
        "media_type": brief.media_type,
        "job_id": brief.job_id,
        "credits_consumed": result.get("credits_consumed", 0),
    }
