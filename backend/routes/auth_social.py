"""Social Login Routes — LinkedIn and X (Twitter) OAuth 2.0.

Follows the same pattern as auth_google.py:
1. /auth/linkedin → redirect to provider
2. /auth/linkedin/callback → exchange code, find-or-create user, issue JWT, redirect to frontend
3. Same for /auth/x

Also stores platform tokens for publishing (like platforms.py does)
so users who sign in with LinkedIn/X are auto-connected for publishing.
"""
import base64
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from config import settings
from database import db
from routes.auth import create_jwt_token, set_auth_cookie, set_csrf_cookie

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-social"])

# ============ CONFIG ============

LINKEDIN_CLIENT_ID = settings.platforms.linkedin_client_id or ""
LINKEDIN_CLIENT_SECRET = settings.platforms.linkedin_client_secret or ""
TWITTER_API_KEY = settings.platforms.twitter_api_key or ""
TWITTER_API_SECRET = settings.platforms.twitter_api_secret or ""
FRONTEND_URL = settings.app.frontend_url.rstrip("/")
BACKEND_URL = settings.app.backend_url.rstrip("/")

# Scopes for login — request profile + email + publish
LINKEDIN_LOGIN_SCOPES = "openid profile email w_member_social"
TWITTER_LOGIN_SCOPES = "tweet.read tweet.write users.read offline.access"


def _is_configured(client_id: str, client_secret: str) -> bool:
    """Check if OAuth credentials are configured (not empty/placeholder)."""
    if not client_id or not client_secret:
        return False
    placeholders = ("placeholder", "your_", "xxx", "change_this")
    return not any(client_id.lower().startswith(p) for p in placeholders)


def _encrypt_token(token: str) -> str:
    """Encrypt token for storage using the platform encryption key."""
    from cryptography.fernet import Fernet
    key = settings.platforms.encryption_key
    if not key:
        logger.warning("ENCRYPTION_KEY not set — storing token unencrypted")
        return token
    key_bytes = key.encode() if isinstance(key, str) else key
    if len(key_bytes) != 44:
        key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
    cipher = Fernet(key_bytes)
    return cipher.encrypt(token.encode()).decode()


async def _find_or_create_user(
    email: str, name: str, picture: str | None, auth_method: str
) -> str:
    """Find existing user by email or create new one. Returns user_id."""
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        update_fields = {"name": name}
        if picture:
            update_fields["picture"] = picture
        await db.users.update_one({"user_id": user_id}, {"$set": update_fields})
        return user_id

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "auth_method": auth_method,
        "plan": "starter",
        "subscription_tier": "starter",
        "credits": 200,
        "credit_allowance": 0,
        "credits_last_refresh": datetime.now(timezone.utc),
        "credits_refreshed_at": datetime.now(timezone.utc),
        "onboarding_completed": False,
        "platforms_connected": [],
        "created_at": datetime.now(timezone.utc),
    })
    return user_id


async def _store_platform_token(
    user_id: str, platform: str, access_token: str,
    refresh_token: str | None, expires_in: int, account_name: str, scope: str
) -> None:
    """Store encrypted platform token for publishing + update user platforms_connected."""
    now = datetime.now(timezone.utc)
    await db.platform_tokens.update_one(
        {"user_id": user_id, "platform": platform},
        {"$set": {
            "access_token": _encrypt_token(access_token),
            "refresh_token": _encrypt_token(refresh_token) if refresh_token else None,
            "expires_at": now + timedelta(seconds=expires_in),
            "scope": scope,
            "account_name": account_name,
            "connected_at": now,
            "updated_at": now,
        }},
        upsert=True,
    )
    await db.users.update_one(
        {"user_id": user_id},
        {"$addToSet": {"platforms_connected": platform}},
    )


def _build_login_redirect(user_id: str, email: str) -> RedirectResponse:
    """Create JWT, set cookies, redirect to frontend dashboard."""
    jwt_token = create_jwt_token(user_id, email)
    csrf_value = secrets.token_urlsafe(32)
    dest = f"{FRONTEND_URL}/dashboard?token={quote(jwt_token, safe='')}"
    response = RedirectResponse(url=dest, status_code=302)
    set_auth_cookie(response, jwt_token)
    set_csrf_cookie(response, csrf_value)
    return response


# ============ LINKEDIN LOGIN ============

@router.get("/linkedin")
async def linkedin_login(request: Request):
    """Initiate LinkedIn OAuth login flow."""
    if not _is_configured(LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET):
        raise HTTPException(status_code=503, detail="LinkedIn sign-in not configured")

    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({
        "state": state,
        "platform": "linkedin_login",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    })

    callback_url = f"{BACKEND_URL}/api/auth/linkedin/callback"
    params = urlencode({
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": callback_url,
        "state": state,
        "scope": LINKEDIN_LOGIN_SCOPES,
    })
    return RedirectResponse(
        url=f"https://www.linkedin.com/oauth/v2/authorization?{params}",
        status_code=302,
    )


@router.get("/linkedin/callback")
async def linkedin_callback(code: str = "", state: str = "", error: str = ""):
    """Handle LinkedIn OAuth callback — login or register user."""
    err_redirect = f"{FRONTEND_URL}/auth?error=linkedin_failed"

    if error or not code:
        logger.warning("LinkedIn OAuth error: %s", error)
        return RedirectResponse(url=err_redirect, status_code=302)

    # Verify state
    oauth_state = await db.oauth_states.find_one_and_delete({
        "state": state,
        "platform": "linkedin_login",
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    if not oauth_state:
        return RedirectResponse(url=f"{err_redirect}&reason=invalid_state", status_code=302)

    try:
        callback_url = f"{BACKEND_URL}/api/auth/linkedin/callback"
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_resp = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": LINKEDIN_CLIENT_ID,
                    "client_secret": LINKEDIN_CLIENT_SECRET,
                    "redirect_uri": callback_url,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            if token_resp.status_code != 200:
                logger.error("LinkedIn token exchange failed: %s", token_resp.text)
                return RedirectResponse(url=err_redirect, status_code=302)

            token_data = token_resp.json()
            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            refresh_token = token_data.get("refresh_token")

            # Get user profile via OpenID userinfo
            profile_resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15.0,
            )
            if profile_resp.status_code != 200:
                logger.error("LinkedIn userinfo failed: %s", profile_resp.text)
                return RedirectResponse(url=err_redirect, status_code=302)

            profile = profile_resp.json()
            email = profile.get("email")
            if not email:
                return RedirectResponse(
                    url=f"{err_redirect}&reason=no_email", status_code=302
                )

            name = profile.get("name", profile.get("given_name", email.split("@")[0]))
            picture = profile.get("picture")

    except Exception as e:
        logger.error("LinkedIn OAuth error: %s", e)
        return RedirectResponse(url=err_redirect, status_code=302)

    # Find or create user
    user_id = await _find_or_create_user(email, name, picture, "linkedin")

    # Store platform token for publishing
    await _store_platform_token(
        user_id, "linkedin", access_token, refresh_token,
        expires_in, name, LINKEDIN_LOGIN_SCOPES,
    )

    return _build_login_redirect(user_id, email)


# ============ X (TWITTER) LOGIN ============

def _generate_pkce():
    """Generate PKCE code verifier and challenge."""
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


@router.get("/x")
async def x_login(request: Request):
    """Initiate X (Twitter) OAuth 2.0 login with PKCE."""
    if not _is_configured(TWITTER_API_KEY, TWITTER_API_SECRET):
        raise HTTPException(status_code=503, detail="X sign-in not configured")

    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce()

    await db.oauth_states.insert_one({
        "state": state,
        "platform": "x_login",
        "code_verifier": code_verifier,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    })

    callback_url = f"{BACKEND_URL}/api/auth/x/callback"
    params = urlencode({
        "response_type": "code",
        "client_id": TWITTER_API_KEY,
        "redirect_uri": callback_url,
        "scope": TWITTER_LOGIN_SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return RedirectResponse(
        url=f"https://twitter.com/i/oauth2/authorize?{params}",
        status_code=302,
    )


@router.get("/x/callback")
async def x_callback(code: str = "", state: str = "", error: str = ""):
    """Handle X (Twitter) OAuth callback — login or register user."""
    err_redirect = f"{FRONTEND_URL}/auth?error=x_failed"

    if error or not code:
        logger.warning("X OAuth error: %s", error)
        return RedirectResponse(url=err_redirect, status_code=302)

    oauth_state = await db.oauth_states.find_one_and_delete({
        "state": state,
        "platform": "x_login",
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    if not oauth_state:
        return RedirectResponse(url=f"{err_redirect}&reason=invalid_state", status_code=302)

    code_verifier = oauth_state["code_verifier"]

    try:
        callback_url = f"{BACKEND_URL}/api/auth/x/callback"
        async with httpx.AsyncClient() as client:
            # Exchange code for token (Basic auth with client_id:client_secret)
            auth_header = base64.b64encode(
                f"{TWITTER_API_KEY}:{TWITTER_API_SECRET}".encode()
            ).decode()

            token_resp = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_url,
                    "code_verifier": code_verifier,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {auth_header}",
                },
                timeout=30.0,
            )
            if token_resp.status_code != 200:
                logger.error("X token exchange failed: %s", token_resp.text)
                return RedirectResponse(url=err_redirect, status_code=302)

            token_data = token_resp.json()
            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 7200)

            # Get user profile
            me_resp = await client.get(
                "https://api.twitter.com/2/users/me",
                params={"user.fields": "name,username,profile_image_url"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15.0,
            )
            if me_resp.status_code != 200:
                logger.error("X user info failed: %s", me_resp.text)
                return RedirectResponse(url=err_redirect, status_code=302)

            user_data = me_resp.json().get("data", {})
            username = user_data.get("username", "")
            name = user_data.get("name", username)
            picture = user_data.get("profile_image_url")

            # X doesn't return email — use username@x.thook.ai as placeholder
            # If user already has account with same X username, we match by x_username
            email = None

    except Exception as e:
        logger.error("X OAuth error: %s", e)
        return RedirectResponse(url=err_redirect, status_code=302)

    # X doesn't provide email — look up by x_username first, then create
    existing = await db.users.find_one({"x_username": username}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        update_fields = {"name": name}
        if picture:
            update_fields["picture"] = picture
        await db.users.update_one({"user_id": user_id}, {"$set": update_fields})
        email = existing.get("email", f"{username}@x.thook.internal")
    else:
        # New user from X — create with placeholder email
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        email = f"{username}@x.thook.internal"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "auth_method": "x",
            "x_username": username,
            "plan": "starter",
            "subscription_tier": "starter",
            "credits": 200,
            "credit_allowance": 0,
            "credits_last_refresh": datetime.now(timezone.utc),
            "credits_refreshed_at": datetime.now(timezone.utc),
            "onboarding_completed": False,
            "platforms_connected": [],
            "created_at": datetime.now(timezone.utc),
        })

    # Store platform token for publishing
    await _store_platform_token(
        user_id, "x", access_token, refresh_token,
        expires_in, f"@{username}", TWITTER_LOGIN_SCOPES,
    )

    return _build_login_redirect(user_id, email)


# ============ AVAILABILITY CHECK ============

@router.get("/social/providers")
async def get_social_providers():
    """Return which social login providers are available."""
    return {
        "providers": {
            "google": settings.google.is_configured(),
            "linkedin": _is_configured(LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET),
            "x": _is_configured(TWITTER_API_KEY, TWITTER_API_SECRET),
        }
    }
