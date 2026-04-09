import logging
import secrets

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timezone, timedelta
from pymongo import WriteConcern
import uuid
from database import db
from auth_utils import hash_password, verify_password, get_current_user
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

ALGORITHM = "HS256"


def _jwt_secret() -> str:
    """Return JWT secret. Raises if not configured — never fall back to a default."""
    secret = settings.security.jwt_secret_key
    if not secret:
        raise ValueError("JWT_SECRET_KEY not configured — refusing to start with no secret")
    return secret


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


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


@router.get("/debug-hash")
async def debug_hash():
    """Temporary debug endpoint — remove after fixing bcrypt."""
    try:
        h = hash_password("test123")
        ok = verify_password("test123", h)
        return {"hash": h[:20] + "...", "verify": ok, "engine": "direct-bcrypt"}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


@router.post("/debug-register")
async def debug_register(response: Response):
    """Temporary: mimics register flow step by step to find crash."""
    import traceback
    steps = {}
    try:
        steps["1_hash"] = "start"
        h = hash_password("test123")
        steps["1_hash"] = "ok"

        steps["2_jwt"] = "start"
        token = create_jwt_token("user_debug123", "debug@test.com")
        steps["2_jwt"] = "ok"

        steps["3_csrf"] = "start"
        csrf_value = secrets.token_urlsafe(32)
        steps["3_csrf"] = "ok"

        steps["4_cookie_auth"] = "start"
        set_auth_cookie(response, token)
        steps["4_cookie_auth"] = "ok"

        steps["5_cookie_csrf"] = "start"
        set_csrf_cookie(response, csrf_value)
        steps["5_cookie_csrf"] = "ok"

        steps["6_db_find"] = "start"
        await db.users.find_one({"email": "nonexistent@debug.test"})
        steps["6_db_find"] = "ok"

        steps["7_write_concern"] = "start"
        users_wm = db.users.with_options(write_concern=WriteConcern("majority"))
        steps["7_write_concern"] = "ok"

        steps["8_db_insert"] = "start"
        test_doc = {
            "user_id": f"debug_{uuid.uuid4().hex[:8]}",
            "email": f"debug-{uuid.uuid4().hex[:6]}@test.internal",
            "name": "debug", "auth_method": "email",
            "hashed_password": h, "_debug": True,
            "created_at": datetime.now(timezone.utc),
        }
        result = await users_wm.insert_one(test_doc)
        steps["8_db_insert"] = f"ok:{result.inserted_id}"

        # Clean up debug doc
        await db.users.delete_one({"_debug": True, "user_id": test_doc["user_id"]})
        steps["9_cleanup"] = "ok"

        return {"status": "all_ok", "steps": steps, "token_len": len(token)}
    except Exception as e:
        steps["error"] = f"{type(e).__name__}: {e}"
        steps["trace"] = traceback.format_exc()[-500:]
        return {"status": "failed", "steps": steps}


@router.post("/register")
async def register(data: RegisterRequest, response: Response):
    import traceback as _tb
    try:
        if await db.users.find_one({"email": data.email}, {"_id": 0}):
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "user_id": user_id, "email": data.email, "name": data.name,
            "picture": None, "auth_method": "email",
            "hashed_password": hash_password(data.password),
            "plan": "starter", "subscription_tier": "starter",
            "credits": 200, "credit_allowance": 0,
            "credits_last_refresh": datetime.now(timezone.utc).isoformat(),
            "credits_refreshed_at": datetime.now(timezone.utc).isoformat(),
            "onboarding_completed": False, "platforms_connected": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        users_wmajority = db.users.with_options(write_concern=WriteConcern("majority"))
        await users_wmajority.insert_one(user)
        token = create_jwt_token(user_id, data.email)
        csrf_value = secrets.token_urlsafe(32)
        set_auth_cookie(response, token)
        set_csrf_cookie(response, csrf_value)
        return {**safe_user(user), "token": token, "csrf_token": csrf_value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Register crash: %s\n%s", e, _tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Registration failed: {type(e).__name__}: {e}")


@router.post("/login")
async def login(data: LoginRequest, response: Response):
    import traceback as _tb
    try:
        user = await db.users.find_one({"email": data.email}, {"_id": 0})
        if not user or user.get("auth_method") == "google":
            logger.warning("Failed login attempt: email=%s (user not found or wrong auth method)", data.email)
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not verify_password(data.password, user.get("hashed_password", "")):
            logger.warning("Failed login attempt: email=%s (wrong password)", data.email)
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_jwt_token(user["user_id"], data.email)
        csrf_value = secrets.token_urlsafe(32)
        set_auth_cookie(response, token)
        set_csrf_cookie(response, csrf_value)
        return {**safe_user(user), "token": token, "csrf_token": csrf_value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login crash: %s\n%s", e, _tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Login failed: {type(e).__name__}: {e}")


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
