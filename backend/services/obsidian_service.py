"""Obsidian Vault HTTP Client for ThookAI.

Wraps the Obsidian Local REST API plugin
(https://github.com/coddingtonbear/obsidian-local-rest-api) version 3.5.0+.

The Obsidian app runs on the user's local machine. For cloud-hosted ThookAI
to reach it, the user must expose the local REST API via Cloudflare Tunnel or
ngrok. OBSIDIAN_BASE_URL should be the tunnel URL (e.g., https://my-vault.example.com).

All calls are non-fatal — content generation proceeds if Obsidian is down or
not configured (OBS-04 graceful degradation).

Path sandboxing (OBS-05): Every file path returned from or sent to the Obsidian
API is validated against VAULT_SUBDIR before any HTTP request is made. Paths
that escape the designated subdirectory are blocked at the service level.

Per-user config override pattern (OBS-06): Per-user config in db.users.obsidian_config
takes precedence over global OBSIDIAN_BASE_URL env var fallback.
"""

import base64
import hashlib
import logging
from pathlib import PurePosixPath
from typing import List, Optional

import httpx

from config import settings
from database import db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path sandboxing (OBS-05)
# ---------------------------------------------------------------------------

def _validate_vault_path(vault_path: str) -> str:
    """Validate and return a safe vault path. Raises ValueError on any traversal attempt.

    Protections applied:
    1. Empty path rejected.
    2. Absolute paths (starting with / or containing :) are rejected.
    3. Path components are checked for '..' after PurePosixPath normalisation.
       This catches both bare '..' and 'a/../../../b' patterns.

    Returns the cleaned path string on success (never modifies path contents,
    just validates). Logs at ERROR level before raising so attacks are visible
    in server logs.
    """
    if not vault_path:
        raise ValueError("path traversal blocked: empty vault path")

    # Block absolute paths and Windows drive letters
    stripped = vault_path.lstrip()
    if stripped.startswith('/') or stripped.startswith('\\') or ':' in stripped:
        logger.error("path traversal blocked (absolute path): %r", vault_path)
        raise ValueError(f"path traversal blocked: absolute path {vault_path!r}")

    # Normalise with PurePosixPath — resolves '..' components
    normalised = PurePosixPath(vault_path)

    # Check every component of the normalised path for '..'
    if '..' in normalised.parts:
        logger.error("path traversal blocked: %r (contains '..' after normalisation)", vault_path)
        raise ValueError(f"path traversal blocked: {vault_path!r} contains '..' component")

    return str(normalised)


# ---------------------------------------------------------------------------
# Fernet decryption (mirrors routes/platforms.py pattern)
# ---------------------------------------------------------------------------

def _decrypt_obsidian_api_key(encrypted_key: str) -> str:
    """Decrypt a Fernet-encrypted Obsidian API key stored in db.users.

    Uses settings.security.fernet_key as the encryption key — same approach
    as routes/platforms.py _decrypt_token(). Returns empty string on any
    failure so the caller gracefully degrades.
    """
    fernet_key = settings.security.fernet_key
    if not fernet_key:
        logger.warning("FERNET_KEY not set — cannot decrypt Obsidian API key")
        return ""

    try:
        from cryptography.fernet import Fernet, InvalidToken

        key = fernet_key.encode() if isinstance(fernet_key, str) else fernet_key
        # Match the key normalisation in platforms.py _get_cipher()
        if len(key) != 44:
            key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        cipher = Fernet(key)
        return cipher.decrypt(encrypted_key.encode()).decode()
    except Exception as e:
        logger.warning("Failed to decrypt Obsidian API key (non-fatal): %s", e)
        return ""


# ---------------------------------------------------------------------------
# Per-user config retrieval
# ---------------------------------------------------------------------------

async def _get_user_obsidian_config(user_id: str) -> Optional[dict]:
    """Fetch the per-user Obsidian config dict from db.users.

    Returns the obsidian_config sub-document if the user has one,
    or None if the user doesn't exist or has no obsidian_config set.
    """
    try:
        user_doc = await db.users.find_one(
            {"user_id": user_id},
            {"_id": 0, "obsidian_config": 1},
        )
        if not user_doc:
            return None
        cfg = user_doc.get("obsidian_config")
        if not cfg or not cfg.get("base_url"):
            return None
        return cfg
    except Exception as e:
        logger.warning("Failed to fetch user obsidian config for %s (non-fatal): %s", user_id, e)
        return None


# ---------------------------------------------------------------------------
# Config resolution: per-user takes precedence, falls back to global env vars
# ---------------------------------------------------------------------------

async def _resolve_config(user_id: Optional[str] = None) -> tuple:
    """Return (base_url, api_key, vault_path) for the given user.

    Priority:
    1. Per-user db.users.obsidian_config (if exists and enabled=True).
    2. Global env fallback: settings.obsidian.base_url / api_key (vault_path="").

    Returns ('', '', '') when nothing is configured.
    """
    if user_id:
        user_cfg = await _get_user_obsidian_config(user_id)
        if user_cfg and user_cfg.get("enabled", False):
            base_url = user_cfg.get("base_url", "")
            encrypted_key = user_cfg.get("api_key_encrypted", "")
            api_key = _decrypt_obsidian_api_key(encrypted_key) if encrypted_key else ""
            vault_path = user_cfg.get("vault_path", "")
            # Validate vault_path if set — catch misconfigurations early
            if vault_path:
                try:
                    vault_path = _validate_vault_path(vault_path)
                except ValueError as e:
                    logger.error("Invalid vault_path in user config for %s: %s", user_id, e)
                    vault_path = ""
            return base_url, api_key, vault_path

    # Fallback to global env var config
    return (
        settings.obsidian.base_url or "",
        settings.obsidian.api_key or "",
        "",
    )


# ---------------------------------------------------------------------------
# Feature gate
# ---------------------------------------------------------------------------

def is_configured(user_id: Optional[str] = None) -> bool:
    """Synchronous check: returns True if Obsidian is configured for this user.

    NOTE: This is a synchronous check for use in import-time guards. For
    accurate per-user status (which requires a DB call), use the async
    _resolve_config() and check the returned base_url.

    Falls back to checking global settings.obsidian.is_configured() only
    (per-user check requires async DB call — use _resolve_config() for that).
    """
    return settings.obsidian.is_configured()


# ---------------------------------------------------------------------------
# Search vault (OBS-01, OBS-04, OBS-05)
# ---------------------------------------------------------------------------

async def search_vault(
    topic: str,
    user_id: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    """Full-text search the Obsidian vault for notes related to a topic.

    Used by Scout agent to enrich content research with vault knowledge (OBS-01).

    Returns dict with keys:
    - findings: formatted string with vault note titles + snippets
    - vault_sources: list of {"title": str, "snippet": str} dicts
    - sources_found: int count of matching notes

    Returns empty result on ANY failure (OBS-04 graceful degradation).
    Filters results to configured vault_path prefix (OBS-05 sandbox).
    """
    _empty = {"findings": "", "vault_sources": [], "sources_found": 0}

    try:
        base_url, api_key, vault_path = await _resolve_config(user_id)
    except Exception as e:
        logger.warning("Obsidian config resolution failed (non-fatal): %s", e)
        return _empty

    if not base_url or not base_url.startswith("http"):
        return _empty

    headers = {
        "Authorization": f"Bearer {api_key}" if api_key else "",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(
                f"{base_url.rstrip('/')}/search/simple/",
                params={"query": topic, "contextLength": 200},
                headers=headers,
            )
            if resp.status_code != 200:
                logger.warning(
                    "Obsidian search returned status %d for topic '%s'",
                    resp.status_code, topic,
                )
                return _empty

            raw_results: list = resp.json()
    except Exception as e:
        logger.warning("Obsidian search_vault failed for topic '%s' (non-fatal): %s", topic, e)
        return _empty

    # Filter results to vault_path sandbox (OBS-05)
    filtered = []
    for item in raw_results:
        filename = item.get("filename", "")
        if vault_path and not (
            filename == vault_path or filename.startswith(vault_path + "/")
        ):
            # Path outside designated subdirectory — silently skip
            continue
        filtered.append(item)

    if not filtered:
        return _empty

    # Build structured output
    vault_sources = []
    findings_lines = []
    for item in filtered[:max_results]:
        filename = item.get("filename", "unknown")
        matches = item.get("matches", [])
        snippet = ""
        if matches:
            snippet = matches[0].get("match", {}).get("content", "")
        # Truncate snippet for readability
        snippet = snippet[:200].strip()
        vault_sources.append({"title": filename, "snippet": snippet})
        findings_lines.append(f"[Vault: {filename}] {snippet}")

    findings_str = "\n".join(findings_lines)
    return {
        "findings": findings_str,
        "vault_sources": vault_sources,
        "sources_found": len(vault_sources),
    }


# ---------------------------------------------------------------------------
# Get recent notes (OBS-02, OBS-04, OBS-05)
# ---------------------------------------------------------------------------

async def get_recent_notes(
    user_id: str,
    hours: int = 24,
    max_results: int = 10,
) -> List[dict]:
    """Return recently modified vault notes from the configured subdirectory.

    Used by Strategist to detect new research notes as recommendation triggers (OBS-02).

    Approach: GET /vault/ to list files, filter by vault_path prefix.
    The Obsidian REST API /vault/ endpoint returns a JSON object with a "files"
    array listing all vault files relative to the vault root. We filter by
    vault_path and return the most recent entries.

    NOTE: The Local REST API v3.x /vault/ endpoint does not expose per-file
    modified timestamps in the listing response. We return the filtered file
    list without modified-time filtering — the Strategist uses the presence
    of new notes as a trigger signal regardless of exact timestamp.

    Returns list of {"title": str, "path": str, "modified": str} dicts.
    Returns [] on ANY failure (OBS-04 graceful degradation).
    """
    try:
        base_url, api_key, vault_path = await _resolve_config(user_id)
    except Exception as e:
        logger.warning("Obsidian config resolution failed in get_recent_notes (non-fatal): %s", e)
        return []

    if not base_url or not base_url.startswith("http"):
        return []

    headers = {
        "Authorization": f"Bearer {api_key}" if api_key else "",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(
                f"{base_url.rstrip('/')}/vault/",
                headers=headers,
            )
            if resp.status_code != 200:
                logger.warning(
                    "Obsidian /vault/ listing returned status %d for user %s",
                    resp.status_code, user_id,
                )
                return []

            data = resp.json()
    except Exception as e:
        logger.warning(
            "Obsidian get_recent_notes failed for user %s (non-fatal): %s", user_id, e
        )
        return []

    # files is a list of path strings relative to vault root
    all_files: list = data.get("files", [])
    if isinstance(all_files, list) is False:
        return []

    # Filter by vault_path sandbox (OBS-05)
    notes = []
    for file_path in all_files:
        if vault_path and not (
            file_path == vault_path or file_path.startswith(vault_path + "/")
        ):
            continue
        # Extract title from filename (last component without extension)
        title = file_path.rsplit("/", 1)[-1]
        if title.endswith(".md"):
            title = title[:-3]
        notes.append({
            "title": title,
            "path": file_path,
            "modified": "",  # timestamp not available in listing API
        })

    return notes[:max_results]
