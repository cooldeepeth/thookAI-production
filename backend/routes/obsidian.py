"""Obsidian vault integration configuration routes (OBS-06).

Per-user Obsidian config CRUD with Fernet-encrypted API key storage.
Vault path sandboxing enforced at save time (OBS-05).

Endpoints:
  POST   /api/obsidian/config  — save vault config (base_url, api_key, vault_path)
  GET    /api/obsidian/config  — read config with masked API key
  DELETE /api/obsidian/config  — remove config
  POST   /api/obsidian/test    — test vault connection via search_vault
"""

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from auth_utils import get_current_user
from config import settings
from database import db
from services.obsidian_service import _validate_vault_path, search_vault

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/obsidian", tags=["obsidian"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ObsidianConfigRequest(BaseModel):
    base_url: str          # e.g., "https://localhost:27124"
    api_key: str           # Plaintext — encrypted before storage
    vault_path: str = ""   # Subdirectory to sandbox reads to (e.g., "research/notes")

    @field_validator("base_url")
    @classmethod
    def base_url_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("base_url must not be empty")
        return v.strip()


class ObsidianConfigResponse(BaseModel):
    configured: bool
    enabled: bool = False
    base_url: str = ""
    api_key_masked: str = ""
    vault_path: str = ""
    vault_path_display: str = ""  # "ThookAI will read files from: research/notes"
    configured_at: Optional[str] = None
    last_tested_at: Optional[str] = None


class ObsidianTestResponse(BaseModel):
    connected: bool
    vault_accessible: bool = False
    notes_found: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Fernet helpers (mirror routes/platforms.py key normalisation)
# ---------------------------------------------------------------------------

def _get_obsidian_cipher():
    """Return a Fernet cipher using settings.security.fernet_key.

    Mirrors the key normalisation in routes/platforms.py _get_cipher():
    - Raw key bytes that are not a 44-byte base64 Fernet key are SHA-256
      hashed then base64-encoded so any FERNET_KEY value works.
    """
    from cryptography.fernet import Fernet  # noqa: PLC0415

    fernet_key = settings.security.fernet_key
    if not fernet_key:
        raise HTTPException(status_code=500, detail="FERNET_KEY not configured")
    key = fernet_key.encode() if isinstance(fernet_key, str) else fernet_key
    if len(key) != 44:
        key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    return Fernet(key)


def _encrypt_api_key(api_key: str) -> str:
    """Encrypt an Obsidian API key for storage in db.users."""
    cipher = _get_obsidian_cipher()
    return cipher.encrypt(api_key.encode()).decode()


def _mask_api_key(encrypted_key: str) -> str:
    """Decrypt and mask an API key, showing only the last 4 characters.

    Returns "****" if decryption fails (non-critical — just masks display).
    """
    try:
        cipher = _get_obsidian_cipher()
        decrypted = cipher.decrypt(encrypted_key.encode()).decode()
        if len(decrypted) > 4:
            return "****" + decrypted[-4:]
        return "****"
    except Exception:
        return "****"


def _build_vault_path_display(vault_path: str) -> str:
    """Build the human-readable vault path display string."""
    if vault_path:
        return f"ThookAI will read files from: {vault_path}"
    return "ThookAI will read files from: entire vault"


# ---------------------------------------------------------------------------
# POST /api/obsidian/config — save config
# ---------------------------------------------------------------------------

@router.post("/config", response_model=ObsidianConfigResponse)
async def save_obsidian_config(
    body: ObsidianConfigRequest,
    user: dict = Depends(get_current_user),
):
    """Save the user's Obsidian vault configuration.

    - Validates vault_path for path traversal (OBS-05).
    - Encrypts api_key with Fernet before storing in db.users.obsidian_config.
    - Sets enabled=True on save.
    """
    user_id: str = user["user_id"]

    # Validate vault_path (OBS-05) — empty string allowed (means whole vault)
    vault_path = body.vault_path.strip() if body.vault_path else ""
    if vault_path:
        try:
            vault_path = _validate_vault_path(vault_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    encrypted_key = _encrypt_api_key(body.api_key)

    config_doc = {
        "base_url": body.base_url.strip(),
        "api_key_encrypted": encrypted_key,
        "vault_path": vault_path,
        "enabled": True,
        "configured_at": datetime.now(timezone.utc).isoformat(),
        "last_tested_at": None,
    }

    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"obsidian_config": config_doc}},
    )

    logger.info("Obsidian config saved for user %s (vault_path=%r)", user_id, vault_path)

    return ObsidianConfigResponse(
        configured=True,
        enabled=True,
        base_url=config_doc["base_url"],
        api_key_masked=_mask_api_key(encrypted_key),
        vault_path=vault_path,
        vault_path_display=_build_vault_path_display(vault_path),
        configured_at=config_doc["configured_at"],
    )


# ---------------------------------------------------------------------------
# GET /api/obsidian/config — read config
# ---------------------------------------------------------------------------

@router.get("/config", response_model=ObsidianConfigResponse)
async def get_obsidian_config(
    user: dict = Depends(get_current_user),
):
    """Retrieve the user's current Obsidian config with API key masked.

    Returns {"configured": false} if no config is set.
    """
    user_id: str = user["user_id"]

    user_doc = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0, "obsidian_config": 1},
    )

    obsidian_cfg = (user_doc or {}).get("obsidian_config") if user_doc else None

    if not obsidian_cfg or not obsidian_cfg.get("base_url"):
        return ObsidianConfigResponse(configured=False)

    vault_path = obsidian_cfg.get("vault_path", "")
    encrypted_key = obsidian_cfg.get("api_key_encrypted", "")
    masked_key = _mask_api_key(encrypted_key) if encrypted_key else "****"

    return ObsidianConfigResponse(
        configured=True,
        enabled=obsidian_cfg.get("enabled", False),
        base_url=obsidian_cfg.get("base_url", ""),
        api_key_masked=masked_key,
        vault_path=vault_path,
        vault_path_display=_build_vault_path_display(vault_path),
        configured_at=obsidian_cfg.get("configured_at"),
        last_tested_at=obsidian_cfg.get("last_tested_at"),
    )


# ---------------------------------------------------------------------------
# DELETE /api/obsidian/config — remove config
# ---------------------------------------------------------------------------

@router.delete("/config")
async def delete_obsidian_config(
    user: dict = Depends(get_current_user),
):
    """Remove the user's Obsidian vault configuration.

    Unsets obsidian_config from db.users — user must re-configure to re-enable.
    """
    user_id: str = user["user_id"]

    await db.users.update_one(
        {"user_id": user_id},
        {"$unset": {"obsidian_config": ""}},
    )

    logger.info("Obsidian config removed for user %s", user_id)
    return {"removed": True}


# ---------------------------------------------------------------------------
# POST /api/obsidian/test — test connection
# ---------------------------------------------------------------------------

@router.post("/test", response_model=ObsidianTestResponse)
async def test_obsidian_connection(
    user: dict = Depends(get_current_user),
):
    """Test the user's Obsidian vault connection by running a search_vault call.

    Returns connected=True and notes_found count on success.
    Returns connected=False with error message on any failure.
    """
    user_id: str = user["user_id"]

    try:
        result = await search_vault(
            topic="test connection",
            user_id=user_id,
            max_results=1,
        )
        return ObsidianTestResponse(
            connected=True,
            vault_accessible=True,
            notes_found=result.get("sources_found", 0),
        )
    except Exception as exc:
        logger.warning(
            "Obsidian connection test failed for user %s: %s", user_id, exc
        )
        return ObsidianTestResponse(
            connected=False,
            vault_accessible=False,
            error=str(exc),
        )
