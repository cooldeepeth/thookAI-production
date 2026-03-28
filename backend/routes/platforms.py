"""Platform OAuth and Connection Routes for ThookAI.

Handles OAuth flows for:
- LinkedIn (OAuth 2.0)
- X/Twitter (OAuth 2.0 with PKCE)
- Instagram (Meta OAuth)
"""
import base64
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from cryptography.fernet import Fernet
import httpx

from database import db
from auth_utils import get_current_user
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/platforms", tags=["platforms"])

# Platform config from settings
LINKEDIN_CLIENT_ID = settings.platforms.linkedin_client_id or ''
LINKEDIN_CLIENT_SECRET = settings.platforms.linkedin_client_secret or ''
META_APP_ID = settings.platforms.meta_app_id or ''
META_APP_SECRET = settings.platforms.meta_app_secret or ''
TWITTER_API_KEY = settings.platforms.twitter_api_key or ''
TWITTER_API_SECRET = settings.platforms.twitter_api_secret or ''
ENCRYPTION_KEY = settings.platforms.encryption_key or Fernet.generate_key().decode()

# Frontend URL for redirects
FRONTEND_URL = settings.app.frontend_url
BACKEND_URL = settings.app.backend_url

# OAuth scopes
LINKEDIN_SCOPES = "openid profile email w_member_social"
TWITTER_SCOPES = "tweet.read tweet.write users.read offline.access"
INSTAGRAM_SCOPES = "instagram_basic,instagram_content_publish,pages_show_list"


def _valid_key(key: str) -> bool:
    """Check if API key is valid (not a placeholder)."""
    if not key:
        return False
    placeholders = ['placeholder', 'your_', 'xxx']
    return not any(key.lower().startswith(p) for p in placeholders)


def _get_cipher():
    """Get Fernet cipher for token encryption."""
    key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
    # Ensure key is valid Fernet key (32 bytes base64)
    if len(key) != 44:
        key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    return Fernet(key)


def _encrypt_token(token: str) -> str:
    """Encrypt OAuth token for storage."""
    cipher = _get_cipher()
    return cipher.encrypt(token.encode()).decode()


def _decrypt_token(encrypted_token: str) -> str:
    """Decrypt stored OAuth token."""
    cipher = _get_cipher()
    return cipher.decrypt(encrypted_token.encode()).decode()


def _generate_pkce():
    """Generate PKCE code verifier and challenge for Twitter OAuth."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    return code_verifier, code_challenge


# ============ PLATFORM STATUS ============

@router.get("/status")
async def get_platforms_status(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get status of all platform connections for the current user."""
    user_id = current_user["user_id"]
    
    # Get all tokens for user
    tokens = await db.platform_tokens.find(
        {"user_id": user_id},
        {"_id": 0, "platform": 1, "account_name": 1, "expires_at": 1, "connected_at": 1, "scope": 1}
    ).to_list(10)
    
    # Build status for each platform
    platforms = {
        "linkedin": {"connected": False, "configured": _valid_key(LINKEDIN_CLIENT_ID)},
        "x": {"connected": False, "configured": _valid_key(TWITTER_API_KEY)},
        "instagram": {"connected": False, "configured": _valid_key(META_APP_ID)}
    }
    
    for token in tokens:
        platform = token.get("platform")
        if platform in platforms:
            expires_at = token.get("expires_at")
            is_valid = expires_at is None or expires_at > datetime.now(timezone.utc)
            
            platforms[platform] = {
                "connected": True,
                "configured": True,
                "account_name": token.get("account_name"),
                "connected_at": token.get("connected_at").isoformat() if token.get("connected_at") else None,
                "token_valid": is_valid,
                "needs_reconnect": not is_valid
            }
    
    return {
        "platforms": platforms,
        "total_connected": sum(1 for p in platforms.values() if p.get("connected"))
    }


# ============ LINKEDIN OAUTH ============

@router.get("/connect/linkedin")
async def connect_linkedin(request: Request, current_user: dict = Depends(get_current_user)):
    """Initiate LinkedIn OAuth flow."""
    if not _valid_key(LINKEDIN_CLIENT_ID):
        raise HTTPException(status_code=400, detail="LinkedIn OAuth not configured. Add LINKEDIN_CLIENT_ID to .env")
    
    # Store state for verification
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({
        "state": state,
        "user_id": current_user["user_id"],
        "platform": "linkedin",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    })
    
    # Build OAuth URL
    callback_url = f"{BACKEND_URL}/api/platforms/callback/linkedin"
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={callback_url}"
        f"&state={state}"
        f"&scope={LINKEDIN_SCOPES}"
    )
    
    return {"auth_url": auth_url, "state": state}


@router.get("/callback/linkedin")
async def callback_linkedin(code: str, state: str):
    """Handle LinkedIn OAuth callback."""
    # Verify state
    oauth_state = await db.oauth_states.find_one_and_delete({
        "state": state,
        "platform": "linkedin",
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    if not oauth_state:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=invalid_state")
    
    user_id = oauth_state["user_id"]
    
    try:
        # Exchange code for token
        callback_url = f"{BACKEND_URL}/api/platforms/callback/linkedin"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": LINKEDIN_CLIENT_ID,
                    "client_secret": LINKEDIN_CLIENT_SECRET,
                    "redirect_uri": callback_url
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"LinkedIn token exchange failed: {response.text}")
                return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=token_exchange_failed")
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            refresh_token = token_data.get("refresh_token")
            
            # Get user profile
            profile_response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15.0
            )
            
            account_name = "LinkedIn User"
            if profile_response.status_code == 200:
                profile = profile_response.json()
                account_name = profile.get("name", profile.get("given_name", "LinkedIn User"))
            
            # Store encrypted token
            now = datetime.now(timezone.utc)
            await db.platform_tokens.update_one(
                {"user_id": user_id, "platform": "linkedin"},
                {
                    "$set": {
                        "access_token": _encrypt_token(access_token),
                        "refresh_token": _encrypt_token(refresh_token) if refresh_token else None,
                        "expires_at": now + timedelta(seconds=expires_in),
                        "scope": LINKEDIN_SCOPES,
                        "account_name": account_name,
                        "connected_at": now,
                        "updated_at": now
                    }
                },
                upsert=True
            )
            
            # Update user's connected platforms
            await db.users.update_one(
                {"user_id": user_id},
                {"$addToSet": {"platforms_connected": "linkedin"}}
            )
            
            return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?success=linkedin")
    
    except Exception as e:
        logger.error(f"LinkedIn OAuth error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=connection_failed")


# ============ X/TWITTER OAUTH (PKCE) ============

@router.get("/connect/x")
async def connect_x(request: Request, current_user: dict = Depends(get_current_user)):
    """Initiate X/Twitter OAuth 2.0 PKCE flow."""
    if not _valid_key(TWITTER_API_KEY):
        raise HTTPException(status_code=400, detail="X OAuth not configured. Add TWITTER_API_KEY to .env")
    
    # Generate PKCE challenge
    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(32)
    
    # Store state and verifier
    await db.oauth_states.insert_one({
        "state": state,
        "user_id": current_user["user_id"],
        "platform": "x",
        "code_verifier": code_verifier,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    })
    
    callback_url = f"{BACKEND_URL}/api/platforms/callback/x"
    auth_url = (
        f"https://twitter.com/i/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={TWITTER_API_KEY}"
        f"&redirect_uri={callback_url}"
        f"&scope={TWITTER_SCOPES}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    
    return {"auth_url": auth_url, "state": state}


@router.get("/callback/x")
async def callback_x(code: str, state: str):
    """Handle X/Twitter OAuth callback."""
    oauth_state = await db.oauth_states.find_one_and_delete({
        "state": state,
        "platform": "x",
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    if not oauth_state:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=invalid_state")
    
    user_id = oauth_state["user_id"]
    code_verifier = oauth_state["code_verifier"]
    
    try:
        callback_url = f"{BACKEND_URL}/api/platforms/callback/x"
        
        # Basic auth header
        credentials = base64.b64encode(f"{TWITTER_API_KEY}:{TWITTER_API_SECRET}".encode()).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": TWITTER_API_KEY,
                    "redirect_uri": callback_url,
                    "code_verifier": code_verifier
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {credentials}"
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"X token exchange failed: {response.text}")
                return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=token_exchange_failed")
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 7200)
            
            # Get user info
            user_response = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15.0
            )
            
            account_name = "X User"
            if user_response.status_code == 200:
                user_data = user_response.json()
                account_name = f"@{user_data.get('data', {}).get('username', 'user')}"
            
            # Store encrypted token
            now = datetime.now(timezone.utc)
            await db.platform_tokens.update_one(
                {"user_id": user_id, "platform": "x"},
                {
                    "$set": {
                        "access_token": _encrypt_token(access_token),
                        "refresh_token": _encrypt_token(refresh_token) if refresh_token else None,
                        "expires_at": now + timedelta(seconds=expires_in),
                        "scope": TWITTER_SCOPES,
                        "account_name": account_name,
                        "connected_at": now,
                        "updated_at": now
                    }
                },
                upsert=True
            )
            
            await db.users.update_one(
                {"user_id": user_id},
                {"$addToSet": {"platforms_connected": "x"}}
            )
            
            return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?success=x")
    
    except Exception as e:
        logger.error(f"X OAuth error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=connection_failed")


# ============ INSTAGRAM (META) OAUTH ============

@router.get("/connect/instagram")
async def connect_instagram(request: Request, current_user: dict = Depends(get_current_user)):
    """Initiate Instagram/Meta OAuth flow."""
    if not _valid_key(META_APP_ID):
        raise HTTPException(status_code=400, detail="Instagram OAuth not configured. Add META_APP_ID to .env")
    
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({
        "state": state,
        "user_id": current_user["user_id"],
        "platform": "instagram",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    })
    
    callback_url = f"{BACKEND_URL}/api/platforms/callback/instagram"
    auth_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth"
        f"?client_id={META_APP_ID}"
        f"&redirect_uri={callback_url}"
        f"&scope={INSTAGRAM_SCOPES}"
        f"&state={state}"
        f"&response_type=code"
    )
    
    return {"auth_url": auth_url, "state": state}


@router.get("/callback/instagram")
async def callback_instagram(code: str, state: str):
    """Handle Instagram/Meta OAuth callback."""
    oauth_state = await db.oauth_states.find_one_and_delete({
        "state": state,
        "platform": "instagram",
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    if not oauth_state:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=invalid_state")
    
    user_id = oauth_state["user_id"]
    
    try:
        callback_url = f"{BACKEND_URL}/api/platforms/callback/instagram"
        
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "client_id": META_APP_ID,
                    "client_secret": META_APP_SECRET,
                    "redirect_uri": callback_url,
                    "code": code
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Instagram token exchange failed: {response.text}")
                return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=token_exchange_failed")
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            # Get long-lived token
            long_lived_response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": META_APP_ID,
                    "client_secret": META_APP_SECRET,
                    "fb_exchange_token": access_token
                },
                timeout=30.0
            )
            
            if long_lived_response.status_code == 200:
                long_lived_data = long_lived_response.json()
                access_token = long_lived_data.get("access_token", access_token)
                expires_in = long_lived_data.get("expires_in", 5184000)  # 60 days default
            else:
                expires_in = 3600
            
            # Get Instagram business account
            pages_response = await client.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={"access_token": access_token},
                timeout=15.0
            )
            
            account_name = "Instagram Account"
            instagram_account_id = None
            
            if pages_response.status_code == 200:
                pages = pages_response.json().get("data", [])
                if pages:
                    page = pages[0]
                    page_token = page.get("access_token")
                    page_id = page.get("id")
                    
                    # Get Instagram business account
                    ig_response = await client.get(
                        f"https://graph.facebook.com/v18.0/{page_id}",
                        params={
                            "fields": "instagram_business_account",
                            "access_token": page_token
                        },
                        timeout=15.0
                    )
                    
                    if ig_response.status_code == 200:
                        ig_data = ig_response.json()
                        instagram_account_id = ig_data.get("instagram_business_account", {}).get("id")
                        account_name = page.get("name", "Instagram Account")
            
            # Store token
            now = datetime.now(timezone.utc)
            await db.platform_tokens.update_one(
                {"user_id": user_id, "platform": "instagram"},
                {
                    "$set": {
                        "access_token": _encrypt_token(access_token),
                        "instagram_account_id": instagram_account_id,
                        "expires_at": now + timedelta(seconds=expires_in),
                        "scope": INSTAGRAM_SCOPES,
                        "account_name": account_name,
                        "connected_at": now,
                        "updated_at": now
                    }
                },
                upsert=True
            )
            
            await db.users.update_one(
                {"user_id": user_id},
                {"$addToSet": {"platforms_connected": "instagram"}}
            )
            
            return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?success=instagram")
    
    except Exception as e:
        logger.error(f"Instagram OAuth error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/connections?error=connection_failed")


# ============ DISCONNECT ============

@router.delete("/disconnect/{platform}")
async def disconnect_platform(platform: str, current_user: dict = Depends(get_current_user)):
    """Disconnect a platform and revoke tokens."""
    user_id = current_user["user_id"]
    
    if platform not in ["linkedin", "x", "instagram"]:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    # Delete token
    result = await db.platform_tokens.delete_one({
        "user_id": user_id,
        "platform": platform
    })
    
    # Remove from user's connected platforms
    await db.users.update_one(
        {"user_id": user_id},
        {"$pull": {"platforms_connected": platform}}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Platform not connected")
    
    return {"message": f"Disconnected from {platform}", "platform": platform}


# ============ HELPER FUNCTIONS ============

async def get_platform_token(user_id: str, platform: str) -> Optional[str]:
    """Get decrypted access token for a platform."""
    token_doc = await db.platform_tokens.find_one({
        "user_id": user_id,
        "platform": platform
    })
    
    if not token_doc:
        return None
    
    # Check expiry
    expires_at = token_doc.get("expires_at")
    if expires_at and expires_at < datetime.now(timezone.utc):
        # Try refresh if available
        refresh_token = token_doc.get("refresh_token")
        if refresh_token:
            new_token = await _refresh_token(user_id, platform, _decrypt_token(refresh_token))
            if new_token:
                return new_token
        return None
    
    return _decrypt_token(token_doc["access_token"])


async def _refresh_token(user_id: str, platform: str, refresh_token: str) -> Optional[str]:
    """Refresh an expired token."""
    try:
        async with httpx.AsyncClient() as client:
            if platform == "linkedin":
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": LINKEDIN_CLIENT_ID,
                        "client_secret": LINKEDIN_CLIENT_SECRET
                    },
                    timeout=30.0
                )
            elif platform == "x":
                credentials = base64.b64encode(f"{TWITTER_API_KEY}:{TWITTER_API_SECRET}".encode()).decode()
                response = await client.post(
                    "https://api.twitter.com/2/oauth2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": TWITTER_API_KEY
                    },
                    headers={"Authorization": f"Basic {credentials}"},
                    timeout=30.0
                )
            else:
                return None
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get("access_token")
                new_refresh_token = data.get("refresh_token", refresh_token)
                expires_in = data.get("expires_in", 3600)
                
                now = datetime.now(timezone.utc)
                await db.platform_tokens.update_one(
                    {"user_id": user_id, "platform": platform},
                    {
                        "$set": {
                            "access_token": _encrypt_token(new_access_token),
                            "refresh_token": _encrypt_token(new_refresh_token),
                            "expires_at": now + timedelta(seconds=expires_in),
                            "updated_at": now
                        }
                    }
                )
                return new_access_token
    except Exception as e:
        logger.error(f"Token refresh failed for {platform}: {e}")
    
    return None
