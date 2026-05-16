"""Native Google OAuth (Authlib). Replaces Emergent-hosted OAuth."""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from config import settings
from database import db
from routes.auth import create_jwt_token, set_auth_cookie, set_csrf_cookie

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-google"])

# One-time OAuth exchange code TTL. Short on purpose — the frontend redeems
# it immediately after landing on the post-auth redirect URL.
_OAUTH_CODE_TTL_SECONDS = 60


class ExchangeCodeRequest(BaseModel):
    code: str

_oauth = OAuth()
_google_registered = False


def _register_google_client() -> bool:
    global _google_registered
    if _google_registered:
        return True
    if not settings.google.is_configured():
        return False
    _oauth.register(
        name="google",
        client_id=settings.google.client_id,
        client_secret=settings.google.client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    _google_registered = True
    return True


def _frontend_url() -> str:
    # FIXED: use settings instead of os.environ.get directly
    return settings.email.frontend_url.rstrip("/")


@router.get("/google")
async def google_login(request: Request):
    if not settings.google.is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "google_auth_unavailable",
                "message": "Google sign-in is not configured on this server."
            }
        )
    if not _register_google_client():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "google_auth_unavailable",
                "message": "Google sign-in is not configured on this server."
            }
        )
    redirect_uri = settings.google.redirect_uri
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request):
    if not settings.google.is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "google_auth_unavailable",
                "message": "Google sign-in is not configured on this server."
            }
        )
    if not _register_google_client():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "google_auth_unavailable",
                "message": "Google sign-in is not configured on this server."
            }
        )
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
        existing_method = existing.get("auth_method", "email")
        if existing_method not in ("google", "email"):
            # Account exists with a different social provider — don't merge silently
            return RedirectResponse(
                url=f"{frontend}/auth?error=account_exists&method={existing_method}",
                status_code=302,
            )
        user_id = existing["user_id"]
        update_fields = {"name": name, "picture": picture}
        if existing_method == "email":
            # Link Google to existing email account only if Google has verified
            # the email. Without this check, a mis-typed or spoofed email claim
            # from an attacker's Google account could take over the original.
            if user_info.get("email_verified") is not True:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "google_email_unverified",
                        "message": "Please verify your Google email before linking.",
                    },
                )
            update_fields["auth_method"] = "google"
        await db.users.update_one({"user_id": user_id}, {"$set": update_fields})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one(
            {
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "auth_method": "google",
                "plan": "starter",
                "subscription_tier": "starter",
                "credits": 200,
                "credit_allowance": 0,
                "credits_last_refresh": datetime.now(timezone.utc),
                "credits_refreshed_at": datetime.now(timezone.utc),
                "onboarding_completed": False,
                "platforms_connected": [],
                "created_at": datetime.now(timezone.utc),
            }
        )

    # Mint a short-lived one-time exchange code rather than embedding the
    # JWT in the redirect URL. The frontend calls POST /api/auth/exchange-code
    # with this code to receive the JWT (body + httpOnly cookie). Keeps the
    # token out of browser history, referer headers, and reverse-proxy logs.
    exchange_code = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    await db.oauth_exchange_codes.insert_one({
        "code": exchange_code,
        "user_id": user_id,
        "email": email,
        "created_at": now,
        "expires_at": now + timedelta(seconds=_OAUTH_CODE_TTL_SECONDS),
        "used": False,
    })
    dest = f"{frontend}/dashboard?code={exchange_code}"
    return RedirectResponse(url=dest, status_code=302)


@router.post("/exchange-code")
async def exchange_code(data: ExchangeCodeRequest, response: Response):
    """Exchange a one-time OAuth code (from Google redirect) for a JWT.

    Atomically flips `used=False` → `used=True` so a replay of the same code
    returns 400. Sets the session and CSRF cookies and also returns the JWT
    in the body for API clients that can't rely on cookie-based sessions.
    """
    now = datetime.now(timezone.utc)
    doc = await db.oauth_exchange_codes.find_one_and_update(
        {"code": data.code, "used": False, "expires_at": {"$gt": now}},
        {"$set": {"used": True, "used_at": now}},
    )
    if not doc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_code",
                "message": "Exchange code is invalid, expired, or already used.",
            },
        )

    user_id = doc["user_id"]
    email = doc["email"]
    jwt_token = create_jwt_token(user_id, email)
    csrf_value = secrets.token_urlsafe(32)
    set_auth_cookie(response, jwt_token)
    set_csrf_cookie(response, csrf_value)
    return {"token": jwt_token, "csrf_token": csrf_value}
