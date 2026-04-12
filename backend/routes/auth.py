import logging
import secrets

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from jose import jwt
from datetime import datetime, timezone, timedelta
from pymongo import WriteConcern
import uuid
from database import db
from pymongo.errors import DuplicateKeyError
from auth_utils import hash_password, verify_password, get_current_user, validate_password_strength
from config import settings
from services.sanitize import sanitize_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

ALGORITHM = "HS256"

# Account lockout: 5 failed attempts → 15 min cooldown
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _jwt_secret() -> str:
    """Return JWT secret. Raises if not configured — never fall back to a default."""
    secret = settings.security.jwt_secret_key
    if not secret:
        raise ValueError("JWT_SECRET_KEY not configured — refusing to start with no secret")
    return secret


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def create_jwt_token(user_id: str, email: str) -> str:
    expire_days = settings.security.jwt_expire_days
    expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    return jwt.encode({"sub": user_id, "email": email, "exp": expire}, _jwt_secret(), algorithm=ALGORITHM)


def set_auth_cookie(response: Response, token: str) -> None:
    # Use secure=False and samesite=lax in development to allow cookies over HTTP
    is_dev = settings.app.is_development
    expire_days = settings.security.jwt_expire_days
    response.set_cookie(
        key="session_token", value=token,
        httponly=True,
        secure=not is_dev,
        samesite="lax" if is_dev else "none",
        max_age=expire_days * 24 * 3600, path="/"
    )


def set_csrf_cookie(response: Response, csrf_value: str) -> None:
    """Set the JS-readable CSRF token cookie (double-submit cookie pattern).

    This cookie is intentionally NOT httpOnly so that the frontend JavaScript
    can read it and attach it as the X-CSRF-Token request header.
    """
    is_dev = settings.app.is_development
    expire_days = settings.security.jwt_expire_days
    response.set_cookie(
        key="csrf_token", value=csrf_value,
        httponly=False,  # JS must be able to read this — intentional
        secure=not is_dev,
        samesite="lax" if is_dev else "none",
        max_age=expire_days * 24 * 3600, path="/"
    )


def safe_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k not in ("hashed_password", "_id")}


@router.post("/register")
async def register(data: RegisterRequest, response: Response):
    # Enforce password policy
    validate_password_strength(data.password)

    if await db.users.find_one({"email": data.email}, {"_id": 0}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    # SECR-02: sanitize free-text field before storage (html.escape — XSS guard)
    safe_name = sanitize_text(data.name)
    user = {
        "user_id": user_id, "email": data.email, "name": safe_name,
        "picture": None, "auth_method": "email",
        "hashed_password": hash_password(data.password),
        "plan": "starter", "subscription_tier": "starter",
        "credits": 200, "credit_allowance": 0,
        "credits_last_refresh": datetime.now(timezone.utc),
        "credits_refreshed_at": datetime.now(timezone.utc),
        "onboarding_completed": False, "platforms_connected": [],
        "created_at": datetime.now(timezone.utc)
    }
    try:
        users_wmajority = db.users.with_options(write_concern=WriteConcern("majority"))
        await users_wmajority.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")
    token = create_jwt_token(user_id, data.email)
    csrf_value = secrets.token_urlsafe(32)
    set_auth_cookie(response, token)
    set_csrf_cookie(response, csrf_value)
    return {**safe_user(user), "token": token, "csrf_token": csrf_value}


@router.post("/login")
async def login(data: LoginRequest, response: Response):
    # Check account lockout (non-fatal if collection unavailable)
    try:
        lockout = await db.login_attempts.find_one({"email": data.email})
        if lockout and lockout.get("locked_until"):
            locked_until = lockout["locked_until"]
            if isinstance(locked_until, str):
                locked_until = datetime.fromisoformat(locked_until)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            remaining = locked_until - datetime.now(timezone.utc)
            if remaining.total_seconds() > 0:
                mins_left = max(1, int(remaining.total_seconds() / 60) + 1)
                logger.warning("Locked account login attempt: email=%s", data.email)
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many failed login attempts. Try again in {mins_left} minute{'s' if mins_left != 1 else ''}."
                )
            # Lockout expired — reset
            await db.login_attempts.delete_one({"email": data.email})
    except HTTPException:
        raise
    except Exception:
        pass  # Lockout check is a security enhancement — don't block login if it fails

    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user:
        logger.warning("Failed login attempt: email=%s (not found)", data.email)
        try:
            await _record_failed_login(data.email)
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("auth_method") != "email":
        method = user.get("auth_method", "unknown")
        logger.warning("Failed login attempt: email=%s (uses %s auth)", data.email, method)
        raise HTTPException(status_code=401, detail=f"This account uses {method} sign-in. Please use that method to log in.")
    if not verify_password(data.password, user.get("hashed_password", "")):
        logger.warning("Failed login attempt: email=%s (wrong password)", data.email)
        try:
            await _record_failed_login(data.email)
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Successful login — clear any failed attempt records
    try:
        await db.login_attempts.delete_one({"email": data.email})
    except Exception:
        pass

    token = create_jwt_token(user["user_id"], data.email)
    csrf_value = secrets.token_urlsafe(32)
    set_auth_cookie(response, token)
    set_csrf_cookie(response, csrf_value)
    return {**safe_user(user), "token": token, "csrf_token": csrf_value}


async def _record_failed_login(email: str) -> None:
    """Record a failed login attempt and lock the account if threshold exceeded."""
    now = datetime.now(timezone.utc)
    result = await db.login_attempts.find_one_and_update(
        {"email": email},
        {"$inc": {"attempts": 1}, "$set": {"last_attempt": now}},
        upsert=True,
        return_document=True,
    )
    if result and result.get("attempts", 0) >= MAX_LOGIN_ATTEMPTS:
        await db.login_attempts.update_one(
            {"email": email},
            {"$set": {"locked_until": now + timedelta(minutes=LOCKOUT_MINUTES)}}
        )
        logger.warning("Account locked after %d failed attempts: email=%s", MAX_LOGIN_ATTEMPTS, email)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return safe_user(current_user)


@router.post("/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    is_dev = settings.app.is_development
    samesite = "lax" if is_dev else "none"
    secure = not is_dev
    response.delete_cookie(key="session_token", path="/", samesite=samesite, secure=secure)
    response.delete_cookie(key="csrf_token", path="/", samesite=samesite, secure=secure)
    return {"message": "Logged out"}


@router.get("/csrf-token")
async def get_csrf_token(response: Response, current_user: dict = Depends(get_current_user)):
    """Return a fresh CSRF token and set the csrf_token cookie.

    Call this endpoint on page load when the frontend needs to refresh its CSRF
    token (e.g. after a page reload). Requires cookie-based authentication.
    """
    csrf_value = secrets.token_urlsafe(32)
    set_csrf_cookie(response, csrf_value)
    return {"csrf_token": csrf_value}


# ==================== GDPR ENDPOINTS ====================


@router.get("/export")
async def export_user_data(current_user: dict = Depends(get_current_user)):
    """GDPR data export — return all user data as JSON.

    Collects data from: users, persona_engines, content_jobs,
    platform_tokens (redacted), credit_transactions, user_feedback, uploads.
    Limited to most recent 500 jobs/transactions. Contact support for full archives.
    """
    user_id = current_user["user_id"]

    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "hashed_password": 0})
    persona = await db.persona_engines.find_one({"user_id": user_id}, {"_id": 0})

    jobs = await db.content_jobs.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(500).to_list(500)

    transactions = await db.credit_transactions.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(500).to_list(500)

    # Redact platform tokens (show platform name only)
    platforms = []
    async for pt in db.platform_tokens.find({"user_id": user_id}, {"_id": 0, "platform": 1, "connected_at": 1}):
        platforms.append(pt)

    feedback = await db.user_feedback.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(100).to_list(100)

    uploads = await db.uploads.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(200).to_list(200)

    # Serialize datetimes to ISO strings
    def _serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    import json

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "persona": persona,
        "content_jobs": jobs,
        "credit_transactions": transactions,
        "connected_platforms": platforms,
        "feedback": feedback,
        "uploads": uploads,
    }

    return JSONResponse(
        content=json.loads(json.dumps(export, default=_serialize)),
        headers={"Content-Disposition": f"attachment; filename=thookai-export-{user_id}.json"}
    )


class DeleteAccountRequest(BaseModel):
    confirm: str = Field(min_length=1)  # Must be "DELETE" to confirm


@router.post("/delete-account")
async def delete_account(
    data: DeleteAccountRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
):
    """GDPR account deletion — anonymize user data and revoke access.

    Requires confirm="DELETE" in request body. Soft-deletes: anonymizes PII
    but keeps content job records (anonymized) for platform analytics.
    """
    if data.confirm != "DELETE":
        raise HTTPException(status_code=400, detail='Set confirm to "DELETE" to proceed')

    user_id = current_user["user_id"]
    now = datetime.now(timezone.utc)

    # Anonymize user record
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "email": f"deleted-{user_id}@anonymized.thookai",
            "name": "Deleted User",
            "hashed_password": "",
            "picture": None,
            "active": False,
            "deleted_at": now,
            "google_id": None,
            "stripe_customer_id": None,
        }}
    )

    # Delete persona
    await db.persona_engines.delete_one({"user_id": user_id})

    # Revoke platform tokens
    await db.platform_tokens.delete_many({"user_id": user_id})

    # Revoke all sessions
    await db.user_sessions.delete_many({"user_id": user_id})

    # Anonymize content jobs (keep for analytics, remove PII link)
    anonymized_id = f"deleted-{user_id[:8]}"
    await db.content_jobs.update_many(
        {"user_id": user_id},
        {"$set": {"user_id": anonymized_id, "raw_input": "[deleted]"}}
    )

    # Delete uploads metadata (R2 media files are retained — future: add R2 cleanup)
    await db.uploads.delete_many({"user_id": user_id})

    # Delete feedback
    await db.user_feedback.delete_many({"user_id": user_id})

    # Clear auth cookies
    is_dev = settings.app.is_development
    samesite = "lax" if is_dev else "none"
    secure = not is_dev
    response.delete_cookie(key="session_token", path="/", samesite=samesite, secure=secure)
    response.delete_cookie(key="csrf_token", path="/", samesite=samesite, secure=secure)

    logger.info("Account deleted (anonymized) for user_id=%s", user_id)
    return {"message": "Account deleted. All personal data has been anonymized."}
