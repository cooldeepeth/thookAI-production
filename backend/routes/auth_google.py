"""Native Google OAuth (Authlib). Replaces Emergent-hosted OAuth."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from database import db
from routes.auth import create_jwt_token, set_auth_cookie

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-google"])

_oauth = OAuth()
_google_registered = False


def _register_google_client() -> bool:
    global _google_registered
    if _google_registered:
        return True
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return False
    _oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    _google_registered = True
    return True


def _backend_redirect_uri() -> str:
    base = os.environ.get("BACKEND_URL", "http://localhost:8001").rstrip("/")
    return f"{base}/api/auth/google/callback"


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


@router.get("/google")
async def google_login(request: Request):
    if not _register_google_client():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET).",
        )
    redirect_uri = _backend_redirect_uri()
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request):
    if not _register_google_client():
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")
    frontend = _frontend_url()
    err_redirect = f"{frontend}/auth?error=oauth_failed"

    try:
        token = await _oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.warning("Google OAuth token exchange failed: %s", e)
        return RedirectResponse(url=err_redirect, status_code=302)

    user_info = token.get("userinfo")
    if not user_info:
        access_token = token.get("access_token")
        if not access_token:
            return RedirectResponse(url=err_redirect, status_code=302)
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=15.0,
                )
                r.raise_for_status()
                user_info = r.json()
        except Exception as e:
            logger.warning("Google userinfo fetch failed: %s", e)
            return RedirectResponse(url=err_redirect, status_code=302)

    email = user_info.get("email")
    if not email:
        return RedirectResponse(url=err_redirect, status_code=302)

    name = user_info.get("name") or email.split("@")[0]
    picture = user_info.get("picture") or None

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one(
            {
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "auth_method": "google",
                "plan": "free",
                "credits": 100,
                "onboarding_completed": False,
                "platforms_connected": [],
                "created_at": datetime.now(timezone.utc),
            }
        )

    jwt_token = create_jwt_token(user_id, email)
    dest = f"{frontend}/dashboard?token={quote(jwt_token, safe='')}"
    response = RedirectResponse(url=dest, status_code=302)
    set_auth_cookie(response, jwt_token)
    return response
