import logging
import uuid
import secrets

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from database import db
from auth_utils import get_current_user
from config import settings
import uuid
import secrets
import logging
import httpx

from services.media_storage import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    upload_bytes_to_r2,
    get_r2_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/persona", tags=["persona"])

# Regional English configurations
REGIONAL_ENGLISH_CONFIG = {
    "US": {
        "name": "American English",
        "spelling_rules": ["-ize spellings (optimize, analyze)", "color (not colour)", "theater (not theatre)"],
        "date_format": "MM/DD/YYYY",
        "number_format": "1,000,000",
        "colloquialisms": "Standard American expressions",
    },
    "UK": {
        "name": "British English",
        "spelling_rules": ["-ise spellings (optimise, analyse)", "colour (not color)", "theatre (not theater)"],
        "date_format": "DD/MM/YYYY",
        "number_format": "1,000,000",
        "colloquialisms": "whilst, amongst, towards",
    },
    "AU": {
        "name": "Australian English",
        "spelling_rules": ["-ise spellings (similar to UK)", "colour, favour"],
        "date_format": "DD/MM/YYYY",
        "number_format": "1,000,000",
        "colloquialisms": "arvo (afternoon), servo (service station), brekkie (breakfast)",
    },
    "IN": {
        "name": "Indian English",
        "spelling_rules": ["British spelling conventions", "formal register"],
        "date_format": "DD/MM/YYYY",
        "number_format": "lakh (1,00,000), crore (1,00,00,000)",
        "colloquialisms": "Formal register, avoid casual contractions",
    },
}


class PersonaCardUpdate(BaseModel):
    card: Optional[Dict[str, Any]] = None


class SharePersonaRequest(BaseModel):
    expiry_days: Optional[int] = 30  # Default 30 days, -1 for permanent (Pro+)


class RegionalEnglishUpdate(BaseModel):
    regional_english: str  # US, UK, AU, IN


@router.get("/me")
async def get_my_persona(current_user: dict = Depends(get_current_user)):
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]}, {"_id": 0})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found. Complete onboarding first.")
    return persona


@router.put("/me")
async def update_my_persona(data: PersonaCardUpdate, current_user: dict = Depends(get_current_user)):
    update = {"updated_at": datetime.now(timezone.utc)}
    if data.card:
        update["card"] = data.card
    await db.persona_engines.update_one({"user_id": current_user["user_id"]}, {"$set": update})
    return {"message": "Persona updated successfully"}


@router.delete("/me")
async def reset_persona(current_user: dict = Depends(get_current_user)):
    await db.persona_engines.delete_one({"user_id": current_user["user_id"]})
    await db.users.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {"onboarding_completed": False}}
    )
    return {"message": "Persona reset. Complete onboarding to create a new one."}


# ============ SHAREABLE PERSONA CARDS ============

@router.post("/share")
async def share_persona(data: SharePersonaRequest, current_user: dict = Depends(get_current_user)):
    """Generate a public share token for the user's persona card."""
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found. Complete onboarding first.")
    
    # Check if user already has an active share token
    existing_share = await db.persona_shares.find_one({
        "user_id": current_user["user_id"],
        "is_active": True,  # Only find active shares
        "$or": [
            {"expires_at": {"$gt": datetime.now(timezone.utc)}},
            {"expires_at": None}  # Permanent shares
        ]
    })
    
    if existing_share:
        return {
            "success": True,
            "share_token": existing_share["share_token"],
            "share_url": f"/creator/{existing_share['share_token']}",
            "expires_at": existing_share.get("expires_at"),
            "is_permanent": existing_share.get("expires_at") is None,
            "created_at": existing_share["created_at"],
            "message": "Existing share link retrieved"
        }
    
    # Get user subscription tier for permanent share eligibility
    user = await db.users.find_one({"user_id": current_user["user_id"]})
    tier = user.get("subscription_tier", "starter")

    # Paid users can have permanent shares
    is_pro_plus = tier not in ("starter", "free")
    
    # Generate new share token
    share_token = secrets.token_urlsafe(16)
    
    # Calculate expiry
    if data.expiry_days == -1 and is_pro_plus:
        expires_at = None  # Permanent
    else:
        expiry_days = data.expiry_days if data.expiry_days > 0 else 30
        if not is_pro_plus:
            expiry_days = min(expiry_days, 30)  # Free tier max 30 days
        expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
    
    share_doc = {
        "share_id": str(uuid.uuid4()),
        "share_token": share_token,
        "user_id": current_user["user_id"],
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
        "view_count": 0,
        "is_active": True
    }
    
    await db.persona_shares.insert_one(share_doc)
    
    return {
        "success": True,
        "share_token": share_token,
        "share_url": f"/creator/{share_token}",
        "expires_at": expires_at,
        "is_permanent": expires_at is None,
        "created_at": share_doc["created_at"],
        "message": "Share link created successfully"
    }


@router.get("/share/status")
async def get_share_status(current_user: dict = Depends(get_current_user)):
    """Get the current share status for the user's persona."""
    share = await db.persona_shares.find_one({
        "user_id": current_user["user_id"],
        "is_active": True,
        "$or": [
            {"expires_at": {"$gt": datetime.now(timezone.utc)}},
            {"expires_at": None}
        ]
    })
    
    if not share:
        return {
            "success": True,
            "is_shared": False,
            "share_token": None,
            "share_url": None
        }
    
    return {
        "success": True,
        "is_shared": True,
        "share_token": share["share_token"],
        "share_url": f"/creator/{share['share_token']}",
        "expires_at": share.get("expires_at"),
        "is_permanent": share.get("expires_at") is None,
        "view_count": share.get("view_count", 0),
        "created_at": share["created_at"]
    }


@router.delete("/share")
async def revoke_share(current_user: dict = Depends(get_current_user)):
    """Revoke the current share link."""
    result = await db.persona_shares.update_many(
        {"user_id": current_user["user_id"]},
        {"$set": {"is_active": False, "revoked_at": datetime.now(timezone.utc)}}
    )
    
    return {
        "success": True,
        "message": "Share link revoked successfully",
        "revoked_count": result.modified_count
    }


@router.get("/public/{share_token}")
async def get_public_persona(share_token: str):
    """
    Public endpoint (no auth) to view a shared persona card.
    Only exposes safe data - excludes UOM internals and sensitive info.
    """
    # Find the share record
    share = await db.persona_shares.find_one({
        "share_token": share_token,
        "is_active": True
    })
    
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found or has been revoked")
    
    # Check expiry
    expires_at = share.get("expires_at")
    if expires_at:
        # Ensure both datetimes have timezone info for comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Share link has expired")
    
    # Increment view count
    await db.persona_shares.update_one(
        {"share_token": share_token},
        {"$inc": {"view_count": 1}}
    )
    
    # Get the persona
    persona = await db.persona_engines.find_one({"user_id": share["user_id"]})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no longer exists")
    
    # Get user info for display
    user = await db.users.find_one({"user_id": share["user_id"]})
    
    # Extract only safe, shareable data
    card = persona.get("card", {})
    voice_fingerprint = persona.get("voice_fingerprint", {})
    
    # Build public persona response
    public_persona = {
        "success": True,
        "creator": {
            "name": user.get("name", "Creator") if user else "Creator",
            "picture": user.get("picture") if user else None,
        },
        "card": {
            "personality_archetype": card.get("personality_archetype", "Creator"),
            "writing_voice_descriptor": card.get("writing_voice_descriptor"),
            "content_niche_signature": card.get("content_niche_signature"),
            "inferred_audience_profile": card.get("inferred_audience_profile"),
            "top_content_format": card.get("top_content_format"),
            "hook_style": card.get("hook_style"),
            "content_pillars": card.get("content_pillars", []),
            "focus_platforms": card.get("focus_platforms", []),
            "regional_english": card.get("regional_english", "US"),
        },
        "voice_metrics": {
            "vocabulary_complexity": voice_fingerprint.get("vocabulary_complexity", 0.65),
            "emoji_frequency": voice_fingerprint.get("emoji_frequency", 0.05),
            "hook_style_preferences": voice_fingerprint.get("hook_style_preferences", []),
        },
        "share_info": {
            "view_count": share.get("view_count", 0) + 1,
            "shared_since": share["created_at"],
        }
    }
    
    return public_persona


# ============ REGIONAL ENGLISH ============

@router.get("/regional-english/options")
async def get_regional_english_options():
    """Get available regional English format options."""
    return {
        "success": True,
        "options": [
            {
                "code": code,
                "name": config["name"],
                "spelling_rules": config["spelling_rules"],
                "date_format": config["date_format"],
                "number_format": config["number_format"],
                "colloquialisms": config["colloquialisms"],
            }
            for code, config in REGIONAL_ENGLISH_CONFIG.items()
        ]
    }


@router.put("/regional-english")
async def update_regional_english(data: RegionalEnglishUpdate, current_user: dict = Depends(get_current_user)):
    """Update the user's regional English preference."""
    if data.regional_english not in REGIONAL_ENGLISH_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid regional English code. Valid options: {list(REGIONAL_ENGLISH_CONFIG.keys())}")
    
    # Update persona card with regional english setting
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found. Complete onboarding first.")
    
    card = persona.get("card", {})
    card["regional_english"] = data.regional_english
    
    await db.persona_engines.update_one(
        {"user_id": current_user["user_id"]},
        {
            "$set": {
                "card": card,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {
        "success": True,
        "regional_english": data.regional_english,
        "config": REGIONAL_ENGLISH_CONFIG[data.regional_english],
        "message": f"Regional English updated to {REGIONAL_ENGLISH_CONFIG[data.regional_english]['name']}"
    }



# ============ HEYGEN AVATAR CREATION ============

class AvatarCreateRequest(BaseModel):
    photo_url: str  # Public URL of the user's photo for avatar creation


@router.post("/avatar/create")
async def create_avatar(data: AvatarCreateRequest, current_user: dict = Depends(get_current_user)):
    """Create a HeyGen photo avatar from a user's photo.

    Tier gate: studio/agency only.
    Stores the resulting avatar_id in persona_engines.heygen_avatar_id.
    """

    # Tier gate
    user = await db.users.find_one({"user_id": current_user["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tier = user.get("subscription_tier", "starter")
    # Allow custom plan users with voice_enabled
    has_access = tier in ("studio", "agency")
    if tier == "custom":
        plan_features = user.get("plan_config", {}).get("features", {})
        has_access = plan_features.get("voice_enabled", False)
    if not has_access:
        raise HTTPException(
            status_code=403,
            detail=f"Avatar creation requires a plan with voice features (current: {tier})"
        )

    # Ensure persona exists
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found. Complete onboarding first.")

    # Check HeyGen API key
    heygen_api_key = getattr(settings, "heygen_api_key", None) or __import__("os").environ.get("HEYGEN_API_KEY", "")
    if not heygen_api_key or heygen_api_key.startswith("placeholder"):
        raise HTTPException(
            status_code=503,
            detail="HeyGen is not configured. Set HEYGEN_API_KEY to enable avatar creation."
        )

    # Call HeyGen photo avatar creation API
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.heygen.com/v2/photo_avatar/avatar/create",
                headers={
                    "X-Api-Key": heygen_api_key,
                    "Content-Type": "application/json",
                },
                json={"image_url": data.photo_url},
            )

            if response.status_code not in (200, 201):
                error_detail = response.text[:500]
                logger.error("HeyGen avatar creation failed: %s %s", response.status_code, error_detail)
                raise HTTPException(
                    status_code=502,
                    detail=f"HeyGen API error ({response.status_code}): {error_detail}"
                )

            resp_data = response.json()
            avatar_id = (
                resp_data.get("data", {}).get("avatar_id")
                or resp_data.get("avatar_id")
            )
            if not avatar_id:
                raise HTTPException(status_code=502, detail="HeyGen did not return an avatar_id")

    except httpx.HTTPError as e:
        logger.error("HeyGen request failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to reach HeyGen API: {e}")

    # Store avatar_id in persona
    now = datetime.now(timezone.utc)
    await db.persona_engines.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {
            "heygen_avatar_id": avatar_id,
            "heygen_avatar_photo_url": data.photo_url,
            "heygen_avatar_created_at": now,
            "updated_at": now,
        }},
    )

    return {
        "success": True,
        "avatar_id": avatar_id,
        "message": "Avatar created successfully. You can now generate talking-head videos."
    }


@router.get("/avatar")
async def get_avatar(current_user: dict = Depends(get_current_user)):
    """Get the user's HeyGen avatar status."""
    persona = await db.persona_engines.find_one(
        {"user_id": current_user["user_id"]},
        {"heygen_avatar_id": 1, "heygen_avatar_photo_url": 1, "heygen_avatar_created_at": 1},
    )
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found. Complete onboarding first.")

    avatar_id = persona.get("heygen_avatar_id")
    return {
        "has_avatar": avatar_id is not None,
        "avatar_id": avatar_id,
        "preview_url": persona.get("heygen_avatar_photo_url"),
        "created_at": persona.get("heygen_avatar_created_at"),
    }


# ============ VOICE CLONE ============

VOICE_CLONE_TIERS = ("studio", "agency", "custom")
VOICE_CLONE_AUDIO_MIMES = set(ALLOWED_MIME_TYPES.get("audio", []))
MAX_VOICE_SAMPLES = 5
MAX_AUDIO_BYTES = MAX_FILE_SIZE.get("audio", 25 * 1024 * 1024)


def _require_voice_clone_tier(user: dict) -> None:
    """Raise 403 if the user's subscription does not include voice cloning."""
    tier = user.get("subscription_tier", "starter")
    has_access = tier in VOICE_CLONE_TIERS
    # Custom plan users need voice_enabled in their plan config
    if tier == "custom":
        plan_features = user.get("plan_config", {}).get("features", {})
        has_access = plan_features.get("voice_enabled", False)
    if not has_access:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "tier_required",
                "message": "Voice cloning requires a plan with voice features.",
                "current_tier": tier,
                "required_tiers": list(VOICE_CLONE_TIERS),
            },
        )


class VoiceCloneCreateRequest(BaseModel):
    voice_name: str


@router.post("/voice-clone/samples")
async def upload_voice_samples(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload 1-5 audio samples for voice cloning. Studio/Agency only."""

    # Tier gate
    user = await db.users.find_one({"user_id": current_user["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _require_voice_clone_tier(user)

    if len(files) < 1 or len(files) > MAX_VOICE_SAMPLES:
        raise HTTPException(
            status_code=400,
            detail=f"Please upload between 1 and {MAX_VOICE_SAMPLES} audio files.",
        )

    user_id = current_user["user_id"]
    uploaded_urls: List[str] = []

    for file in files:
        ct = (file.content_type or "").split(";")[0].strip().lower()
        if ct not in VOICE_CLONE_AUDIO_MIMES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' has unsupported type '{ct}'. Allowed: {', '.join(sorted(VOICE_CLONE_AUDIO_MIMES))}",
            )

        file_data = await file.read()
        if len(file_data) > MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds the 25 MB limit.",
            )

        safe_name = "".join(c for c in (file.filename or "sample") if c.isalnum() or c in "._-")[:120] or "sample"
        storage_key = f"voice-samples/{user_id}/{uuid.uuid4().hex[:12]}_{safe_name}"
        url = upload_bytes_to_r2(storage_key, file_data, ct)
        uploaded_urls.append(url)

    # Store sample URLs in persona_engines
    now = datetime.now(timezone.utc)
    await db.persona_engines.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "voice_sample_urls": uploaded_urls,
                "voice_samples_uploaded_at": now,
                "updated_at": now,
            }
        },
    )

    return {
        "success": True,
        "sample_count": len(uploaded_urls),
        "sample_urls": uploaded_urls,
        "message": f"Uploaded {len(uploaded_urls)} voice sample(s). You can now create your voice clone.",
    }


@router.post("/voice-clone/create")
async def create_voice_clone(
    data: VoiceCloneCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a voice clone from uploaded samples via ElevenLabs. Studio/Agency only."""
    from agents.voice import create_voice_clone as _create_voice_clone

    user = await db.users.find_one({"user_id": current_user["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _require_voice_clone_tier(user)

    user_id = current_user["user_id"]

    # Fetch sample URLs from persona
    persona = await db.persona_engines.find_one({"user_id": user_id})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found. Complete onboarding first.")

    sample_urls = persona.get("voice_sample_urls", [])
    if not sample_urls:
        raise HTTPException(
            status_code=400,
            detail="No voice samples uploaded. Upload samples first via POST /api/persona/voice-clone/samples.",
        )

    result = await _create_voice_clone(user_id, sample_urls, data.voice_name)

    if result.get("status") == "failed":
        raise HTTPException(status_code=502, detail=result.get("error", "Voice clone creation failed."))

    return {
        "success": True,
        "voice_id": result.get("voice_id"),
        "voice_name": result.get("name"),
        "status": result.get("status"),
        "message": "Voice clone created successfully.",
    }


@router.get("/voice-clone")
async def get_voice_clone_status(current_user: dict = Depends(get_current_user)):
    """Return the current voice clone status for the user."""
    user = await db.users.find_one({"user_id": current_user["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tier = user.get("subscription_tier", "free")

    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]})
    if not persona:
        return {
            "success": True,
            "has_clone": False,
            "tier_eligible": tier in VOICE_CLONE_TIERS,
        }

    voice_clone_id = persona.get("voice_clone_id")
    voice_clone_name = persona.get("voice_clone_name")
    sample_urls = persona.get("voice_sample_urls", [])

    return {
        "success": True,
        "has_clone": bool(voice_clone_id),
        "voice_id": voice_clone_id,
        "voice_name": voice_clone_name,
        "sample_count": len(sample_urls),
        "sample_urls": sample_urls,
        "created_at": persona.get("voice_clone_created_at"),
        "tier_eligible": tier in VOICE_CLONE_TIERS,
    }


@router.delete("/voice-clone")
async def delete_voice_clone(current_user: dict = Depends(get_current_user)):
    """Delete the user's voice clone from ElevenLabs and clear local records."""
    from agents.voice import delete_voice_clone as _delete_voice_clone

    user = await db.users.find_one({"user_id": current_user["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _require_voice_clone_tier(user)

    user_id = current_user["user_id"]
    persona = await db.persona_engines.find_one({"user_id": user_id})
    if not persona or not persona.get("voice_clone_id"):
        raise HTTPException(status_code=404, detail="No voice clone found to delete.")

    deleted = await _delete_voice_clone(user_id)
    if not deleted:
        raise HTTPException(status_code=502, detail="Failed to delete voice clone from ElevenLabs.")

    return {
        "success": True,
        "message": "Voice clone deleted successfully.",

    }
